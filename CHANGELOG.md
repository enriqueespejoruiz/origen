# Changelog — Origen

Formato: cambios agrupados por fecha. El proyecto sigue el espíritu *build-in-public* del XPRIZE.

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

## Antes
- Captura PWA (GPS + polígono + foto), multi-tenant con login Google, dossier EUDR + GeoJSON TRACES,
  envíos consolidados, 4 fuentes de deforestación (Hansen/JRC/GFW alerts/WDPA), anti-fraude de
  volumen, notarización Fase 0 + `/verificar`, export CSV, landing B2B.
