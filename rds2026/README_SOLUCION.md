# P1 - Navegación en entornos complejos

La solución separa percepción/cobertura, planificación y control. El mapa es una
rejilla de **espacio de configuración**: una celda libre representa una posición
segura para el centro de la aspiradora de 2x2, no un píxel decorativo del plano.

## Apartado A: mapeo y cobertura

`apartado_a.py` realiza exploración DFS en línea a resolución de 0,5, igual al
paso físico del robot. Prueba las cuatro poses vecinas mediante los sensores de
contacto, retrocede en callejones y termina cuando no queda ninguna pose alcanzable
sin explorar. A diferencia del antiguo seguidor de paredes, cubre interiores,
esquinas y ramificaciones. El mapa separa los centros navegables de las celdas de
suelo realmente cubiertas por la huella 2x2.

El explorador **no recibe el tamaño ni el origen del plano**: almacena poses,
contactos y celdas cubiertas en conjuntos dispersos de coordenadas odométricas.
Solo cuando termina calcula `min_x`, `max_x`, `min_y` y `max_y` de lo observado,
reserva la matriz y guarda su origen en el JSON. El tamaño que usa internamente
el simulador para dibujar la ventana no se entrega al algoritmo. La comparación
con el plano real se realiza después y únicamente para el diagnóstico.

```bash
cd rds2026
../tmp/bin/python apartado_a.py --config cfg_0.py --start 21,21
```

Para ejecutar rápidamente sin ventana:

```bash
SDL_VIDEODRIVER=dummy ../tmp/bin/python apartado_a.py \
  --config cfg_2.py --start 21,21 --fps 0 --headless
```

Genera `mapa_grid.json` (formato versionado con origen, poses a 0,5, cobertura,
estados desconocido/libre/obstáculo y metadatos) y `mapa_grid.txt` (matriz
binaria: 1 celda cubierta, 0 celda no cubierta). Un 0 del TXT **no significa**
obstáculo: para distinguir desconocido y contacto hay que consultar el JSON.

## Apartado B: navegación punto a punto

Se utiliza A* con heurística Manhattan admisible sobre poses libres de medio paso. El camino
óptimo de la rejilla se comprime en tramos cardinales máximos, reduciendo giros sin
arriesgar atajos diagonales cuyo volumen barrido no esté observado.

```bash
../tmp/bin/python apartado_b.py --map mapa_grid.json \
  --start 23,7 --goal 2,26
```

El origen y el destino deben corresponder a poses libres conocidas. Un punto
ocupado o desconocido se rechaza antes de iniciar el simulador. Si ambos extremos
son libres pero están en componentes desconectadas, A* informa de que no existe
ruta; no se cambia el destino a otro punto cercano. La orden termina con código
de salida 1 y un mensaje legible.

Para coordenadas entre muestras solo se permite un ajuste local de discretización
si todos los vértices de su intervalo son libres conocidos. Se publica la distancia
del ajuste; no se certifica llegada continua exacta a la coordenada arbitraria.
Un intervalo con poses bloqueadas o desconocidas se rechaza, aunque haya una pose
libre cercana. Este tratamiento también se aplica al origen.

## Apartado C: teleoperación y reproducción

Grabación manual:

```bash
../tmp/bin/python apartado_c.py record --config cfg_0.py \
  --start 21,21 --route rutas/mi_ruta.json
```

- Flecha arriba: avanzar mientras se mantiene pulsada.
- Flechas izquierda/derecha: girar 15 grados.
- `W`: añadir waypoint.
- `S`: guardar.
- `Q`: guardar el punto final y salir.
- `D`: activar o desactivar la vista de depuración.

Reproducción autónoma (replanifica entre waypoints con el apartado B):

```bash
../tmp/bin/python apartado_c.py replay --route rutas/mi_ruta.json \
  --map mapa_grid.json
```

## Validación

```bash
../tmp/bin/python -m unittest discover -s tests -v
../tmp/bin/python validar_practica.py
```

La segunda orden explora los cuatro mapas, verifica poses y superficie, ejecuta
rutas largas y reproduce una ruta guardada. Los resultados quedan en
`resultados/diagnostico.json`. La crítica completa está en
`AUDITORIA_TECNICA.md`.

## Decisiones y limitaciones honestas

- El simulador proporciona odometría perfecta; no se implementa SLAM probabilista.
- Los objetos son estáticos, como especifica el enunciado.
- El mapa operativo representa transitabilidad del robot, por lo que un hueco libre
  pero demasiado estrecho para la aspiradora no se etiqueta como navegable.
- Se prioriza la seguridad del camino cardinal sobre Theta* diagonal: con sensores
  de contacto y muestras sólo en centros enteros no existe evidencia suficiente para
  certificar todo el volumen barrido por un segmento diagonal.
- DFS ofrece completitud sobre la rejilla alcanzable, aunque no minimiza la longitud
  total de cobertura. Una descomposición boustrophedon reduciría recorridos en mapas
  conocidos, pero necesita geometría más completa que los sensores disponibles.
