#!/usr/bin/env bash
# Despliegue de Origen a Google Cloud Run.
# Requisitos: gcloud instalado y autenticado en la cuenta del proyecto
#   gcloud auth login        (cuenta dueña de origen-eudr-2026)
#   gcloud config set project origen-eudr-2026
#
# Uso:   bash deploy.sh
#
# Nota: 'gcloud run deploy --source .' CONSERVA las variables de entorno y secretos ya
# configurados en el servicio. Por eso aquí solo fijamos lo no-secreto; los secretos
# (GFW_API_KEY, GOOGLE_OAUTH_CLIENT_ID, SESSION_SECRET, GCS_BUCKET) permanecen como están.
set -euo pipefail

PROJECT="${PROJECT:-origen-eudr-2026}"
SERVICE="${SERVICE:-origen}"
REGION="${REGION:-us-central1}"

echo "▸ Desplegando '$SERVICE' a Cloud Run (proyecto $PROJECT, región $REGION)…"

# Secretos: GFW siempre; ArcGIS solo si ya existe el secreto esri-api-key en Secret Manager.
SECRETS="GFW_API_KEY=gfw-api-key:latest"
if gcloud secrets describe esri-api-key --project "$PROJECT" >/dev/null 2>&1; then
  SECRETS="$SECRETS,ESRI_API_KEY=esri-api-key:latest"
fi

gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --min-instances 1 \
  --update-env-vars "GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=global,GEMINI_MODEL=gemini-3.5-flash-lite,DATA_DIR=/tmp,PUBLIC_BASE_URL=https://eudrperu.com" \
  --update-secrets "$SECRETS"
# Gemini: Google está retirando gemini-2.5-flash (Vertex AI lo listó para el 20-oct-2026; la Gemini API,
# para el 1-dic-2026). config.py prueba en orden
# gemini-3.5-flash-lite → gemini-2.5-flash → gemini-3.8-flash si un modelo no está disponible.
# --update-env-vars / --update-secrets (no --set-*): añaden/actualizan solo estas claves y
# CONSERVAN el resto (GOOGLE_OAUTH_CLIENT_ID, SESSION_SECRET, GCS_BUCKET, etc.).

echo "▸ Listo. URL pública (la única que compartimos):"
echo "https://eudrperu.com"
