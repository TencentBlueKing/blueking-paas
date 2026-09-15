{{/* Keep resource names and selectors consistent with the sibling app-spark-api chart. */}}
{{- define "app-spark-forgejo.name" -}}
{{- include "common.names.name" . -}}
{{- end -}}

{{- define "app-spark-forgejo.fullname" -}}
{{- include "common.names.fullname" . -}}
{{- end -}}

{{- define "app-spark-forgejo.selectorLabels" -}}
{{- include "common.labels.matchLabels" . -}}
{{- end -}}

{{- define "app-spark-forgejo.labels" -}}
{{- include "common.labels.standard" . -}}
{{- end -}}

{{- define "app-spark-forgejo.image" -}}
{{/* common 2.13.3 does not supply an appVersion fallback; preserve the chart's default tag. */}}
{{- $image := merge (dict "tag" (.Values.image.tag | default .Chart.AppVersion)) .Values.image -}}
{{- include "common.images.image" (dict "imageRoot" $image "global" .Values.global) -}}
{{- end -}}

{{/* Keep top-level imagePullSecrets compatible; this chart only ever pulls one image. */}}
{{- define "app-spark-forgejo.imagePullSecrets" -}}
{{- $images := list (dict "pullSecrets" .Values.imagePullSecrets) .Values.image -}}
{{- include "common.images.renderPullSecrets" (dict "images" $images "context" .) -}}
{{- end -}}

{{/* A fresh Job per Helm revision avoids modifying immutable Job pod templates. */}}
{{- define "app-spark-forgejo.initJobName" -}}
{{- printf "%s-init-%d" (include "app-spark-forgejo.fullname" . | trunc 50 | trimSuffix "-") (int .Release.Revision) -}}
{{- end -}}

{{- define "app-spark-forgejo.claimName" -}}
{{- .Values.persistence.existingClaim | default (printf "%s-data" (include "app-spark-forgejo.fullname" .)) -}}
{{- end -}}

{{/* 集群内地址。init Job 用它，避免依赖可能尚未生效的 Ingress 和 TLS。 */}}
{{- define "app-spark-forgejo.clusterUrl" -}}
{{- printf "http://%s:%d" (include "app-spark-forgejo.fullname" .) (int .Values.service.port) -}}
{{- end -}}

{{/*
对外根地址。显式配置优先；其次由 Ingress 推导（配了 tls 用 https）；
都没有时退回集群内地址。Forgejo 用它生成 clone URL，调用方必须能解析。
*/}}
{{- define "app-spark-forgejo.rootUrl" -}}
{{- if .Values.server.rootUrl -}}
{{- trimSuffix "/" .Values.server.rootUrl -}}
{{- else if .Values.ingress.enabled -}}
{{- printf "%s://%s" (ternary "https" "http" (not (empty .Values.ingress.tls))) .Values.ingress.host -}}
{{- else -}}
{{- include "app-spark-forgejo.clusterUrl" . -}}
{{- end -}}
{{- end -}}

{{/* DOMAIN 只要主机名：从根地址里去掉 scheme、端口和路径。 */}}
{{- define "app-spark-forgejo.domain" -}}
{{- if .Values.server.domain -}}
{{- .Values.server.domain -}}
{{- else -}}
{{- $parts := include "app-spark-forgejo.rootUrl" . | splitList "/" -}}
{{- index $parts 2 | splitList ":" | first -}}
{{- end -}}
{{- end -}}

{{/*
Forgejo 的配置不变量，以 YAML 文本给出，调用方用 fromYaml 取回。
写成文本而不是 dict 字面量，是为了能在模板里给每条加注释——Go 模板的 action 内部
不允许注释。逐条完整的「作用 / 必要性」在 ../../compose.yaml，那里是唯一说明来源，
这里只留一句提要。值统一用字符串，类型转换交给 environment-to-ini。
*/}}
{{- define "app-spark-forgejo.invariantConfig" -}}
{{- $db := .Values.database }}
FORGEJO__database__DB_TYPE: "mysql"
FORGEJO__database__HOST: {{ printf "%s:%d" $db.host (int $db.port) | quote }}
FORGEJO__database__NAME: {{ $db.name | quote }}
FORGEJO__database__USER: {{ $db.user | quote }}
{{/* 对外身份：决定 clone URL、跳转和邮件链接。容器内 HTTP 端口固定 3000。 */}}
FORGEJO__server__DOMAIN: {{ include "app-spark-forgejo.domain" . | quote }}
FORGEJO__server__HTTP_PORT: "3000"
FORGEJO__server__ROOT_URL: {{ include "app-spark-forgejo.rootUrl" . | quote }}
{{/* 不发 SSH 密钥，只走 HTTP + token；少一个协议就少一套密钥和防火墙开口。 */}}
FORGEJO__server__DISABLE_SSH: "true"
{{/* 跳过首次访问的安装向导，否则空卷启动会卡在 web 安装页，init 进不去。 */}}
FORGEJO__security__INSTALL_LOCK: "true"
{{/* 仓库名写错必须失败，不能静默冒出一个新仓让 Project 对不上。 */}}
FORGEJO__repository__ENABLE_PUSH_CREATE_USER: "false"
FORGEJO__repository__ENABLE_PUSH_CREATE_ORG: "false"
{{/* 仓库范围 token 对所有公开仓仍有只读权限，public 是隔离性漏洞而不是偏好。 */}}
FORGEJO__repository__DEFAULT_PRIVATE: "private"
{{/* 建仓、分支保护、Agent push、检查点都钉在这一条分支名上。 */}}
FORGEJO__repository__DEFAULT_BRANCH: "main"
{{/* 能注册就能在组织外建仓，绕过「一项目一私有仓」。 */}}
FORGEJO__service__DISABLE_REGISTRATION: "true"
{{/* 避免仓库列表、clone URL、默认分支被匿名扫到；/api/healthz 仍然公开。 */}}
FORGEJO__service__REQUIRE_SIGNIN_VIEW: "true"
{{/* 所有 Project 仓必须落在受控的 app-spark 组织下。 */}}
FORGEJO__service__DEFAULT_ALLOW_CREATE_ORGANIZATION: "false"
{{- end -}}

{{- define "app-spark-forgejo.validateValues" -}}
{{- if ne (int .Values.replicaCount) 1 }}
{{- fail "Forgejo 独占 /data 里的 Git 对象和仓库锁，replicaCount 必须为 1。" }}
{{- end }}
{{- if not .Values.database.host }}
{{- fail "database.host 必填：本 chart 只对接外部 MySQL 8，不安装数据库。" }}
{{- end }}
{{- if not .Values.database.password }}
{{- fail "database.password 必填。" }}
{{- end }}
{{- if and .Values.ingress.enabled (not .Values.ingress.host) }}
{{- fail "ingress.enabled 时必须设置 ingress.host。" }}
{{- end }}
{{- if and .Values.init.enabled (or (not .Values.auth.adminPassword) (not .Values.auth.serviceAccountPassword)) }}
{{- fail "init.enabled 时 auth.adminPassword 和 auth.serviceAccountPassword 必填，且部署后保持稳定。" }}
{{- end }}
{{- end -}}
