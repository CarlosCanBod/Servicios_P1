#!/usr/bin/python
# encoding: utf-8
"""Variante extra con pilares y esquinas: datos de entrada para el simulador.

walls se lee por filas Y y columnas X. A conoce contactos al intentar avanzar;
no lee esta lista para decidir su recorrido ni para reservar la matriz final.
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
    '###     ###',
    '#         #',
    '#    #    #',
    '#         #',
    '#  #   #  #',
    '#         #',
    '#         #',
    '#  #   #  #',
    '#         #',
    '#         #',
    '###########',
]
