# jarvis-apps

Hosted apps for a Jarvis cluster: one folder per app. Everything here is **untrusted**. A Jarvis env decides which of these apps it runs and what each may do, and the cluster holds every app to that. Nothing in this repository can switch an app on, grant it anything, or reach the cluster's core.

The rules an app follows are in Jarvis's `platform/optional/app-hosting/CONTRACT.md`, and the walkthrough is `docs/add-a-hosted-app.md`. This README is the short version.

## Layout

```text
<name>/
  app.yaml        # the app file: the whole definition of the app (kind App)
  deploy/         # the app's Kubernetes objects: plain manifests, or a kustomization
  VERSION         # <major>.<minor>.<patch>; main tags each new one <name>/v<VERSION>
  README.md       # optional; nothing outside app.yaml and deploy/ reaches the cluster
ci/               # this repository's own checks (not an app)
```

- The folder name is the app's name: a lowercase DNS label of at most 59 characters. It must match `metadata.name` in `app.yaml`.
- The app's namespace is `app-<name>` and its address is `https://<name>.apps.<dns suffix>`. The Ingress host is always `${app_host}`, which the cluster fills in.
- Defaults: 500m CPU and 512Mi memory for the whole app, nothing risky, and a closed network: no web address without `network.web`, no LAN port, no egress beyond DNS (no internet, no LAN, no other app), and no other app may call it.
- The network section of `app.yaml`:

  ```yaml
  network:
    web:                  # absent = no web address
      port: 8080          # plain-HTTP container port; served at https://<name>.apps.<dns suffix>
      healthPath: /       # optional, default /; the uptime check counts any answer but a 5xx
    ports:                # LAN ports; each needs the env's lan-port line
      - listen: 25565
        target: 25565
        protocol: TCP     # or UDP
    egress:
      internet: true      # any port to the internet, never the LAN or the cluster; default false
      lan: [nas]          # LAN targets the env names and grants, or [all]; default none
      apps: [notes]       # apps this one calls; each must list this one under callers
    callers: [web-ui]     # apps that may call this one
  ```
- The image and the probes are the app's own concern; the cluster does not check them. This repository's convention is to pin images by digest (`image: <repo>@sha256:...`) and to put probes in the app's own `deploy/` manifests.

## Versions

An env runs an app at a tag, never at `main`: it pins `<name>: v<version>` under `versions` in its `values/apps.yaml`, and Flux reads `refs/tags/<name>/v<version>`. Each app's `VERSION` is its version. When a change to an app reaches `main`, `.github/workflows/tag-apps.yml` tags `<name>/v<VERSION>` if that tag is new; Renovate in the env repository then offers the bump. A change to an app whose `VERSION` is already tagged fails CI (`ci/check-versions`): bump `VERSION` in the same PR, so a tag never moves under an env that pins it.

## Examples

| App | What it proves |
| --- | --- |
| [hello-web](hello-web/) | A web app with an init container and ConfigMap config. It calls [notes](notes/) (granted, `egress.apps` + `callers`), is refused calling lan-demo, and has internet egress. No exception line. |
| [notes](notes/) | One volume with `backup: true`, backed up with the app's own credential, seeded by an init container, surviving restarts. Callable by hello-web only. No exception line. |
| [lan-demo](lan-demo/) | One risky item, a port open to the LAN, and no web address. It is refused without the env's exception line (`lan-demo: lan-port 8080/TCP`) and admitted with it. |

All three run restricted: non-root, capabilities dropped, read-only root filesystem, `hosted-app` priority, probes, and memory request equal to limit.

Copy one of these to start a new app.

## How an app is turned on

Not here. An env runs an app only when **both** of these are true, and both live in the env's own repository:

1. **App hosting is on for the env.** It is an optional Jarvis component and off by default.
2. **The env lists the app by name** in `envs/<env>/values/switches.yaml`, one line per app:

   ```yaml
   apps:
     - hello-web
     - lan-demo
   ```

The env then renders its wiring with Jarvis's `tools/lib/render_switches.py` and commits the result. Listing a name switches an app on and grants it nothing.

If an app asks for something risky (privileged mode, root, host network, host paths, a custom hostname, a LAN port or a LAN target), it also needs a matching exception line in the env's `values/apps.yaml`:

```yaml
exceptions:
  - lan-demo: lan-port 8080/TCP
```

The LAN addresses behind a target name live only in the env's repository, never here. An app that asks without a line is refused. A line in this repository grants nothing. An app with a `backup: true` volume also needs its own backup credential registered by the env. Until then that volume is not backed up and the env's verify step fails it.

After you merge here, an env that lists the app keeps running its pinned tag. The change reaches it when the env moves the pin ([Versions](#versions)).

## Add an app

1. Make `<name>/` with `app.yaml` and `deploy/`. Start from the example closest to what you need.
2. Run the same check CI runs, from a Jarvis checkout at the release `.github/workflows/ci.yml` uses (the `app-check` Action's ref):

   ```sh
   git clone https://github.com/gordoncooper/jarvis.git .jarvis
   git -C .jarvis checkout <ref>
   python3 .jarvis/tools/app-check --repo . --exclude ci
   ```

3. Open a PR. CI runs Jarvis's `app-check` Action at that release over every top-level folder but `ci/`. It fails if any app file is invalid, or if any such folder has no `app.yaml`. Set the new app's `VERSION` (start at `0.1.0`).
4. Ask the env's owner to list the app and pin it, and to add any exception line or backup credential it needs.

## License

[Apache License 2.0](LICENSE). Contributing: [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md).
