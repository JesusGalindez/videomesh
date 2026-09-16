# Prompt de ejecución — encargo 05

Pegar tal cual como primer mensaje al agente, en la raíz de `VideoMesh`.

---

```text
Trabajas en VideoMesh, en /Users/albertogalindez/Documents/VideoMesh, rama main.
Este encargo toca también SoftSight, en ../Dron/softsight.

Tu encargo está en docs/encargo-agente-05.md. Léelo entero antes de tocar nada.
Las reglas de trabajo son las del encargo 01, sección 1, y no se repiten: la
prueba primero, compruebas que falla, cambio mínimo, verificación entera, commit.

IDIOMA: español, en el código, en los comentarios, en los commits y conmigo.

QUÉ ES ESTE ENCARGO: separar las piezas móviles de una malla de una sola pieza
—la que sale de cualquier generativo— y saber CON NÚMEROS si el corte está bien.

Lo segundo es lo que falta. Lo primero se hizo a mano el 2026-09-15 y funcionó,
pero cada iteración era «cambio una constante, recargo, miro la captura». Eso no
lo puedes hacer tú, y por eso el encargo empieza por las medidas y no por el
segmentador.

EL ORDEN NO ES NEGOCIABLE:

  Primero las medidas, en SoftSight. Después el segmentador, en VideoMesh.

  Al revés es lo que costó las horas de aquel día: sin puerta, cada mejora es una
  opinión y no se puede iterar.

ARRANQUE:

  1. bash scripts/verify.sh
     Verde antes de empezar, y apunta el recuento. Si sale rojo, PARA.

  2. En ../Dron/softsight: npm run test:animation
     Verde también. Vas a añadir puertas ahí.

  3. Lee la sección 0.1 del encargo. Son los cinco fallos concretos de aquel día,
     cada uno con la regla que deja. Te van a pasar los mismos si no.

DÓNDE PARAR Y ENSEÑARME:

  Al final del bloque A: conservación y longitud del borde del corte. Para de
  verdad.

  Con esas dos ya se puede decidir si el enfoque vale. Enséñame el número del
  borde sobre DOS cortes del mismo objeto: uno por su costura y otro por la
  mitad de una superficie. Si la medida no los distingue con claridad, lo demás
  sobra y lo hablamos antes de seguir.

EL CRITERIO QUE DECIDE SI UNA MEDIDA ESTÁ HECHA:

  ¿DISTINGUE UN CORTE BUENO DE UNO MALO?

  No «¿devuelve un número?». Una medida que siempre devuelve algo parecido es
  peor que no tenerla: da confianza sin informar. El caso rojo de cada puerta es
  el corte deliberadamente malo, y tiene que dar un número mucho peor.

  Para el eje es aún más literal: desplázalo a propósito y comprueba que la caja
  envolvente crece, y que lo que crece se parece a lo que desplazaste.

TRES TRAMPAS QUE YA SE PISARON, para que no las pises otra vez:

  - Los marcos. El GLB viene cuantizado —enteros con la escala en el nodo—, así
    que restar posiciones entre marcos distintos da resultados absurdos con tres
    síntomas distintos: cero coincidencias, piezas disparadas, piezas invisibles.
    Declara el marco de cada medida.

  - Un pico en un histograma no es una identidad. Buscando «la pared interior del
    conducto» se encontraba la superficie exterior, que concentra más. Comprueba
    qué encontraste.

  - No modifiques el árbol de objetos mientras lo recorres. El error sale por un
    sitio que no tiene nada que ver.

LO QUE NO ES TU TRABAJO:

  - No escribas un segmentador antes que las medidas.
  - No reimplementes diffMeshes, boundsTree ni meshTopology. Están y funcionan.
  - No uses una captura como criterio de aceptación. Nunca.
  - Si encuentras algo roto fuera del encargo, apúntalo al final y sigue.

CUANDO ACABES CADA BLOQUE, dime: qué medidas añadiste, cómo las viste fallar con
un caso malo, y el recuento de verify.sh y de la suite de SoftSight antes y
después.
```
