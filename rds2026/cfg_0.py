#!/usr/bin/python
# encoding: utf-8

# symbols:
#   #   walls
#   |=  wall with a window
#   Ww  wall is a window
#   dD  door
#   R   recharge point
#   any other are ignored

walls = [
    '###################',
    '#.................|',
    '#.................|',
    '#.................|',
    '#.................|',
    '#.................#===#====#',
    '#..........................#',
    '#..........................#',
    '#..........................#',
    '#..........................#',
    '#..........................#',
    '#======#...................#',
    '       D...................#',
    '       D...................#',
    '       D...................#',
    '       D...................#',
    '       D...................#',
    '       D...................#',
    '#======#...................#',
    '#..........................#',
    '#..........................#',
    '#..........................#',
    '#..........................#',
    '#..........................#',
    '#..........................#',
    '#.......................RRR#',
    '#.......................RRR#',
    '############################'
]

#
# format:
#   "coord": image center coordinates (x,y) in meters
#   "level": robot moves in level 0; lower levels are drawn under,
#       higher levels are drawn upper; robot collisions only with
#       objects in level 0
#   "desc": object text decscription to be used in machine detector
#   "file": image file (resolution of 20px per meter)

objects = [
    # alfombra
    {
        'coord': (9, 8),
        'level': -1,
        'desc': 'clothes',
        'file': './img/alfombra.png'
    },
    
    # zapatos sobre la alfombra
    {
        'coord': (12, 7),
        'desc': 'clothes',
        'file': './img/zapatos.png'
    },
    
    # muebles
    {
        'coord': (25, 7),
        'desc': 'object',
        'file': './img/silla.png'
    },
    {
        'coord': (25, 10.5),
        'desc': 'object',
        'file': './img/silla.png'
    },
    {
        'coord': (3, 5),
        'desc': 'object',
        'file': './img/sofa-izqda.png'
    },
    {
        'coord': (10.5, 3.07),
        'desc': 'object',
        'file': './img/sofa-drcha.png'
    },
    
    # plantas
    {
        'coord': (4, 25),
        'desc': 'plant',
        'file': './img/planta-base.png'
    },
    {
        'coord': (4, 25),
        'level': 1,
        'desc': 'plant',
        'file': './img/planta-upper.png'
    },
    {
        'coord': (17, 3),
        'desc': 'plant',
        'file': './img/planta-base.png'
    },
    {
        'coord': (17, 3),
        'level': 1,
        'desc': 'plant',
        'file': './img/planta-upper.png'
    },
    {
        'coord': (7, 25),
        'desc': 'plant',
        'file': './img/cactus.png'
    },
    # planta sobre silla
    #{
    #    'coord': (25, 11),
    #    'level': 1,
    #    'desc': 'plant',
    #    'file': './img/planta-base.png'
    #},
    #{
    #    'coord': (25, 11),
    #    'level': 2,
    #    'desc': 'plant',
    #    'file': './img/planta-upper.png'
    #},

    # persona    
    {
        'coord': (13, 12.5),
        'desc': 'person',
        'file': './img/persona-base.png'
    },
    {
        'coord': (15, 11),
        'level': 1,
        'desc': 'person',
        'file': './img/persona-upper.png'
    },

    # gato con sobrepeso sobre silla
    {
        'coord': (25, 6.5),
        'level': 1,
        'desc': 'animal',
        'file': './img/gato.png'
    }
]

