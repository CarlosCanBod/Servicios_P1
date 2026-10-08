#!/usr/bin/python
# encoding: utf-8
"""Tercer escenario original, utilizado para comprobar recorridos largos.

walls describe el mundo real simulado, no la matriz que crea A. objects sitúa
muebles por su centro (coord); solo los objetos con level=0 bloquean el avance.
El tamaño de estas filas lo necesita el simulador, pero no se entrega a A.
"""

# symbols:
#   #   walls
#   |-  wall with a window
#   Ww  wall is a window
#   dD  door
#   R   recharge point
#   any other are ignored

walls = [
    '###################',
    '#                 |',
    '#                 |',
    '#                 |',
    '#                 |',
    '#                 #-----################',
    '#                     RRR#             #',
    '#                     RRR#             |',
    '#                        #             |',
    '##====##                 #             |',
    '       |                 #             #',
    '       |                 #             |',
    '       |                 #             |',
    '       |                 #             |',
    '       |                 #             #',
    '#------#                 #####    ######',
    '#                           #      #',
    '#                           #      #',
    '#                           #      #',
    '#                           #      #',
    '#                           #      #',
    '#                           #      #',
    '#                 ###########      ######',
    '#                 #                     #',
    '#                                       |',
    '#                                       |',
    '#                                       |',
    '#                                       |',
    '#                 #                     |',
    '#                 #                     #',
    '#                 #                     |',
    '#                 #                     |',
    '#                 #                     |',
    '#                 #                     |',
    '#                 #                     |',
    '#                 #                     #',
    '#                 #                     |',
    '#                 #                     |',
    '#                 #                     |',
    '#                 #                     |',
    '#                 #                     #',
    '###dddd####----#####----#----#----#----##'
]
