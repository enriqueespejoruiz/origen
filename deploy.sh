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

gcloud run deploy "$SERVICE" \
  --source . \
  --project "$PROJECT" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --timeout 300 \
  --update-env-vars "GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=${PROJECT},GOOGLE_CLOUD_LOCATION=${REGION},GEMINI_MODEL=gemini-2.5-flash"
# --update-env-vars (no --set-env-vars): añade/actualiza solo estas claves y CONSERVA el resto
# (secretos como GFW_API_KEY, GOOGLE_OAUTH_CLIENT_ID, SESSION_SECRET, GCS_BUCKET).

echo "▸ Listo. URL del servicio:"
gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" \
  --format 'value(status.url)'
