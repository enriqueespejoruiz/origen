# Changelog — Origen

Formato: cambios agrupados por fecha. El proyecto sigue el espíritu *build-in-public* del XPRIZE.

## 2026-11-18 (5) — Web: evidencia propia, revisión experta y formatos (traspaso del chat de la app)
- Portada (22 idiomas): bloque «Evidencia propia de cada parcela» en Tecnología (Sentinel-2 2020 frente a lo más reciente,
  radar Sentinel-1 con nubes, revisión experta e imagen de 15–50 cm cotizada antes) y FAQ de formatos (importa Excel, CSV,
  GeoJSON, KML/KMZ, GPX y Shapefile; exporta GeoJSON, KML/KMZ, Shapefile y Excel; GPX solo se importa).
- /eudr-software-importadores (7 idiomas): formatos, y revisión experta con alta resolución bajo pedido.
- llms.txt y featureList (es, en): evidencia propia, revisión experta, alta resolución, formatos y país por lote.

## 2026-11-18 (4) — Revisión de UX por usuario (gerente, técnico de campo, comprador)
- **Panel (gerente)**: el título es el nombre de la organización; **resumen** arriba (lotes, en orden, a revisar,
  observados, sin verificar) que filtra la lista al tocarlo, y un aviso de **siguiente paso**. Cada fila tiene dos
  acciones visibles (Dossier + Revisión experta o Compartir) y el resto en un menú «Más ▾» (antes eran 10 enlaces).
  Columnas «Estado» y «Acciones». Etiquetas con icono además del color: «✓ En orden», «! A revisar», «× Observado».
- **Cabecera**: «Salir» y «EN» eran invisibles (texto blanco sobre fondo blanco); corregido. En el celular la
  cabecera ya no desborda y las tablas pasan a tarjetas (antes había scroll lateral y se perdían Estado y Acciones).
- **Captura (técnico)**: cabecera sin desborde en 390 px; los lotes del servidor muestran el estado arriba y los
  enlaces debajo (la etiqueta se salía de la pantalla); controles de 44 px; «organización» en vez de «cooperativa».
- **Página del comprador**: país de producción, organización y fecha de verificación; conclusión del analista si la
  hay; logotipo de Origen; explicación sin jerga («mass-balance»). `/api/share/*` devuelve `countries`,
  `verified_at` y `analyst`.
- Foco visible en teclado (`:focus-visible`) y textos de las acciones con `aria-label`.

## 2026-11-18 (3) — País de producción por lote (ya no «PE» fijo)
- **`app/countries.py`**: países ISO 3166-1 alfa-2 con nombre en español e inglés (CLDR), orígenes frecuentes
  del EUDR primero; `norm()` acepta código o nombre («Colombia», «Costa de Marfil»); `of_lot()` devuelve «PE»
  solo para lotes antiguos guardados sin país (no se migra nada en Firestore).
- **Organización**: al crearla se elige su país (`/api/coop` acepta `country`); es el valor por defecto de sus lotes.
- **Captura**: selector «País de producción» (recuerda el último elegido; el mapa abre en ese país); la cola
  sin señal lo guarda y lo envía al sincronizar. Edición del lote: también el país.
- **Importación**: columna `pais`/`country` validada (código o nombre); vacía → país de la organización; en
  GeoJSON/KML/Shapefile se lee `ProducerCountry`/`country`. Plantilla con columna `pais` y ejemplo de Colombia.
- **Dossier y GeoJSON**: usan el país del lote («Colombia (CO)»); el dossier del envío lista todos los países.
  Un envío ya puede juntar lotes de varios países (antes se rechazaba).
- Textos sin Perú fijo: copiloto, resumen de Gemini, ayuda de coordenadas, ejemplos de región. `GET /api/countries`.
- Tests: `tests/test_country.py` (446 en total).

## 2026-11-18 (2) — Revisión experta: analista + alta resolución bajo pedido; archivos sin tope de 1 MiB
- **Panel**: en lotes «a revisar» u «observados», enlace **Alta resolución**: la coop pide imagen de archivo
  comercial (15–50 cm) para antes/después del corte, ve la cotización y la acepta o rechaza. Nada se compra
  sin su aceptación. Estados: solicitada → cotizada → aceptada → entregada (o sin imagen / cancelada).
- **API**: `GET/POST /lots/{id}/hires`, `POST /lots/{id}/hires/{hid}/accept|cancel`. Administración con llave
  de agente: `GET /admin/hires` (con la geometría de la parcela para buscar en el archivo),
  `POST /admin/hires/{hid}/quote|status|deliver`. Al entregar, la imagen se guarda en su propio documento
  (≤ 700 KB) y el dossier se regenera con la sección «Imagen de muy alta resolución (bajo pedido)».
- Aviso a Origen por WhatsApp si `HIRES_NOTIFY_WA` está configurado; siempre queda en el log (`hires_*`).
- `tools/hires_render.py`: recorta la entrega GeoTIFF a la parcela, ajusta el color y dibuja el borde.
- **Revisión del analista** (lo que Coolx vende como «un experto revisa cada alerta»): `POST /admin/lots/{id}/review`
  con conclusión `descartada | confirmada | campo`, nota y evidencia revisada. Sale en el dossier («Revisión del
  analista de Origen») y como etiqueta en el panel. Explica el veredicto automático; no lo reemplaza. El pedido
  desde el panel pasa a llamarse «Revisión experta» e incluye la opción «solo analista, sin compra».
- **Almacenamiento de archivos**: cada archivo (dossier, GeoJSON, fotos, imágenes) va en sus propios documentos
  de Firestore, en partes de 900 KB (`blobs/`). Antes todos los archivos de un lote compartían un documento con
  tope de 1 MiB y, con varias fotos, la escritura fallaba en silencio. Lee también el formato antiguo.
- **Exportar en otros formatos** (`app/exporter.py`): cada lote y cada envío se descargan también en
  Google Earth (KMZ), KML, Shapefile (.zip con capa de polígonos y de puntos, WGS84) y Excel (centroide + WKT).
  `GET /lots/{id}/export.{kmz|kml|shp|xlsx}`, `/consignments/{id}/export.{…}` y `/api/lots/export.{…}`
  (todas las parcelas de la coop en un archivo). En el panel: «Otros formatos…» por fila y «Exportar parcelas…».
- Tests: `tests/test_hires.py`, `tests/test_export_formats.py` (440 en total).

## 2026-11-18 — SEO global: 7 productos, cualquier país, importadores y estado de noviembre
- **Mensaje**: portada y metas en 22 idiomas con «7 productos, cualquier país»; H1 «tu envío»; descriptor
  «EUDR · 7 productos»; FAQ «¿Sirve para productores de cualquier país?»; bloque «¿Importas a la UE?»; los
  nombres de producto enlazan a sus guías. Las versiones europeas dejan de decir «de Perú». Requiere que la app
  ya no fije el país del productor en «PE» (lo hace el chat de la app).
- **Páginas nuevas**: /eudr-software-importadores y /eudr-30-diciembre-2026 (es, en, de, fr, it, nl, pl);
  /eudr-caucho, /eudr-palma, /eudr-soya, /eudr-madera y /eudr-ganado (es, en).
- **i18n_pages**: una página puede existir solo en algunos idiomas (`available`, `langs_for`, `x_default`);
  hreflang, selector, sitemap y enlaces internos lo respetan (donde no existe, el enlace va a la versión en inglés).
- **Estado del EUDR**: novedades de noviembre (plan de contingencia, versión 8.2.2 con la interfaz 4, ley alemana
  del 12-nov, Países Bajos), cronología y fuentes. La guía de TRACES, al día y sin «Perú» fijo.
- **llms.txt y schema**: funciones nuevas (featureList en es y en) y páginas nuevas. Sitemap: 332 URL. Tests: 421.

## 2026-11-04 — Los 7 productos del EUDR, Gemini vigente y tecnología en la landing
- **Catálogo de productos** (`app/commodities.py`): café, cacao, palma aceitera, soya, caucho, madera y
  ganado bovino, con alias (cacao→cocoa, palma→oil_palm, jebe→rubber…), partida SA por defecto,
  nombre científico y reglas. El dossier muestra el producto en su idioma; `extra.hs` y `extra.species`
  precisan la partida y la especie. Madera pide especie; ganado admite un punto por establecimiento.
- El anti-fraude de volumen solo se aplica donde hay techo fiable (café y cacao); antes, un producto
  desconocido caía en el techo del café. Los envíos comparan el producto normalizado (cacao = cocoa).
- **Gemini**: modelo por defecto `gemini-3.5-flash-lite` (Google retira `gemini-2.5-flash`), con respaldo
  automático `gemini-2.5-flash` → `gemini-3.8-flash` si un modelo no existe; `GOOGLE_CLOUD_LOCATION=global`.
  `/api/health` informa el modelo activo y la cadena de respaldo.
- **Landing**: sección de tecnología con las 4 fuentes (satélites, resolución, qué responde cada una),
  reglas del veredicto y sello en Bitcoin; sección de los 7 productos; FAQ actualizada. Traducido a los
  22 idiomas.
- Tests: `tests/test_commodities.py` (389 en total).

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
