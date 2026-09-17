Cosas para hacer

• Construir un algoritmo que mapee el entorno para identificar qué celdas están
ocupadas y qué celdas están libres. ¿Conseguís cubrir toda la superficie?
Recomiendo comenzar por un algoritmo de seguimiento de paredes, para
luego tratar de llegar a todas las celdas del interior del apartamento.


• Construir un algoritmo para desplazarse en línea recta entre dos puntos
arbitrarios, mientras sortea obstáculos. Hay dos posibilidades principales:
Ir avanzando simplemente en la dirección deseada y, ante un obstáculo,
intentar rodearlo siguiendo la regla de la mano derecha. Alternativamente,
podeis utilizar el mapa de celdas libres y ocupadas del punto anterior para
planificar una ruta entre los puntos inicial y final con un algoritmo de
inundación, y luego mover el robot por el camino calculado.

• Introducir capacidades de teleoperación. Básicamente, construir rutas con
ayuda del usuario, almacenarlas en fichero y recuperarlas para que el robot
vuelva a recorrerlas. De nuevo, dos posibilidades:
Ir controlando manualmente el robot y que éste recuerde las celdas por las
que pasa, o ir controlando manualmente el robot y periódicamente pulsar
un botón para que deje un waypoint; luego, recuperar estos puntos y hacer
que de manera autónoma vaya en línea recta entre ellos