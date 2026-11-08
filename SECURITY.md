# Security

## Reporting a vulnerability

Report it privately through GitHub: the repository's **Security** tab, **Report a vulnerability**. Do not open a public issue or pull request for it.

Everything here is untrusted by design: a Jarvis cluster holds each app to its own namespace and to what its env grants. An app file or manifest in this repository that gets past that boundary is a vulnerability in Jarvis itself; report it on the Jarvis repository the same way.

## Scope

In scope: the example apps and this repository's own checks (`ci/`). Out of scope: the upstream images the apps run. Report those to their projects.

## Supported versions

Only `main` gets fixes.
