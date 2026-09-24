#!/usr/bin/python
"""Generate the final technical report from measured diagnostic results."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PILImage, ImageDraw
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
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
    data = json.loads(map_path.read_text(encoding="utf-8"))
    image = PILImage.new("RGB", (data["width"] * scale, data["height"] * scale), "white")
    draw = ImageDraw.Draw(image)
    coverage = data.get("coverage", data["cells"])
    for y, row in enumerate(coverage):
        for x, value in enumerate(row):
            draw.rectangle(
                (x * scale, y * scale, (x + 1) * scale - 1, (y + 1) * scale - 1),
                fill=(55, 180, 95) if value else (225, 228, 232),
            )
    resolution = data.get("planning_resolution", 1.0)
    origin_x, origin_y = data.get("origin", [0, 0])
    for key_x, key_y in data.get("configuration_obstacles", []):
        x = (key_x * resolution - origin_x) * scale
        y = (key_y * resolution - origin_y) * scale
        radius = max(1, scale // 5)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(215, 65, 65))
    image.save(output_path)


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("DejaVu", 8)
    canvas.setFillColor(colors.HexColor("#536273"))
    canvas.drawString(1.7 * cm, A4[1] - 1.1 * cm, "Robótica de Servizos - P1")
    canvas.drawRightString(A4[0] - 1.7 * cm, 1.0 * cm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#CCD4DD"))
    canvas.line(1.7 * cm, A4[1] - 1.25 * cm, A4[0] - 1.7 * cm, A4[1] - 1.25 * cm)
    canvas.restoreState()


def build() -> Path:
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
                          fontSize=9.2, leading=13, alignment=TA_JUSTIFY,
                          textColor=colors.HexColor("#243342"), spaceAfter=7)
    title = ParagraphStyle("Title", parent=styles["Title"], fontName="DejaVu-Bold",
                           fontSize=25, leading=30, alignment=TA_CENTER,
                           textColor=colors.HexColor("#173B65"))
    subtitle = ParagraphStyle("Subtitle", parent=body, fontSize=13, leading=18,
                              alignment=TA_CENTER, textColor=colors.HexColor("#536273"))
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontName="DejaVu-Bold",
                        fontSize=16, leading=20, textColor=colors.HexColor("#173B65"),
                        spaceBefore=4, spaceAfter=10)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="DejaVu-Bold",
                        fontSize=11, leading=14, textColor=colors.HexColor("#1E6B55"),
                        spaceBefore=7, spaceAfter=4)
    note = ParagraphStyle("Note", parent=body, fontSize=8.5, leading=11,
                          backColor=colors.HexColor("#EEF4FA"), borderPadding=7,
                          borderColor=colors.HexColor("#B8CBE0"), borderWidth=0.6)
    small = ParagraphStyle("Small", parent=body, fontSize=7.5, leading=10)
    bullet = ParagraphStyle("Bullet", parent=body, leftIndent=13, firstLineIndent=-7,
                            bulletIndent=3, spaceAfter=4)

    doc = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=1.7 * cm,
                          leftMargin=1.7 * cm, topMargin=1.55 * cm,
                          bottomMargin=1.45 * cm, title="Memoria P1")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=header_footer))
    story = []

    story += [Spacer(1, 2.0 * cm), Paragraph("Práctica P1", title),
              Paragraph("Navegación en entornos complejos", title), Spacer(1, 0.5 * cm),
              Paragraph("Mapeo y cobertura, navegación punto a punto y teleoperación", subtitle),
              Spacer(1, 1.2 * cm)]
    cover_table = Table([
        ["Asignatura", "Robótica de Servizos"],
        ["Curso", "2026/2027"],
        ["Autor confirmado", "Alejandro Lavandeira"],
        ["Entorno", "Python 3.12.3, Pygame 2.6.1"],
    ], colWidths=[4.3 * cm, 10.2 * cm])
    cover_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "DejaVu", 9),
        ("FONT", (0, 0), (0, -1), "DejaVu-Bold", 9),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F0F8")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#AFC0D2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 7),
    ]))
    story += [cover_table, Spacer(1, 1.1 * cm),
              Paragraph("Nota de entrega: completar en portada los demás integrantes del equipo antes de subir el ZIP.", note),
              Spacer(1, 1.0 * cm), Paragraph("Resumen", h1),
              Paragraph("Se presenta una solución integral para una aspiradora con odometría y tres sensores de contacto. El seguidor de paredes inicial se sustituyó por cobertura completa sobre una rejilla del espacio de configuración; la navegación utiliza A* y la teleoperación guarda waypoints que se reproducen con el mismo planificador. La validación recorre los cuatro escenarios proporcionados: alcanza el 100% de las posiciones transitables, completa rutas largas con error final nulo y no registra colisiones durante navegación ni reproducción.", body),
              PageBreak()]

    story += [Paragraph("1. Requisitos y diseño global", h1),
              Paragraph("El enunciado solicita: (A) distinguir celdas ocupadas y libres y cubrir la superficie; (B) desplazarse entre dos puntos arbitrarios sorteando obstáculos; y (C) teleoperar, guardar rutas y recuperarlas. La evaluación usa también entornos no proporcionados, por lo que se evitó codificar trayectorias específicas.", body),
              Paragraph("Arquitectura", h2)]
    architecture = Table([
        ["Capa", "Responsabilidad", "Implementación"],
        ["Simulador", "Dinámica, contacto y odometría", "rds2026machines.py"],
        ["Modelo", "Rejilla segura para el centro del robot", "OccupancyGrid"],
        ["Exploración", "Descubrir y cubrir todo lo alcanzable", "CompleteCoverageExplorer"],
        ["Planificación", "Ruta óptima conocida", "A* + compresión cardinal"],
        ["Control", "Giro y avance con realimentación", "MotionController"],
        ["Persistencia", "Mapas y waypoints versionados", "JSON + escritura atómica"],
    ], colWidths=[2.5 * cm, 6.1 * cm, 6.0 * cm], repeatRows=1)
    architecture.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "DejaVu", 8),
        ("FONT", (0, 0), (-1, 0), "DejaVu-Bold", 8),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173B65")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6F9")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C4D0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story += [architecture, Paragraph("Correcciones del simulador", h2),
              Paragraph("Se eliminaron contenedores mutables compartidos entre robots y planos, se inicializaron posición y orientación del sensor por instancia, se corrigió la coordenada Y de recarga y se anuló el ruido trigonométrico en movimientos cardinales. Además, el cálculo de contacto futuro se realiza en una sola conversión a rectángulo: el doble redondeo anterior hacía algunas aristas transitables sólo en un sentido.", body),
              Paragraph("La solución sólo usa el oráculo geométrico del plano en la batería de evaluación. La exploración operativa decide con posición odométrica y contactos; no consulta los objetos del entorno.", note),
              PageBreak()]

    story += [Paragraph("2. Apartado A: mapeo y cobertura", h1),
              Paragraph("Representación", h2),
              Paragraph("El explorador desconoce las dimensiones del piso: conserva poses libres, contactos y celdas cubiertas en conjuntos dispersos de coordenadas odométricas. Terminada la exploración, calcula los mínimos y máximos observados en ambos ejes y sólo entonces crea la matriz densa con su origen. El simulador conoce el tamaño para dibujar, pero no se lo entrega al algoritmo. El mapa distingue poses libres del centro cada 0,5 celdas y suelo cubierto por la huella 2x2; además conserva el estado desconocido separado del obstáculo.", body),
              Paragraph("Algoritmo de cobertura", h2),
              Paragraph("Se emplea exploración en línea mediante un árbol de expansión con retroceso (DFS). Desde cada pose se prueban los cuatro vecinos cardinales a distancia 0,5, que coincide con un paso físico del simulador. El sensor frontal se consulta antes de mandar el avance: una pose libre se añade al árbol y una ocupada se registra sin impacto. Al agotar los vecinos se vuelve al padre. El algoritmo termina cuando la pila queda vacía.", body),
              Paragraph("La primera implementación sólo ramificaba en centros enteros. Aunque atravesaba poses intermedias, no podía explorar desde ellas y omitía cuatro celdas de superficie en cfg_0. La nueva rejilla de medio paso cubre todas las poses y toda la huella alcanzable.", note),
              Paragraph("Propiedades y complejidad", h2),
              Paragraph("Para V posiciones alcanzables y E transiciones candidatas, el coste de búsqueda es O(V+E) y la memoria O(V). El recorrido no es de longitud mínima, pero sí finito, reproducible y completo sobre la discretización. Frente al seguimiento de pared, puede abandonar contornos, cubrir interiores y cerrar ramas mediante backtracking.", body),
              Paragraph("Visualización de mapas resultantes", h2)]
    images = []
    for index, preview in enumerate(previews):
        img = Image(str(preview), width=3.4 * cm, height=3.4 * cm)
        images.append([img, Paragraph(f"cfg_{index}", small)])
    grid_table = Table([[item[0] for item in images], [item[1] for item in images]],
                       colWidths=[3.8 * cm] * 4)
    grid_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story += [grid_table, Paragraph("Verde: superficie barrida por la huella; rojo: pose de contacto observada; gris: desconocido o inaccesible. La capa JSON conserva por separado las poses navegables.", small),
              PageBreak()]

    story += [Paragraph("3. Apartado B: navegación punto a punto", h1),
              Paragraph("Planificación", h2),
              Paragraph("Los puntos arbitrarios se proyectan a la pose de medio paso más próxima dentro de la componente conexa del origen, y se informa de la distancia de ajuste. A* busca sobre vecinos cardinales con coste unitario y heurística Manhattan, admisible y consistente; por tanto devuelve un camino de coste mínimo en la rejilla medida.", body),
              Paragraph("Reducción de giros", h2),
              Paragraph("Después de A* se eliminan waypoints colineales y se conservan sólo los cambios de dirección. Se estudió Theta* para producir diagonales, pero se descartó como modo predeterminado: incluso con muestras cada 0,5, un mapa táctil discreto no certifica todo el volumen continuo barrido por un robot 2x2. La compresión cardinal conserva la seguridad y obtuvo cero colisiones.", body),
              Paragraph("Control de movimiento", h2),
              Paragraph("Cada tramo se ejecuta en lazo cerrado: se calcula el rumbo, se aplica el giro mínimo, se consulta contacto antes de cada paso y se detiene al alcanzar exactamente el objetivo. Todos los waypoints están alineados con el paso de 0,5 celdas.", body),
              Paragraph("Resultado representativo", h2)]
    nav_rows = [["Mapa", "Origen - destino", "Celdas A*", "Tramos", "Longitud", "Error", "Col."]]
    for config, data in metrics["navigation"].items():
        nav_rows.append([
            config.replace(".py", ""), f"{tuple(data['start'])} - {tuple(data['goal'])}",
            str(data["astar_cells"]), str(data["waypoints"] - 1), str(data["path_length"]),
            str(data["final_error"]), str(data["collisions"]),
        ])
    nav_table = Table(nav_rows, colWidths=[1.5 * cm, 4.6 * cm, 1.8 * cm, 1.5 * cm, 1.7 * cm, 1.5 * cm, 1.1 * cm])
    nav_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "DejaVu", 7.5), ("FONT", (0, 0), (-1, 0), "DejaVu-Bold", 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173B65")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C4D0")), ("ALIGN", (2, 1), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [nav_table, PageBreak()]

    story += [Paragraph("4. Apartado C: teleoperación y rutas", h1),
              Paragraph("Grabación", h2),
              Paragraph("El usuario controla el robot con las flechas, añade waypoints con W y guarda con S o Q. Se almacena una ruta JSON versionada con nombre, escenario, fecha y coordenadas. Se omiten puntos consecutivos duplicados y la escritura usa un fichero temporal para evitar archivos parciales.", body),
              Paragraph("Reproducción autónoma", h2),
              Paragraph("La reproducción no copia órdenes de teclado: carga cada waypoint y llama al planificador del apartado B entre la posición actual y el siguiente objetivo. Así puede rodear obstáculos, valida que mapa y ruta pertenezcan al mismo escenario y reutiliza exactamente el controlador ya probado.", body),
              Paragraph("Controles", h2)]
    controls = Table([
        ["Entrada", "Acción"], ["Arriba", "Avanzar mientras está pulsada"],
        ["Izquierda / derecha", "Girar 15 grados"], ["W", "Añadir waypoint"],
        ["S", "Guardar ruta"], ["Q", "Añadir punto final, guardar y salir"],
    ], colWidths=[4.5 * cm, 10.0 * cm])
    controls.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "DejaVu", 8.5), ("FONT", (0, 0), (-1, 0), "DejaVu-Bold", 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E6B55")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F7F4")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C4D0")), ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    replay = metrics["replay"]["cfg_3.py"]
    story += [controls, Paragraph("Prueba de reproducción", h2),
              Paragraph(f"La ruta de demostración contiene {replay['waypoints']} waypoints y {replay['segments_replayed']} desplazamientos principales. Finalizó con error {replay['final_error']}, {replay['collisions']} colisiones y {replay['frames']} frames de simulación.", body),
              Paragraph("Los ficheros inválidos, vacíos o pertenecientes a otro escenario se rechazan con un error explicativo.", note),
              PageBreak()]

    story += [Paragraph("5. Metodología y resultados", h1),
              Paragraph("Se añadió una prueba unitaria para estado por instancia, A*, compresión del camino y persistencia; las pruebas de integración ejecutan cobertura, navegación y replay. El diagnóstico completo calcula el conjunto realmente alcanzable a partir de la geometría, pero ese oráculo está confinado a la evaluación.", body)]
    cov_rows = [["Mapa", "Poses", "Celdas", "Cobertura", "Omitidas", "Pasos", "Colisiones"]]
    for config, data in metrics["coverage"].items():
        cov_rows.append([
            config.replace(".py", ""), str(data["reachable_poses"]), str(data["reachable_cells"]),
            f"{data['coverage_percent']:.1f}%", str(data["missed_cells"]),
            str(data["trajectory_steps"]), str(data["collisions"]),
        ])
    cov_table = Table(cov_rows, colWidths=[1.5 * cm, 2.0 * cm, 1.8 * cm, 1.8 * cm, 1.6 * cm, 1.7 * cm, 1.8 * cm])
    cov_table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "DejaVu", 7.7), ("FONT", (0, 0), (-1, 0), "DejaVu-Bold", 7.7),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173B65")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F6F9")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B7C4D0")), ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [cov_table, Paragraph("Interpretación", h2),
              Paragraph("Los cuatro escenarios alcanzan el 100% tanto en poses de medio paso como en superficie, sin omisiones ni visitas imposibles. El apartado A consulta el volumen frontal antes de moverse y termina con cero colisiones; B y C también terminan sin contacto.", body),
              Paragraph("Casos diagnosticados durante el desarrollo", h2)]
    for text in [
        "Posición inicial fuera de cfg_3 y mapa exportado de otro escenario.",
        "Estado mutable compartido entre instancias del simulador.",
        "Doble redondeo que generaba aristas no reversibles.",
        "Confusión entre aproximación bloqueada y celda globalmente ocupada.",
        "Atajos diagonales que no respetaban el volumen barrido del robot.",
    ]:
        story.append(Paragraph("• " + text, bullet))
    story += [Spacer(1, 4), Paragraph("Criterios de aceptación: cobertura de poses=100%, cobertura de superficie=100%, omitidas=0, visitas imposibles=0, error final=0 y colisiones=0 en A/B/C.", note),
              PageBreak()]

    story += [Paragraph("6. Limitaciones y mejoras", h1),
              Paragraph("Limitaciones", h2)]
    for text in [
        "La odometría del simulador es perfecta; no hay ruido, deriva ni localización probabilista.",
        "Los sensores son de contacto. El interior de obstáculos y regiones aisladas permanece honestamente desconocido.",
        "La cobertura DFS es completa pero puede recorrer cada arista del árbol dos veces y no minimiza energía.",
        "El mundo es estático; no se mantiene un mapa temporal de personas u objetos móviles.",
        "El sensor sólo informa del siguiente volumen frontal; no ofrece distancia ni geometría del obstáculo.",
    ]:
        story.append(Paragraph("• " + text, bullet))
    story += [Paragraph("Mejoras con más tiempo", h2)]
    for text in [
        "Sustituir sondeos táctiles por lidar/sonar simulado y un mapa probabilista log-odds.",
        "Aplicar descomposición boustrophedon o Spanning Tree Coverage optimizado para reducir distancia.",
        "Añadir SLAM, estimación de pose y replanteo incremental D* Lite para obstáculos dinámicos.",
        "Optimizar la secuencia de fronteras por ganancia de información y coste de viaje.",
        "Integrar consumo de batería y retorno automático al cargador.",
    ]:
        story.append(Paragraph("• " + text, bullet))
    story += [Paragraph("La elección final no persigue usar el algoritmo más complejo, sino el más avanzado que puede justificarse con la información sensorial disponible y comprobarse con invariantes claros.", note),
              PageBreak()]

    story += [Paragraph("7. Conclusiones", h1),
              Paragraph("La práctica muestra que navegación, mapeo y control no deben resolverse de forma independiente. Un mapa visualmente plausible puede ser inútil para planificar si ignora la huella del robot; un camino geométricamente corto puede ser inseguro si no se conoce su volumen barrido; y un seguidor de pared puede moverse indefinidamente sin cubrir el interior.", body),
              Paragraph("La solución final construye una abstracción común de espacio de configuración, garantiza terminación de la cobertura, usa búsqueda heurística óptima en la rejilla conocida y reutiliza el planificador durante la reproducción. La evaluación automatizada convierte afirmaciones como 'funciona' en medidas reproducibles.", body),
              Paragraph("Ejecución para la defensa", h2),
              Paragraph("1. Ejecutar <b>python validar_practica.py</b> para mostrar las métricas. 2. Lanzar el apartado A con cfg_0 y enseñar el overlay. 3. Ejecutar una ruta larga del apartado B. 4. Grabar dos o tres waypoints y reproducirlos con el apartado C. 5. Explicar por qué se conserva UNKNOWN y por qué no se usan diagonales no certificadas.", body),
              Paragraph("Referencias", h2),
              Paragraph("[1] P. Hart, N. Nilsson y B. Raphael. A Formal Basis for the Heuristic Determination of Minimum Cost Paths. IEEE TSSC, 4(2), 1968. DOI: 10.1109/TSSC.1968.300136.", small),
              Paragraph("[2] B. Yamauchi. A Frontier-Based Approach for Autonomous Exploration. IEEE CIRA, 1997. DOI: 10.1109/CIRA.1997.613851.", small),
              Paragraph("[3] H. Choset. Coverage for Robotics - A Survey of Recent Results. Annals of Mathematics and Artificial Intelligence 31, 2001. DOI: 10.1023/A:1016639210559.", small),
              Paragraph("[4] A. Nash, K. Daniel, S. Koenig y A. Felner. Theta*: Any-Angle Path Planning on Grids. AAAI, 2007, pp. 1177-1183.", small),
              Paragraph("[5] Enunciado oficial Práctica P1: Navegación en entornos complejos, USC, curso 2026/2027.", small)]

    doc.build(story)
    return OUTPUT


if __name__ == "__main__":
    print(build())
