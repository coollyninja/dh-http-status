from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from deckhand.models import StatusValue, StrictModel
from deckhand.plugin_api import (
    DeckhandPlugin,
    PluginContext,
    PluginContribution,
    PluginManifest,
    PluginPermissions,
)
from pydantic import Field, field_validator


class HttpEndpoint(StrictModel):
    base_url: str
    health_path: str = "/"
    authorization_file: Path | None = None
    verify_tls: bool = True
    timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    stale_after_seconds: int = Field(default=30, ge=1, le=3600)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("base_url must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password:
            raise ValueError("credentials are not allowed in base_url")
        if parsed.query or parsed.fragment:
            raise ValueError("base_url must not include query or fragment")
        return value.rstrip("/")

    @field_validator("health_path")
    @classmethod
    def validate_health_path(cls, value: str) -> str:
        if not value.startswith("/") or ".." in value or "?" in value or "#" in value:
            raise ValueError("health_path must be a fixed absolute path")
        return value


class HttpPluginConfig(StrictModel):
    endpoints: dict[str, HttpEndpoint] = Field(default_factory=dict)


class HttpStatusProvider:
    def __init__(
        self, endpoint: HttpEndpoint, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.endpoint = endpoint
        self.transport = transport

    async def observe(self) -> StatusValue:
        headers: dict[str, str] = {}
        if self.endpoint.authorization_file is not None:
            headers["Authorization"] = self.endpoint.authorization_file.read_text(
                encoding="utf-8"
            ).strip()
        try:
            async with httpx.AsyncClient(
                timeout=self.endpoint.timeout_seconds,
                verify=self.endpoint.verify_tls,
                follow_redirects=False,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    f"{self.endpoint.base_url}{self.endpoint.health_path}", headers=headers
                )
            healthy = 200 <= response.status_code < 400
            return StatusValue(
                state="healthy" if healthy else "degraded",
                stale_after_seconds=self.endpoint.stale_after_seconds,
                details={"status_code": response.status_code},
            )
        except (httpx.HTTPError, OSError) as error:
            return StatusValue(
                state="unavailable",
                stale_after_seconds=self.endpoint.stale_after_seconds,
                details={"error_class": type(error).__name__},
            )


CONFIG_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "additionalProperties": False,
    "required": ["endpoints"],
    "properties": {
        "endpoints": {
            "type": "object",
            "propertyNames": {"pattern": "^[a-z][a-z0-9_-]{0,63}$"},
            "additionalProperties": {
                "type": "object",
                "additionalProperties": False,
                "required": ["base_url"],
                "properties": {
                    "base_url": {"type": "string", "format": "uri"},
                    "health_path": {"type": "string", "default": "/"},
                    "authorization_file": {"type": "string"},
                    "verify_tls": {"type": "boolean", "default": True},
                    "timeout_seconds": {
                        "type": "number",
                        "exclusiveMinimum": 0,
                        "maximum": 30,
                    },
                    "stale_after_seconds": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3600,
                    },
                },
            },
        }
    },
}


class HttpStatusPlugin:
    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            id="dh-http-status",
            name="HTTP Status",
            version="0.1.0",
            description="Observe explicitly configured HTTP health endpoints without mutation.",
            status_provider_types=["http-health"],
            permissions=PluginPermissions(
                mutation=False,
                credential_slots=["http.authorization"],
                egress_bindings=["endpoints.*.base_url"],
            ),
            config_schema=CONFIG_SCHEMA,
        )

    def build(self, context: PluginContext) -> PluginContribution:
        config = HttpPluginConfig.model_validate(dict(context.config))
        providers: Mapping[str, HttpStatusProvider] = {
            name: HttpStatusProvider(endpoint) for name, endpoint in config.endpoints.items()
        }
        return PluginContribution(status_providers=providers)


def create_plugin() -> DeckhandPlugin:
    return HttpStatusPlugin()
