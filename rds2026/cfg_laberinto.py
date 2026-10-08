#!/usr/bin/python
# encoding: utf-8
"""Mapa extra con pasillos y paredes interiores para probar retrocesos de A.

walls describe filas del mundo, no una ruta. Un pasillo visualmente abierto
solo es transitable si cabe el cuerpo 2x2, no únicamente el centro del robot.
"""

# symbols:
#   #   walls
#   |-  wall with a window
#   Ww  wall is a window
#   dD  door
#   R   recharge point
#   any other are ignored

walls = [
    '#################',
    '#    #          #',
    '#    #          #',
    '#    #  #########',
    '#               #',
    '#               #',
    '#               #',
    '#               #',
    '########        #',
    '#             ###',
    '#               #',
    '#######         #',
    '#    #        # #',
    '#             # #',
    '#             # #',
    '#################',
]
