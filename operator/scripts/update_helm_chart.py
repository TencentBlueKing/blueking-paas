# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at

    http://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software distributed under
the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
either express or implied. See the License for the specific language governing permissions and
limitations under the License.

We undertake not to change the open source license (MIT license) applicable
to the current version of the project delivered to anyone in the future.
"""

import argparse
import difflib
import os
import shutil
from collections import namedtuple
from os import path, walk
from pathlib import Path
from textwrap import dedent, indent

import yaml

TMPL_DIR = "templates"


def wrap_multiline_str(space_num: int, m_string: str) -> str:
    """对多行字符串做处理，避免格式化时候丢失缩进"""
    return indent(dedent(m_string), " " * space_num)


# 目标文件 与 原始文件集合的映射关系，如果存在多个原始文件，则进行合并
filepath_conf = {
    "_helpers.tpl": ["_helpers.tpl"],
    # crd
    "crds/paas.bk.tencent.com_bkapps.tpl": ["bkapp-crd.yaml"],
    "crds/paas.bk.tencent.com_domaingroupmappings.yaml": ["domaingroupmapping-crd.yaml"],
    "crds/paas.bk.tencent.com_projectconfigs.yaml": ["projectconfig-crd.yaml"],
    # controller
    "controller/deployment.yaml": ["deployment.yaml"],
    "controller/config.yaml": ["manager-config.yaml"],
    "controller/service.yaml": ["metrics-service.yaml"],
    "controller/metrics-monitor.yaml": ["metrics-monitor.yaml"],
    "controller/leader-election-rbac.yaml": ["leader-election-rbac.yaml"],
    "controller/manager-rbac.yaml": ["manager-rbac.yaml"],
    "controller/metrics-reader-rbac.yaml": ["metrics-reader-rbac.yaml"],
    "controller/proxy-rbac.yaml": ["proxy-rbac.yaml"],
    # webhooks
    "webhooks/mutating-webhook.tpl": ["mutating-webhook-configuration.yaml"],
    "webhooks/validating-webhook.tpl": ["validating-webhook-configuration.yaml"],
    "webhooks/webhook-cert-secret.tpl": ["webhook-cert-secret.yaml"],
    "webhooks/webhook-service.yaml": ["webhook-service.yaml"],
    # certificate
    "certificate/selfsigned-issuer.yaml": ["selfsigned-issuer.yaml"],
    "certificate/serving-cert.yaml": ["serving-cert.yaml"],
    # 包含需要使用自动生成的证书的模板，统一渲染避免重复调用 genCA 导致的证书不一致问题
    "certificate/certificate.yaml": ["certificate.yaml"],
}

# 格式：文件路径: [(src_str1, dst_str1), (src_str2, dst_str2)]
content_patch_conf = {
    "deployment.yaml": [
        # 替换 rbac-proxy 镜像
        (
            wrap_multiline_str(
                8,
                """
                image: {{ .Values.controllerManager.kubeRbacProxy.image.repository }}:{{ .Values.controllerManager.kubeRbacProxy.image.tag | default .Chart.AppVersion }}
                """,  # noqa E501
            ),
            wrap_multiline_str(
                8,
                """
                image: {{ include "bkpaas-app-operator.proxyImage" . }}
                imagePullPolicy: {{ .Values.image.pullPolicy }}
                """,
            ),
        ),
        # 替换 operator 镜像
        (
            wrap_multiline_str(
                8,
                """
                image: {{ .Values.controllerManager.manager.image.repository }}:{{ .Values.controllerManager.manager.image.tag | default .Chart.AppVersion }}
                """,  # noqa E501
            ),
            wrap_multiline_str(
                8,
                """
                image: {{ include "bkpaas-app-operator.image" . }}
                imagePullPolicy: {{ .Values.image.pullPolicy }}
                """,
            ),
        ),
        # 替换 rbac-proxy resources 为固定值
        (
            wrap_multiline_str(
                8,
                """
                resources: {{- toYaml .Values.controllerManager.kubeRbacProxy.resources | nindent 10 }}
                """,
            ),
            wrap_multiline_str(
                8,
                """
                resources:
                  limits:
                    cpu: 500m
                    memory: 512Mi
                  requests:
                    cpu: 5m
                    memory: 64Mi
                """,
            ),
        ),
        # 替换 operator 资源配额
        (
            ".Values.controllerManager.manager.resources",
            ".Values.resources",
        ),
        # 替换 imagePullSecrets，改成引用 values
        (
            wrap_multiline_str(
                6,
                """
                imagePullSecrets:
                - name: {{ include "bkpaas-app-operator.fullname" . }}-docker-registry
                """,
            ),
            wrap_multiline_str(
                6,
                """
                {{- with .Values.imagePullSecrets }}
                imagePullSecrets:
                  {{- toYaml . | nindent 8 }}
                {{- end }}
                """,
            ),
        ),
        # 替换副本数量引用
        (
            ".Values.controllerManager.replicas",
            ".Values.replicaCount",
        ),
        # webhook secret 添加前缀
        (
            "secretName: webhook-server-cert",
            "secretName: bkpaas-webhook-server-cert",
        ),
        # 替换启动命令
        (
            "- --config=controller_manager_config.yaml",
            "- --config=controller_manager_config.yaml\n        - -zap-devel={{ .Values.controller.zapOpts.zapDevel }}",
        ),
    ],
    "serving-cert.yaml": [
        # webhook secret 添加前缀
        (
            "secretName: webhook-server-cert",
            "secretName: bkpaas-webhook-server-cert",
        ),
        # 移除 fullname 渲染
        (
            '{{ include "bkpaas-app-operator.fullname" . }}-webhook-service.{{ .Release.Namespace }}.svc',
            "bkpaas-app-operator-webhook-service.{{ .Release.Namespace }}.svc",
        ),
        (
            '{{ include "bkpaas-app-operator.fullname" . }}-webhook-service.{{ .Release.Namespace }}.svc.{{ .Values.kubernetesClusterDomain }}',  # noqa: E501
            "bkpaas-app-operator-webhook-service.{{ .Release.Namespace }}.svc.{{ .Values.kubernetesClusterDomain }}",
        ),
    ],
    "manager-config.yaml": [
        (".Values.managerConfig.controllerManagerConfigYaml", ".Values.controller"),
        (
            # 白名单控制支持 enabled & 挪到 values 顶层
            wrap_multiline_str(
                4,
                """
                ingressPlugin:
                  accessControl:
                    redisConfigKey: {{ .Values.controller.ingressPlugin.accessControl.redisConfigKey | quote }}
                  paasAnalysis:
                    enabled: {{ .Values.controller.ingressPlugin.paasAnalysis.enabled }}
                  tenantGuard:
                    enabled: {{ .Values.controller.ingressPlugin.tenantGuard.enabled }}
                """,  # noqa: E501
            ),
            wrap_multiline_str(
                4,
                """
                {{- if or .Values.accessControl.enabled .Values.paasAnalysis.enabled .Values.tenantGuard.enabled }}
                ingressPlugin:
                  {{- if .Values.accessControl.enabled }}
                  accessControl:
                    redisConfigKey: {{ .Values.accessControl.redisConfigKey }}
                  {{- end }}
                  {{- if .Values.paasAnalysis.enabled }}
                  paasAnalysis:
                    enabled: {{ .Values.paasAnalysis.enabled }}
                  {{- end }}
                  {{- if .Values.tenantGuard.enabled }}
                  tenantGuard:
                    enabled: {{ .Values.tenantGuard.enabled }}
                  {{- end }}
                {{- else }}
                ingressPlugin: {}
                {{- end }}
                """,
            ),
        ),
        (
            wrap_multiline_str(
                6,
                """
                ingressClassName: {{ .Values.controller.platform.ingressClassName | quote }}
                """,
            ),
            wrap_multiline_str(
                6,
                """
                ingressClassName: {{ .Values.controller.platform.ingressClassName | quote }}
                {{- if .Values.controller.platform.customDomainIngressClassName }}
                customDomainIngressClassName: {{ .Values.controller.platform.customDomainIngressClassName | quote }}
                {{- end }}
                """,
            ),
        ),
        (
            # 默认资源 Limits 配置挪到 values 顶层
            ".Values.controller.resLimits",
            ".Values.resLimits",
        ),
        (
            # 默认资源 Requests 配置挪到 values 顶层
            ".Values.controller.resRequests",
            ".Values.resRequests",
        ),
        (
            # 自动扩缩容配置挪到 values 顶层
            ".Values.controller.autoscaling",
            ".Values.autoscaling",
        ),
        (
            # 最大进程数量配置挪到 values 顶层
            ".Values.controller.maxProcesses",
            ".Values.maxProcesses",
        ),
        (
            # 平台配置挪到 values 顶层，依旧保留 Config 后缀以兼容存量 values
            ".Values.controller.platform",
            ".Values.platformConfig",
        ),
    ],
    "validating-webhook-configuration.yaml": [
        (
            wrap_multiline_str(
                2,
                """
                annotations:
                  cert-manager.io/inject-ca-from: {{ .Release.Namespace }}/{{ include "bkpaas-app-operator.fullname" . }}-serving-cert
                """,  # noqa: E501
            ),
            wrap_multiline_str(
                2,
                """
                {{- if .Values.cert.managerEnabled }}
                annotations:
                  cert-manager.io/inject-ca-from: {{ .Release.Namespace }}/{{ include "bkpaas-app-operator.fullname" . }}-serving-cert
                {{- end }}
                """,  # noqa: E501
            ),
        ),
        (
            wrap_multiline_str(
                2,
                """
                clientConfig:
                """,
            ),
            wrap_multiline_str(
                2,
                """
                clientConfig:
                  {{- if not .Values.cert.managerEnabled }}
                  caBundle: {{ include "bkpaas-app-operator.webhookCaBundle" (dict "cert" .Values.cert "genCa" .ca) }}
                  {{- end }}
                """,
            ),
        ),
        ('{{ include "bkpaas-app-operator.fullname" . }}-webhook-service', "bkpaas-app-operator-webhook-service"),
    ],
    "mutating-webhook-configuration.yaml": [
        (
            wrap_multiline_str(
                2,
                """
                annotations:
                  cert-manager.io/inject-ca-from: {{ .Release.Namespace }}/{{ include "bkpaas-app-operator.fullname" . }}-serving-cert
                """,  # noqa: E501
            ),
            wrap_multiline_str(
                2,
                """
                {{- if .Values.cert.managerEnabled }}
                annotations:
                  cert-manager.io/inject-ca-from: {{ .Release.Namespace }}/{{ include "bkpaas-app-operator.fullname" . }}-serving-cert
                {{- end }}
                """,  # noqa: E501
            ),
        ),
        (
            wrap_multiline_str(
                2,
                """
                clientConfig:
                """,
            ),
            wrap_multiline_str(
                2,
                """
                clientConfig:
                  {{- if not .Values.cert.managerEnabled }}
                  caBundle: {{ include "bkpaas-app-operator.webhookCaBundle" (dict "cert" .Values.cert "genCa" .ca) }}
                  {{- end }}
                """,
            ),
        ),
        ('{{ include "bkpaas-app-operator.fullname" . }}-webhook-service', "bkpaas-app-operator-webhook-service"),
    ],
    "webhook-service.yaml": [
        ('{{ include "bkpaas-app-operator.fullname" . }}-webhook-service', "bkpaas-app-operator-webhook-service")
    ],
    # 为 Helm Charts 中的 CRD 统一添加删除保护注解
    "bkapp-crd.yaml": [
        (
            "controller-gen.kubebuilder.io/version: v0.14.0",
            "controller-gen.kubebuilder.io/version: v0.14.0\n    helm.sh/resource-policy: keep",
        ),
        (
            wrap_multiline_str(
                4,
                """
                cert-manager.io/inject-ca-from: '{{ .Release.Namespace }}/{{ include "bkpaas-app-operator.fullname" . }}-serving-cert'
                """,  # noqa: E501
            ),
            wrap_multiline_str(
                4,
                """
                {{- if .Values.cert.managerEnabled }}
                cert-manager.io/inject-ca-from: '{{ .Release.Namespace }}/{{ include "bkpaas-app-operator.fullname" . }}-serving-cert'
                {{- end }}
                """,  # noqa: E501
            ),
        ),
        (
            wrap_multiline_str(
                6,
                """
                clientConfig:
                """,
            ),
            wrap_multiline_str(
                6,
                """
                clientConfig:
                  {{- if not .Values.cert.managerEnabled }}
                  caBundle: {{ include "bkpaas-app-operator.webhookCaBundle" (dict "cert" .Values.cert "genCa" .ca) }}
                  {{- end }}
                """,
            ),
        ),
    ],
    "domaingroupmapping-crd.yaml": [
        (
            "controller-gen.kubebuilder.io/version: v0.14.0",
            "controller-gen.kubebuilder.io/version: v0.14.0\n    helm.sh/resource-policy: keep",
        )
    ],
    "projectconfig-crd.yaml": [
        (
            "controller-gen.kubebuilder.io/version: v0.14.0",
            "controller-gen.kubebuilder.io/version: v0.14.0\n    helm.sh/resource-policy: keep",
        )
    ],
}

# 对模板内容的包装，front 即需要添加到文件头的内容，back 即文件尾需要添加的内容
WrapContent = namedtuple("WrapContent", "front, back")

content_wrap_conf = {
    "_helpers.tpl": WrapContent(
        "",
        """
{{/*
Image Tag
*/}}
{{- define "bkpaas-app-operator.image" -}}
{{ include "common.images.image" (dict "imageRoot" .Values.image "global" .Values.global) }}
{{- end -}}

{{/*
Proxy Image Tag
*/}}
{{- define "bkpaas-app-operator.proxyImage" -}}
{{ include "common.images.image" (dict "imageRoot" .Values.proxyImage "global" .Values.global) }}
{{- end -}}

{{/*
Webhook Cert
*/}}
{{- define "bkpaas-app-operator.webhookCert" -}}
{{- if .cert.autoGenerate }}
{{- .genCert.Cert | b64enc | quote }}
{{- else }}
{{- .cert.webhookCert | required "cert.webhookCert is required" }}
{{- end }}
{{- end -}}

{{/*
Webhook Key
*/}}
{{- define "bkpaas-app-operator.webhookKey" -}}
{{- if .cert.autoGenerate }}
{{- .genCert.Key | b64enc | quote }}
{{- else }}
{{- .cert.webhookKey | required "cert.webhookKey is required" }}
{{- end }}
{{- end -}}

{{/*
Webhook CaBundle
*/}}
{{- define "bkpaas-app-operator.webhookCaBundle" -}}
{{- if .cert.autoGenerate }}
{{- .genCa.Cert | b64enc | quote }}
{{- else }}
{{- .cert.webhookCaBundle | required "cert.webhookCaBundle is required" }}
{{- end }}
{{- end -}}
""",
    ),
    "selfsigned-issuer.yaml": WrapContent("{{- if .Values.cert.managerEnabled }}\n", "{{- end }}\n"),
    "serving-cert.yaml": WrapContent("{{- if .Values.cert.managerEnabled }}\n", "{{- end }}\n"),
    "certificate.yaml": WrapContent(
        "",
        """
{{- $dnsNames := list ( printf "bkpaas-app-operator-webhook-service.%s.svc" .Release.Namespace ) ( printf "bkpaas-app-operator-webhook-service.%s.svc.%s" .Release.Namespace .Values.kubernetesClusterDomain ) -}}
{{- $ca := genCA "bkpaas-app-operator-ca" 3650 -}}
{{- $cert := genSignedCert "bkpaas-app-operator-ca" nil $dnsNames 3650 $ca -}}
---
{{ include "bkpaas-app-operator.webhookCertSecret" (dict "Chart" .Chart "Release" .Release "Values" .Values "cert" $cert "ca" $ca) }}
---
{{ include "bkpaas-app-operator.mutatingWebhook" (dict "Chart" .Chart "Release" .Release "Values" .Values "cert" $cert "ca" $ca) }}
---
{{ include "bkpaas-app-operator.validatingWebhook" (dict "Chart" .Chart "Release" .Release "Values" .Values "cert" $cert "ca" $ca) }}
---
{{ include "bkpaas-app-operator.bkappCRD" (dict "Chart" .Chart "Release" .Release "Values" .Values "cert" $cert "ca" $ca) }}
        """.lstrip(),  # noqa E501
    ),
    "bkapp-crd.yaml": WrapContent('{{ define "bkpaas-app-operator.bkappCRD" -}}\n', "{{- end -}}\n"),
    "webhook-cert-secret.yaml": WrapContent(
        "",
        """
{{ define "bkpaas-app-operator.webhookCertSecret" -}}
{{- if not .Values.cert.managerEnabled }}
apiVersion: v1
kind: Secret
metadata:
  name: bkpaas-webhook-server-cert
  namespace: {{ .Release.Namespace }}
type: kubernetes.io/tls
data:
  ca.crt: {{ include "bkpaas-app-operator.webhookCaBundle" (dict "cert" .Values.cert "genCa" .ca) }}
  tls.crt: {{ include "bkpaas-app-operator.webhookCert" (dict "cert" .Values.cert "genCert" .cert) }}
  tls.key: {{ include "bkpaas-app-operator.webhookKey" (dict "cert" .Values.cert "genCert" .cert) }}
{{- end }}
{{- end -}}
""".lstrip(),  # noqa: E501
    ),
    "mutating-webhook-configuration.yaml": WrapContent(
        '{{ define "bkpaas-app-operator.mutatingWebhook" -}}\n',
        "{{- end -}}\n",
    ),
    "validating-webhook-configuration.yaml": WrapContent(
        '{{ define "bkpaas-app-operator.validatingWebhook" -}}\n',
        "{{- end -}}\n",
    ),
    "metrics-monitor.yaml": WrapContent(
        "",
        """
{{- if .Values.serviceMonitor.enabled }}
---
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "bkpaas-app-operator.fullname" . }}-controller-manager-metrics-monitor
  labels:
    control-plane: controller-manager
  {{- include "bkpaas-app-operator.labels" . | nindent 4 }}
spec:
  endpoints:
  - bearerTokenFile: /var/run/secrets/kubernetes.io/serviceaccount/token
    path: /metrics
    port: https
    scheme: https
    tlsConfig:
      insecureSkipVerify: true
  selector:
    matchLabels:
      control-plane: controller-manager
{{- end -}}
""".lstrip(),
    ),
}


class HelmChartUpdater:
    def __init__(self, chart_target_dir: str):
        self.chart_target_dir = Path(chart_target_dir)
        self.chart_source_dir = Path(__file__).resolve().parents[1] / "bkpaas-app-operator"

    def update(self):
        # 1. 检查目标 chart 是否合法
        self._check_target_chart()

        self._print_dividing_line()

        # 2.1 移除不需要的换行
        self._remove_useless_newline()
        # 2.2 patch 部分 chart 文件内容
        self._patch_chart_file_contents()
        # 2.3 部分 chart 文件追加内容
        self._wrap_chart_file_contents()
        # 2.4 使用处理完的 chart 文件替换原 chart 的
        self._replace_chart_yaml_files()
        # 2.5 检查是否存在未处理的文件
        self._check_left_files()

        self._print_dividing_line()

        # 3.1 patch values 文件
        self._patch_values_file()
        # 3.2 对新旧 values 文件进行 diff，输出需要手动修改的
        self._diff_values()

        self._print_dividing_line()

        # 4. 清理工作空间
        self._clean_workspace()

    def _check_target_chart(self):
        """检查目标路径的 chart 是否存在"""
        if not path.isfile(self.chart_target_dir / "Chart.yaml"):
            raise Exception("target chart.yaml not exists")  # noqa: TRY002

        if not path.isfile(self.chart_target_dir / "values.yaml"):
            raise Exception("target values.yaml not exists")  # noqa: TRY002

        if not path.isdir(self.chart_target_dir / TMPL_DIR):
            raise Exception(f"target {TMPL_DIR} dir not exists")  # noqa: TRY002

        for sub_tmpl_dir in ["crds", "controller", "webhooks"]:
            if not path.isdir(self.chart_target_dir / TMPL_DIR / sub_tmpl_dir):
                raise Exception(f"target {TMPL_DIR}/{sub_tmpl_dir} dir not exists")  # noqa: TRY002

    def _patch_chart_file_contents(self):
        """对 chart 文件的部分内容进行替换"""
        for filepath, patch_list in content_patch_conf.items():
            fp = self.chart_source_dir / TMPL_DIR / filepath

            contents = fp.read_text()
            for src_str, dst_str in patch_list:
                contents = contents.replace(src_str, dst_str)

            fp.write_text(contents)

    def _wrap_chart_file_contents(self):
        """对部分文件追加/填充内容"""
        for filepath, wrap_contents in content_wrap_conf.items():
            fp = self.chart_source_dir / TMPL_DIR / filepath
            # 如果不存在，则创建空文件
            if not os.path.exists(fp):
                open(fp, "w").close()

            file_contents = fp.read_text()
            contents = wrap_contents.front + file_contents + wrap_contents.back
            fp.write_text(contents)

    def _remove_useless_newline(self):
        """去除 go-yaml unmarshal 中不需要的换行"""
        for src_files in filepath_conf.values():
            for src in src_files:
                if not src.endswith("yaml"):
                    continue

                fp = self.chart_source_dir / TMPL_DIR / src
                try:
                    contents = fp.read_text().splitlines()
                except FileNotFoundError:
                    print(f"file {src} not exists, auto create...")
                    fp.touch()
                    continue

                for idx in range(len(contents)):
                    # 忽略第一行，因为首行不会是被强制换行的
                    if (
                        idx
                        and contents[idx].count("}}")
                        and contents[idx - 1].count("{{") - contents[idx - 1].count("}}") == 1
                    ):
                        # 去掉上一行原来的换行符，拼接上当前行，把当前行设置为空字符串
                        contents[idx - 1] = contents[idx - 1].rstrip() + " "
                        contents[idx - 1] += contents[idx].lstrip()
                        contents[idx] = ""

                # 使用换行符号拼接每行的内容，并且在最后添加新空行
                fp.write_text("\n".join([line for line in contents if line]) + "\n")

    def _replace_chart_yaml_files(self):
        """使用新的 Charts 中的文件，替换原有的文件"""
        for dst, src_files in filepath_conf.items():
            print(f"replace {dst} with merged {src_files}")
            contents = []
            for src in src_files:
                src_fp = self.chart_source_dir / TMPL_DIR / src
                contents.append(src_fp.read_text())
                os.remove(src_fp)

            dst_fp = self.chart_target_dir / TMPL_DIR / dst
            dst_fp.write_text("---\n".join(contents))

        print(f"successfully replace {len(filepath_conf)} chart files!")

    def _check_left_files(self):
        # 有些文件是开发用的，不需要放到 chart 中，在检查时候跳过
        not_chart_required_files = ["docker-registry.yaml"]

        tmpl_dir = self.chart_source_dir / TMPL_DIR
        for _, _, files in walk(tmpl_dir):
            for file in files:
                if file in not_chart_required_files:
                    continue
                raise Exception(f"Some files are left in the directory ({tmpl_dir}), please check if they are needed")  # noqa: TRY002

    def _patch_values_file(self):
        """对 values 中的部分配置进行调整"""
        fp = self.chart_source_dir / "values.yaml"
        values = yaml.load(fp.read_text(), yaml.SafeLoader)

        # 镜像，副本等平铺
        values["proxyImage"] = {
            "registry": "hub.bktencent.com",
            "repository": "blueking/kube-rbac-proxy",
            "pullPolicy": "IfNotPresent",
            "tag": "v0.14.0",
        }
        values["image"] = {
            "registry": "hub.bktencent.com",
            "repository": "blueking/bkpaas-app-operator",
            "pullPolicy": "IfNotPresent",
            "tag": "0.0.1",
        }
        values["replicaCount"] = values["controllerManager"]["replicas"]
        values["resources"] = values["controllerManager"]["manager"]["resources"]

        del values["controllerManager"]

        # 镜像拉取凭证
        del values["dockerRegistry"]
        values["imagePullSecrets"] = []

        # 名称相关
        values["nameOverride"] = ""
        values["fullnameOverride"] = ""

        # manager 配置相关
        values["controller"] = values["managerConfig"]["controllerManagerConfigYaml"]
        values["controller"]["zapOpts"] = {"zapDevel": "false"}
        del values["managerConfig"]

        # 白名单控制配置挪到顶层
        values["accessControl"] = {"enabled": False, "redisConfigKey": ""}
        # PA 访问日志统计挪到顶层
        values["paasAnalysis"] = {"enabled": False}
        # 租户网关访问守卫挪到顶层
        values["tenantGuard"] = {"enabled": False}
        del values["controller"]["ingressPlugin"]

        values["resLimits"] = values["controller"].pop("resLimits")
        values["resRequests"] = values["controller"].pop("resRequests")
        values["autoscaling"] = values["controller"].pop("autoscaling")
        values["maxProcesses"] = values["controller"].pop("maxProcesses")

        # 平台配置挪到顶层，依旧保留 Config 后缀以兼容存量 values
        values["platformConfig"] = values["controller"].pop("platform")

        # service monitor
        values["serviceMonitor"] = {"enabled": False}

        # 证书管理相关
        values["cert"] = {
            "managerEnabled": False,
            "autoGenerate": True,
            "webhookCert": "",
            "webhookKey": "",
            "webhookCaBundle": "",
        }

        fp.write_text(yaml.dump(values))

    def _diff_values(self):
        """
        生成新旧 values 的 diff 结果，人工处理！
        不直接替换的原因是无法保留原有 values 中的注释，空行，顺序等
        """
        new_fp = self.chart_source_dir / "values.yaml"
        new_values = new_fp.read_text().splitlines()

        old_fp = self.chart_target_dir / "values.yaml"
        old_values = yaml.dump(yaml.load(old_fp.read_text(), yaml.SafeLoader)).splitlines()

        diff_rets = list(difflib.unified_diff(old_values, new_values, "old", "new"))
        if not diff_rets:
            print("diff values file found nothing...")
            return

        print("diff values file found something need to be resolved...")
        for line in difflib.unified_diff(old_values, new_values, "old", "new"):
            print(line)

    def _clean_workspace(self):
        """一切执行完成后，清理工作空间"""
        print("clean workspace...")
        shutil.rmtree(self.chart_source_dir)

    @staticmethod
    def _print_dividing_line():
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    """根据 helmify 生成的新 Chart，更新原来的 Chart"""
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", type=str, default="/tmp/bkpaas-app-operator")
    args = parser.parse_args()

    HelmChartUpdater(args.d).update()
