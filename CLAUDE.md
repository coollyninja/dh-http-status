# dh-http-status

Inherit `../CLAUDE.md` and the vault standards. This repository owns only topology-neutral, read-only HTTP health observation.

- Keep plugin ID `dh-http-status`, Python package `dh_http_status`, and entry point name `dh-http-status` aligned.
- Do not follow redirects or accept URL-embedded credentials, query strings, fragments, or non-HTTP schemes.
- Credentials are optional file references supplied by a private deployment.
- Keep `deckhand-plugin.yaml` identical to the runtime manifest and retain the installed-entry-point integration test.
- Do not add mutations to this plugin.
