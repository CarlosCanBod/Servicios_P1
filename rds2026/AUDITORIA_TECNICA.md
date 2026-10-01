# Auditoría técnica y correcciones

Este documento separa los fallos encontrados de las limitaciones que siguen
siendo inherentes al simulador. Las métricas definitivas están en
`resultados/diagnostico.json`.

## Apartado A

### Fallos corregidos

1. **Rejilla demasiado gruesa.** La primera versión exploraba centros separados
   una celda, aunque el robot se mueve en pasos de 0,5. Podía atravesar una pose
   intermedia sin explorar sus ramificaciones ni contabilizar toda su huella.
   En `cfg_0` esto dejaba fuera de la métrica las celdas `(12,11)` a `(15,11)`.
   La búsqueda ahora opera sobre todas las poses alcanzables de medio paso.

2. **Centro navegable confundido con superficie limpiada.** Que el centro no
   pueda entrar en una esquina no implica que la aspiradora no la cubra. El mapa
   JSON contiene dos capas: espacio de configuración y celdas de superficie
   cubiertas. El overlay verde representa cobertura física.

3. **Tamaño conocido antes de explorar.** La versión anterior creaba la matriz
   con `floor.size` y rechazaba vecinos según ese rectángulo. Ahora A guarda
   observaciones dispersas sin ancho, alto ni origen prefijados; son los
   contactos y el movimiento los que delimitan la búsqueda. Tras terminar se
   calculan mínimos y máximos y se reserva la matriz. El plano real se consulta
   sólo después para medir resultados.

4. **Sondeos contabilizados como choques.** Se intentaba el movimiento y después
   se leía el contacto. El controlador consulta el sensor frontal antes de cada
   paso; la cobertura conserva la información y registra cero colisiones.

5. **Visualización engañosa.** Los contactos de espacio de configuración se
   pintaban como celdas físicas rojas completas. Ahora la superficie cubierta se
   rellena en verde y los contactos se muestran como marcadores rojos compactos.

6. **Oráculo de pruebas con redondeo distinto.** Crear un `pygame.Rect` con
   floats no redondea igual que asignar sus propiedades, que es lo que hace el
   simulador. El oráculo independiente reproduce esa semántica y comprueba tanto
   poses como superficie.

### Limitaciones restantes

- La odometría es perfecta porque así la proporciona el simulador.
- Los sensores no permiten conocer el interior de un objeto ni una habitación
  físicamente desconectada; esas regiones permanecen desconocidas.
- DFS es completo y reproducible, pero no minimiza la distancia total. Un
  algoritmo de cobertura más corto necesitaría geometría conocida o sensores de
  distancia antes de comprometer un movimiento.

## Apartado B

### Fallos corregidos

1. **A* a resolución distinta del robot.** Ahora planifica sobre las poses libres
   de 0,5 medidas por A, no sobre una aproximación entera.
2. **Destino imposible sustituido por otro cercano.** B valida los extremos:
   rechaza poses ocupadas o desconocidas. Si son libres pero están desconectados,
   A* devuelve error antes de iniciar el simulador; no se cambia el destino para
   forzar una ruta. También se rechaza un origen ocupado o desconocido.
3. **Mapa y escenario incompatibles.** Se valida el nombre de configuración,
   pero no se presupone que las dimensiones observadas coincidan con las del
   simulador: el mapa sólo abarca los mínimos y máximos explorados.
4. **Coordenadas inválidas.** Se rechazan valores no finitos o fuera del plano.
5. **Éxito aproximado silencioso.** Los tramos planificados exigen llegada exacta;
   ya no se acepta un overshoot de 0,26 celdas como éxito.
6. **Atajos diagonales no certificados.** Se conservan tramos cardinales máximos.
   Esto reduce giros sin atravesar volumen que el mapa táctil no haya observado.

### Limitaciones restantes

- Si el mundo cambia después de mapearlo, el controlador se detiene con error
  seguro. El enunciado especifica que no hay objetos móviles, por lo que no se
  implementa D* Lite ni actualización dinámica.
- Las coordenadas entre muestras se discretizan localmente solo cuando todos los
  vértices de su intervalo son libres conocidos. La distancia del ajuste se
  devuelve; no se ejecuta una llegada continua exacta al punto arbitrario.

## Apartado C

### Fallos corregidos

1. Los waypoints se validan por forma, tipo, finitud, límites y escenario.
2. Se impide que el campo de configuración contenga una ruta de directorio.
3. Cada waypoint se ajusta en la componente actualmente alcanzable.
4. El replay informa del ajuste máximo y exige error final cero.
5. Al salir se detiene el robot antes de añadir y guardar el punto final.
6. Se añadió la tecla `D` para depuración sin perder eventos de teleoperación.

### Limitaciones restantes

- La ruta conserva waypoints, no el tiempo exacto ni la velocidad manual. Es la
  alternativa recomendada por el enunciado y permite replanificar con seguridad.
- La teleoperación requiere una ventana real; su reproducción sí se prueba en
  modo headless.

## Simulador e infraestructura

- Estado mutable de robots y planos aislado por instancia.
- Odometría inicializada desde la pose real.
- Rectángulo de recarga corregido.
- Velocidades cardinales sin residuos trigonométricos.
- Predicción de contacto calculada con un único redondeo, reversible.
- `simulation.stop()` actualiza también `is_running`.
- Mapas y rutas se escriben atómicamente y llevan versión.
- Pruebas negativas cubren rutas malformadas y puntos arbitrarios.
