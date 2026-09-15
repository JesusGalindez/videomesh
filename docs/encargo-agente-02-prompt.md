# Prompt de ejecución — encargo 02

Pegar tal cual como primer mensaje al agente, en la raíz de `VideoMesh`.

---

```text
Trabajas en VideoMesh, en /Users/albertogalindez/Documents/VideoMesh, rama main.

Tu encargo está en docs/encargo-agente-02.md. Léelo entero antes de tocar nada.
Las reglas de trabajo son las del encargo 01, sección 1, y no se repiten: la
prueba primero, compruebas que falla, cambio mínimo, verificación entera, commit.

IDIOMA: español, en el código, en los comentarios, en los commits y conmigo.

QUÉ ES ESTE ENCARGO, para que no lo confundas con el 01: no añade funcionalidad.
Las tres tareas hacen que un tipo de fallo deje de poder ocurrir en silencio —que
un documento diga una cosa y el código otra— y ya ocurrió dos veces, las dos
contadas en el encargo con fecha.

ARRANQUE:

  1. bash scripts/verify.sh
     Verde antes de empezar. Apunta el recuento de pruebas: es tu línea base, y
     las tres tareas tienen que dejarlo verde con MÁS pruebas.
     Si sale rojo, PARA y dime la línea exacta.

  2. shasum -a 256 docs/contrato-videomesh.md
     Compáralo con la cabecera de docs/OBLIGACIONES-VIDEOMESH.md. Se revisó el
     2026-09-15, así que debería cuadrar. Si no cuadra, dímelo y sigue igualmente:
     la tarea 1 es exactamente automatizar esta comprobación, y encontrártela
     rota ya te dice por qué hace falta.

  3. Empieza por la tarea 1. Las tres son independientes, pero la 1 es la más
     barata y es la que te enseña el patrón que usan las otras dos.

EL CRITERIO QUE DECIDE SI UNA TAREA ESTÁ HECHA, y es el mismo en las tres:

  ¿HAS VISTO LA PRUEBA EN ROJO?

  No «¿pasa?». Las tres pruebas de este encargo van a pasar a la primera, porque
  el repositorio está bien hoy. Una prueba que solo se ha visto verde no ha
  demostrado que mire nada: una que devolviera True sin comprobar pasaría igual.

  Así que las tres se escriben para poder romperse sin tocar el repositorio: la
  función que compara recibe el dato como argumento, y la prueba le pasa un dato
  inventado que TIENE que fallar. Si no puedes escribir ese caso, la función está
  mal diseñada: sácala de donde esté hasta que reciba lo que compara.

CUÁNDO ME PARAS. Solo esto:

  - verify.sh se pone rojo y no lo arregla tu propio cambio.
  - La tarea 2 te obliga a decidir dónde vive el estado publicado y hay dos
    sitios razonables. Elige el que menos duplique y dímelo; no preguntes.
  - Descubres que algún documento del repositorio dice algo que el código
    contradice. Eso NO es una interrupción: apúntalo, sigue, y dímelo al final.
    Es literalmente lo que este encargo busca.

LO QUE NO HACES:

  - No copias contracts/versions.json a este repositorio. Se LEE del original en
    ../Dron/softsight/contracts/. Una copia diverge, y es el mismo error que el
    symlink del contrato evita.
  - No escribes AGENTS.md entero a mano. Lo que un script puede saber se genera;
    lo que no —dónde va un cambio, qué se rompe si lo tocas— se escribe a mano y
    vive fuera de los delimitadores. Fingir que un script sabe eso es peor que no
    tener el fichero.
  - No tocas nada dentro de ../Dron/softsight. Solo lees.
  - No arreglas la deriva que encuentres en los documentos como parte de estas
    tareas, salvo que sea de una línea. Apúntala. Arreglar contenido y construir
    la puerta que lo vigila son dos cosas, y mezclarlas deja un commit del que no
    se sabe qué sujeta qué.

CUANDO ACABES LAS TRES, una última comprobación que vale más que las tres juntas:
rompe a mano el hash de la cabecera de OBLIGACIONES, corre verify.sh, y
comprueba que se pone ROJO con un mensaje que te diga qué hacer. Luego deshazlo.
Si no se pone rojo, no has cerrado nada.

Empieza. No me confirmes que has entendido: dime el recuento del paso 1 y sigue.
```

---

## Por qué el prompt insiste tanto en el rojo

Las tres pruebas de este encargo pasan a la primera. Eso las hace peligrosas: **el
repositorio está bien hoy, así que una prueba que no comprobara nada daría
exactamente el mismo resultado que una correcta**, y quedaría en la suite durante
meses dando una seguridad que no existe.

Es el fallo que más cuesta ver, porque no produce ningún síntoma hasta el día en
que tenía que haber avisado.
