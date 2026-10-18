# P1: Navegación en entornos complejos

Robótica de Servizos · Curso 2026/2027.

Alejandro Lavandeira Casais, Carlos Adrián Cancela Bodlak y Yago Martínez Pena.

## Contenido

- `memoria_P1.pdf`: diseño, algoritmos, resultados y limitaciones.
- `video_P1.mp4`: demostración de A, B y C; duración de 1 min 59,93 s.
- `rds2026/`: programas, escenarios, imágenes, mapas y rutas de ejemplo.
- `requirements.txt`: dependencia necesaria para ejecutar el simulador.
- `SHA256SUMS`: sumas de comprobación de los archivos del paquete.

En el repositorio, la memoria está en `output/pdf/` y el vídeo principal en
`output/video/practica/entrega_2min.mp4`. El ZIP coloca ambos en su raíz.

## Instalación

Entorno comprobado: Python 3.12 y Pygame 2.6.1. Para las ejecuciones interactivas
se necesita una sesión gráfica. Desde la carpeta extraída:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd rds2026
```

En Windows, activar el entorno con `.venv\Scripts\activate` antes de entrar en
`rds2026`. Los siguientes comandos presuponen el entorno activado.

## Ejecución de los tres apartados

### A: exploración y mapa

```bash
python apartado_a.py --config cfg_3.py --start 7,7 --fps 60 \
  --output resultados/mapa_cfg_3.json --legacy-output resultados/mapa_cfg_3.txt
```

Explora las posiciones alcanzables mediante DFS. Guarda las observaciones sin
dimensiones prefijadas y crea la matriz al terminar. El TXT representa cobertura
binaria; el JSON conserva también estados y posiciones de medio paso.

### B: navegación

```bash
python apartado_b.py --map resultados/mapa_cfg_3.json \
  --start 2,2 --goal 12,12 --fps 8
```

Valida los extremos, busca con A* y ejecuta el camino. Un destino bloqueado,
desconocido o desconectado se rechaza; no se sustituye por otro destino cercano.
Por ejemplo, esta orden debe terminar con un mensaje de rechazo y código 1:

```bash
python apartado_b.py --map resultados/mapa_cfg_3.json --start 2,2 --goal 9.5,3
```

### C: teleoperación y reproducción

```bash
python apartado_c.py record --config cfg_3.py --start 2,2 \
  --route rutas/ruta_usuario_cfg3.json --fps 8
python apartado_c.py replay --route rutas/ruta_usuario_cfg3.json \
  --map resultados/mapa_cfg_3.json --fps 8
```

Arriba avanza; soltar arriba detiene. Izquierda/derecha giran 90 grados por
pulsación. W marca un punto, S guarda y Q guarda el punto final y termina.
Los waypoints se muestran con X azules numeradas; el objetivo del replay es rojo.

Para reproducir una ruta incluida sin grabar una nueva:

```bash
python apartado_c.py replay --route rutas/ruta_demo_cfg3.json \
  --map resultados/mapa_cfg_3.json --fps 8
```

C planifica entre waypoints, no repite las pulsaciones. Puede aproximarlos a
poses libres conectadas; `max_snap_distance` mide el ajuste y `final_error` se
refiere al objetivo ejecutado. Estas limitaciones se explican en la memoria.

## Escenarios del vídeo

El vídeo muestra A, B y C en `cfg_0.py`, y C en `cfg_laberinto.py`.
Se incluyen sus mapas y rutas para reproducir los recorridos:

```bash
python apartado_b.py --map resultados/mapa_cfg_0.json \
  --start 14,17.5 --goal 14,7.5 --fps 8
python apartado_c.py replay --route rutas/ruta_muebles.json \
  --map resultados/mapa_cfg_0.json --fps 8
python apartado_c.py replay --route rutas/ruta_laberinto.json \
  --map resultados/mapa_cfg_laberinto.json --fps 8
```

Las rutas del vídeo se obtuvieron mediante eventos de teclado automatizados para
repetir las demostraciones. El modo `record` permite introducirlos manualmente.
También se incluyen los escenarios modificados con cajas interiores y pilares.
Al modificar un escenario es necesario volver a ejecutar A antes de usar su mapa.

## Pruebas y resultados

Desde `rds2026`, con el entorno activado:

```bash
python -m unittest discover -s tests -v
python validar_practica.py
```

Los tests comprueban representación del mapa, planificación, rechazos de destinos
y ejecución integrada. El diagnóstico ejecuta los cuatro escenarios originales
y guarda las medidas en `resultados/diagnostico.json`, junto con sus mapas.
Al repetirlo se sustituyen esos archivos de resultados.

Para ejecutar A sin ventana y sin esperas entre ciclos:

```bash
python apartado_a.py --config cfg_3.py --start 7,7 --headless --fps 0 \
  --output resultados/mapa_cfg_3.json --legacy-output resultados/mapa_cfg_3.txt
```

`--fps` limita los ciclos por segundo; cada avance sigue siendo de 0,5 unidades.
La cobertura se mide sobre lo alcanzable desde el inicio, no sobre habitaciones
aisladas. El simulador usa objetos estáticos y odometría sin ruido.

La descripción de las interfaces y los formatos está en
`rds2026/README_SOLUCION.md`. Los archivos `cfg_*.py` se ejecutan como código al
cargarse: deben proceder de una fuente de confianza.

En Linux se puede verificar la integridad desde la raíz del paquete con:

```bash
sha256sum -c SHA256SUMS
```
