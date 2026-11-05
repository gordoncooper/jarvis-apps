# jarvis-apps

Hosted apps for a Jarvis cluster: one folder per app. Everything here is **untrusted**. A Jarvis env decides which of these apps it runs and what each may do, and the cluster holds every app to that. Nothing in this repository can switch an app on, grant it anything, or reach the cluster's core.

The rules an app follows are in Jarvis's `platform/app-hosting/CONTRACT.md`, and the walkthrough is `docs/add-a-hosted-app.md`. This README is the short version.

## Layout

```text
<name>/
  app.yaml        # the app file: the whole definition of the app (kind App)
  deploy/         # the app's Kubernetes objects: plain manifests, or a kustomization
  README.md       # optional; nothing outside app.yaml and deploy/ reaches the cluster
ci/               # this repository's own checks (not an app)
```

- The folder name is the app's name: a lowercase DNS label of at most 59 characters. It must match `metadata.name` in `app.yaml`.
- The app's namespace is `app-<name>` and its address is `https://<name>.apps.<dns suffix>`. The Ingress host is always `${app_host}`, which the cluster fills in.
- Defaults: 500m CPU and 512Mi memory for the whole app, no internet, no other app may call it, no extra ports, nothing risky.
- The image and the probes are the app's own concern; the cluster does not check them. This repository's convention is to pin images by digest (`image: <repo>@sha256:...`) and to put probes in the app's own `deploy/` manifests.

## Examples

| App | What it proves |
| --- | --- |
| [hello-web](hello-web/) | A static web app on plain defaults: no volumes, no internet, nothing risky. |
| [notes](notes/) | One volume with `backup: true`, backed up with the app's own credential. |
| [lan-demo](lan-demo/) | One risky item, a port open to the home network. It is refused without the env's exception line and admitted with it. |

Copy one of these to start a new app.

## How an app is turned on

Not here. An env runs an app only when **both** of these are true, and both live in the env's own repository:

1. **App hosting is on for the env.** It is an optional Jarvis component and off by default.
2. **The env lists the app by name** in `envs/<env>/values/apps.yaml`, the file that also holds any exception lines:

   ```yaml
   apps:
     - hello-web
     - lan-demo
   exceptions:
     - lan-demo: lan-port 8080/TCP
   ```

The env then re-renders its app wiring with Jarvis's `tools/lib/render_apps.py` and commits the result.

If an app asks for something risky (privileged mode, root, host network, host paths, a custom hostname or a home-network port), it also needs a matching exception line in that same env file. An app that asks without a line is refused. A line in this repository grants nothing. An app with a `backup: true` volume also needs its own backup credential registered by the env. Until then that volume is not backed up and the env's verify step fails it.

After you merge here, the change reaches every env that lists the app. No env edit is needed.

## Add an app

1. Make `<name>/` with `app.yaml` and `deploy/`. Start from the example closest to what you need.
2. Run the same check CI runs, against a Jarvis checkout. For identical results, check out the `JARVIS_REF` from `.github/workflows/ci.yml`:

   ```sh
   git clone https://github.com/gordoncooper/jarvis.git .jarvis
   git -C .jarvis checkout <JARVIS_REF>
   ci/check-apps .jarvis
   ```

3. Open a PR. CI runs `ci/check-apps` against the Jarvis commit pinned in `.github/workflows/ci.yml`. It fails if any app file is invalid, or if any top-level folder (other than `ci/`) has no `app.yaml`.
4. Ask the env's owner to list the app, and to add any exception line or backup credential it needs.

`ci/test_examples.py` is a fuller local proof (not run in CI) for the three examples. It renders their wiring with Jarvis's renderer, runs env-schema, and runs Jarvis's admission policies through the `kyverno` CLI: `pytest ci/test_examples.py` (needs PyYAML, pytest and kyverno).
