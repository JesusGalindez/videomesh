# Prompt de ejecución — encargo 01

Pegar tal cual como primer mensaje al agente, en la raíz de `VideoMesh`. Está
escrito para que **empiece a trabajar**, no para que pida permiso ni resuma lo que
va a hacer.

---

```text
Trabajas en VideoMesh, en /Users/albertogalindez/Documents/VideoMesh, rama main.

Tu encargo entero está en docs/encargo-agente-01.md. Léelo antes que nada, y con
él lee lo que su sección 0 te manda leer. Ese documento manda sobre este mensaje
en todo lo que sea concreto; este mensaje solo dice cómo trabajar.

IDIOMA: español, en el código, en los comentarios, en los commits y conmigo.

LO PRIMERO QUE TIENES QUE SABER, porque cambia cómo trabajas: el repositorio no
tiene código. Dos commits, todo documentación. Lo que sí existe y está terminado
es el consumidor del otro lado —SoftSight, en ../Dron/softsight, 57 puertas
verdes— y es EJECUTABLE. No estás escribiendo contra una especificación: estás
escribiendo contra un programa que va a rechazar lo que hagas mal.

ARRANQUE, en este orden y sin saltarte pasos:

  1. shasum -a 256 docs/contrato-videomesh.md
     Compáralo con el hash de la cabecera de docs/OBLIGACIONES-VIDEOMESH.md.
     Si no cuadra, PARA y dime: la tabla está vieja y escribir código contra ella
     es trabajar contra un contrato que ya no es. Si cuadra, sigue.

  2. ~/.local/bin/python3.12 --version
     Tiene que decir 3.12.x. El python3 del sistema es 3.9.6 y NO SIRVE: el
     roadmap pide 3.11/3.12. Usa uv, que ya lo tiene.

  3. node ../Dron/softsight/tools/reconstruction.mjs inspect \
       ../Dron/softsight/artifacts/cube-v1/manifest.json --human
     Si ese paquete no existe, genéralo con:
       cd ../Dron/softsight && npm run cube-v1
     Esto es para que VEAS qué tiene que salir de lo que vas a construir, y para
     comprobar que el consumidor corre en esta máquina. No toques nada de ese
     repositorio: solo lees y ejecutas.

  4. Empieza por A0. Es el esqueleto del proyecto y todo lo demás cuelga de él.

CÓMO HACES CADA TAREA — el bucle, sin excepciones:

  a. Escribe PRIMERO la prueba que falla sin la tarea hecha. Ejecútala y
     COMPRUEBA QUE FALLA. Una prueba que pasa antes del cambio no prueba nada.
     Esto no es ceremonia: en SoftSight tres puertas nacieron verdes en un día y
     a las tres hubo que añadirles el caso que las rompe, porque una puerta que
     nunca ha fallado no ha demostrado que mire nada.
  b. Haz el cambio mínimo que la pone en verde.
  c. Corre la verificación ENTERA, no la prueba sola.
  d. Si la tarea produce un paquete, pásalo por el consumidor de verdad:
       node ../Dron/softsight/tools/reconstruction.mjs inspect <ruta>/manifest.json
     Un paquete que SoftSight rechaza está mal aunque tu código crea que no.
  e. Un commit, en español, con el estilo del git log actual: qué cambió y POR QUÉ,
     no una lista de ficheros.
  f. Dime en tres líneas: qué hiciste, qué prueba lo sujeta, qué te sorprendió.
     Luego sigue con la siguiente tarea sin preguntarme si puedes.

CUÁNDO ME PARAS. Solo estos casos. En todos los demás, construye y dime qué
supusiste:

  - La verificación se pone roja y no lo arregla tu propio cambio.
  - SoftSight rechaza un paquete que tú crees correcto Y el motivo apunta a que el
    contrato admite dos lecturas. Si el motivo es que tu paquete está mal,
    arréglalo y sigue: eso no es una pregunta.
  - Dos lecturas del enunciado dan trabajos distintos y elegir mal tira el trabajo.
  - La decisión es de criterio y no de hecho. Los cinco identificadores
    SS-PKG-010..014 y sus 27 hermanos son de ésas: están PROPUESTOS esperando
    respuesta desde hace un mes. NO los fijes tú.
  - Una tarea necesita COLMAP, FFmpeg o una GPU. Ninguna de este encargo los
    necesita; si crees que sí, es que te has salido del encargo.

  Una pregunta cada vez, con tu respuesta recomendada y por qué. Y si el dato se
  puede averiguar mirando el código, el git o el disco, MÍRALO: no me preguntes
  hechos comprobables.

LO QUE NO HACES, NUNCA:

  - No escribes modelos a mano. Se GENERAN de ../Dron/softsight/contracts/*.schema.json.
    Un modelo escrito a mano es un segundo original que diverge en el primer campo
    nuevo, y el envío 02 metió cuatro campos obligatorios de golpe.
  - No copias código de SoftSight. Puedes LEERLO para entender qué tiene que salir
    —tools/cubeV1.mjs hace lo mismo del otro lado— pero copiarlo anula la prueba:
    el segundo productor existe para demostrar que el contrato es escribible por
    quien solo leyó el esquema publicado. Compartir código lo convierte en el
    primero disfrazado.
  - No reimplementas cobertura, confianza ni auditoría geométrica. Eso es de
    SoftSight y está hecho. P1 y P11.
  - No mandas ficheros en base64. El paquete viaja POR RUTA desde
    bridgeContractVersion 2. D1.
  - No tocas nada dentro de ../Dron/softsight salvo para leer y ejecutar. Si algo
    de allí te parece mal, dímelo y sigue con lo tuyo.
  - No marcas un paquete como CONSUMED ni escribes en un paquete ya sellado.

DÓNDE ESTÁ EL VALOR, para que priorices bien si algo se tuerce: el bloque D es el
que desbloquea. Tres decisiones del contrato —D23, D26 y D34— llevan un mes
esperando a que cube-v1 salga de aquí y pase las tres comparaciones de paridad.
Los bloques A, B y C existen para poder llegar a D con algo que no se caiga.

Empieza. No me confirmes que has entendido el encargo: dime el resultado del paso
1 y sigue.
```

---

## Por qué el prompt dice lo que dice

Tres decisiones de redacción que no son obvias:

**El paso 1 es el hash, no el código.** Si la tabla de obligaciones está vieja, todo
lo que se escriba después estará bien construido contra un contrato equivocado, y
eso no se detecta hasta el final. Ya pasó una vez: un mes sin comprobarlo dejó
nueve filas caducadas.

**El paso 3 hace ejecutar el consumidor antes de escribir nada.** Es la diferencia
entre este encargo y el de agosto: entonces VideoMesh escribía contra una
especificación; ahora escribe contra un programa que va a decirle que no. Verlo
funcionar primero cambia la forma de trabajar el resto del encargo.

**«No copias código de SoftSight» va en LO QUE NO HACES y no en las reglas.** Es la
tentación más razonable del encargo —`cubeV1.mjs` hace exactamente lo que hay que
hacer— y a la vez lo que destruiría el valor entero de R0-B: dos productores que
comparten código son uno. `producers/colmap/` lo demostró del otro lado
coincidiendo **exacta a 0 en dieciséis números** sin compartir una línea.
