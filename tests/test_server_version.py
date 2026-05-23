from importlib.metadata import PackageNotFoundError

import mcp_sequel.server as server


def test_get_package_version_reads_installed_metadata(monkeypatch):
    monkeypatch.setattr(server, "version", lambda package_name: "1.2.3")

    assert server._get_package_version() == "1.2.3"


def test_get_package_version_falls_back_when_metadata_missing(monkeypatch):
    def missing_version(package_name):
        raise PackageNotFoundError(package_name)

    monkeypatch.setattr(server, "version", missing_version)

    assert server._get_package_version() == "unknown"


def test_get_version_tool_returns_package_version(monkeypatch):
    monkeypatch.setattr(server, "_get_package_version", lambda: "1.2.3")

    assert server.get_version() == "1.2.3"
