# Contributing

Changes come as pull requests against `main`. The repository owner reviews and merges every one.

## Adding or changing an app

- One folder per app, named after it, holding `app.yaml` and `deploy/` ([README.md](README.md)). Jarvis's `docs/add-a-hosted-app.md` walks through it, and `platform/optional/app-hosting/CONTRACT.md` holds the rules.
- Ask for nothing the app does not need. An env grants anything risky (root, host paths, LAN, extra hostnames) itself; this repository cannot.
- Pin images by digest (`image: <repo>@sha256:...`).
- No LAN IP, numeric user ID or secret in plaintext.

## Before you push

Run this repository's checks, as CI does:

```bash
ci/check-apps <jarvis checkout>
pytest ci/test_examples.py   # needs PyYAML, pytest and kyverno
```

Then fill in the pull request description: which app, what changed, and what it asks for.

## License

Contributions are licensed under the [Apache License 2.0](LICENSE), the license of this repository.
