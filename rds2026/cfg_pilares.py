#!/usr/bin/python
# encoding: utf-8
"""Mapa extra con obstáculos aislados, útil para enseñar cómo A rodea pilares.

Cada '#' ocupa una celda física; los espacios no crean objetos. A registra
poses bloqueadas del centro, que no coinciden con la silueta exacta del pilar.
"""

# symbols:
#   #   walls
#   |-  wall with a window
#   Ww  wall is a window
#   dD  door
#   R   recharge point
#   any other are ignored

walls = [
    '###########',
    '#         #',
    '#         #',
    '#  #   #  #',
    '#         #',
    '#         #',
    '#  #   #  #',
    '#         #',
    '#         #',
    '###########'
]
