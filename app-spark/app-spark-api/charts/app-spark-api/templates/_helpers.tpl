{{/* Keep resource names and selectors consistent with the reference chart. */}}
{{- define "app-spark-api.name" -}}
{{- include "common.names.name" . -}}
{{- end -}}

{{- define "app-spark-api.fullname" -}}
{{- include "common.names.fullname" . -}}
{{- end -}}

{{- define "app-spark-api.selectorLabels" -}}
{{- include "common.labels.matchLabels" . -}}
{{- end -}}

{{- define "app-spark-api.labels" -}}
{{- include "common.labels.standard" . -}}
{{- end -}}

{{- define "app-spark-api.image" -}}
{{/* common 2.13.3 does not supply an appVersion fallback; preserve the chart's default tag. */}}
{{- $image := merge (dict "tag" (.Values.image.tag | default .Chart.AppVersion)) .Values.image -}}
{{- include "common.images.image" (dict "imageRoot" $image "global" .Values.global) -}}
{{- end -}}

{{/* Keep top-level imagePullSecrets compatible while including only images used by this Pod. */}}
{{- define "app-spark-api.imagePullSecrets" -}}
{{- $images := prepend .images (dict "pullSecrets" .context.Values.imagePullSecrets) -}}
{{- include "common.images.renderPullSecrets" (dict "images" $images "context" .context) -}}
{{- end -}}

{{/* A fresh Job per Helm revision avoids modifying immutable Job pod templates. */}}
{{- define "app-spark-api.migrateJobName" -}}
{{- printf "%s-migrate-%d" (include "app-spark-api.fullname" . | trunc 50 | trimSuffix "-") (int .Release.Revision) -}}
{{- end -}}

{{/* Dynaconf @json preserves types, including numeric-looking passwords as strings. */}}
{{- define "app-spark-api.envValue" -}}
{{- printf "@json %s" (mustToJson .) | quote -}}
{{- end -}}
