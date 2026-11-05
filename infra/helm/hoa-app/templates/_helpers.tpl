{{/*
Resource name prefix. Using tenant.name (not .Release.Name) keeps names
stable even if the Helm release is ever renamed.
*/}}
{{- define "hoa-app.fullname" -}}
hoa-{{ .Values.tenant.name }}
{{- end }}

{{- define "hoa-app.labels" -}}
app.kubernetes.io/name: hoa-app
app.kubernetes.io/instance: {{ .Values.tenant.name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
tenant: {{ .Values.tenant.name }}
{{- end }}

{{- define "hoa-app.selectorLabels" -}}
app.kubernetes.io/name: hoa-app
app.kubernetes.io/instance: {{ .Values.tenant.name }}
{{- end }}

{{/*
Fails the render early with a clear message instead of deploying a tenant
with no identity — better than a 500 at request time months later.
*/}}
{{- define "hoa-app.validateTenant" -}}
{{- if not .Values.tenant.id }}
{{- fail "tenant.id is required (a UUID) — see infra/helm/hoa-app/tenants/*.yaml" }}
{{- end }}
{{- if not .Values.tenant.name }}
{{- fail "tenant.name is required — see infra/helm/hoa-app/tenants/*.yaml" }}
{{- end }}
{{- end }}
