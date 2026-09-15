# Prompt de ejecución — encargo 03

Pegar tal cual como primer mensaje al agente, en la raíz de `VideoMesh`.

---

```text
Trabajas en VideoMesh, en /Users/albertogalindez/Documents/VideoMesh, rama main.

Tu encargo está en docs/encargo-agente-03.md. Léelo entero antes de tocar nada.
Las reglas de trabajo son las del encargo 01, sección 1, y no se repiten: la
prueba primero, compruebas que falla, cambio mínimo, verificación entera, commit.

IDIOMA: español, en el código, en los comentarios, en los commits y conmigo.

QUÉ ES ESTE ENCARGO: cuatro reparaciones. Ninguna añade nada. Las cuatro son un
documento o una comprobación que afirma hoy algo que no es verdad, y las cuatro
están medidas: el encargo dice cómo se reprodujo cada una.

ARRANQUE, y este es distinto de los anteriores:

  1. bash scripts/verify.sh
     VA A SALIR ROJO. Eso es lo esperado, y es la tarea 1:

       tests/test_contrato_no_ha_derivado.py — declarado 9023b479... / real 02ce8a7e...

     El contrato cambió ayer en SoftSight (commit 49b7e4e) y nadie tocó este
     repositorio. La puerta que escribiste en el encargo 02 lo cazó sola. Si sale
     rojo por CUALQUIER OTRA cosa, para y dime la línea exacta.

  2. No actualices el hash todavía. Lee primero qué cambió:

       git -C ../Dron/softsight show 49b7e4e -- docs/contrato-videomesh.md

     Son catorce líneas. Si te limitas a copiar el hash nuevo sin leer el diff,
     has convertido la puerta en un trámite y la próxima vez que cambie algo que
     sí importe harás lo mismo.

  3. Después, las tareas 2, 3 y 4 en ese orden. Son independientes.

EL CRITERIO QUE DECIDE SI LA TAREA 2 ESTÁ HECHA:

  ¿LA HAS VISTO EN ROJO?

  Es la única de las cuatro que toca código, y la trampa es la de siempre: vas a
  arreglar `doctor` y va a seguir saliendo verde, porque en TU máquina dist-node
  existe. Verde no demuestra nada ahí.

  La forma de verla en rojo está en el encargo y es literal: mueves
  ../Dron/softsight/dist-node a un lado, corres doctor, tiene que salir distinto
  de 0 nombrando lo que falta, y lo devuelves a su sitio. Si no lo has hecho, la
  tarea no está hecha aunque el código parezca correcto.

  Y cuando lo muevas, comprueba también lo otro: que pytest se pone rojo con él
  fuera. Si no se pusiera, el problema sería mayor que el que vienes a arreglar.

LO QUE NO ES TU TRABAJO:

  - No reescribas el árbol de directorios del roadmap. Es una foto del
    2026-08-12 y cambiarla la falsifica. Se le añade una nota al lado.
  - No toques research/. Está sin versionar a propósito o por descuido y eso lo
    decide quien lleva el repositorio, no tú.
  - No arregles nada que no esté en el encargo. Si encuentras algo, apúntalo al
    final de tu informe y sigue.

CUANDO ACABES, dime en un párrafo por cada tarea: qué cambiaste, cómo la viste
fallar, y el recuento de verify.sh antes y después.
```
