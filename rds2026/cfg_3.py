#!/usr/bin/python
# encoding: utf-8
"""Cuarto escenario original: caso pequeño para las pruebas de integración.

walls contiene filas del escenario; '#' y ventanas/puertas son obstáculos.
objects contiene imágenes centradas en coord; level=0 bloquea, otros niveles
solo decoran. No confundir estos datos con el JSON descubierto en el apartado A.
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
    '#         #',
    '#         #',
    '#         ####',
    '#            #',
    '#            #',
    '##           #',
    ' ##########  #',
    '##           #',
    '#            #',
    '#            #',
    '#wwwwwwwwwwww#',
]
