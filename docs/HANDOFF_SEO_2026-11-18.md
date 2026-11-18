# Traspaso para el chat SEO — 18-nov-2026

Del chat de producto (app) al chat SEO. No toqué `web/landing.html`, `web/i18n/*.json`, `app/i18n_pages.py`, el `llms.txt` de `app/main.py` ni las páginas públicas de contenido. Aquí van los textos para que los integres tú.

## 1. Estado del código (sin commit todavía)

- El arreglo del país pedido por ti ya está hecho: «PE» queda solo como respaldo de lotes viejos. Detalle en `CHANGELOG.md`, entrada «2026-11-18 (3)». Pruebas en `tests/test_country.py`; la suite completa pasa (446).
- Toqué `app/main.py` en muchas partes, pero no el bloque de `llms.txt`. **Edita sobre el archivo actual**, no sobre una copia anterior.
- Archivos nuevos: `app/countries.py`, `app/exporter.py`, `app/satellite.py` y `web/countries.js` (lista de países para los selectores, en caché del service worker v5).
- Enrique hará los commits separados (ver sección 5). No despliegues hasta que estén.

## 2. Funciones nuevas que la web puede contar (todas reales y probadas)

| Función | Qué decir | Qué NO decir |
|---|---|---|
| Evidencia satelital propia | Imagen Sentinel-2 de 2020 contra la más reciente en cada parcela, con índice de cambio de vegetación; radar Sentinel-1 cuando hay nubes. | «Modelo de IA propio» o «detecta todo». Solo puede subir una parcela a «revisar», nunca bajarla. |
| Revisión experta | Un analista de Origen revisa la alerta con todas las imágenes y deja su conclusión en el dossier. | «Cada alerta la revisa un experto» (es a pedido) o «cero falsos positivos». |
| Alta resolución bajo pedido | Imagen de archivo de satélites comerciales (15–50 cm). Se cotiza antes y solo se compra si el cliente acepta. | Precios fijos, o «siempre hay imagen» (en zonas nubladas puede no haberla). |
| Formatos | Importa y exporta Excel, CSV, GeoJSON, KML/KMZ (Google Earth), GPX y Shapefile. | — |
| Cualquier país | El país de producción se elige por lote y el dossier y el GeoJSON lo usan. Un envío puede juntar varios países. | — |
| Resumen del panel | El panel muestra cuántos lotes están en orden, a revisar u observados, y el siguiente paso. | — |

## 3. Textos propuestos (es / en)

**Sección de tecnología (landing), un bloque nuevo:**
- es: «**Evidencia propia de cada parcela.** Además de las 4 fuentes, Origen arma su propia imagen Sentinel-2 de 2020 y la compara con la más reciente. Si hay nubes, mira con el radar Sentinel-1. ¿Sigue la duda? Pide una revisión experta: un analista revisa la alerta y, si hace falta, conseguimos imagen de 15–50 cm. Te cotizamos antes y solo compramos si aceptas.»
- en: «**Our own evidence for every plot.** On top of the 4 sources, Origen builds its own Sentinel-2 image from 2020 and compares it with the latest one. Under clouds, it checks Sentinel-1 radar. Still unsure? Request an expert review: an analyst checks the alert and, if needed, we source 15–50 cm imagery. You get a quote first, and we only buy if you accept.»

**Formatos (FAQ o bloque «Importas…»):**
- es: «¿En qué formato tengo que tener mis parcelas? En el que ya uses: Excel, CSV, GeoJSON, KML o KMZ de Google Earth, GPX del GPS o Shapefile. Y las descargas en los mismos formatos.»
- en: «What format do my plots need to be in? Whatever you already use: Excel, CSV, GeoJSON, Google Earth KML/KMZ, GPS GPX or Shapefile. And you can download them in the same formats.»

**`llms.txt` / featureList (añadir):** evidencia Sentinel-2/Sentinel-1 por parcela; revisión experta a pedido; imagen de alta resolución bajo pedido con cotización previa; importación y exportación KML/KMZ/GPX/Shapefile/Excel; país de producción por lote (ISO 3166-1).

## 4. Página «Empezar» (`/empezar`)

Me parece que es tuya porque se traduce con `web/i18n/*.json`. Propuestas:
- Añadir el campo **País** (selector). Puedes usar `web/countries.js` y `fillCountrySelect(select, "PE")`. El backend de `/lead` todavía no lo guarda; si lo agregas, avísame y lo sumo a `LeadIn`.
- El teléfono de ejemplo `+51 999 999 999` y «Mi Empresa S.A.C.» son del Perú. Mejor neutros: «+57 300 000 0000» o «Tu empresa».
- La casilla cita solo la Ley 29733 (Perú). Con clientes de otros países conviene «Acepto la política de privacidad» y que la política cubra la ley de cada país y el RGPD.
- Estilo: los campos cuadrados y el botón amarillo con sombra no se parecen al resto de la app (bordes redondeados de 4 px y botón azul). Si la rehaces, alinéala con el panel.

## 5. Commits propuestos (los corre Enrique, desde la carpeta `mvp`)

```
git add app/countries.py web/countries.js tests/test_country.py app/models.py app/geo.py app/portability.py app/gemini.py app/copilot.py app/importer.py web/sw.js
git commit -m "País de producción por lote (ISO 3166-1): sin PE fijo; dossier y GeoJSON usan el país del lote"

git add -A app tests tools web/panel.html web/capturar.html web/share.html web/i18n.js requirements.txt CHANGELOG.md docs/HANDOFF_SEO_2026-11-18.md
git commit -m "Evidencia Sentinel-2/1, revisión experta y alta resolución bajo pedido, formatos KML/KMZ/GPX/Shapefile, archivos sin tope de 1 MiB, UX del panel, la captura y la página del comprador"
```

`app/main.py`, `app/dossier.py` y `web/capturar.html` mezclan los dos temas, así que van en el segundo commit.
