#!/usr/bin/python
"""Crear la memoria PDF a partir del diagnóstico guardado, sin ejecutar A/B/C.

Para renovar sus medidas ejecutar antes rds2026/validar_practica.py. Este script
solo transforma los datos en tablas, dibuja mapas y maqueta el documento.
"""

from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageDraw
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "rds2026" / "resultados"
OUTPUT = ROOT / "output" / "pdf" / "memoria_P1.pdf"
TMP = ROOT / "tmp" / "pdfs"


def map_preview(map_path: Path, output_path: Path, scale: int = 10) -> None:
    """Dibujar observaciones de A; no rellenar desconocidos con la geometría real."""
    data = json.loads(map_path.read_text(encoding="utf-8"))
    image = PILImage.new("RGB", (data["width"] * scale, data["height"] * scale), "white")
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(data.get("coverage", data["cells"])):
        for x, value in enumerate(row):
            draw.rectangle(
                (x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1),
                fill=(55, 180, 95) if value else (225, 228, 232),
            )
    resolution = data.get("planning_resolution", 1.0)
    origin_x, origin_y = data.get("origin", [0, 0])
    for key_x, key_y in data.get("configuration_obstacles", []):
        # Convertir clave a coordenada mundial y luego a píxeles locales.
        x = (key_x * resolution - origin_x) * scale
        y = (key_y * resolution - origin_y) * scale
        radius = max(1, scale // 5)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(215, 65, 65))
    image.save(output_path)


def header_footer(canvas, doc) -> None:
    """Dibujar la asignatura y el número de página fuera del área de contenido."""
    canvas.saveState()
    canvas.setFont("DejaVu", 8)
    canvas.setFillColor(colors.HexColor("#536273"))
    canvas.drawString(1.7 * cm, A4[1] - 1.1 * cm, "Robótica de Servizos - P1")
    canvas.drawRightString(A4[0] - 1.7 * cm, 1.0 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#CCD4DD"))
    canvas.line(1.7 * cm, A4[1] - 1.25 * cm, A4[0] - 1.7 * cm, A4[1] - 1.25 * cm)
    canvas.restoreState()


def build() -> Path:
    """Componer ocho páginas con texto explicativo y medidas leídas del JSON."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    metrics = json.loads((RESULTS / "diagnostico.json").read_text(encoding="utf-8"))
    previews = []
    for index in range(4):
        path = TMP / f"mapa_cfg_{index}.png"
        map_preview(RESULTS / f"mapa_cfg_{index}.json", path)
        previews.append(path)

    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="DejaVu",
                          fontSize=9.7, leading=14, alignment=TA_LEFT,
                          textColor=colors.HexColor("#243342"), spaceAfter=8)
    title = ParagraphStyle("Title", parent=styles["Title"], fontName="DejaVu-Bold",
                           fontSize=25, leading=30, alignment=TA_CENTER,
                           textColor=colors.HexColor("#173B65"))
    subtitle = ParagraphStyle("Subtitle", parent=body, fontSize=12, leading=17,
                              alignment=TA_CENTER, textColor=colors.HexColor("#536273"))
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="DejaVu-Bold",
                        fontSize=16, leading=20, textColor=colors.HexColor("#173B65"),
                        spaceBefore=4, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="DejaVu-Bold",
                        fontSize=11, leading=14, textColor=colors.HexColor("#1E6B55"),
                        spaceBefore=9, spaceAfter=5)
    note = ParagraphStyle("Note", parent=body, fontSize=9, leading=12,
                          backColor=colors.HexColor("#EEF4FA"), borderPadding=7,
                          borderColor=colors.HexColor("#B8CBE0"), borderWidth=0.6,
                          spaceBefore=8, spaceAfter=10)
    caption = ParagraphStyle("Caption", parent=body, fontSize=8.3, leading=11,
                             textColor=colors.HexColor("#536273"), spaceBefore=6,
                             spaceAfter=10)
    small = ParagraphStyle("Small", parent=body, fontSize=8, leading=11)
    table_body = ParagraphStyle("TableBody", parent=small, fontSize=8, leading=10)
    table_head = ParagraphStyle("TableHead", parent=table_body,
                               fontName="DejaVu-Bold", textColor=colors.white)

    def table(rows, widths):
        """Ajustar texto dentro de cada celda para que no invada otras columnas."""
        cells = [[Paragraph(escape(str(value)), table_head if index == 0 else table_body)
                  for value in row] for index, row in enumerate(rows)]
        result = Table(cells, colWidths=[width * cm for width in widths], repeatRows=1)
        result.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173B65")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6F9")]),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C4D0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return result

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=1.7 * cm,
                          leftMargin=1.7 * cm, topMargin=1.65 * cm,
                          bottomMargin=1.5 * cm, title="Memoria P1",
                          author="Alejandro Lavandeira Casais; Carlos Adrián Cancela Bodlak; Yago Martínez Pena")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=header_footer))
    story = []

    # Los nombres de portada son texto, no otra tabla de resultados sin título.
    story += [Spacer(1, 1.8 * cm), Paragraph("Práctica P1", title),
              Paragraph("Navegación en entornos complejos", title), Spacer(1, 0.5 * cm),
              Paragraph("Mapeo, navegación y teleoperación de una aspiradora", subtitle),
              Spacer(1, 1.0 * cm), Paragraph("Robótica de Servizos · Curso 2026/2027", subtitle),
              Spacer(1, 0.6 * cm),
              Paragraph("Alejandro Lavandeira Casais<br/>Carlos Adrián Cancela Bodlak<br/>Yago Martínez Pena", subtitle),
              Spacer(1, 1.0 * cm), Paragraph("Resumen", h1),
              Paragraph("Esta práctica consiste en conseguir que una aspiradora explore un piso, se desplace entre dos puntos y repita una ruta marcada por el usuario. El robot tiene un cuerpo de 2x2 unidades y avanza 0,5 unidades por ciclo. Para decidir si puede moverse utiliza sus sensores de contacto y su posición simulada.", body),
              Paragraph("En A guarda las posiciones que descubre y crea la matriz cuando termina de explorar. En B busca un camino en ese mapa con A*. En C permite conducir con el teclado, guardar puntos de paso y volver a recorrerlos. Los giros manuales son de 90 grados y los puntos se muestran con una X numerada.", body),
              Paragraph("Las pruebas de los cuatro escenarios originales no dejan celdas alcanzables sin cubrir. Las rutas de navegación y la reproducción ensayadas terminan sin colisiones registradas. Estos resultados tienen límites: no se descubren habitaciones desconectadas y el simulador no introduce errores de posición.", body),
              Spacer(1, 0.4 * cm), Paragraph("Entorno de ejecución: Python 3.12 y Pygame 2.6.1.", small), PageBreak()]

    story += [Paragraph("1. Diseño de la práctica", h1),
              Paragraph("El enunciado divide el trabajo en tres partes. A debe descubrir y recorrer el entorno; B debe ir de un origen a un destino sorteando obstáculos; C debe guardar y recuperar rutas construidas mediante teleoperación. Se utiliza la opción de planificación sobre un mapa para B y la de marcar puntos de paso para C.", body),
              Paragraph("Qué información conoce el robot", h2),
              Paragraph("La odometría es la estimación de posición y orientación que proporcionan los sensores de movimiento. Aquí coincide con la posición real del simulador: no hay ruido ni errores acumulados. Los sensores de contacto indican si el siguiente avance está bloqueado, pero no dan la distancia a un mueble ni su forma completa.", body),
              Paragraph("El simulador conoce el plano para dibujarlo y producir los sensores. El explorador no recibe su ancho, alto ni lista de muebles. Guarda coordenadas mientras recorre el piso; al terminar calcula los límites de lo observado y reserva la matriz.", body),
              Paragraph("Organización del código", h2),
              Paragraph("La tabla 1 indica dónde está cada tarea. Los tres scripts llaman a funciones compartidas: así B y C ejecutan los caminos con el mismo controlador, en lugar de tener dos formas distintas de mover el robot.", body)]
    architecture = table([
        ["Parte", "Qué hace", "Dónde se implementa"],
        ["Simulador", "Carga el mundo, genera sensores y mueve el robot.", "rds2026environment.py, rds2026machines.py, rds2026simulation.py"],
        ["A", "Explora, guarda observaciones y crea el mapa final.", "apartado_a.py; SparseExplorationMap y CompleteCoverageExplorer"],
        ["B", "Valida extremos, busca el camino y lo ejecuta.", "apartado_b.py; astar y MotionController"],
        ["C", "Graba puntos y planifica entre ellos al reproducir.", "apartado_c.py; RecordedRoute y WaypointOverlay"],
        ["Pruebas", "Comprueba funciones y mide recorridos completos.", "tests/test_practica.py y validar_practica.py"],
    ], [2.1, 6.4, 8.7])
    story += [KeepTogether([architecture, Paragraph("Tabla 1. Distribución de responsabilidades. Las clases y funciones compartidas están en robotica_servicios.py.", caption)]),
              Paragraph("A partir del simulador original se corrigió el estado compartido entre instancias y el redondeo de la posición futura. Este último podía permitir un paso al ir y bloquearlo al volver. Son cambios del modelo simulado; no aportan al explorador información que todavía no haya observado.", body), PageBreak()]

    story += [Paragraph("2. Apartado A: descubrir y cubrir", h1),
              Paragraph("Posición del robot y celda de suelo", h2),
              Paragraph("No son lo mismo. Una pose es una posición del centro del robot. Que sea libre significa que cabe el cuerpo completo. Una celda puede quedar cubierta por un lateral aunque el centro nunca pase por ella. La cobertura usa las mismas cuatro muestras bajo el cuerpo que el simulador; no calcula un área continua exacta.", body),
              Paragraph("Antes de crear la matriz", h2),
              Paragraph("SparseExplorationMap mantiene tres conjuntos sin duplicados: fine_free para centros visitados, fine_obstacles para centros bloqueados y covered para suelo cubierto. Las poses usan claves enteras: (21,5; 21) se representa como (43; 42), porque cada unidad de clave equivale a 0,5 unidades del mundo.", body),
              Paragraph("Al acabar, finalize calcula los mínimos y máximos de las celdas cubiertas y las poses observadas. El ancho es max_x - min_x + 1; el alto se calcula igual. El origen guardado permite traducir coordenadas del mundo a filas y columnas. El TXT tiene 1 para suelo cubierto y 0 para suelo sin cobertura registrada. El JSON guarda también desconocido, libre y bloqueado (0, 1 y 2) y las poses de medio paso.", body),
              Paragraph("Cómo recorre el entorno", h2),
              Paragraph("La búsqueda en profundidad, o DFS, prueba los cuatro vecinos de cada pose. Si puede avanzar, guarda la nueva pose y continúa desde ella. Al agotar sus vecinos vuelve físicamente a la posición anterior. Una pila recuerda esas ramas pendientes; cuando queda vacía, termina. Esto recorre bordes e interior, pero no es un seguidor de paredes ni un barrido por filas.", body),
              Paragraph("Probar vecinos cada 0,5 unidades permite explorar desde posiciones intermedias que antes se atravesaban sin examinar sus salidas. La figura 1 muestra el suelo cubierto y las poses bloqueadas. El rojo marca centros donde no cabe el robot, no la silueta exacta de los muebles.", body)]
    images = []
    for index, preview in enumerate(previews):
        # Conservar proporciones del mapa, aunque su rectángulo no sea cuadrado.
        with PILImage.open(preview) as source:
            factor = 3.35 * cm / max(source.size)
            width, height = (value * factor for value in source.size)
        images.append([Image(str(preview), width=width, height=height), Paragraph(f"cfg_{index}", small)])
    gallery = Table([[item[0] for item in images], [item[1] for item in images]], colWidths=[4.15 * cm] * 4)
    gallery.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    story += [KeepTogether([gallery, Paragraph("Figura 1. Mapas observados tras explorar. Verde: suelo con cobertura registrada. Rojo: poses bloqueadas del centro. Gris: suelo sin cobertura registrada; no demuestra que sea un obstáculo.", caption)]), PageBreak()]

    story += [Paragraph("3. Apartado B: ir de un punto a otro", h1),
              Paragraph("Comprobar los extremos", h2),
              Paragraph("Antes de mover el robot se comprueban el origen y el destino. Un punto fuera del mapa, bloqueado o desconocido se rechaza. Si ambos son libres pero están separados por paredes sin paso, A* informa de que no hay camino. No se sustituye el destino por otro cercano para dar la ruta por completada.", body),
              Paragraph("Los puntos entre muestras admiten un ajuste local solo si todos los vértices que los rodean son libres conocidos. Por ejemplo, una coordenada 2,2 puede aproximarse a 2 o 2,5. Se informa de la distancia del ajuste. Esto no demuestra llegada exacta a cualquier coordenada continua y también se aplica al origen.", body),
              Paragraph("Cómo decide A*", h2),
              Paragraph("Cada pose libre es un nodo y sus cuatro vecinos son las posibles transiciones. A* prioriza la suma de los pasos ya recorridos y una estimación de los que faltan. Esa estimación suma las diferencias horizontal y vertical hasta el destino: es la distancia Manhattan. Al ignorar obstáculos no sobreestima el recorrido. A* obtiene un camino mínimo en la rejilla, no necesariamente el camino continuo más corto.", body),
              Paragraph("Después se quitan puntos intermedios de la misma recta y se conservan las esquinas, sin crear diagonales. El controlador gira hacia cada esquina, consulta el contacto antes de cada avance y comprueba la posición para detenerse al llegar. Si un tramo falla, no sigue con el resto de la ruta.", body),
              Paragraph("Qué muestran las pruebas", h2),
              Paragraph("La tabla 2 recoge un recorrido por escenario. Poses cuenta las posiciones de A*, incluyendo el origen. Tramos cuenta las rectas después de quitar puntos intermedios. Longitud y error se expresan en unidades del mundo; el error compara la posición final con el destino ejecutado en la rejilla. Colisiones es el contador del simulador.", body)]
    nav_rows = [["Mapa", "Origen → destino", "Poses", "Tramos", "Longitud", "Error", "Colisiones"]]
    for config, data in metrics["navigation"].items():
        nav_rows.append([config.replace(".py", ""), f"{tuple(data['start'])} → {tuple(data['goal'])}",
                         data["astar_cells"], data["waypoints"] - 1, data["path_length"],
                         data["final_error"], data["collisions"]])
    story += [KeepTogether([table(nav_rows, [1.65, 5.25, 1.75, 1.85, 2.2, 1.75, 2.75]),
              Paragraph("Tabla 2. Navegación sobre mapas descubiertos en A. Los pares mostrados están alineados con la rejilla: en estos casos no hay ajuste de los extremos.", caption)]),
              Paragraph(f"Por ejemplo, en cfg_2 hay {metrics['navigation']['cfg_2.py']['astar_cells']} poses: son {metrics['navigation']['cfg_2.py']['astar_cells'] - 1} avances de 0,5 unidades, es decir, {metrics['navigation']['cfg_2.py']['path_length']:g} unidades de recorrido. Tras comprimirlo quedan {metrics['navigation']['cfg_2.py']['waypoints'] - 1} tramos rectos. En los cuatro casos de la tabla 2 el error final y las colisiones registradas son cero.", body), PageBreak()]

    replay = metrics["replay"]["cfg_3.py"]
    story += [Paragraph("4. Apartado C: conducir y repetir", h1),
              Paragraph("Guardar puntos de paso", h2),
              Paragraph("Un waypoint es un punto de paso que queremos que el robot visite después. No se guarda cada posición de la conducción: se guarda el inicio, los puntos marcados con W y el punto final al salir. El JSON incluye nombre de ruta, escenario, fecha y lista ordenada de coordenadas. Dos puntos consecutivos iguales no se repiten.", body),
              Paragraph("La tabla 3 resume el teclado. Los giros de 90 grados mantienen las cuatro direcciones principales cuando se parte de orientación cero. Soltar la flecha de avance detiene el robot; S guarda sin cerrar la grabación.", body)]
    controls = table([
        ["Tecla", "Acción"], ["Flecha arriba", "Avanzar mientras se mantiene pulsada."],
        ["Izquierda / derecha", "Girar +90 / -90 grados por pulsación."],
        ["W", "Guardar la posición actual como waypoint."],
        ["S", "Guardar la ruta y seguir conduciendo."],
        ["Q / cerrar ventana", "Guardar el punto final y salir."],
        ["D", "Mostrar u ocultar los rectángulos de los sensores."],
    ], [5.0, 12.2])
    story += [KeepTogether([controls, Paragraph("Tabla 3. Controles del modo record de apartado_c.py.", caption)]),
              Paragraph("Cada punto aparece con una X azul y su número, empezando por el inicio como punto 1. En replay el siguiente objetivo es rojo. Si la ruta vuelve a una coordenada, se muestran allí todos sus números. La numeración corresponde al archivo, no a las esquinas internas del camino de A*.", body),
              Paragraph("Reproducir la ruta", h2),
              Paragraph("replay carga mapa y ruta, comprueba que correspondan al mismo escenario y usa el A* y el controlador compartidos entre puntos consecutivos. No repite pulsaciones ni garantiza seguir exactamente la trayectoria manual: puede rodear un mueble por otro camino.", body),
              Paragraph("C tiene una diferencia importante respecto a B: aproxima cada waypoint a una pose libre conectada con el robot. Puede acabar en un punto distinto al guardado si el mapa no lo contiene. max_snap_distance informa del mayor ajuste; una línea y un círculo rojos muestran el objetivo ejecutado cuando cambia. El error final compara la llegada con ese objetivo ajustado.", note),
              Paragraph(f"La ruta de prueba de cfg_3 tiene {replay['waypoints']} waypoints y {replay['segments_replayed']} trayectos entre ellos. El mayor ajuste fue {replay['max_snap_distance']} unidades y el error final fue {replay['final_error']} unidades, con {replay['collisions']} colisiones. Se ejecutaron {replay['frames']} ciclos de avance del controlador; no es una duración en segundos.", body), PageBreak()]

    story += [Paragraph("5. Pruebas y resultados", h1),
              Paragraph("Cómo se mide la cobertura", h2),
              Paragraph("Al terminar A, una función de evaluación consulta la geometría real y calcula qué poses libres están conectadas con el inicio. Después calcula las celdas bajo las muestras de sus huellas. Es la referencia con la que se compara lo visitado. Se calcula después de explorar: no ayuda a elegir movimientos ni a crear la matriz.", body),
              Paragraph("La tabla 4 distingue ambas medidas. Poses alcanzables cuenta posiciones diferentes del centro; suelo alcanzable cuenta celdas diferentes que se pueden cubrir. Cobertura es el porcentaje de ese suelo cubierto. Omitidas cuenta celdas alcanzables no cubiertas. Pasos cuenta avances físicos, incluidos retrocesos, por lo que puede superar el número de poses.", body)]
    cov_rows = [["Mapa", "Poses alcanzables", "Suelo alcanzable", "Cobertura", "Omitidas", "Pasos", "Colisiones"]]
    for config, data in metrics["coverage"].items():
        cov_rows.append([config.replace(".py", ""), data["reachable_poses"], data["reachable_cells"],
                         f"{data['coverage_percent']:.1f}%", data["missed_cells"],
                         data["trajectory_steps"], data["collisions"]])
    story += [KeepTogether([table(cov_rows, [1.65, 2.6, 2.6, 2.55, 2.1, 2.1, 3.6]),
              Paragraph("Tabla 4. Cobertura de A en los cuatro escenarios originales, con el inicio definido para cada uno. Suelo alcanzable y omitidas se expresan en celdas.", caption)]),
              Paragraph("En cfg_0 hay 1.308 posiciones distintas del centro, pero 416 celdas de suelo alcanzables. Se hacen 2.614 avances porque el robot vuelve por las ramas exploradas. Como muestra la tabla 4, no quedan celdas alcanzables omitidas. La comparación de poses también da 100 % y no encuentra visitas fuera de la referencia en estos cuatro casos.", body),
              Paragraph("Por qué puede haber zonas grises", h2),
              Paragraph("El 100 % no se refiere a todas las celdas del piso. Una habitación aislada o un hueco demasiado estrecho no pertenece al conjunto alcanzable desde el inicio. El gris de la figura 1 indica que no se ha registrado cobertura; por sí solo no permite decidir si hay un obstáculo o suelo libre al que no se puede llegar.", body),
              Paragraph("Pruebas automáticas y diagnóstico", h2),
              Paragraph("Los tests comprueban que dos robots no compartan sensores, que guardar y cargar conserve los datos, que la matriz se cree al final y que A* rodee obstáculos. También prueban rechazos de B y una ejecución completa de A, B y C en cfg_3. Usan aserciones: comparaciones entre el resultado obtenido y el esperado que hacen fallar la prueba si no coinciden.", body),
              Paragraph("validar_practica.py ejecuta los cuatro casos de las tablas 2 y 4 y el replay de ejemplo. Guarda medidas en resultados/diagnostico.json, pero no sustituye a los tests: registrar un resultado no equivale a comprobar automáticamente que sea correcto.", body), PageBreak()]

    story += [Paragraph("6. Retos, simplificaciones y mejoras", h1),
              Paragraph("En el apartado A", h2),
              Paragraph("El reto principal fue separar lo que puede ocupar el centro de lo que cubre el cuerpo. Explorar solo desde coordenadas enteras dejaba salidas sin examinar en posiciones intermedias. La rejilla de medio paso corrige ese problema para este simulador. Aun así, la cobertura es la definida por sus muestras, no una medición continua de todo el suelo.", body),
              Paragraph("DFS termina si el espacio alcanzable es finito, los objetos no cambian y el inicio es válido y está alineado con la rejilla. No supone conocer las dimensiones, pero depende de que los contactos cierren el entorno. En un mundo abierto podría seguir descubriendo puntos; max_probes limita los intentos para diagnóstico, no garantiza cobertura.", body),
              Paragraph("El recorrido repite pasos al volver atrás. Una mejora sería elegir mejor el orden de las zonas pendientes o reducir los retornos por caminos conocidos. Eso buscaría ahorrar distancia, no aumentar una cobertura que ya es completa en los casos medidos. La versión actual no hace una fase separada de seguimiento de paredes.", body),
              Paragraph("En el apartado B", h2),
              Paragraph("La dificultad fue no aceptar un obstáculo como destino por haber encontrado cerca un punto libre. Ahora se rechazan puntos bloqueados, desconocidos o desconectados. Queda la simplificación de ajustar localmente coordenadas entre muestras. El error cero significa llegada al objetivo de rejilla; no prueba llegada exacta a todos los puntos continuos posibles.", body),
              Paragraph("Los caminos solo son horizontales y verticales. Las diagonales podrían acortarlos, pero habría que comprobar todo el espacio que ocupa el cuerpo durante ese movimiento, no solo sus extremos. Con el mapa observado actual no se da esa comprobación por hecha.", body),
              Paragraph("En el apartado C", h2),
              Paragraph("Guardar puntos en vez de órdenes permite repetir la ruta con planificación, pero no conserva el camino manual exacto. Queda por decidir si C debería rechazar también cualquier waypoint no accesible, como B, en lugar de aproximarlo. Mostrar y medir el ajuste evita confundir lo solicitado con lo ejecutado, pero no elimina esa diferencia.", body),
              Paragraph("Fuera del simulador", h2),
              Paragraph("La posición es perfecta y los objetos son estáticos. En un robot real habría que corregir errores de posición y revisar el mapa ante obstáculos nuevos. Un sensor de distancia permitiría descubrir más sin acercarse a cada mueble. Hay batería en el simulador, pero no se ha implementado retorno autónomo al cargador.", body), PageBreak()]

    story += [Paragraph("7. Conclusiones", h1),
              Paragraph("La principal lección es que un mapa para navegar no basta con que se parezca al dibujo del piso. Debe representar dónde cabe el robot y distinguir lo observado de lo desconocido. También hay que comprobar el suelo cubierto por su cuerpo por separado del recorrido de su centro.", body),
              Paragraph("A crea el mapa sin reservar una matriz del tamaño del escenario. B encuentra caminos en la rejilla conocida y comunica cuándo no puede llegar. C guarda puntos ordenados y usa el mismo planificador para reproducirlos. Las pruebas permiten comprobar estos comportamientos; sus resultados no se extienden automáticamente a un robot real o a cualquier escenario nuevo.", body),
              Paragraph("También hemos aprendido que llegar sin error a un objetivo no basta para evaluar una ruta: hay que comprobar si ese objetivo coincide con el solicitado y cuánto se ha ajustado. Por eso se distinguen las coordenadas originales de las ejecutadas, y se conservan por separado las medidas de cobertura, distancia y colisiones.", body),
              Paragraph("Reproducción de resultados", h2),
              Paragraph("Desde rds2026, con el entorno de Python activado y Pygame instalado:<br/><b>python -m unittest discover -s tests -v</b><br/><b>python validar_practica.py</b>", note),
              Paragraph("La primera orden ejecuta las pruebas automáticas de representación del mapa, planificación, rechazo de destinos y movimiento en el simulador. La segunda explora los cuatro escenarios originales, ejecuta los recorridos de B y reproduce la ruta de ejemplo de C. Guarda las medidas en resultados/diagnostico.json, que es el archivo utilizado para elaborar las tablas de esta memoria.", body),
              Paragraph("El diagnóstico se ejecuta sin ventana y sin limitar los ciclos por segundo para reducir el tiempo de cálculo. Se mantienen el paso físico de 0,5 unidades y las mismas comprobaciones de contacto de las ejecuciones con ventana. No se interpreta el número de ciclos como una duración real del recorrido.", body)]

    doc.build(story)
    return OUTPUT


if __name__ == "__main__":
    print(build())
