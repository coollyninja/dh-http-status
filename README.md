# dh-http-status

`dh-http-status` is an independently releasable Deckhand integration. It contributes topology-neutral HTTP health status providers; it does not contribute mutations or contain deployment-specific endpoints.

## Identity

- Repository and plugin ID: `dh-http-status`
- Python package: `dh_http_status`
- Entry point: `deckhand.plugins` / `dh-http-status`
- Status keys: selected by the private site or a public solution pack

## Configuration

```yaml
schema_version: 1
plugins:
  dh-http-status:
    enabled: true
    config:
      endpoints:
        example:
          base_url: https://status.example.invalid
          health_path: /ready
          verify_tls: true
          stale_after_seconds: 30
```

Credentials are optional file references supplied by deployment tooling. Do not put bearer values, real internal addresses, or resource identifiers in configuration committed to a public repository.

The plugin is MIT licensed. Its initial core dependency is pinned to the exact Deckhand plugin-architecture commit; this changes to a released compatibility range after the first core plugin-API release.
