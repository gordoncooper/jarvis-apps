"""Local proof for the example apps, run against a jarvis checkout with jarvis's own tools.

    pytest ci/test_examples.py

Reads the checkout at .jarvis (where CI puts it) or $JARVIS_CHECKOUT. The admission cases
need the kyverno CLI on PATH (jarvis: make deps); without it they fail, not skip.

For an env that lists the three apps (env-00, copied):
- tools/app-check passes each folder;
- tools/lib/render_apps.py renders their wiring, and env-schema passes the render;
- each app's deploy/ objects pass jarvis's admission policies with the env's grants;
- lan-demo's home-network Service is refused without the env's exception line.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
JARVIS = Path(os.environ.get("JARVIS_CHECKOUT", ROOT / ".jarvis")).resolve()
if not (JARVIS / "tools" / "app-check").is_file():
    pytest.skip(f"no jarvis checkout at {JARVIS}", allow_module_level=True)
for _entry in (JARVIS / "ci" / "tests", JARVIS / "ci" / "checks" / "lib", JARVIS / "tools" / "lib", JARVIS):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

import _apps  # noqa: E402
from _app_file import check_folder  # noqa: E402
from render_apps import render_env  # noqa: E402
from schema import env as env_schema  # noqa: E402
import test_app_admission as admission  # noqa: E402

APPS = ["hello-web", "notes", "lan-demo"]
LAN_LINE = {"lan-demo": "lan-port 8080/TCP"}


def _env(tmp_path: Path, exceptions: list[dict]) -> tuple[Path, Path, dict]:
    """An instance holding env-00 that lists the three apps with these exception lines,
    its wiring rendered and committed as the env would."""
    instance = tmp_path / "instance"
    env_dir = instance / "envs" / "env-00"
    shutil.copytree(JARVIS / "envs" / "env-00", env_dir)
    (instance / "core").symlink_to(JARVIS)
    values = {"apps": APPS, "exceptions": exceptions}
    (env_dir / _apps.APPS_VALUES).write_text(yaml.safe_dump(values), encoding="utf-8")
    text = render_env(env_dir)
    assert text is not None
    (env_dir / "flux" / _apps.GENERATED_REL).write_text(text, encoding="utf-8")
    return instance, env_dir, values


def _substitutes(env_dir: Path) -> dict[str, dict]:
    docs = yaml.safe_load_all((env_dir / "flux" / _apps.GENERATED_REL).read_text(encoding="utf-8"))
    return {doc["spec"]["postBuild"]["substitute"]["app_name"]: doc["spec"]["postBuild"]["substitute"] for doc in docs if doc}


@pytest.mark.parametrize("app", APPS)
def test_app_check_passes_each_example(app: str) -> None:
    assert check_folder(ROOT / app) == []


def test_render_wires_each_example_and_env_schema_passes(tmp_path: Path) -> None:
    instance, env_dir, _values = _env(tmp_path, [LAN_LINE])
    subs = _substitutes(env_dir)
    assert list(subs) == APPS
    assert subs["lan-demo"]["app_grant_lan_ports"] == "8080/TCP"
    assert subs["hello-web"]["app_grant_lan_ports"] == subs["notes"]["app_grant_lan_ports"] == ""
    cluster_vars = yaml.safe_load((env_dir / "values" / "cluster-vars.yaml").read_text(encoding="utf-8"))
    assert env_schema._validate_apps(env_dir, instance, cluster_vars, pre_host=False) == []


def _admission_env(monkeypatch: pytest.MonkeyPatch, values: dict) -> None:
    """Point jarvis's admission harness at this repository's apps and the env's grants."""
    monkeypatch.setattr(admission, "APPS", ROOT)
    monkeypatch.setattr(admission, "_ENV", {app: (admission._app(app), _apps.grants_for(values, app)) for app in APPS})


def test_examples_pass_admission_with_the_env_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _instance, _env_dir, values = _env(tmp_path, [LAN_LINE])
    _admission_env(monkeypatch, values)
    cases = [(doc, admission.PASS) for app in APPS for doc in admission._deploy(app)]
    admission._run(tmp_path, "granted", None, cases)


def test_lan_port_refused_without_the_env_line(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _instance, env_dir, values = _env(tmp_path, [])
    assert _substitutes(env_dir)["lan-demo"]["app_grant_lan_ports"] == ""
    _admission_env(monkeypatch, values)
    service = next(doc for doc in admission._deploy("lan-demo") if doc["kind"] == "Service")
    admission._run(tmp_path, "ungranted", None, [(service, {"app-file": "pass", "app-grants": "fail"})])
