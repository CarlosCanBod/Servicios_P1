# Vídeos de la práctica P1

El enunciado solo pide un «vídeo breve (screencast)» y no fija duración ni FPS. Hay 12 demostraciones completas, una por apartado y escenario, y un resumen concatenado que conserva los 12 clips completos en orden A/B/C. Los MP4 se codifican a 30 fps; la velocidad indicada es pasos físicos visibles por segundo (un paso desplaza 0,5 unidades).
Rótulo: **12 ejemplos completos · A, B y C en 4 mapas**. Resumen íntegro: [resumen_completo.mp4](resumen_completo.mp4) (4:56.1).

## Casos

### Apartado A

- **cfg_0.py** — cfg_0.py original, con muebles y objetos: contactos y cobertura densa. resumen 00:00.0; velocidad: 60 pasos/s; duración: 47.57 s; [vídeo](A_muebles.mp4).
  Cobertura: 100.0% poses y 100.0% suelo alcanzable; omisiones 0, inesperadas 0, colisiones 0.
- **cfg_1_copy.py** — cfg_1_copy.py modificado: cajas interiores y estrechamientos. resumen 00:47.6; velocidad: 60 pasos/s; duración: 44.0 s; [vídeo](A_interior.mp4).
  Cobertura: 100.0% poses y 100.0% suelo alcanzable; omisiones 0, inesperadas 0, colisiones 0.
- **cfg_laberinto.py** — cfg_laberinto.py modificado: pasillos y retrocesos. resumen 01:31.6; velocidad: 45 pasos/s; duración: 20.87 s; [vídeo](A_laberinto.mp4).
  Cobertura: 100.0% poses y 100.0% suelo alcanzable; omisiones 0, inesperadas 0, colisiones 0.
- **cfg_pilares_grande.py** — cfg_pilares_grande.py modificado: pilares y esquinas. resumen 01:52.4; velocidad: 35 pasos/s; duración: 10.57 s; [vídeo](A_pilares.mp4).
  Cobertura: 100.0% poses y 100.0% suelo alcanzable; omisiones 0, inesperadas 0, colisiones 0.

### Apartado B

- **cfg_0.py** — cfg_0.py original, con muebles y objetos: contactos y cobertura densa. resumen 02:03.0; velocidad: 5 pasos/s; duración: 14.0 s; [vídeo](B_muebles.mp4).
  A*: 30 pasos frente a Manhattan 20 (+10 por rodeo); error final 0.0, colisiones 0. Se muestran los rechazos medidos: Destino bloqueado, Destino desconocido, Destino fuera del mapa
- **cfg_1_copy.py** — cfg_1_copy.py modificado: cajas interiores y estrechamientos. resumen 02:17.0; velocidad: 9 pasos/s; duración: 15.1 s; [vídeo](B_interior.mp4).
  A*: 64 pasos frente a Manhattan 32 (+32 por rodeo); error final 0.0, colisiones 0. Se muestran los rechazos medidos: Destino bloqueado, Destino desconocido, Destino fuera del mapa
- **cfg_laberinto.py** — cfg_laberinto.py modificado: pasillos y retrocesos. resumen 02:32.1; velocidad: 8 pasos/s; duración: 14.73 s; [vídeo](B_laberinto.mp4).
  A*: 54 pasos frente a Manhattan 22 (+32 por rodeo); error final 0.0, colisiones 0. Se muestran los rechazos medidos: Destino bloqueado, Destino desconocido, Destino fuera del mapa
- **cfg_pilares_grande.py** — cfg_pilares_grande.py modificado: pilares y esquinas. resumen 02:46.8; velocidad: 5 pasos/s; duración: 14.0 s; [vídeo](B_pilares.mp4).
  A*: 30 pasos frente a Manhattan 16 (+14 por rodeo); error final 0.0, colisiones 0. Se muestran los rechazos medidos: Destino bloqueado, Destino desconocido, Destino fuera del mapa

### Apartado C

- **cfg_0.py** — cfg_0.py original, con muebles y objetos: contactos y cobertura densa. resumen 03:00.8; velocidad: 5 pasos/s; duración: 28.1 s; [vídeo](C_muebles.mp4).
  6 waypoints grabados con teclas automatizadas y persistidos en [ruta_muebles.json](datos/ruta_muebles.json); replay: max_snap_distance 0.0, error final 0.0, colisiones teleop/replay 0/0.
- **cfg_1_copy.py** — cfg_1_copy.py modificado: cajas interiores y estrechamientos. resumen 03:28.9; velocidad: 9 pasos/s; duración: 29.0 s; [vídeo](C_interior.mp4).
  7 waypoints grabados con teclas automatizadas y persistidos en [ruta_interior.json](datos/ruta_interior.json); replay: max_snap_distance 0.0, error final 0.0, colisiones teleop/replay 0/0.
- **cfg_laberinto.py** — cfg_laberinto.py modificado: pasillos y retrocesos. resumen 03:57.9; velocidad: 8 pasos/s; duración: 30.27 s; [vídeo](C_laberinto.mp4).
  8 waypoints grabados con teclas automatizadas y persistidos en [ruta_laberinto.json](datos/ruta_laberinto.json); replay: max_snap_distance 0.0, error final 0.0, colisiones teleop/replay 0/0.
- **cfg_pilares_grande.py** — cfg_pilares_grande.py modificado: pilares y esquinas. resumen 04:28.2; velocidad: 5 pasos/s; duración: 27.9 s; [vídeo](C_pilares.mp4).
  6 waypoints grabados con teclas automatizadas y persistidos en [ruta_pilares.json](datos/ruta_pilares.json); replay: max_snap_distance 0.0, error final 0.0, colisiones teleop/replay 0/0.

## Repetir ejemplos

Desde la raíz del proyecto, estos comandos generan o reemplazan únicamente el MP4 del caso indicado dentro de output/video/practica. Los mapas y rutas personales no se modifican. `--speed` permite fijar otros pasos visibles/s.

- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section A --scenario muebles`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section A --scenario interior`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section A --scenario laberinto`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section A --scenario pilares`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section B --scenario muebles`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section B --scenario interior`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section B --scenario laberinto`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section B --scenario pilares`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section C --scenario muebles`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section C --scenario interior`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section C --scenario laberinto`
- `/home/alejandro/Alejandro/Robotica_Servicios/P1/tmp/bin/python generar_videos_practica.py --section C --scenario pilares`

Los datos por escenario, rutas guardadas y métricas están en `datos/` y `metricas.json`. Hojas de revisión: [A](revision/contacto_A.jpg), [B](revision/contacto_B.jpg), [C](revision/contacto_C.jpg); los clips C tienen una captura del replay rojo y los B una del rechazo. En C la secuencia de teclas es una demostración automatizada de los controles reales; no representa a una persona manejando.

## Grabación manual opcional

Estos comandos abren el simulador con ventana y permiten manejarlo; no crean MP4. Para entregar el screencast generado con las 12 demostraciones automatizadas, usa los MP4 anteriores. En C: flechas para avanzar/girar 90°, W marca, S guarda, Q termina.

A genera el mapa previo que usa B/C. Los pasos A son 35–60/s según el tamaño; B usa 5–9/s. C interactivo va a 12 fps y el replay a 8 fps.

### cfg_0.py

```bash
tmp/bin/python rds2026/apartado_a.py --config cfg_0.py --start 21,21 --fps 60 --output ../output/video/practica/datos/mapa_muebles.json --legacy-output ../output/video/practica/datos/mapa_muebles.txt
```
```bash
tmp/bin/python rds2026/apartado_b.py --config cfg_0.py --map ../output/video/practica/datos/mapa_muebles.json --start 14,17.5 --goal 14,7.5 --fps 5
```
```bash
tmp/bin/python rds2026/apartado_c.py record --config cfg_0.py --start 21,21 --route rutas/video_manual_muebles.json --fps 12
tmp/bin/python rds2026/apartado_c.py replay --route rutas/video_manual_muebles.json --map ../output/video/practica/datos/mapa_muebles.json --fps 8
```

### cfg_1_copy.py

```bash
tmp/bin/python rds2026/apartado_a.py --config cfg_1_copy.py --start 21,21 --fps 60 --output ../output/video/practica/datos/mapa_interior.json --legacy-output ../output/video/practica/datos/mapa_interior.txt
```
```bash
tmp/bin/python rds2026/apartado_b.py --config cfg_1_copy.py --map ../output/video/practica/datos/mapa_interior.json --start 2,2 --goal 2,18 --fps 9
```
```bash
tmp/bin/python rds2026/apartado_c.py record --config cfg_1_copy.py --start 21,21 --route rutas/video_manual_interior.json --fps 12
tmp/bin/python rds2026/apartado_c.py replay --route rutas/video_manual_interior.json --map ../output/video/practica/datos/mapa_interior.json --fps 8
```

### cfg_laberinto.py

```bash
tmp/bin/python rds2026/apartado_a.py --config cfg_laberinto.py --start 3,3 --fps 45 --output ../output/video/practica/datos/mapa_laberinto.json --legacy-output ../output/video/practica/datos/mapa_laberinto.txt
```
```bash
tmp/bin/python rds2026/apartado_b.py --config cfg_laberinto.py --map ../output/video/practica/datos/mapa_laberinto.json --start 2,2 --goal 2,13 --fps 8
```
```bash
tmp/bin/python rds2026/apartado_c.py record --config cfg_laberinto.py --start 3,3 --route rutas/video_manual_laberinto.json --fps 12
tmp/bin/python rds2026/apartado_c.py replay --route rutas/video_manual_laberinto.json --map ../output/video/practica/datos/mapa_laberinto.json --fps 8
```

### cfg_pilares_grande.py

```bash
tmp/bin/python rds2026/apartado_a.py --config cfg_pilares_grande.py --start 3,3 --fps 35 --output ../output/video/practica/datos/mapa_pilares.json --legacy-output ../output/video/practica/datos/mapa_pilares.txt
```
```bash
tmp/bin/python rds2026/apartado_b.py --config cfg_pilares_grande.py --map ../output/video/practica/datos/mapa_pilares.json --start 5.5,2 --goal 5.5,10 --fps 5
```
```bash
tmp/bin/python rds2026/apartado_c.py record --config cfg_pilares_grande.py --start 3,3 --route rutas/video_manual_pilares.json --fps 12
tmp/bin/python rds2026/apartado_c.py replay --route rutas/video_manual_pilares.json --map ../output/video/practica/datos/mapa_pilares.json --fps 8
```

Al regenerar un ejemplo con `--section` y `--scenario`, el generador sustituye el MP4 de ese caso y sus datos propios en `datos/`, actualiza su fila de métricas e índice y vuelve a concatenar el resumen con el inventario completo. `--speed` solo cambia la velocidad visible del apartado/escenario indicado.
