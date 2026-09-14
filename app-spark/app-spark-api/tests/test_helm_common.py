"""Render the chart to verify common helpers preserve Kubernetes resource contracts."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from dynaconf.vendor.ruamel.yaml import YAML

HELM = shutil.which("helm")
CHART = Path(__file__).resolve().parents[1] / "charts" / "app-spark-api"
CHART_METADATA = YAML(typ="safe").load((CHART / "Chart.yaml").read_text())
pytestmark = pytest.mark.skipif(HELM is None, reason="Helm is required for chart rendering tests")


def _render(
    overrides: dict[str, Any] | None = None, *, release: str = "spark-test", kube_version: str = "1.19.0"
) -> dict[str, Any]:
    command = [HELM or "helm", "template", release, str(CHART), "--kube-version", kube_version]
    for key, value in (overrides or {}).items():
        command.extend(["--set-json", f"{key}={json.dumps(value)}"])
    rendered = subprocess.run(command, check=False, capture_output=True, text=True)
    assert rendered.returncode == 0, rendered.stderr
    return {resource["kind"]: resource for resource in YAML(typ="safe").load_all(rendered.stdout) if resource}


@pytest.mark.parametrize("kube_version", ["1.19.0", "1.35.0"])
@pytest.mark.parametrize("service_port", [8080, "8080"])
def test_ingress_backend_uses_stable_api(kube_version, service_port):
    resources = _render({"service.port": service_port}, kube_version=kube_version)
    ingress = resources["Ingress"]
    assert ingress["apiVersion"] == "networking.k8s.io/v1"
    assert "ingressClassName" not in ingress["spec"]
    assert "tls" not in ingress["spec"]
    assert ingress["spec"]["rules"] == [
        {
            "host": "app-spark-api.example.com",
            "http": {
                "paths": [
                    {
                        "path": "/api-svc(/|$)(.*)",
                        "pathType": "ImplementationSpecific",
                        "backend": {
                            "service": {"name": resources["Service"]["metadata"]["name"], "port": {"number": 8080}}
                        },
                    }
                ]
            },
        }
    ]
    assert ingress["metadata"]["annotations"]["nginx.ingress.kubernetes.io/rewrite-target"] == "/$2"


@pytest.mark.parametrize("path_prefix", ["/api-svc", "/api-svc/", "/custom-svc"])
def test_ingress_path_follows_path_prefix(path_prefix):
    ingress = _render({"ingress.pathPrefix": path_prefix})["Ingress"]
    expected_prefix = path_prefix.rstrip("/")
    assert ingress["spec"]["rules"][0]["http"]["paths"][0]["path"] == f"{expected_prefix}(/|$)(.*)"


@pytest.mark.parametrize("ingress_class", [None, "nginx"])
def test_explicit_ingress_class_supersedes_legacy_annotation(ingress_class):
    overrides = {"ingress.annotations.kubernetes\\.io/ingress\\.class": "legacy"}
    if ingress_class is not None:
        overrides["ingress.ingressClass"] = ingress_class
    ingress = _render(overrides)["Ingress"]
    annotations = ingress["metadata"]["annotations"]
    if ingress_class is None:
        assert annotations["kubernetes.io/ingress.class"] == "legacy"
        assert "ingressClassName" not in ingress["spec"]
    else:
        assert ingress["spec"]["ingressClassName"] == ingress_class
        assert "kubernetes.io/ingress.class" not in annotations
    assert annotations["nginx.ingress.kubernetes.io/proxy-buffering"] == "off"


def test_ingress_renders_annotation_and_tls_templates():
    ingress = _render(
        {
            "ingress.annotations.example\\.com/release": "{{ .Release.Name }}",
            "ingress.tls": [{"hosts": ["{{ .Values.ingress.host }}"], "secretName": "{{ .Release.Name }}-tls"}],
        }
    )["Ingress"]
    assert ingress["metadata"]["annotations"]["example.com/release"] == "spark-test"
    assert ingress["spec"]["tls"] == [{"hosts": ["app-spark-api.example.com"], "secretName": "spark-test-tls"}]


def test_ingress_can_be_disabled():
    assert "Ingress" not in _render({"ingress.enabled": False})


def test_ingress_accepts_null_annotations():
    ingress = _render({"ingress.annotations": None})["Ingress"]
    assert "annotations" not in ingress["metadata"]


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, f"app-spark-api:{CHART_METADATA['appVersion']}"),
        ({"image.tag": "v2"}, "app-spark-api:v2"),
        ({"image.repository": "private.example/team/api"}, f"private.example/team/api:{CHART_METADATA['appVersion']}"),
        ({"image.registry": "private.example", "image.tag": "v2"}, "private.example/app-spark-api:v2"),
        (
            {"image.registry": "local.example", "global.imageRegistry": "global.example", "image.tag": "v2"},
            "global.example/app-spark-api:v2",
        ),
        ({"image.digest": "sha256:abc", "image.tag": "ignored"}, "app-spark-api@sha256:abc"),
    ],
)
def test_api_and_migration_job_use_same_image(overrides, expected):
    resources = _render(overrides)
    for kind in ("Deployment", "Job"):
        assert resources[kind]["spec"]["template"]["spec"]["containers"][0]["image"] == expected


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, "groundnuty/k8s-wait-for:v1.5.1"),
        ({"utility.images.k8sWaitFor.registry": "local.example"}, "local.example/groundnuty/k8s-wait-for:v1.5.1"),
        ({"global.imageRegistry": "global.example"}, "global.example/groundnuty/k8s-wait-for:v1.5.1"),
        ({"utility.images.k8sWaitFor.digest": "sha256:def"}, "groundnuty/k8s-wait-for@sha256:def"),
    ],
)
def test_wait_for_migrations_image_supports_common_options(overrides, expected):
    pod = _render(overrides)["Deployment"]["spec"]["template"]["spec"]
    assert pod["initContainers"][0]["image"] == expected


@pytest.mark.parametrize("migrate_enabled", [False, True])
def test_pull_secrets_merge_sources_and_only_include_images_in_each_pod(migrate_enabled):
    resources = _render(
        {
            "migrate.enabled": migrate_enabled,
            "imagePullSecrets": [{"name": "legacy"}, "shared"],
            "global.imagePullSecrets": ["global", {"name": "shared"}],
            "image.pullSecrets": ["api", {"name": "legacy"}],
            "utility.images.k8sWaitFor.pullSecrets": [{"name": "utility"}, "shared"],
        }
    )
    api_secrets = {"legacy", "shared", "global", "api"}
    pod = resources["Deployment"]["spec"]["template"]["spec"]
    expected = api_secrets | ({"utility"} if migrate_enabled else set())
    assert {item["name"] for item in pod["imagePullSecrets"]} == expected
    assert len(pod["imagePullSecrets"]) == len(expected)
    if migrate_enabled:
        job_secrets = resources["Job"]["spec"]["template"]["spec"]["imagePullSecrets"]
        assert {item["name"] for item in job_secrets} == api_secrets
        assert len(job_secrets) == len(api_secrets)
    else:
        assert "Job" not in resources
        assert "initContainers" not in pod
        assert "serviceAccountName" not in pod


def test_default_pods_omit_empty_pull_secrets():
    resources = _render()
    for kind in ("Deployment", "Job"):
        assert "imagePullSecrets" not in resources[kind]["spec"]["template"]["spec"]


@pytest.mark.parametrize(
    ("release", "overrides", "name", "fullname"),
    [
        ("spark-test", {}, "app-spark-api", "spark-test-app-spark-api"),
        ("prod-app-spark-api", {}, "app-spark-api", "prod-app-spark-api"),
        ("spark-test", {"nameOverride": "custom"}, "custom", "spark-test-custom"),
        ("spark-test", {"fullnameOverride": "pinned"}, "app-spark-api", "pinned"),
        ("spark-test", {"fullnameOverride": "x" * 62 + "-truncated"}, "app-spark-api", "x" * 62),
    ],
)
def test_names_labels_and_selectors_stay_compatible(release, overrides, name, fullname):
    resources = _render(overrides, release=release)
    selector = {"app.kubernetes.io/name": name, "app.kubernetes.io/instance": release}
    for kind in ("Deployment", "Ingress", "Service", "ConfigMap"):
        metadata = resources[kind]["metadata"]
        assert metadata["name"] == fullname
        assert metadata["labels"] == {
            **selector,
            "helm.sh/chart": f"app-spark-api-{CHART_METADATA['version']}",
            "app.kubernetes.io/version": CHART_METADATA["appVersion"],
            "app.kubernetes.io/managed-by": "Helm",
        }
    api_selector = {**selector, "app.kubernetes.io/component": "api"}
    assert resources["Deployment"]["spec"]["selector"]["matchLabels"] == api_selector
    assert resources["Deployment"]["spec"]["template"]["metadata"]["labels"] == api_selector
    assert resources["Service"]["spec"]["selector"] == api_selector
    assert resources["Job"]["metadata"]["name"] == f"{fullname[:50].rstrip('-')}-migrate-1"
