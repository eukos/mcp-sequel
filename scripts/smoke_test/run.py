#!/usr/bin/env python3
"""Smoke-test mcp-sequel installed via uvx in clean Docker containers.

    scripts/smoke_test/run.py pre-release   build a wheel from the working tree and test it
    scripts/smoke_test/run.py release       test mcp-sequel==<pyproject version> as published on PyPI

Options:
    --platform <p>     linux/arm64, linux/amd64, native (host only) or all (default: all =
                       both architectures; the non-native one runs under emulation and is slower)
    --pythons "<list>" space-separated versions (default: 3.10 3.11 3.12 3.13 3.14)
    --jobs N           containers running at once (default: 2)

Every (platform, python) combination is one job in a shared pool. Each container gets an
isolated $HOME with a throwaway SQLite connection ("smoke"), talks to the server over stdio
(see in_container.sh) and is removed afterwards. Images are pulled up front (sequentially) so pool
workers never race on a pull. Images this script pulled are removed on exit; images that were
already present are left alone.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HERE = Path(__file__).resolve().parent
DEFAULT_PYTHONS = "3.10 3.11 3.12 3.13 3.14"


def die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def docker(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=check
    )


def image_for(py: str) -> str:
    return f"ghcr.io/astral-sh/uv:python{py}-bookworm-slim"


def native_platform() -> str:
    arch = docker("info", "--format", "{{.Architecture}}").stdout.strip()
    return "linux/arm64" if arch in ("aarch64", "arm64") else "linux/amd64"


def read_version() -> str:
    m = re.search(r'^version = "(.*)"', (ROOT / "pyproject.toml").read_text(), re.M)
    if not m:
        die("could not read version from pyproject.toml")
    return m.group(1)


def has_image(image: str, platform: str) -> bool:
    """Whether the image is present locally for this platform."""
    fmt = ["-f", "{{.Os}}/{{.Architecture}} {{.Id}}", image]
    # With the containerd image store a plain inspect returns the multi-platform
    # index, so ask for this platform explicitly (older engines lack the flag).
    r = docker("image", "inspect", "--platform", platform, *fmt)
    if r.returncode != 0 and "unknown flag" in r.stderr:
        r = docker("image", "inspect", *fmt)
    if r.returncode != 0:
        return False
    plat, _, _ = r.stdout.strip().partition(" ")
    return plat == platform


def ensure_image(image: str, platform: str, pulled: set[str]) -> None:
    if has_image(image, platform):
        return
    print(f"==> pulling {image} ({platform})", flush=True)
    r = docker("pull", "--platform", platform, image)
    if r.returncode != 0:
        die(f"failed to pull {image} ({platform}):\n{r.stderr}")
    if not has_image(image, platform):
        die(f"{image} ({platform}) not found locally after pull")
    pulled.add(image)


class Job:
    def __init__(self, platform: str, py: str, image: str, name: str) -> None:
        self.platform = platform
        self.py = py
        self.image = image
        self.name = name
        self.label = f"{platform} python {py}"
        self.ok = False
        self.log = ""
        self.seconds = 0.0


def run_job(job: Job, mode: str, spec: str, expected: str, mounts: list[str]) -> Job:
    start = time.monotonic()
    r = docker(
        "run", "--rm", "--name", job.name, "--platform", job.platform,
        *mounts,
        "-v", f"{HERE}:/smoke:ro",
        "-e", f"SPEC={spec}", "-e", f"PYV={job.py}", "-e", f"EXPECTED={expected}",
        job.image, "bash", "/smoke/in_container.sh",
    )  # fmt: skip
    job.seconds = time.monotonic() - start
    job.ok = r.returncode == 0
    job.log = r.stdout + r.stderr
    return job


def main() -> int:
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("mode", choices=["pre-release", "release"])
    ap.add_argument("--platform", default="all")
    ap.add_argument("--pythons", default=DEFAULT_PYTHONS)
    ap.add_argument("--jobs", type=int, default=2)
    args = ap.parse_args()
    if args.jobs < 1:
        die("--jobs must be >= 1")

    version = read_version()
    if docker("info").returncode != 0:
        die("docker daemon is not running")

    mounts: list[str] = []
    if args.mode == "pre-release":
        print(f"==> building wheel for {version}", flush=True)
        wheel = f"mcp_sequel-{version}-py3-none-any.whl"
        for old in (ROOT / "dist").glob(f"mcp_sequel-{version}-*.whl"):
            old.unlink()
        subprocess.run(["uv", "build", "--wheel", "-q"], cwd=ROOT, check=True)
        if not (ROOT / "dist" / wheel).is_file():
            die(f"expected dist/{wheel} was not built")
        spec = f"/dist/{wheel}"
        mounts = ["-v", f"{ROOT / 'dist'}:/dist:ro"]
    else:
        spec = f"mcp-sequel=={version}"

    native = native_platform()
    if args.platform == "all":
        platforms = ["linux/arm64", "linux/amd64"]
    elif args.platform == "native":
        platforms = [native]
    else:
        platforms = [args.platform]
    pythons = args.pythons.split()

    pulled: set[str] = set()
    jobs: list[Job] = []
    try:
        for plat in platforms:
            for py in pythons:
                ensure_image(image_for(py), plat, pulled)

        tag = f"smoke-{int(time.time())}"
        for plat in platforms:
            for py in pythons:
                name = f"{tag}-{plat.replace('/', '_')}-py{py}"
                jobs.append(Job(plat, py, image_for(py), name))

        # slow (emulated) jobs go first so they don't end up alone at the tail
        queue = sorted(jobs, key=lambda j: j.platform == native)
        print(f"==> running {len(jobs)} jobs, {args.jobs} at a time", flush=True)
        try:
            with ThreadPoolExecutor(max_workers=args.jobs) as ex:
                futs = [
                    ex.submit(run_job, j, args.mode, spec, version, mounts)
                    for j in queue
                ]
                for f in as_completed(futs):
                    j = f.result()
                    print(
                        f"    {'PASS' if j.ok else 'FAIL'}  {j.label}  ({j.seconds:.0f}s)",
                        flush=True,
                    )
        except KeyboardInterrupt:
            for j in jobs:
                docker("kill", j.name)
            raise
    finally:
        for image in pulled:
            docker("rmi", image)

    for j in jobs:  # original order: platform, then python
        print(f"\n==> {j.label} ({args.mode}, {spec})")
        if j.ok:
            print("\n".join(
                ln for ln in j.log.splitlines()
                if ln.startswith(("python", "  ok"))
            ))  # fmt: skip
        else:
            print(j.log)

    print(f"\n== smoke summary: {args.mode} {version} ==")
    for j in jobs:
        print(f"{j.label}  {'PASS' if j.ok else 'FAIL'}")
    return 0 if all(j.ok for j in jobs) else 1


if __name__ == "__main__":
    sys.exit(main())
