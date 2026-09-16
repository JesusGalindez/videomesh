# Prompt de ejecución — encargo 04

Pegar tal cual como primer mensaje al agente, en la raíz de `VideoMesh`.

---

```text
Trabajas en VideoMesh, en /Users/albertogalindez/Documents/VideoMesh, rama main.

Tu encargo está en docs/encargo-agente-04.md. Léelo entero antes de tocar nada.
Las reglas de trabajo son las del encargo 01, sección 1, y no se repiten: la
prueba primero, compruebas que falla, cambio mínimo, verificación entera, commit.

IDIOMA: español, en el código, en los comentarios, en los commits y conmigo.

QUÉ ES ESTE ENCARGO, y es más grande que los tres anteriores juntos: construir la
cadena de producción que convierte una malla medida en un asset que se usa. Son
los Sprints 5, 6, 8, 9 y 10 del roadmap. Seis bloques, A a F, y tres entregas.

LO QUE NO ES: un generador de 3D. No inventas geometría. Si una etapa rellena un
agujero, lo declara. El asset bonito que no dice qué parte se inventó es
exactamente lo que este proyecto existe para no producir.

ARRANQUE:

  1. bash scripts/verify.sh
     Verde antes de empezar, y apunta el recuento. Es tu línea base.
     Si sale rojo, PARA y dime la línea exacta.

  2. videomesh doctor
     Te va a decir que faltan COLMAP y FFmpeg. Da igual: la densa se hace en
     Colab y no en esta máquina. Lo que necesitas es que el vecino esté y que el
     hash del esquema coincida.

  3. Lee la sección 0.3 del encargo antes que nada más. Es el inventario de lo
     que YA existe en los dos repositorios. La mitad de este encargo es no
     reescribir cosas que están escritas: el trazador de rayos, el diff de
     mallas, las auditorías de UV y textura, los presupuestos por destino.

  4. Bloque A. No empieces por B aunque sea más divertido: sin A no tienes una
     malla real con la que trabajar, y las decisiones de B se toman mirando una
     malla real.

DÓNDE PARAR Y ENSEÑARME:

  Al final del bloque B. Para de verdad, no sigas.

  Hasta que no vea una malla real limpiada y decimada, todo lo de C en adelante
  son parámetros elegidos a ciegas. Enséñame: triángulos antes y después, cuántos
  componentes conexos había y cuántos quedaron, y la distancia de superficie
  contra la entrada.

EL CRITERIO QUE DECIDE SI UNA ETAPA ESTÁ HECHA:

  ¿PUBLICA EL NÚMERO QUE DICE CUÁNTO SE PERDIÓ?

  Decimar es perder detalle. Limpiar es tirar geometría. Retopologizar es mover
  vértices. Las tres son legítimas y las tres son medibles. Una etapa que hace su
  trabajo y no dice cuánto cambió la superficie no está hecha, está a medias — y
  es la mitad que separa esto de cualquier otra herramienta.

  El número sale de `diffMeshes` de SoftSight, en las DOS direcciones por
  separado. Promediarlas escondería justo lo que interesa.

UNA DEPENDENCIA QUE NO ES TUYA:

  Hoy `diffMeshes` lee glTF y GLB, no PLY, así que no puede comparar contra la
  malla medida. Eso se arregla en SoftSight y está asignado fuera de este
  encargo. Si al llegar al bloque B todavía no está, declara ese número como
  NOT_RUN con ese motivo y sigue. NO lo reimplementes en Python: tendrías dos
  medidas de la misma cosa y acabarían discrepando.

LO QUE NO ES TU TRABAJO:

  - No dupliques auditorías. Lo que SoftSight ya juzga —UV, textura, LOD,
    colisión, silueta— se produce aquí y se juzga allí.
  - No metas la densa en esta máquina. Exige CUDA, no la hay, y el cuaderno de
    Colab ya existe en SoftSight.
  - No toques research/.
  - Si encuentras algo roto fuera del encargo, apúntalo al final y sigue.

CUANDO ACABES CADA BLOQUE, dime: qué etapas añadiste, qué publica cada una, cómo
viste fallar sus pruebas, y el recuento de verify.sh antes y después.
```
