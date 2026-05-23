from importlib.metadata import PackageNotFoundError

import mcp_sequel.server as server


def test_get_version_returns_installed_version(monkeypatch):
    monkeypatch.setattr(server, "version", lambda pkg: "1.2.3")

    assert server.get_version() == "1.2.3"


def test_get_version_falls_back_when_metadata_missing(monkeypatch):
    def missing_version(pkg):
        raise PackageNotFoundError(pkg)

    monkeypatch.setattr(server, "version", missing_version)

    assert server.get_version() == "unknown"
