import httpx
import pytest
import yaml
from deckhand.plugin_api import PluginContext
from deckhand.plugins import (
    PluginActivation,
    PluginConfiguration,
    PluginLock,
    PluginLockEntry,
    PluginManager,
)

from dh_http_status.plugin import HttpEndpoint, HttpStatusProvider, create_plugin


def test_manifest_uses_ecosystem_namespace() -> None:
    manifest = create_plugin().manifest
    assert manifest.id == "dh-http-status"
    assert manifest.api_version == 1
    assert manifest.permissions.mutation is False


def test_repository_manifest_matches_runtime_manifest() -> None:
    with open("deckhand-plugin.yaml", encoding="utf-8") as manifest_file:
        document = yaml.safe_load(manifest_file)
    assert document == create_plugin().manifest.model_dump(mode="json")


def test_plugin_builds_logically_named_providers() -> None:
    contribution = create_plugin().build(
        PluginContext(
            config={
                "endpoints": {
                    "example": {
                        "base_url": "https://status.example.invalid",
                        "health_path": "/ready",
                    }
                }
            }
        )
    )
    assert list(contribution.status_providers) == ["example"]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://user:password@example.invalid",
        "relative/path",
        "https://example.invalid/path?secret=value",
    ],
)
def test_endpoint_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        HttpEndpoint(base_url=url)


@pytest.mark.asyncio
async def test_provider_normalizes_healthy_response() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(204))
    provider = HttpStatusProvider(
        HttpEndpoint(base_url="https://status.example.invalid", health_path="/ready"),
        transport=transport,
    )
    result = await provider.observe()
    assert result.state == "healthy"
    assert result.details == {"status_code": 204}


def test_core_discovers_and_loads_installed_plugin() -> None:
    loaded = PluginManager().load(
        PluginConfiguration(
            plugins={
                "dh-core": PluginActivation(),
                "dh-http-status": PluginActivation(
                    config={
                        "endpoints": {"example": {"base_url": "https://status.example.invalid"}}
                    }
                ),
            }
        ),
        PluginLock(
            plugins=[
                PluginLockEntry(id="dh-core", version="0.2.0", source="builtin"),
                PluginLockEntry(id="dh-http-status", version="0.1.0", source="python"),
            ]
        ),
        allow_external=True,
    )
    assert [manifest.id for manifest in loaded.manifests] == ["dh-core", "dh-http-status"]
    assert set(loaded.status.providers) == {"example"}
