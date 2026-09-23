{{/*
Expand the name of the chart.
*/}}
{{- define "app-spark-ui.name" -}}
{{- include "common.names.name" . -}}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "app-spark-ui.fullname" -}}
{{- include "common.names.fullname" . -}}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
Common labels.
*/}}
{{- define "app-spark-ui.labels" -}}
{{- include "common.labels.standard" . -}}
{{- end }}

{{/*
Selector labels.
*/}}
{{- define "app-spark-ui.selectorLabels" -}}
{{- include "common.labels.matchLabels" . -}}
{{- end }}

{{- define "app-spark-ui.image" -}}
{{/* common 2.13.3 does not supply an appVersion fallback; preserve the chart's default tag. */}}
{{- $image := merge (dict "tag" (.Values.image.tag | default .Chart.AppVersion)) .Values.image -}}
{{- include "common.images.image" (dict "imageRoot" $image "global" .Values.global) -}}
{{- end -}}

{{/* Keep top-level imagePullSecrets compatible while including only images used by this Pod. */}}
{{- define "app-spark-ui.imagePullSecrets" -}}
{{- $images := prepend .images (dict "pullSecrets" .context.Values.imagePullSecrets) -}}
{{- include "common.images.renderPullSecrets" (dict "images" $images "context" .context) -}}
{{- end -}}
