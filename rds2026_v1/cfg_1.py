#!/usr/bin/python
# encoding: utf-8

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
    '#                 #-----#',
    '#                       #',
    '#                       #',
    '#                       #',
    '#dddddd#                #',
    '       |                #',
    '       |                #',
    '       |                #',
    '       |                #',
    '       |                #',
    '#------#                #',
    '#                       #',
    '#                       #',
    '#                       #',
    '#                       #',
    '#                       #',
    '#                       #',
    '#                    RRR#',
    '#                    RRR#',
    '#########################'
]

#
# format:
#   "coord": image center coordinates (x,y) in meters
#   "level": robot moves in level 0; lower levels are drawn under,
#       higher levels are drawn upper; robot collisions only with
#       objects in level 0
#   "desc": object text decscription to be used in machine detector
#   "file": image file (resolution of 20px per meter)

objects = []

