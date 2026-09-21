"""Regression checks for rendered Helm manifests; requires built dependencies.

Prepare with: helm dependency build charts/app-spark-ui
Run with: python3 -m unittest discover -s tests -v
"""

import json
import re
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHART = PROJECT_ROOT / "charts/app-spark-ui"
CHART_METADATA = (CHART / "Chart.yaml").read_text(encoding="utf-8")
APP_VERSION = re.search(r'^appVersion: "?([^"\n]+)', CHART_METADATA, re.MULTILINE)[1]
CHART_VERSION = re.search(r"^version: (.+)$", CHART_METADATA, re.MULTILINE)[1]


class ChartDeploymentTests(unittest.TestCase):
    def render(self, *extra, version="1.35.0", release="regression", overrides=None):
        settings = []
        for key, value in (overrides or {}).items():
            settings.extend(["--set-json", f"{key}={json.dumps(value)}"])
        return subprocess.run(
            [
                "helm",
                "template",
                release,
                str(CHART),
                "--kube-version",
                version,
                "--set-string",
                "env.BK_LOGIN_URL=https://login.example/",
                *settings,
                *extra,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def manifests(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        documents = {}
        for document in result.stdout.split("---\n"):
            kind = re.search(r"^kind: (\w+)$", document, re.MULTILINE)
            if kind:
                documents[kind.group(1)] = document
        return documents

    def test_defaults_connect_service_deployment_and_only_public_runtime_env(self):
        manifests = self.manifests(self.render())
        deployment = manifests["Deployment"]
        service = manifests["Service"]
        ingress = manifests["Ingress"]
        selector = "app.kubernetes.io/name: app-spark-ui\napp.kubernetes.io/instance: regression"
        # Compare complete selector blocks: adding a version label would break
        # rolling upgrades, even when all three documents still contain a name.
        deployment_selector = re.search(r"    matchLabels:\n((?:      [^\n]+\n)+)", deployment).group(1)
        service_selector = re.search(r"  selector:\n((?:    [^\n]+\n)+)", service).group(1)
        for block in (deployment_selector, service_selector):
            self.assertEqual("\n".join(line.strip() for line in block.splitlines()), selector)
        pod_labels = deployment.split("  template:\n", 1)[1].split("    spec:\n", 1)[0]
        for label in selector.splitlines():
            self.assertIn(label, pod_labels)
        self.assertEqual(
            re.findall(r"- name: (BK_\w+)", deployment),
            ["BK_LOGIN_URL", "BK_SITE_URL", "BK_TEMPLATE_URL"],
        )
        self.assertIn("containerPort: 5000", deployment)
        self.assertIn("targetPort: http", service)
        self.assertIn("number: 5000", ingress)
        self.assertEqual(deployment.count("path: /healthz"), 3)
        self.assertIn("runAsNonRoot: true", deployment)
        self.assertIn("runAsUser: 101", deployment)
        self.assertNotRegex(deployment, r"(?m)^\s+(command|args):", msg=deployment)

    def test_tls_class_annotations_subpath_and_service_port(self):
        manifests = self.manifests(
            self.render(
                "--set-string",
                "env.BK_SITE_URL=/spark/",
                "--set-string",
                "ingress.pathPrefix=/spark",
                "--set-string",
                "ingress.host=spark.example.com",
                "--set-string",
                "ingress.ingressClass=nginx",
                "--set-string",
                "ingress.annotations.kubernetes\\.io/ingress\\.class=old",
                "--set-string",
                "ingress.annotations.example\\.com/test=kept",
                "--set-string",
                "ingress.tls[0].secretName=spark-tls",
                "--set-string",
                "ingress.tls[0].hosts[0]=spark.example.com",
                "--set",
                "service.port=8080",
            )
        )
        ingress = manifests["Ingress"]
        self.assertIn('ingressClassName: "nginx"', ingress)
        self.assertNotIn("kubernetes.io/ingress.class", ingress)
        self.assertIn("example.com/test: kept", ingress)
        self.assertIn("secretName: spark-tls", ingress)
        self.assertIn("- spark.example.com", ingress)
        self.assertIn('host: "spark.example.com"', ingress)
        self.assertIn('path: "/spark"', ingress)
        self.assertIn("number: 8080", ingress)
        self.assertIn("port: 8080", manifests["Service"])
        self.assertIn("containerPort: 5000", manifests["Deployment"])
        self.assertNotIn("rewrite-target", ingress)

    def test_supported_clusters_use_stable_ingress_backend(self):
        for version in ("1.19.0", "1.35.0"):
            with self.subTest(version=version):
                ingress = self.manifests(self.render(version=version))["Ingress"]
                self.assertIn("apiVersion: networking.k8s.io/v1", ingress)
                self.assertIn("pathType: Prefix", ingress)
                self.assertIn("name: regression-app-spark-ui", ingress)
                self.assertIn("number: 5000", ingress)
                self.assertNotIn("serviceName:", ingress)
                self.assertNotIn("ingressClassName:", ingress)
                self.assertNotIn("tls:", ingress)

    def test_clusters_before_stable_ingress_api_are_rejected(self):
        result = self.render(version="1.18.0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("kubeVersion", result.stderr)

    def test_ingress_normalizes_root_and_trailing_slash_prefixes(self):
        for prefix, site, expected in (
            ("/", "", "/"),
            ("/", "/", "/"),
            ("/spark", "/spark/", "/spark"),
            ("/spark/", "/spark", "/spark"),
            ("/custom/spark/", "/custom/spark/", "/custom/spark"),
        ):
            with self.subTest(prefix=prefix, site=site):
                ingress = self.manifests(
                    self.render(
                        overrides={
                            "ingress.pathPrefix": prefix,
                            "env.BK_SITE_URL": site,
                        }
                    )
                )["Ingress"]
                self.assertIn(f'path: "{expected}"', ingress)
                self.assertIn("pathType: Prefix", ingress)
                # Nginx owns subpath removal; ingress rewriting would strip it twice.
                self.assertNotIn("rewrite-target", ingress)
                self.assertNotIn("use-regex", ingress)

    def test_ingress_preserves_annotation_only_class(self):
        ingress = self.manifests(
            self.render(overrides={"ingress.annotations": {"kubernetes.io/ingress.class": "legacy"}})
        )["Ingress"]
        self.assertIn("kubernetes.io/ingress.class: legacy", ingress)
        self.assertNotIn("ingressClassName:", ingress)

    def test_ingress_accepts_null_annotations(self):
        ingress = self.manifests(self.render(overrides={"ingress.annotations": None}))["Ingress"]
        self.assertNotIn("annotations:", ingress)

    def test_ingress_renders_annotation_and_tls_templates(self):
        ingress = self.manifests(
            self.render(
                overrides={
                    "ingress.host": "spark.example.com",
                    "ingress.annotations": {"example.com/release": "{{ .Release.Name }}"},
                    "ingress.tls": [
                        {
                            "hosts": ["{{ .Values.ingress.host }}"],
                            "secretName": "{{ .Release.Name }}-tls",
                        }
                    ],
                }
            )
        )["Ingress"]
        self.assertRegex(ingress, r"example.com/release: [\"']?regression[\"']?\n")
        self.assertRegex(ingress, r"secretName: [\"']?regression-tls[\"']?\n")
        self.assertRegex(ingress, r"- [\"']?spark\.example\.com[\"']?\n")
        self.assertNotIn("{{", ingress)

    def test_image_registry_tag_global_override_and_digest(self):
        for overrides, expected in (
            ({}, f"app-spark-ui:{APP_VERSION}"),
            ({"image.tag": "v2"}, "app-spark-ui:v2"),
            (
                {"image.repository": "private.example/team/ui"},
                f"private.example/team/ui:{APP_VERSION}",
            ),
            (
                {"image.registry": "private.example", "image.tag": "v2"},
                "private.example/app-spark-ui:v2",
            ),
            (
                {
                    "image.registry": "local.example",
                    "global.imageRegistry": "global.example",
                    "image.tag": "v2",
                },
                "global.example/app-spark-ui:v2",
            ),
            (
                {"image.digest": "sha256:abc", "image.tag": "ignored"},
                "app-spark-ui@sha256:abc",
            ),
        ):
            with self.subTest(overrides=overrides):
                deployment = self.manifests(self.render(overrides=overrides))["Deployment"]
                self.assertRegex(deployment, rf'(?m)^\s+image: "?{re.escape(expected)}"?$')
                self.assertIn("imagePullPolicy: IfNotPresent", deployment)

    def test_pull_secrets_merge_strings_objects_and_remove_duplicates(self):
        deployment = self.manifests(
            self.render(
                overrides={
                    "imagePullSecrets": [{"name": "legacy"}, "shared"],
                    "global.imagePullSecrets": ["global", {"name": "shared"}],
                    "image.pullSecrets": ["ui", {"name": "legacy"}],
                }
            )
        )["Deployment"]
        secrets = re.search(r"      imagePullSecrets:\n((?:      [ -][^\n]*\n)+)", deployment)[1]
        names = re.findall(r'- name: "?([^"\n]+)"?', secrets)
        self.assertCountEqual(names, ["legacy", "shared", "global", "ui"])

    def test_pull_secrets_render_templates(self):
        deployment = self.manifests(
            self.render(
                overrides={
                    "imagePullSecrets": ["{{ .Release.Name }}-legacy"],
                    "global.imagePullSecrets": [{"name": "{{ .Release.Name }}-global"}],
                    "image.pullSecrets": ["{{ .Release.Name }}-ui"],
                }
            )
        )["Deployment"]
        for source in ("legacy", "global", "ui"):
            self.assertRegex(deployment, rf'- name: "?regression-{source}"?\n')
        self.assertNotIn("{{", deployment)

    def test_default_pod_omits_empty_pull_secrets(self):
        deployment = self.manifests(self.render())["Deployment"]
        self.assertNotIn("imagePullSecrets:", deployment)

    def test_names_and_labels_keep_selectors_stable(self):
        for release, overrides, name, fullname in (
            ("regression", {}, "app-spark-ui", "regression-app-spark-ui"),
            ("prod-app-spark-ui", {}, "app-spark-ui", "prod-app-spark-ui"),
            ("regression", {"nameOverride": "custom"}, "custom", "regression-custom"),
            (
                "regression",
                {"fullnameOverride": "pinned"},
                "app-spark-ui",
                "pinned",
            ),
            (
                "regression",
                {"fullnameOverride": "x" * 62 + "-truncated"},
                "app-spark-ui",
                "x" * 62,
            ),
        ):
            with self.subTest(release=release, overrides=overrides):
                manifests = self.manifests(self.render(release=release, overrides=overrides))
                selector = {
                    f"app.kubernetes.io/name: {name}",
                    f"app.kubernetes.io/instance: {release}",
                }
                for document in manifests.values():
                    metadata = document.split("metadata:\n", 1)[1].split("spec:\n", 1)[0]
                    self.assertIn(f"  name: {fullname}\n", metadata)
                    self.assertIn(f"helm.sh/chart: app-spark-ui-{CHART_VERSION}", metadata)
                    self.assertRegex(
                        metadata,
                        rf'app.kubernetes.io/version: "?{re.escape(APP_VERSION)}"?\n',
                    )
                    self.assertIn("app.kubernetes.io/managed-by: Helm", metadata)
                    for label in selector:
                        self.assertIn(label, metadata)
                deployment = manifests["Deployment"]
                blocks = [
                    re.search(r"    matchLabels:\n((?:      [^\n]+\n)+)", deployment)[1],
                    re.search(r"  selector:\n((?:    [^\n]+\n)+)", manifests["Service"])[1],
                ]
                for block in blocks:
                    self.assertEqual({line.strip() for line in block.splitlines()}, selector)
                pod_labels = re.search(
                    r"  template:\n    metadata:\n      labels:\n"
                    r"((?:        [^\n]+\n)+)",
                    deployment,
                )[1]
                # Pods may carry release/version labels; immutable selectors must
                # only use name and instance so version upgrades remain possible.
                self.assertTrue(selector <= {line.strip() for line in pod_labels.splitlines()})

    def test_ingress_can_be_disabled(self):
        manifests = self.manifests(self.render("--set", "ingress.enabled=false"))
        self.assertEqual(set(manifests), {"Service", "Deployment"})

    def test_mismatched_ingress_path_is_rejected(self):
        result = self.render("--set-string", "env.BK_SITE_URL=/spark")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ingress.pathPrefix must match env.BK_SITE_URL", result.stderr)

    def test_schema_rejects_unused_env_invalid_types_paths_and_ports(self):
        for flag, assignment in (
            ("--set-string", "env.BK_PAAS_ENVIRONMENT=production"),
            ("--set", "env.BK_TEMPLATE_URL=true"),
            ("--set-string", "env.BK_SITE_URL=/spark/../admin"),
            ("--set-string", "service.port=5000"),
            ("--set", "service.port=65536"),
            ("--set", "replicaCount=0"),
            ("--set-string", "ingress.path=/"),
            ("--set-string", "ingress.pathType=ImplementationSpecific"),
        ):
            with self.subTest(assignment=assignment):
                result = self.render(flag, assignment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("schema", result.stderr)


if __name__ == "__main__":
    unittest.main()
