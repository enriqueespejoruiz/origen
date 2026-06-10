/* Origen — i18n ES/EN compartido. Traduce nodos de texto por su contenido en español. */
(function () {
  // Diccionario: clave = texto en español (recortado) -> valor en inglés.
  var T = {
    // -- nav / común --
    "MVP en vivo": "Live MVP",
    "Cómo funciona": "How it works",
    "Normativa EUDR": "EUDR regulation",
    "Verificar": "Verify",
    "Entrar": "Log in",
    "Capturar parcelas": "Capture plots",
    "Capturar": "Capture",
    "Panel": "Dashboard",
    "← Volver a Origen": "← Back to Origen",
    "Salir": "Log out",
    // -- hero --
    "Trazabilidad de origen · EUDR": "Origin traceability · EUDR",
    "Mantén tu café y cacao": "Keep your coffee and cocoa",
    "en el mercado europeo.": "in the European market.",
    "Origen genera el paquete de datos que exige el reglamento antideforestación de la UE —geolocalización de parcelas (con polígono para predios grandes), verificación contra cuatro fuentes satelitales oficiales y dossier para tu comprador— capturado desde el celular, en minutos.":
      "Origen produces the data package the EU's anti-deforestation law requires —plot geolocation (with a boundary polygon for larger plots), verification against four official satellite sources, and a dossier for your buyer— captured from a phone, in minutes.",
    "Empezar a capturar": "Start capturing",
    "Conversemos": "Let's talk",
    "4 fuentes oficiales": "4 official sources",
    "En español": "In Spanish",
    "para cooperativas": "for cooperatives",
    "Sin señal": "No signal",
    "funciona en campo": "works in the field",
    "Origen · captura": "Origen · capture",
    "en línea": "online",
    "limpio": "clean",
    "revisar": "review",
    "3 parcelas · sincronizadas": "3 plots · synced",
    "listo para TRACES": "ready for TRACES",
    // -- strip --
    "Construido con": "Built with",
    "GFW · Hansen · WDPA · JRC 2020 (UE)": "GFW · Hansen · WDPA · JRC 2020 (EU)",
    "UE TRACES-ready": "EU TRACES-ready",
    "Verificable · SHA-256": "Verifiable · SHA-256",
    // -- problema --
    "El problema": "The problem",
    "Sin la prueba, pierdes Europa.": "No proof, no Europe.",
    "Desde el 30 de diciembre de 2026, toda cooperativa que venda café o cacao a la UE debe demostrar —parcela por parcela— que no se cultivó en bosque talado después de 2020. Si no lo pruebas, no es una multa: te quedas fuera de tu principal mercado.":
      "From December 30, 2026, any cooperative selling coffee or cocoa to the EU must prove —plot by plot— that it wasn't grown on land cleared after 2020. If you can't prove it, it's not a fine: you're locked out of your main market.",
    "El reloj ya corre": "The clock is ticking",
    "30 dic 2026 para operadores grandes y medianos; 30 jun 2027 para pequeños. Europa toma cerca de la mitad del cacao y casi la mitad del café del Perú.":
      "Dec 30, 2026 for large and medium operators; Jun 30, 2027 for small ones. Europe takes about half of Peru's cocoa and nearly half of its coffee.",
    "Las soluciones son carísimas": "The tools are expensive",
    "Hechas para grandes importadores. Y, como denuncia Fairtrade, el costo del cumplimiento termina cayendo sobre el pequeño productor, que ya vive al límite.":
      "Built for big importers. And, as Fairtrade warns, the compliance cost ends up falling on the smallholder, who is already living on the edge.",
    "Geolocalizar ya no basta": "Geolocation is no longer enough",
    "Mapear parcelas se está volviendo gratis. Lo que tu comprador europeo paga es la evidencia verificada que de verdad puede presentar.":
      "Mapping plots is becoming free. What your European buyer pays for is verified evidence it can actually submit.",
    // -- cómo funciona --
    "De la parcela al dossier, en tres pasos.": "From plot to dossier, in three steps.",
    "Sin planillas, sin consultoras caras. El técnico captura en campo y la IA arma el paquete que tu comprador europeo necesita.":
      "No spreadsheets, no expensive consultants. The technician captures in the field and the AI assembles the package your European buyer needs.",
    "Captura en campo": "Field capture",
    "El técnico registra cada parcela con el GPS del celular y una foto; en predios de más de 4 ha camina el perímetro para el polígono que exige el EUDR. Funciona sin señal.":
      "The technician records each plot with the phone's GPS and a photo; for plots over 4 ha they walk the perimeter for the polygon the EUDR requires. Works offline.",
    "Verificación": "Verification",
    "Cruzamos cada parcela con cuatro fuentes oficiales —Hansen, alertas recientes, áreas protegidas (WDPA) y el mapa de referencia JRC 2020 de la UE— y marcamos limpio, revisar o deforestación.":
      "We cross-check each plot against four official sources —Hansen, recent alerts, protected areas (WDPA) and the EU's JRC 2020 reference map— and flag it clean, review or deforestation.",
    "Dossier listo": "Dossier ready",
    "Generamos el dossier y el GeoJSON que tu comprador presenta en el sistema de la UE (TRACES).":
      "We generate the dossier and the GeoJSON your buyer submits in the EU system (TRACES).",
    "Limpio": "Clean",
    "Sin pérdida de bosque tras el 31-dic-2020. Lista para el dossier.": "No forest loss after 31-Dec-2020. Ready for the dossier.",
    "Revisar": "Review",
    "Señal dudosa cerca del límite. La verificas antes de enviar a tu comprador.": "Uncertain signal near the boundary. Check it before sending to your buyer.",
    "Deforestación": "Deforestation",
    "Pérdida de bosque detectada. Se marca para excluir o sustentar.": "Forest loss detected. Flagged to exclude or substantiate.",
    // -- stats --
    "Commodities que regula el EUDR (café, cacao, soya, palma, madera, ganado, caucho)": "Commodities the EUDR regulates (coffee, cocoa, soy, palm, timber, cattle, rubber)",
    "Datos de deforestación de licencia abierta — sin candados ni costos ocultos": "Open-licensed deforestation data — no locks, no hidden costs",
    "Deforestación permitida solo hasta el 31 de diciembre de ese año": "Deforestation allowed only up to December 31 of that year",
    "Cumplimiento obligatorio para operadores grandes y medianos (30 dic)": "Mandatory compliance for large and medium operators (Dec 30)",
    // -- tecnología --
    "Tecnología transparente": "Transparent technology",
    "Potente por dentro, sin cajas negras.": "Powerful inside, no black boxes.",
    "Todo lo que afirmamos se puede comprobar: datos abiertos, IA de Google y una huella digital que cualquiera verifica.":
      "Everything we claim can be checked: open data, Google's AI, and a digital fingerprint anyone can verify.",
    "4 fuentes satelitales abiertas": "4 open satellite sources",
    "Hansen, alertas GFW, áreas protegidas (WDPA) y el mapa de referencia JRC 2020 de la UE. De licencia abierta, sin candados.":
      "Hansen, GFW alerts, protected areas (WDPA) and the EU's JRC 2020 reference map. Open-licensed, no locks.",
    "IA de Google (Gemini)": "Google AI (Gemini)",
    "Gemini, sobre Vertex AI, redacta el dictamen legible para tu comprador. El veredicto sale de los satélites, no del modelo: explicable y defendible.":
      "Gemini, on Vertex AI, writes the human-readable assessment for your buyer. The verdict comes from the satellites, not the model: explainable and defensible.",
    "Notarización en cadena (blockchain)": "On-chain notarization (blockchain)",
    "Cada dossier lleva una huella SHA-256 y un QR. Cualquiera escanea, sube el PDF y confirma que es auténtico y desde cuándo existe — sin que el archivo salga de su equipo.":
      "Every dossier carries a SHA-256 hash and a QR. Anyone scans it, uploads the PDF and confirms it's authentic and since when — without the file leaving their device.",
    "Abierto y auditable": "Open and auditable",
    "Sin mapas con licencia cerrada ni \"confía en mí\". Puedes ver y verificar cada fuente y cada dato — lo contrario de las cajas negras de los grandes.":
      "No closed-license maps, no \"trust me.\" You can see and verify every source and every data point — the opposite of the big players' black boxes.",
    // -- por qué --
    "Por qué Origen": "Why Origen",
    "Hecho para cooperativas, no para ingenieros.": "Built for cooperatives, not engineers.",
    "Abierto, auditable y verificable": "Open, auditable and verifiable",
    "Datos satelitales de licencia abierta y un dossier con huella digital verificable por cualquiera — sin cajas negras ni candados.":
      "Open-licensed satellite data and a dossier with a digital fingerprint anyone can verify — no black boxes, no locks.",
    "En minutos, en español": "In minutes, in your language",
    "Sin planillas ni consultoras caras: el técnico captura y el dossier se arma solo.":
      "No spreadsheets or expensive consultants: the technician captures and the dossier builds itself.",
    "Pensado para el campo": "Made for the field",
    "Captura sin internet y sincroniza sola cuando vuelve la señal.": "Captures offline and syncs on its own when the signal returns.",
    "Mantiene tu mercado": "Keeps your market",
    "Le entregas a tu comprador europeo justo lo que la ley le exige, a tiempo.": "You hand your European buyer exactly what the law requires, on time.",
    // -- faq --
    "Preguntas frecuentes": "FAQ",
    "Lo que más nos preguntan.": "What people ask us most.",
    "¿Necesito internet en la parcela?": "Do I need internet on the plot?",
    "No. El técnico captura todo en el celular —GPS y foto— sin señal, y las parcelas se envían solas cuando vuelve la conexión.":
      "No. The technician captures everything on the phone —GPS and photo— offline, and plots upload on their own when the connection returns.",
    "¿Qué pasa si una parcela tiene deforestación?": "What if a plot has deforestation?",
    "Se marca como «revisar» o «deforestación» para que la verifiques antes de enviarla a tu comprador. Origen es la herramienta de detección; la decisión final es tuya y del operador europeo.":
      "It's flagged as \"review\" or \"deforestation\" so you check it before sending it to your buyer. Origen is the detection tool; the final decision is yours and the EU operator's.",
    "¿Quién presenta la declaración en la UE?": "Who submits the declaration in the EU?",
    "El operador europeo (tu comprador/importador) la presenta en el sistema de la UE. Origen le entrega el paquete de datos listo para que pueda hacerlo.":
      "The EU operator (your buyer/importer) submits it in the EU system. Origen hands them the data package ready to do so.",
    "¿Sirve para café y cacao?": "Does it work for coffee and cocoa?",
    "Sí, y para cualquier producto del EUDR cuyo origen sea una parcela. Hoy nos enfocamos en café y cacao.":
      "Yes, and for any EUDR commodity whose origin is a plot of land. Today we focus on coffee and cocoa.",
    "¿Y las parcelas grandes (más de 4 ha)?": "What about large plots (over 4 ha)?",
    "La app deja caminar el perímetro y registrar el polígono de límites con el GPS — el formato que la UE exige para predios de más de 4 hectáreas. Las parcelas chicas se registran con un punto.":
      "The app lets you walk the perimeter and record the boundary polygon with GPS — the format the EU requires for plots over 4 hectares. Small plots are recorded with a point.",
    "¿Origen certifica el cumplimiento?": "Does Origen certify compliance?",
    "No. Origen entrega evidencia verificada, lista para sustentar la declaración; el responsable legal es el operador europeo que la presenta, y los sellos son complementarios. Nuestro trabajo es darte datos confiables que tu comprador acepte, no un sello.":
      "No. Origen delivers verified evidence, ready to support the declaration; the legal responsibility lies with the EU operator who submits it, and certifications are complementary. Our job is to give you trustworthy data your buyer accepts, not a seal.",
    "¿Cómo sé que un dossier es auténtico?": "How do I know a dossier is authentic?",
    "Cada dossier lleva un código QR y una huella digital (SHA-256). Cualquiera puede entrar a": "Every dossier carries a QR code and a digital fingerprint (SHA-256). Anyone can go to",
    "la página de verificación": "the verification page",
    ", subir el archivo y confirmar al instante que es auténtico y desde cuándo existe — sin que el archivo salga de su equipo.":
      ", upload the file and instantly confirm it's authentic and since when — without the file leaving their device.",
    // -- cta / footer --
    "Empieza a registrar tus parcelas hoy.": "Start registering your plots today.",
    "Sin instalar nada. Abre el enlace en el celular del técnico y captura tu primera parcela en minutos.":
      "Nothing to install. Open the link on the technician's phone and capture your first plot in minutes.",
    "Origen · Del origen a Europa, libre de deforestación.": "Origen · From origin to Europe, deforestation-free.",
    "Normativa": "Regulation",
    // -- verificar --
    "Verificar dossier": "Verify dossier",
    "Comprueba que un dossier de Origen es auténtico y desde cuándo existe.": "Check that an Origen dossier is authentic and since when it exists.",
    "Código de lote": "Lot code",
    "Buscar": "Search",
    "Comprobar el archivo (opcional)": "Check the file (optional)",
    "Sube el PDF que recibiste; tu navegador calcula su huella y la compara — el archivo no sale de tu equipo.": "Upload the PDF you received; your browser computes its hash and compares it — the file never leaves your device.",
    "La notarización registra la huella": "Notarization records the",
    "del dossier con su fecha de emisión, a prueba de manipulación. Anclaje público en cadena (OpenTimestamps): en preparación.": "hash of the dossier with its issue date, tamper-evident. Public on-chain anchoring (OpenTimestamps): coming soon.",
    // -- empezar --
    "Empieza hoy": "Start today",
    "Cuéntanos de tu cooperativa.": "Tell us about your cooperative.",
    "Déjanos tus datos y te ayudamos a dejar tus parcelas listas para el EUDR. Te contactamos en menos de 24 horas.": "Leave your details and we'll help get your plots EUDR-ready. We'll contact you within 24 hours.",
    "Tu nombre": "Your name", "Cooperativa / empresa": "Cooperative / company", "WhatsApp / teléfono": "WhatsApp / phone",
    "Eres…": "You are…", "Cooperativa / asociación": "Cooperative / association", "Exportador": "Exporter",
    "Comprador / importador": "Buyer / importer", "Otro": "Other", "Producto": "Product", "Café": "Coffee", "Cacao": "Cocoa", "Ambos": "Both",
    "¿Cuántos productores o parcelas, aprox.?": "How many producers or plots, approx.?", "Mensaje (opcional)": "Message (optional)",
    "Enviar y agendar": "Send and schedule", "Solo usamos tus datos para contactarte sobre Origen.": "We only use your details to contact you about Origen.",
    "¡Recibido! Te contactamos pronto.": "Got it! We'll contact you soon.",
    "Mientras, puedes probar la captura de parcelas ahora mismo — sin instalar nada.": "Meanwhile, you can try plot capture right now — nothing to install.",
    "Probar la captura": "Try capture", "← Inicio": "← Home",
    // -- panel --
    "Panel de Origen": "Origen dashboard", "Inicia sesión con Google para ver los lotes de tu cooperativa.": "Sign in with Google to see your cooperative's lots.",
    "Tu cooperativa": "Your cooperative", "¿Cómo se llama tu cooperativa o asociación?": "What's your cooperative or association called?",
    "Continuar": "Continue", "Panel de la cooperativa": "Cooperative dashboard", "Tus lotes": "Your lots",
    "Cada lote capturado, verificado contra las 4 fuentes, con su dossier listo para tu comprador.": "Every captured lot, verified against the 4 sources, with its dossier ready for your buyer.",
    "Riesgo": "Risk", "Fecha": "Date", "Descargas": "Downloads", "Ver en mapa": "View on map",
    "Aún no hay lotes.": "No lots yet.", "Captura tu primera parcela →": "Capture your first plot →",
    // -- captura --
    "captura": "capture", "Cooperativa": "Cooperative", "Nueva parcela": "New plot", "Productor": "Producer",
    "Área (ha)": "Area (ha)", "Región": "Region", "Cantidad (kg, aprox.)": "Quantity (kg, approx.)", "Idioma del dossier": "Dossier language",
    "Capturar ubicación GPS": "Capture GPS location", "Marcar esquina (vértice)": "Mark corner (vertex)",
    "Párate en cada esquina del predio y marca el vértice. Mínimo 3; lo ideal, todas las esquinas.": "Stand at each corner of the plot and mark the vertex. Minimum 3; ideally, all corners.",
    "Foto del predio (opcional) — cámara o galería": "Plot photo (optional) — camera or gallery",
    "Datos adicionales (opcional)": "Additional data (optional)", "Título / derecho de uso del predio": "Land title / use right",
    "Conformidad ambiental / forestal": "Environmental / forest compliance", "Conformidad laboral": "Labour compliance",
    "Comprador / importador UE (si lo conoces)": "EU buyer / importer (if known)", "País del comprador": "Buyer country",
    "Guardar parcela": "Save plot", "Sincronizar": "Sync",
    "Las parcelas se guardan en tu teléfono y se envían solas cuando hay señal.": "Plots are saved on your phone and upload on their own when there's signal.",
    "Captura de Origen": "Origen capture", "Inicia sesión con Google para capturar las parcelas de tu cooperativa.": "Sign in with Google to capture your cooperative's plots.",
    "Más ágil y seguro: tus capturas quedan firmadas con tu cuenta.": "Faster and safer: your captures are signed with your account.",
    "Instala Origen en tu teléfono": "Install Origen on your phone", "Instalar": "Install",
    "Funciona sin señal, como una app nativa. Ocupa casi nada.": "Works offline, like a native app. Takes almost no space.",
    "Cerrar": "Close",
    // -- panel: dinámico (lotes + envíos) --
    "Cada lote verificado contra las 4 fuentes, y los envíos consolidados listos para tu comprador.":
      "Every lot verified against the 4 sources, and consolidated shipments ready for your buyer.",
    "Marca los lotes que entran en un envío y pulsa «Crear envío».": "Tick the lots that go into a shipment and press 'Create shipment'.",
    "Una operación puede acopiar de muchas parcelas y regiones: el EUDR pide un dossier consolidado por envío.":
      "One operation may aggregate from many plots and regions: the EUDR requires one consolidated dossier per shipment.",
    "Envíos": "Shipments", "Envío": "Shipment", "Destino": "Destination", "Lotes": "Lots", "Parcelas": "Plots",
    "Volumen": "Volume", "Veredicto": "Verdict",
    "Aún no hay envíos. Marca lotes arriba y crea tu primer envío consolidado.": "No shipments yet. Tick lots above and create your first consolidated shipment.",
    "sin procesar": "unprocessed", "por procesar": "pending", "apto": "eligible", "segregar": "segregate",
    "deforestación": "deforestation", "Pendiente": "Pending", "enviado": "sent", "Sincronizado": "Synced",
    "Reprocesar": "Reprocess", "Regenerar": "Regenerate", "Limpiar": "Clear", "Crear envío": "Create shipment",
    "Nuevo envío": "New shipment", "Consolida los lotes seleccionados en un solo dossier EUDR.": "Consolidate the selected lots into a single EUDR dossier.",
    "Identificación del envío": "Shipment ID", "Destino (UE)": "Destination (EU)",
    "Comprador / importador (opcional)": "Buyer / importer (optional)", "Cancelar": "Cancel", "Seleccionar todo": "Select all",
    "No se pudieron cargar los lotes.": "Couldn't load lots.", "No se pudieron cargar los envíos.": "Couldn't load shipments.",
    // -- normativa (cuerpo) --
    "El reglamento de la UE contra la deforestación, claro.": "The EU anti-deforestation regulation, made clear.",
    "El EUDR (Reglamento UE 2023/1115) cambia cómo se exporta café y cacao a Europa. Aquí lo esencial, sin letra chica.":
      "The EUDR (Regulation EU 2023/1115) changes how coffee and cocoa are exported to Europe. Here's the essentials, no fine print.",
    "¿Qué es el EUDR?": "What is the EUDR?",
    "¿A qué productos aplica?": "Which products does it apply to?",
    "Y sus derivados (chocolate, muebles, cuero, etc.).": "And their derivatives (chocolate, furniture, leather, etc.).",
    "¿Qué exige?": "What does it require?",
    "Geolocalización:": "Geolocation:", "Libre de deforestación:": "Deforestation-free:", "Legalidad:": "Legality:",
    "las coordenadas (o el polígono) de cada parcela de origen.": "the coordinates (or polygon) of each plot of origin.",
    "el producto no viene de tierra deforestada después del 31-dic-2020.": "the product doesn't come from land deforested after 31-Dec-2020.",
    "la producción cumple las leyes del país de origen.": "production complies with the laws of the country of origin.",
    "Declaración de Diligencia Debida (DDS):": "Due Diligence Statement (DDS):",
    "se presenta en el sistema de información de la UE (TRACES).": "submitted in the EU information system (TRACES).",
    "Fechas clave (vigentes a 2026)": "Key dates (as of 2026)",
    "Operadores": "Operators", "grandes y medianos": "large and medium", "deben cumplir.": "must comply.",
    "pequeños y micro": "small and micro",
    "La aplicación se pospuso (de 2024 a 2025, y luego a 2026–2027) y se simplificó. Aunque la fecha legal es futura,":
      "Enforcement was postponed (from 2024 to 2025, then to 2026–2027) and simplified. Although the legal date is in the future,",
    "muchos compradores europeos ya piden los datos hoy": "many European buyers already ask for the data today",
    "para sus campañas.": "for their seasons.",
    "¿Quién presenta la declaración?": "Who submits the declaration?",
    "¿Qué hace Origen por ti?": "What does Origen do for you?",
    "Empezar a capturar parcelas": "Start capturing plots",
    "Fuentes oficiales": "Official sources",
    "Resumen informativo, no constituye asesoría legal. Las fechas y reglas del EUDR han cambiado varias veces; verifica siempre con las fuentes oficiales antes de tomar decisiones.":
      "Informational summary, not legal advice. EUDR dates and rules have changed several times; always check the official sources before making decisions.",
    "Inicio": "Home",
    // -- panel: equipo + filtros + export --
    "Equipo": "Team",
    "Invita a los técnicos de tu cooperativa: entran con su cuenta de Google y capturan a tu nombre.":
      "Invite your cooperative's technicians: they sign in with Google and capture under your name.",
    "Exportar CSV": "Export CSV", "Todos los riesgos": "All risks", "Sin procesar": "Unprocessed",
    "Miembro": "Member", "Rol": "Role", "Administrador": "Administrator", "Técnico": "Technician",
    "Invitar": "Invite", "Invitando…": "Inviting…", "Aún no hay miembros.": "No members yet.",
    "No se pudo cargar el equipo.": "Couldn't load the team.",
    "Ningún lote coincide con el filtro.": "No lots match the filter.",
    "Buscar productor, lote o región…": "Search producer, lot or region…",
    "⚠ volumen": "⚠ volume",
    // -- landing B2B (hero/dolor/envíos/cta) --
    "Cumplimiento EUDR · café y cacao": "EUDR compliance · coffee & cocoa",
    "Cumple el EUDR, o tu café se queda": "Comply with the EUDR, or your coffee stays",
    "fuera de Europa.": "out of Europe.",
    "Tu comprador europeo ya está pidiendo la prueba. Origen la genera: geolocalización parcela por parcela, verificación contra 4 fuentes satelitales y el dossier + GeoJSON listo para TRACES. Y consolida decenas de parcelas, de muchos productores y regiones, en un solo dossier por envío — capturado desde el celular, en minutos.":
      "Your European buyer is already asking for the proof. Origen produces it: plot-by-plot geolocation, verification against 4 satellite sources, and the dossier + GeoJSON ready for TRACES. And it consolidates dozens of plots, from many producers and regions, into a single dossier per shipment — captured from a phone, in minutes.",
    "Listo para TRACES": "Ready for TRACES", "GeoJSON + dossier": "GeoJSON + dossier",
    "Si no lo pruebas, no hay multa: simplemente tu comprador firma con otro y te quedas fuera de tu principal mercado.":
      "If you can't prove it, there's no fine: your buyer simply signs with someone else and you're locked out of your main market.",
    "Desde el 30 de diciembre de 2026, toda cooperativa que venda café o cacao a la UE debe demostrar —parcela por parcela— que no se cultivó en bosque talado después de 2020. Si no lo pruebas, no hay multa: simplemente tu comprador firma con otro y te quedas fuera de tu principal mercado.":
      "From December 30, 2026, any cooperative selling coffee or cocoa to the EU must prove —plot by plot— that it wasn't grown on land cleared after 2020. If you can't prove it, there's no fine: your buyer simply signs with someone else and you're locked out of your main market.",
    "Generamos el dossier y el GeoJSON listos para TRACES — por lote, o consolidando decenas de parcelas en un solo dossier por envío.":
      "We generate the dossier and GeoJSON ready for TRACES — per lot, or consolidating dozens of plots into a single dossier per shipment.",
    "Envíos · consolidación": "Shipments · consolidation",
    "Una operación, un solo dossier.": "One operation, one dossier.",
    "Tu comprador no acopia de una sola parcela: junta café de decenas de productores y varias regiones en un contenedor. El EUDR exige un dossier consolidado por envío, con la geolocalización de todas las parcelas. Lo que las consultoras cobran miles por armar, Origen lo genera en un clic.":
      "Your buyer doesn't source from a single plot: they pool coffee from dozens of producers and several regions into one container. The EUDR requires a consolidated dossier per shipment, with the geolocation of every plot. What consultants charge thousands to assemble, Origen generates in one click.",
    "Consolida decenas de parcelas": "Consolidate dozens of plots",
    "Marca los lotes de un contenedor —de muchos productores y regiones— y genera un único dossier + GeoJSON listo para TRACES.":
      "Tick the lots of a container —from many producers and regions— and generate a single dossier + GeoJSON ready for TRACES.",
    "Veredicto global, sin mezclar": "Global verdict, no mixing",
    "Si una sola parcela está observada, el envío se marca y te dice exactamente cuál excluir o sustentar. La norma prohíbe compensar: Origen te lo resuelve.":
      "If a single plot is flagged, the shipment is marked and tells you exactly which one to exclude or substantiate. The rule forbids offsetting: Origen handles it for you.",
    "Anti-fraude de volumen": "Volume anti-fraud",
    "Cruzamos los kilos declarados con el rendimiento real del área. Si no cuadra, lo marcamos antes que lo haga la aduana europea.":
      "We cross-check the declared kilos against the real yield of the area. If it doesn't add up, we flag it before EU customs does.",
    "Dossier consolidado": "Consolidated dossier", "GeoJSON listo para TRACES": "GeoJSON ready for TRACES",
    "Notarización SHA-256 + QR": "SHA-256 notarization + QR", "Equipo multi-técnico": "Multi-technician team",
    "Funciona sin señal": "Works offline", "Español e inglés": "Spanish & English",
    "Tus compradores europeos ya están preguntando.": "Your European buyers are already asking.",
    "Pon tu cooperativa en regla antes que tu competencia. Sin instalar nada, sin consultoras: captura tu primera parcela hoy y ten el dossier listo en minutos.":
      "Get your cooperative compliant before your competition does. Nothing to install, no consultants: capture your first plot today and have the dossier ready in minutes.",
    "Agenda una demo": "Book a demo"
  };

  var nodes = [], phs = [];
  function collect() {
    nodes = nodes.filter(function (n) { return n.isConnected; });   // descarta nodos removidos por re-render
    phs = phs.filter(function (e) { return e.isConnected; });
    var w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        var p = n.parentNode;
        if (!p) return NodeFilter.FILTER_REJECT;
        if (/^(SCRIPT|STYLE|NOSCRIPT)$/i.test(p.nodeName)) return NodeFilter.FILTER_REJECT;
        if (p.closest && p.closest('[data-count],[data-noi18n],svg')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var n; while (n = w.nextNode()) { if (n.__es !== undefined) continue; n.__es = n.nodeValue; nodes.push(n); }
    [].forEach.call(document.querySelectorAll('input[placeholder],textarea[placeholder]'), function (e) { if (e.__phes !== undefined) return; e.__phes = e.getAttribute('placeholder'); phs.push(e); });
  }
  function apply(l) {
    try { localStorage.setItem('origen_lang', l); } catch (e) {}
    document.documentElement.lang = l;
    nodes.forEach(function (n) {
      var es = n.__es, key = es.trim();
      n.nodeValue = (l === 'en' && T[key] != null) ? es.replace(key, T[key]) : es;
    });
    phs.forEach(function (e) { var key = (e.__phes || '').trim(); e.setAttribute('placeholder', (l === 'en' && T[key] != null) ? T[key] : e.__phes); });
    [].forEach.call(document.querySelectorAll('[data-langbtn]'), function (b) { b.textContent = (l === 'en' ? 'ES' : 'EN'); });
  }
  function curLang() { try { return localStorage.getItem('origen_lang') === 'en' ? 'en' : 'es'; } catch (e) { return 'es'; } }
  window.toggleLang = function () { apply(curLang() === 'en' ? 'es' : 'en'); };
  // Re-traduce contenido insertado por JS (lotes/envíos): colecta los nodos nuevos y aplica el idioma actual.
  window.i18nSync = function () { collect(); apply(curLang()); };
  window.origenLang = curLang;
  function init() {
    collect();
    var saved; try { saved = localStorage.getItem('origen_lang'); } catch (e) {}
    if (!saved) saved = ((navigator.language || 'es').slice(0, 2) === 'en') ? 'en' : 'es';
    apply(saved === 'en' ? 'en' : 'es');
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
