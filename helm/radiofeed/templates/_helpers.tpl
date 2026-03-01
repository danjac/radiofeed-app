{{/*
Extract the PostgreSQL major version from the image tag.
e.g. "postgres:18.1-bookworm" -> "18"
*/}}
{{- define "radiofeed.postgresVersion" -}}
{{- $tag := .Values.postgres.image | splitList ":" | last -}}
{{- $tag | splitList "." | first -}}
{{- end }}
