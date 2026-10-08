#!/usr/bin/python
# encoding: utf-8
"""Mapa extra con huecos y zonas separadas para observar qué es alcanzable.

Cada fila de walls es una fila del mundo: '#' bloquea; espacios son suelo.
A no debe cruzar paredes ni conocer habitaciones a las que no puede entrar.
Este mapa no forma parte de las cuatro filas del diagnóstico de la memoria.
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
    '#         ####',
    '#            #',
    '#            #',
    '#     ###    #',
    '#     # #    #',
    '##    ###    #',
    ' #############',
    '##           #',
    '#            #',
    '#            #',
    '#wwwwwwwwwwww#',
]
