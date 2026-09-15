# Encargo 03 — lo que quedó roto o mintiendo

Cuatro cosas, encontradas el 2026-09-15 escribiendo el workflow de CI. Ninguna es
una mejora: las cuatro son un documento o una comprobación que **afirma algo que
no es verdad hoy**. Van en orden de urgencia; la primera tiene la verificación en
rojo ahora mismo.

Contexto que conviene tener antes de empezar: el contrato
(`docs/contrato-videomesh.md`, enlace al original de SoftSight) **cambió hoy**, en
el commit `49b7e4e` de SoftSight. Siete decisiones marcadas IMPLEMENTADAS
apuntaban en su línea `**Prueba:**` a algo que no se podía ejecutar ni abrir:

```text
D7, D20     nombraban `hash-mismatch-v1`, `depth-optical-axis-v1` y
            `depth-ray-length-v1` — tres ficheros que nunca existieron
D8, D18     «casos A y B», «es la prueba» — teniendo puerta
D11, D12    «sin escribir» — teniendo puerta
D29         seis casos enumerados, ninguna puerta nombrada
```

Ahora las siete nombran la puerta que se ejecuta, y `test:contracts` lo comprueba
en cada ejecución: una decisión IMPLEMENTADA cuya prueba no resuelve pone la
suite de SoftSight en rojo.

**Lo llamativo es de dónde salió el dato.** Tres de esos nombres ya estaban
desmentidos en `docs/OBLIGACIONES-VIDEOMESH.md`, líneas 68–74, desde ayer. Este
repositorio sabía que no existían y el contrato siguió nombrándolos un día más,
porque quien escribió la tabla arregló su copia y no el original. Es literalmente
el fallo que la tabla describe, cometido sobre la tabla.

---

## 1 — El hash del contrato, que está rojo ahora

`tests/test_contrato_no_ha_derivado.py` falla:

```text
declarado  9023b479...
real       02ce8a7e...
```

**Eso es la puerta funcionando, no un fallo.** El contrato cambió y nadie tocó
VideoMesh; la segunda vez que esta puerta se estrena y la segunda vez que acierta.

Qué hacer:

1. Leer el diff real antes de tocar el hash. `git -C ../Dron/softsight show 49b7e4e
   -- docs/contrato-videomesh.md`. Son catorce líneas: siete `**Prueba:**`
   reescritas. Ninguna cambia qué obliga una decisión — solo dónde mirar para
   comprobarla.
2. Actualizar la cabecera de `docs/OBLIGACIONES-VIDEOMESH.md`: sha256
   `02ce8a7e...`, **1838 líneas**, fecha 2026-09-15.
3. Repasar la columna derecha de la tabla contra las siete decisiones tocadas. Si
   alguna fila nombraba una puerta distinta de la que el contrato nombra ahora,
   manda el contrato.
4. El párrafo de las líneas 68–74 —el que explica que cuatro fixtures no existen
   con ese nombre— **describe un problema que ya no existe aguas arriba**. Ahora
   el contrato lo dice en su propio texto. Dejarlo sin tocar crearía la segunda
   fuente del mismo dato; conviene reducirlo a una frase que apunte al contrato.

Criterio: `./scripts/verify.sh` en verde, y el hash declarado sale de
`shasum -a 256 docs/contrato-videomesh.md`, no de este documento.

---

## 2 — `doctor` dice DISPONIBLE de un consumidor que no se puede ejecutar

`src/videomesh/cli/doctor.py:53` decide con `consumidor.is_file()`. Pero
`tools/reconstruction.mjs` importa `../dist-node/agent3d.mjs`, que **no está
versionado en SoftSight**: lo escribe `npm run build:agent3d` y su `.gitignore`
lo excluye.

Así que hay un estado, y es el estado de un clon recién hecho de SoftSight:

```text
$ videomesh doctor
  SoftSight, consumidor    DISPONIBLE    .../tools/reconstruction.mjs
lo que R0 necesita esta.                         ← salida 0

$ pytest tests/test_d1_cube_v1.py
ERROR ... ERROR ... ERROR ...                    ← la puerta entera
```

Medido hoy moviendo `dist-node/` de sitio: `doctor` sale 0 y la puerta de D1 da
error en todos sus casos. El diagnóstico dice que está lo que hace falta, y lo
que hace falta no está.

Esto importa más de lo que parece porque `doctor` es lo primero que corre un
agente nuevo, y su respuesta decide si lo que viene después se cree o no. Un
diagnóstico que se equivoca en verde es peor que no tenerlo: manda a leer el
código de uno mismo buscando un fallo que está en el vecino.

Qué hacer: que la comprobación afirme lo que dice su nombre. **Que el consumidor
se pueda consumir**, no que el fichero esté. Ejecutarlo es lo único que lo
demuestra — con un manifest que no existe, por ejemplo, y mirando que el error
sea el de «no encuentro el paquete» y no el de un módulo que falta. Si se
prefiere no ejecutar nada, vale comprobar el artefacto que el fichero importa,
pero entonces el estado tiene que decir cuál falta y cómo se construye; el
usuario de esa línea no tiene por qué saber qué es `dist-node`.

Criterio, y es el que importa: **hay que verla en rojo**. Mover `dist-node/` a un
lado, correr `doctor`, y que salga distinto de 0 nombrando lo que falta.
Devolverlo a su sitio después. Una prueba que solo se ha visto en verde no ha
demostrado que mire.

---

## 3 — El roadmap sigue nombrando fixtures que nunca existieron

`VIDEOMESH_V1_1_IMPLEMENTATION_ROADMAP.md`, líneas 675–677 y 4020–4022:

```text
hash-mismatch-v1
camera-transform-v1
image-orientation-v1
```

Ninguno existe, y desde hoy el contrato dice por qué: los casos acabaron dentro
de fixtures que ya viajaban. El roadmap es la foto del 2026-08-12 y se respeta
como foto, pero un árbol de directorios no es una opinión de agosto: se lee como
la lista de lo que hay que escribir.

Qué hacer: lo mínimo que quite la trampa. Una nota junto al árbol que diga que
esos tres nombres nunca llegaron a existir y dónde acabaron sus casos. **No
reescribir el árbol** — es parte de la foto, y cambiarlo la falsifica.

---

## 4 — `3.12` vive en tres sitios

`scripts/verify.sh` sugiere, cuando falta el entorno:

```text
uv venv --python ~/.local/bin/python3.12 .venv
```

`pyproject.toml` ya declara `python_version = "3.12"` para mypy, y el workflow de
CI lo saca de ahí precisamente para no escribirlo otra vez. La línea de
`verify.sh` es el tercer original, y además nombra una ruta de una máquina
concreta: en otra no está.

Qué hacer: que el mensaje derive la versión del `pyproject.toml`, como hace el
workflow, y no nombre rutas de nadie. Es una línea.

---

## Lo que NO hay que tocar

`research/` sigue sin versionar —tres documentos de agosto, 2069 líneas—. Lo he
mirado dos veces y sigo sin saber si es una decisión o un descuido, así que no es
de un agente decidirlo. Queda apuntado para quien lleve el repositorio.
