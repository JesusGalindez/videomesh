# Encargo 02 — que la deriva se vea sola

**Este encargo no añade funcionalidad.** Las tres tareas existen para que un tipo
concreto de fallo deje de poder ocurrir en silencio: **que un documento diga una
cosa y el código diga otra, y nadie se entere hasta que alguien construye encima.**

No es hipotético y conviene saber que ya pasó dos veces:

```text
2026-09-15  OBLIGACIONES-VIDEOMESH.md declaraba el contrato de hace un mes.
            Nueve filas caducadas y cuatro nombres de fixture inexistentes.
            El aviso para detectarlo estaba escrito en el propio documento
            desde el primer día. Nadie lo ejecutó.

2026-09-14  En SoftSight, `measurementClass` tenía TRES formas distintas en el
            mismo esquema publicado. Validaba, porque en tres de los cinco
            sitios el tipo era `string` libre y la afirmación vivía en la
            descripción. Una descripción no valida nada.
```

El patrón es el mismo: **el mecanismo de detección existía o era trivial, y no
estaba conectado a nada que se ejecute.**

---

## 0. Antes de empezar

```bash
bash scripts/verify.sh
```

Verde antes de tocar nada. Apunta el recuento: es tu línea base y las tres tareas
tienen que dejarlo verde con más pruebas, nunca con menos.

Lee `docs/encargo-agente-01.md` §1 — las reglas de trabajo son las mismas y no se
repiten aquí. En particular: **la prueba primero, y compruebas que falla.**

---

## 1. La puerta del hash — que el contrato no derive sin avisar

### El problema

`docs/OBLIGACIONES-VIDEOMESH.md` declara en su cabecera el sha256 del contrato
contra el que se escribió, y dice cómo comprobarlo. Eso está bien y no sirve de
nada: **depende de que alguien se acuerde.** Un mes sin acordarse dejó la tabla
inservible sin que ninguna ejecución se pusiera roja.

### Qué hay que construir

Una prueba que lea el hash declarado en la cabecera de `OBLIGACIONES-VIDEOMESH.md`,
calcule el del contrato real —`docs/contrato-videomesh.md`, que es un symlink al de
SoftSight— y los compare.

### Cómo se cierra

```python
tests/test_contrato_no_ha_derivado.py
```

Tres casos, y el tercero es el que hace que la prueba valga:

```text
1  el hash declarado es el del contrato de hoy
2  la cabecera tiene un hash con forma de sha256, no un texto cualquiera
3  un hash declarado que NO cuadra pone la prueba en rojo
```

El 3 se comprueba sin tocar el documento: la función que compara recibe el texto
de la cabecera como argumento, y la prueba le pasa una cabecera inventada con otro
hash. **Una prueba que solo se ha visto verde no ha demostrado que mire nada** —
en SoftSight tres puertas nacieron verdes el mismo día y a las tres hubo que
añadirles el caso que las rompe.

### Lo que el mensaje de fallo tiene que decir

No basta con «no cuadra». Quien lo lea tiene que saber qué hacer:

```text
el contrato cambió desde que esta tabla se revisó
declarado  6dc06081…  (2026-08-12)
real       b9e0e708…
revisa docs/OBLIGACIONES-VIDEOMESH.md contra el contrato antes de escribir
código que dependa de su tabla
```

**Importa la última línea.** El riesgo no es que la tabla esté vieja: es que
alguien escriba código correcto contra un contrato equivocado y no lo descubra
hasta el final.

---

## 2. Estado legible por máquina — que la combinación no mienta

### El problema

Hoy el estado de VideoMesh vive en tablas de Markdown. Un humano las lee; **una
prueba no puede verificarlas**, así que nada impide que la tabla diga que D23 está
cerrada y el código diga otra cosa.

Y hay un caso concreto ya en el repositorio:

```python
# tests/test_a0_esqueleto.py
assert CONTRACT_VERSION == "0.1"
```

Eso es un **campo suelto**, y D12 dice literalmente lo contrario: *«el consumidor
comprueba el bloque, no un campo»*. El motivo no es estético. El 2026-09-14
`reconstructionReport` subió de `0.1` a `0.2` en SoftSight después de cambiar seis
veces con el número quieto. El paquete sigue en `0.1`, así que esa constante
todavía es correcta — **por casualidad, no por comprobación**. El día que el
paquete suba, la constante mentirá y ninguna prueba lo verá.

### Qué hay que construir

Un documento generado —`contracts/estado.json` o donde encaje— que publique la
**combinación entera** de versiones que VideoMesh habla, y una prueba que lo
compare contra el registro de SoftSight:

```text
../Dron/softsight/contracts/versions.json
```

Ese fichero ya publica las siete versiones y cuál es la combinación vigente. Hoy:

```text
animationAudit 1 · bridge 2 · reconstructionPackage 0.1 · reconstructionReport 0.2
report 3 · stagingAudit 1 · storyAudit 1
```

### Cómo se cierra

```text
1  el estado publicado declara la combinación entera, no versiones sueltas
2  la combinación que VideoMesh declara es una de las admitidas por SoftSight
3  una combinación que nadie ha declarado se rechaza — con el caso inventado,
   como en la tarea 1
```

**Y `CONTRACT_VERSION` deja de ser una constante suelta**: pasa a leerse del estado
publicado, o se queda pero con una prueba que la ata a la combinación. Una de las
dos, no las dos — dos fuentes del mismo número divergen en la primera subida.

### Lo que NO hay que hacer

No copiar `versions.json` a este repositorio. Es el mismo error que la tabla de
obligaciones evitó con el symlink: **una copia diverge**. Se lee del original y, si
un día los repositorios se separan, se lee de su URL publicada.

---

## 3. `AGENTS.md` generado — que la lista no se quede corta

### El problema

No existe. Un agente frío que llegue dentro de un mes tiene 4.753 líneas de
roadmap, 295 de encargo y 177 de obligaciones, y **ninguna página que le diga qué
comando corre y qué se rompe si toca algo**.

Escribirlo entero a mano no lo arregla: miente tres commits después, cuando
alguien añada una prueba y no la apunte.

### Qué hay que construir

El patrón está resuelto del otro lado y se puede leer —
`../Dron/softsight/tools/agents-md.mjs`—: **lo que un script puede saber se genera,
lo que no, se escribe a mano**, y los dos viven en el mismo fichero separados por
delimitadores.

```text
<!-- generado: nombre -->   ...lo de dentro lo reescribe el script...
<!-- /generado: nombre -->
```

Se genera: la lista de pruebas con lo que cubre cada una, los comandos de
`pyproject.toml` y las dependencias declaradas.

Se escribe a mano: dónde va un cambio, qué se rompe si lo tocas, a qué documento
ir. Un script no puede saber eso y fingir que sí es peor que no tenerlo.

### Cómo se cierra

```text
scripts/agents_md.py           reescribe AGENTS.md
scripts/agents_md.py --check   sale 1 si el fichero commiteado no está al día
```

Y `--check` entra en `verify.sh`. **Eso es lo que lo convierte en una puerta**: sin
estar en la verificación, es otro documento que depende de que alguien se acuerde,
que es exactamente el fallo que este encargo existe para cerrar.

---

## 4. Un aviso para el Sprint 1, que no es tarea de este encargo

D28 dice que las reducciones paralelas se parten **por índices de entrada y un
tamaño de bloque fijo, nunca por el número de workers**. Cuatro workers dan cuatro
trozos y ocho dan ocho, así que los sumandos se agrupan distinto y la suma cambia
aunque cada ejecución reduzca ordenada.

En SoftSight esa regla **no se puede probar** porque no hay reducción paralela: la
visibilidad es de un solo hilo. Aquí sí va a haberla — providers y compute están en
el Sprint 1.

**Conviene que el arnés que lo comprueba exista antes que el paralelismo.**
Comprobarlo después significa reescribir la reducción con código encima, y el
síntoma es de los caros: un número que cambia según la máquina, sin error, sin
excepción y sin nada que lo delate.

---

## 5. Qué reportar

Después de cada tarea, tres líneas: qué se hizo, qué prueba lo sujeta, qué
sorprendió. Y en las tres, la misma comprobación antes de darla por buena:

**¿La has visto en rojo?** Si no, no sabes si mira algo.
