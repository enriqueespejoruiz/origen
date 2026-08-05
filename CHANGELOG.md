# Changelog — Origen

Formato: cambios agrupados por fecha. El proyecto sigue el espíritu *build-in-public* del XPRIZE.

## 2026-06-27 (2) — Demo por link + importación masiva
- **Acceso demo** `GET /demo?key=…` (env `DEMO_KEY`): sesión de invitado sin login, coop sandbox
  precargada (3 lotes con veredictos distintos + envío "Contenedor Taipéi #1"). 404 sin la llave.
- **Importación masiva** (`app/importer.py`): la coop que ya tiene la georreferencia sube
  **Excel/CSV/GeoJSON** (encabezados flexibles ES/EN, puntos o polígonos, agrupación por lote o
  productor) → mismos lotes → misma verificación → mismo sello. Endpoints `POST /api/import` +
  `GET /api/import/template`; botón "Importar parcelas" + modal en el panel. Dependencia: `openpyxl`.
  Tests en el suite.

## 2026-06-27 — Canal, vigilancia y legalidad

### WhatsApp (Cloud API)
- `app/whatsapp.py`: `send_text()` (alertas/respuestas) + `parse_messages()`. Webhook `GET/POST
  /webhooks/whatsapp`: el gerente envía un código de lote (LOT-…) o envío (ENV-…) y recibe el estado
  EUDR + el link de la página. Solo lecturas seguras — nunca ejecuta órdenes del mensaje entrante.
  Best-effort: sin credenciales, no rompe nada. Config: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`,
  `WHATSAPP_VERIFY_TOKEN`.

### Monitoreo continuo + alertas
- `app/monitor.py`: `run_monitor()` re-verifica las parcelas y crea una **alerta** si el veredicto
  empeora (una parcela se vuelve no conforme), actualizando el estado y el cache. Endpoint protegido
  `POST /cron/monitor` (header `X-Cron-Token`) para Cloud Scheduler; `GET /api/alerts` para el panel.
- Panel: **banner de alertas** arriba del tablero (lotes que cambiaron de estado). Config: `CRON_TOKEN`.

### Módulo de legalidad
- El EUDR exige legalidad además de cero deforestación. Endpoints `GET/POST /lots/{id}/legality`:
  checklist (título/tenencia, conformidad ambiental, laboral) + **carga de documentos** de respaldo.
- Panel: enlace **Legalidad** por lote → modal para completar y adjuntar. Alimenta el factor de
  legalidad del score de confianza; el dossier ya muestra esta sección.
- Tests nuevos (WhatsApp + monitoreo) en el suite.

## 2026-06-26 — Inteligencia del lote

### Copiloto Gemini
- Nuevo módulo `app/copilot.py`: `analyze_lot()` explica cada parcela y devuelve veredicto + acción
  (`excluir` / `sustentar` / `ninguna`), recomendación y borrador de legalidad; `chat()` responde
  preguntas EUDR. Razona con Vertex AI (`gemini-2.5-flash`) y cae a *fallbacks* deterministas si no
  hay credenciales o falla la llamada (la demo nunca se rompe).
- Endpoints `POST /lots/{id}/copilot` y `POST /copilot/chat` (con throttle).
- UI: botón flotante **✦ Copiloto** + panel de chat en el panel; enlace **Copiloto** por lote.

### Simulador what-if + score de confianza
- Nuevo módulo `app/scoring.py`:
  - `simulate()` / `simulate_consignment()` — excluye parcelas (lote) o lotes (envío) y calcula
    volumen conforme restante, % retenido y estado `apto`/`revisar`/`no_apto`. El volumen del lote se
    prorratea por área entre parcelas.
  - `confidence_score()` — score 0–100 ponderado: conformidad de parcelas (40), calidad geométrica
    TRACES (25), plausibilidad de volumen (20), legalidad documentada (15).
  - `suggest_exclusions[_consignment]()` — propone excluir las observadas (`high`).
- Endpoints `GET /lots/{id}/score`, `POST /lots/{id}/whatif`, `GET|POST /consignments/{cid}/whatif`.
- UI: enlace **Simular** en lotes y envíos → modal con gauge de score por factores, casillas por
  unidad y totales en vivo.
- Pruebas: `tests/test_origen.py` cubre prorrateo por área, límites del score y exclusión por envío.
- i18n ES/EN para toda la interfaz nueva.

### Notarización Fase 1 — anclaje en Bitcoin (OpenTimestamps)
- `app/notarize.py` pasa del registro SHA-256 (Fase 0) a un **anclaje público real**: `ots_stamp()`
  envía la huella a los calendarios OpenTimestamps y guarda una prueba **`.ots`** (verificable de
  forma independiente en opentimestamps.org / `ots verify`). `ots_status()` lee si ya está confirmada
  en un bloque de Bitcoin o pendiente; `ots_upgrade()` la completa cuando el bloque confirma. Todo
  best-effort: si falla la red/lib, conserva la Fase 0 y nada se rompe.
- Endpoints: `/api/verify` enriquecido (tipo de ancla + estado OTS), `GET /verificar/{id}.ots`
  (descarga la prueba), `POST /api/verify/upgrade`.
- `web/verificar.html`: muestra el estado del ancla (confirmado en Bitcoin / pendiente), botón para
  descargar la prueba `.ots` e instrucciones de verificación independiente. i18n ES/EN.
- Dependencia nueva: `opentimestamps-client`. Test de notarización en el suite.

### Compartir con el comprador + portabilidad de datos
- Nuevo módulo `app/portability.py`: `build_export_zip()` arma un ZIP con la data de la coop en
  **formatos abiertos** — `lotes.csv`, `lotes.geojson` (TRACES), `manifest.json` (con sellos de
  notarización), los dossiers PDF y un `LEEME.txt`. Es el moat de *la coop es dueña de su data*.
- Página pública del comprador `web/share.html` servida en `/s/c/{cid}` y `/s/{lot_id}`: marca,
  veredicto, datos del envío/lote, descargas (dossier + GeoJSON) y verificación. Reemplaza el envío
  de un PDF crudo por un link con todo.
- Endpoints `GET /api/share/c/{cid}`, `GET /api/share/{lot_id}` (resumen público seguro) y
  `GET /api/export.zip` (auth).
- Panel: enlace **Compartir** (copia el link del comprador) en lotes y envíos, botón **Llévate tu
  data**, y el WhatsApp ahora envía la página. i18n ES/EN. Test del ZIP en el suite.

## Antes
- Captura PWA (GPS + polígono + foto), multi-tenant con login Google, dossier EUDR + GeoJSON TRACES,
  envíos consolidados, 4 fuentes de deforestación (Hansen/JRC/GFW alerts/WDPA), anti-fraude de
  volumen, notarización Fase 0 + `/verificar`, export CSV, landing B2B.
