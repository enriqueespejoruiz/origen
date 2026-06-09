# Origen - MVP (EUDR + Export Copilot)

Sistema AI-native para que exportadores/cooperativas de cafe-cacao entreguen a su comprador
europeo el paquete de datos que exige el EUDR (geolocalizacion + chequeo de deforestacion +
dossier), y de paso un perfil comercial multi-idioma del lote. Un solo flujo de datos, dos salidas.

## Flujo
captura (web/WhatsApp) -> Gemini estructura el lote -> chequeo de deforestacion (Earth Engine)
-> dossier (PDF + GeoJSON listo para TRACES NT) + perfil comercial.

## Correr local (sin nube, modo STUB)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python seed_demo.py            # pipeline demo end-to-end
uvicorn app.main:app --reload  # API en http://localhost:8000  (POST /intake, /lots/{id}/process)
```
Abre `web/index.html` (o sirvelo) para el formulario de captura.

## Activar Gemini de verdad
- Rapido (AI Studio): exporta `GEMINI_API_KEY=...` (ver `.env.example`).
- Produccion (Vertex AI en Google Cloud): `GOOGLE_GENAI_USE_VERTEXAI=1` + `GOOGLE_CLOUD_PROJECT`.

## Activar el chequeo de deforestacion real
Setea `EE_PROJECT` (Google Earth Engine). Sin esto usa un mock determinista.

## Endpoints
- `GET  /healthz`
- `POST /intake`               (form: notes, images[])
- `POST /lots/{id}/process`    -> corre deforestacion + genera dossier
- `GET  /lots/{id}/dossier`    -> descarga el PDF

## Despliegue
Ver `../06_Donde_montar_todo_Requisitos_tecnicos.md` (Cloud Run + Vertex AI + Earth Engine +
Firestore + Cloud Storage) y el `Dockerfile`.

## Cumplimiento XPRIZE
- Usa >=1 producto Google Cloud (Cloud Run/Vertex AI/Firestore/Storage/Earth Engine).
- Usa la Gemini API en >=1 llamada en produccion (extraccion + generacion).
- Proyecto nuevo, repo con codigo, demo funcional. Logs de uso = evidencia.
