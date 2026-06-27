# Origen — EUDR + Export Co-pilot

**Build with Gemini XPRIZE** · Co-piloto AI-native para que cooperativas y exportadores de
**café y cacao** del Perú generen, desde el celular, el paquete de datos que exige el
**Reglamento UE de Deforestación (EUDR 2023/1115)**: geolocalización parcela por parcela,
verificación contra fuentes satelitales y un **dossier + GeoJSON listo para TRACES** — más
inteligencia comercial del lote. Un solo flujo de datos, varias salidas.

🌐 **En producción:** https://origen-711831043664.us-central1.run.app

---

## Qué hace

- **Captura en campo (PWA, offline-first):** GPS de alta precisión, polígono para parcelas >4 ha,
  foto del predio, cantidad y legalidad. Instalable en el celular del técnico.
- **Verificación de deforestación:** chequeo por parcela contra **4 fuentes** — Hansen GFC (GFW Data
  API, licencia abierta), **JRC Global Forest Cover 2020** (mapa de referencia de la UE), **GFW
  Integrated Alerts** y **áreas protegidas WDPA**. Veredicto: `negligible` / `review` / `high`.
- **Dossier EUDR + GeoJSON TRACES:** PDF de marca (ES/EN) y GeoJSON en el formato que el sistema de
  la UE acepta (6 decimales, propiedades de productor/país/lugar), por **lote** o **consolidado por
  envío**.
- **Envíos (consignaciones):** agrupa decenas de parcelas de varios productores y regiones en **un
  solo dossier** por contenedor — como exige el EUDR para una operación comercial (sin *mass-balance*).
- **Copiloto Gemini:** explica cada hallazgo en lenguaje claro, recomienda qué parcela **excluir** o
  **sustentar**, redacta un borrador de legalidad y responde preguntas sobre el EUDR. Con *fallbacks*
  deterministas para no romper la demo.
- **Simulador what-if + score de confianza:** simula excluir parcelas/lotes observados y muestra, en
  vivo, el **volumen conforme** y el estado resultante (`apto`/`revisar`/`no apto`); resume la salud
  del lote en un **score 0–100** explicable (conformidad, geometría, volumen, legalidad).
- **Notarización (Fase 1):** ancla el hash del dossier en **Bitcoin vía OpenTimestamps** (prueba
  `.ots` verificable de forma independiente) y lo expone en `/verificar`.
- **WhatsApp (Cloud API):** la coop consulta el estado EUDR de un lote/envío enviando su código por
  WhatsApp; canal de cero fricción donde ya viven las cooperativas.
- **Monitoreo continuo + alertas:** re-verifica las parcelas periódicamente y avisa (banner en el
  panel) si una se vuelve no conforme — vigilancia, no un chequeo único.
- **Módulo de legalidad:** checklist (tenencia, ambiental, laboral) + carga de documentos por lote;
  el EUDR exige legalidad además de cero deforestación.
- **Multi-tenant:** login con Google, cuentas por cooperativa, roles e invitaciones, panel con
  búsqueda/filtro, export CSV y logs de uso.

## Stack

FastAPI · **Cloud Run** · **Vertex AI (`gemini-2.5-flash`)** · Firestore + Cloud Storage ·
GFW Data API / JRC COG (rasterio) · Shapely · ReportLab · PWA (service worker, i18n ES/EN en runtime).
Todo sobre **Google Cloud** (cumplimiento XPRIZE).

## Endpoints (selección)

| Método | Ruta | Qué hace |
|---|---|---|
| `GET` | `/`, `/capturar`, `/panel`, `/normativa`, `/empezar` | Landing, captura PWA, panel, normativa, onboarding |
| `POST` | `/auth/google`, `/auth/logout` · `GET /api/me` | Login multi-tenant |
| `POST` | `/capture` | Captura estructurada de campo (GPS + foto + legalidad) |
| `GET` | `/api/lots` · `GET /api/lots.csv` | Lotes de la coop + export |
| `POST` | `/api/consignments` · `GET /api/consignments` | Crear / listar envíos |
| `GET` | `/lots/{id}/dossier` · `/lots/{id}/geojson` | Dossier PDF + GeoJSON TRACES por lote |
| `GET` | `/consignments/{cid}/dossier` · `/geojson` · `POST /regenerate` | Dossier consolidado por envío |
| `POST` | `/lots/{id}/copilot` · `POST /copilot/chat` | **Copiloto Gemini** (análisis + chat) |
| `GET` | `/lots/{id}/score` · `POST /lots/{id}/whatif` | **Score + simulador** por lote |
| `GET` | `/consignments/{cid}/whatif` · `POST` | **Simulador** por envío |
| `GET` | `/verificar` · `/api/verify` · `/verificar/{id}.ots` | Verificación pública + prueba OpenTimestamps |
| `GET` | `/s/c/{cid}` · `/s/{lot}` · `/api/export.zip` | Página del comprador + portabilidad (ZIP) |
| `GET/POST` | `/webhooks/whatsapp` | Consulta de estado por WhatsApp (Cloud API) |
| `POST` | `/cron/monitor` · `GET /api/alerts` | Monitoreo continuo + alertas |
| `GET/POST` | `/lots/{id}/legality` | Checklist + documentos de legalidad |

## Correr local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # rellena las claves que tengas (funciona en modo STUB sin ellas)
uvicorn app.main:app --reload # http://localhost:8000  · panel en /panel · captura en /capturar
```

Sin claves, el chequeo de deforestación y Gemini usan *mocks* deterministas: la demo corre igual.

### Variables clave (`.env`)

- **Gemini:** `GEMINI_API_KEY` (AI Studio) **o** `GOOGLE_GENAI_USE_VERTEXAI=1` + `GOOGLE_CLOUD_PROJECT`
  (Vertex en producción). `GEMINI_MODEL=gemini-2.5-flash`.
- **Deforestación:** `GFW_API_KEY` (Global Forest Watch). `EE_PROJECT` opcional (Earth Engine).
- **Auth / sesión:** `GOOGLE_OAUTH_CLIENT_ID`, `SESSION_SECRET`, `PUBLIC_BASE_URL`.
- **Storage:** `GCS_BUCKET` (prod) o `DATA_DIR=./_data` (local).
- **WhatsApp (opcional):** `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_VERIFY_TOKEN`. En Meta,
  apunta el webhook a `…/webhooks/whatsapp` con ese verify token. Sin esto, el resto funciona igual.
- **Monitoreo (opcional):** `CRON_TOKEN`. Programa Cloud Scheduler para `POST /cron/monitor` con la
  cabecera `X-Cron-Token: <CRON_TOKEN>` (p. ej. diario).

## Desplegar (Cloud Run)

```bash
./deploy.sh         # build + deploy a Cloud Run (proyecto origen-eudr-2026, región us-central1)
```

El script usa `gcloud run deploy --source .` con el `Dockerfile` (instala `libexpat1` para el COG de
JRC). Requiere `gcloud auth login` en la cuenta del proyecto. Ver `deploy.sh` para las variables.

## Pruebas / CI

```bash
pytest -q
```

GitHub Actions (`.github/workflows/ci.yml`) compila y corre las pruebas en cada push. Cubren TRACES,
agregación de envíos, PDFs, geometría y el **simulador + score**.

## Cumplimiento XPRIZE

- ✅ Usa varios productos **Google Cloud** (Cloud Run, Vertex AI, Firestore, Cloud Storage).
- ✅ Llama a la **Gemini API** en producción (extracción, generación y copiloto).
- ✅ Proyecto nuevo, repo con código, demo funcional en vivo; logs de Cloud Run como evidencia.

## Estructura

```
app/        FastAPI: main, gemini, deforestation, dossier, geo, scoring, copilot, notarize, auth, storage
web/        PWA: panel.html, captura, landing, i18n.js, service worker
tests/      pytest (sin red ni GCP)
docs/       guías de marca y normativa
Dockerfile  runtime Cloud Run (Python 3.12 + libexpat1)
deploy.sh   build + deploy a Cloud Run
```

> Documento técnico del MVP. La estrategia, validación de mercado y roadmap viven en `../` (docs 01–27).
