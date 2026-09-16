# Encargo 04 — de la malla medida al asset que se usa

**Objetivo del encargo entero, en una frase:** que un vídeo de un objeto real
salga de aquí como un **GLB que entra en un motor y se puede afirmar, con
números, que sigue siendo ese objeto**.

Eso es lo que separa este proyecto de un generador de 3D. Tripo, Luma y los que
vengan producen assets bonitos que **se inventan lo que no vieron**, y no tienen
contra qué comprobarlo. Aquí la geometría sale de fotogramas reales, y al final
el diff de superficie dice en milímetros cuánto se movió el acabado respecto de
lo medido. Si esa cifra no se publica, el asset es tan afirmación como el suyo.

Son los Sprints 5, 6, 8, 9 y 10 del roadmap, ejecutados contra lo que existe hoy.
**El roadmap sigue mandando sobre el alcance**; este documento dice cómo se hace
y en qué orden, con lo que se sabe en septiembre de 2026.

---

## 0. Antes del primer comando

### 0.1 Lo que hay que leer, en este orden

```text
docs/contrato-videomesh.md                 D9, D18, D22, D28, D29, D34
docs/OBLIGACIONES-VIDEOMESH.md             la tabla entera
VIDEOMESH_V1_1_IMPLEMENTATION_ROADMAP.md   Sprints 5, 6, 8, 9, 10
docs/encargo-agente-01.md                  §1, las reglas de trabajo
```

Las reglas del encargo 01 §1 siguen vigentes y **no se repiten aquí**: la prueba
primero, comprobar que falla, cambio mínimo, verificación entera, commit.

### 0.2 La comprobación que no se salta

```bash
shasum -a 256 docs/contrato-videomesh.md
```

Contra la cabecera de `docs/OBLIGACIONES-VIDEOMESH.md`. Ya hay puerta que lo
comprueba sola, pero míralo antes de escribir código contra la tabla.

### 0.3 De dónde partimos, medido y no supuesto

Lo que hay hoy en este repositorio:

```text
videomesh init/status/doctor/resume      proyecto en disco, stages con resume
EjecucionDeStage                         estado, hashes, determinismo, proveedor
cube_v1                                  el único productor, y FABRICA un cubo
sellado atómico                          D29, entero
formatos/ply.py, formatos/png.py         lectura y escritura
adapters/gltf_transforms.py              convenciones de glTF en un solo sitio
```

Lo que NO hay: ni una sola etapa que toque una malla real. `cube_v1` no
reconstruye — fabrica un cubo con geometría conocida para probar el contrato.

Lo que hay al otro lado, en SoftSight, y **no hay que reescribir**:

```text
producers/colmap/build.mjs        salida de COLMAP → paquete sellado, con malla
producers/colmap/colab.ipynb      vídeo → fotogramas → disperso → densa → malla
diffMeshes                        distancia de superficie en las DOS direcciones
boundsTree                        BVH con trazado de rayos, probado a fuerza bruta
auditUvs, auditTexture            R13
LOD por silueta, proxy de colisión R12, R14
PRODUCTION_READY                  R15, conjunción y no nota
presupuestos por destino          R9
```

**La mitad de verificación está escrita. Falta la de producción entera.**

### 0.4 La restricción de máquina, que decide el diseño

La densa exige CUDA y ninguna máquina de casa la tiene. Se hace en Colab con el
cuaderno de SoftSight, y **eso no se intenta mover aquí**. Todo lo demás —las
cinco etapas de acabado— corre en CPU y tiene que seguir corriendo en CPU.

Consecuencia directa para el bloque A: el paquete con la malla densa **llega de
fuera**, y hay que tratarlo como lo que es: producto de un proveedor no
determinista, en otra máquina, con otra versión.

---

## 1. Lo que no se re-discute

Cinco decisiones ya tomadas. Si una tarea parece pedir lo contrario, la tarea
está mal entendida.

**No se inventa geometría.** Ninguna etapa rellena un agujero por defecto. Si una
lo hace —Poisson cierra por construcción—, el artifact lo declara con
`purelyReconstructed: false` y el informe lo publica. Un asset cerrado y bonito
que no dice qué parte se inventó es exactamente lo que este proyecto existe para
no producir.

**Sin referencia de escala, no hay milímetros.** D9: COLMAP reconstruye forma, no
tamaño. `scale: UNKNOWN` no es un hueco que rellenar con una estimación.

**Ninguna etapa devuelve una nota.** Ni «calidad 87». Números con su unidad y su
sitio, o un veredicto que es conjunción de comprobaciones declaradas.

**Lo que no se pudo comprobar se declara NOT_RUN con su motivo.** Nunca un PASS
callado. Y `PRODUCTION_READY` no se gana con silencio: si falta una comprobación,
es `UNKNOWN`.

**El determinismo se declara, no se promete.** `Instant Meshes` es aleatorio;
`OpenMVS` depende de su versión. Cada stage anota su `Determinismo` real —
`DETERMINISTIC_WITH_SEED` o `NON_DETERMINISTIC_PROVIDER`— y su proveedor con
versión. Declarar `DETERMINISTIC` lo que no lo es rompe el `resume`, que decide
por los hashes.

---

## 2. Bloque A — el paquete que llega de Colab

**Qué cierra:** Sprint 5 y la mitad del 6.

### A1 — ingerir un paquete producido fuera

`videomesh import <ruta-al-paquete>` registra un paquete externo como la salida
de un stage `densa`, sin reejecutarlo.

Lo que tiene que hacer, y en este orden:

```text
1  comprobar el manifest contra el esquema publicado de SoftSight
2  recalcular el sha256 de cada artifact y compararlo con el declarado
3  registrar EjecucionDeStage con:
     estado COMPLETE, determinismo NON_DETERMINISTIC_PROVIDER,
     proveedor "colmap", version la que el manifest declare,
     hash_de_salida el del manifest
4  NO recalcular nada de la geometría: el paquete ya viene sellado
```

El paso 2 es el que importa. Un paquete que viajó 300 MB por la red y llegó con
un byte cambiado tiene que morir aquí y no tres etapas más tarde, cuando el
síntoma sea una malla con un pico.

**Se ve en rojo:** cambia un byte del PLY de un paquete de prueba y comprueba que
`import` falla nombrando el artifact, no con un error de parseo.

### A2 — el registro de procedencia

El paquete importado lleva `producer` y una versión. Hay que guardar **de qué
máquina y qué versión de COLMAP salió**, porque dos densas de dos versiones no
son comparables y dentro de seis meses nadie se acordará.

Si el manifest no lo trae, `import` lo pide por argumento y falla sin él. Un
campo vacío aquí es peor que no tenerlo: parece dato.

### A3 — `videomesh status` cuenta la verdad de la cadena

Después de importar, `status` tiene que decir qué etapas están hechas, cuáles
caducaron —entrada cambiada— y cuál toca. Ya existe la maquinaria; esto es
conectar la etapa nueva.

---

## 3. Bloque B — que la malla se pueda abrir

**Qué cierra:** el primer hito visible. Al acabar B tienes un fichero que puedes
abrir en Blender sin que se arrastre.

La densa de un objeto sale con **millones de triángulos** y trozos flotantes: la
pared de detrás, el suelo, nubes de puntos sueltos que el fusionado no supo
descartar. No es utilizable y tampoco es agradable de mirar.

### B1 — limpieza

Etapa `limpieza`. Tres operaciones, y ninguna decide dónde va un vértice:

```text
componentes conexos    se quedan los que superen un umbral de tamaño
                       relativo al mayor — nunca absoluto
triángulos degenerados area cero, aristas nulas
vértices sueltos       sin ninguna cara
```

El umbral es un parámetro con valor por defecto declarado, **no una constante
escondida**. Y la etapa publica cuántos componentes había y cuántos quedaron: si
de 400 quedan 3, quieres enterarte.

Proveedor recomendado: `Open3D` o `pymeshlab`. Los dos en CPU, los dos con rueda
para 3.12. Elige uno y **decláralo**; no los mezcles por etapa.

**Se ve en rojo:** una malla sintética con dos cubos separados y una mota de tres
triángulos. La limpieza tiene que dejar dos componentes, no uno ni tres.

### B2 — decimado

Etapa `decimado`. Colapso de aristas por error cuadrático (quadric edge
collapse), con **objetivo de triángulos** como parámetro.

Lo que la etapa publica, y es lo que la hace auditable:

```text
triángulos antes y después
la distancia de superficie contra la entrada, en las dos direcciones
```

Esa segunda línea es la clave del encargo entero: **decimar es perder detalle, y
cuánto se perdió es un número medible, no una impresión**. Se obtiene con
`diffMeshes` de SoftSight.

> **Dependencia:** hoy `diffMeshes` lee glTF y GLB, no PLY, así que no puede
> comparar la malla medida. Eso es tarea de SoftSight y **está asignada fuera de
> este encargo** — `parsePly` ya existe y solo hay que enchufarlo en
> `loadFlattenedMesh`. Si al llegar aquí todavía no está, declara el número como
> NOT_RUN con ese motivo y sigue; no lo reimplementes en Python.

**Se ve en rojo:** decima un plano subdividido a la mitad de triángulos. La
distancia tiene que quedar por debajo del suelo de ruido —un plano decimado sigue
siendo el mismo plano— y decimarlo al 1 % tiene que superarlo.

---

## 4. Bloque C — que el asset tenga topología y coordenadas

**Qué cierra:** Sprint 8, la parte de malla maestra.

### C1 — retopología

Etapa `retopologia`. Triángulos desordenados → quads alineados con la forma.

Proveedor: **Instant Meshes** o **QuadriFlow**. Los dos son de campo de
direcciones, abiertos, en CPU, y hacen sin IA lo que otros venden como IA.

Dos avisos que ahorran un día:

**Es aleatorio.** Instant Meshes siembra su campo al azar. El stage es
`DETERMINISTIC_WITH_SEED` y **la semilla se guarda**. Sin eso, dos ejecuciones dan
dos topologías distintas y el `resume` no puede saltarse nada.

**Puede cerrar agujeros.** Según parámetros, tapa aberturas pequeñas. Si lo hace,
`purelyReconstructed` pasa a `false`. Hay que comprobarlo, no suponerlo: compara
el número de bordes abiertos antes y después.

### C2 — UV

Etapa `uv`, con **xatlas**: corta y empaqueta el atlas. CPU, rápido, determinista.

SoftSight ya sabe auditar el resultado —`auditUvs`: degeneradas, solape, rejilla—
así que esta etapa **no escribe su propia comprobación**: produce y deja que la
auditoría existente juzgue. Duplicarla crearía dos criterios de qué es una UV
válida, y acabarían discrepando.

**Se ve en rojo:** un asset cuyas UV se solapan a propósito tiene que salir
rechazado por `auditUvs`, no por código de aquí.

---

## 5. Bloque D — que el asset tenga color

**Qué cierra:** Sprint 8, texturing.

### D1 — textura desde los fotogramas

Etapa `textura`, con **OpenMVS `TextureMesh`**. CPU.

Esto es lo que ningún generador puede dar: proyecta **tus fotogramas reales**
sobre la malla. El color es el del objeto, con su desgaste y sus manchas, no una
textura plausible generada.

Necesita el espacio de trabajo de COLMAP —imágenes y cámaras—, así que el
paquete importado en A1 tiene que conservarlas. No las tires en la limpieza.

### D2 — mapa de normales horneado

Etapa `normales`. El detalle que el decimado quitó vuelve como mapa.

El horneado es lanzar rayos de la malla decimada contra la densa y anotar la
diferencia de normal. **SoftSight ya tiene el trazador**: `boundsTree`, BVH
probado contra fuerza bruta con mil rayos.

Decisión abierta y es tuya cuando llegues: hacerlo aquí en Python o llamar al de
SoftSight por el puente. Lo segundo reutiliza código probado; lo primero mantiene
la producción en el productor. **Escribe cuál elegiste y por qué** — es
exactamente el tipo de decisión que dentro de tres meses nadie recuerda.

### D3 — el material

Un material declarado, con sus mapas. Sin esto, R13 no puede auditar la textura:
su puerta dice que el manifest de producción todavía no las declara. Esta etapa
es la que cierra ese hueco desde el lado del productor.

---

## 6. Bloque E — que el destino mande

**Qué cierra:** Sprints 9 y 10.

### E1 — perfiles de destino

Un asset «bueno» no existe en abstracto. Existe **bueno para web** o **bueno para
Unreal**, y son topes distintos:

```text
web        triángulos bajos, textura comprimida, un solo fichero
juego      varios LOD, proxy de colisión, atlas grande
```

Los presupuestos **los declara el destino**, y SoftSight ya tiene ese vocabulario
en R9. Aquí se escriben los perfiles y se publican con el paquete.

Regla que se hereda de R15 y no se negocia: **un destino que no declara nada no
obtiene PRODUCTION_READY**. Si no, el asset más vacío sería el más listo.

### E2 — LOD y colisión

Etapa `lod`: la cadena de niveles, cada uno decimado del anterior, con su
distancia de superficie publicada. SoftSight audita la silueta, que es donde un
LOD se nota.

Etapa `colision`: el proxy. Cuidado — **SoftSight se niega a proponerlo** y dice
por qué: calcular un casco convexo es modelar, y en cuanto decidiera dónde va un
vértice dejaría de poder afirmar que sus números son exactos. Producirlo es de
aquí; juzgar su holgura es de allí.

### E3 — GLB

Etapa `glb`. El asset final, con `meshoptimizer` y `KTX2` para el perfil web.

Las convenciones de glTF **ya viven en un solo sitio**: `adapters/gltf_transforms.py`,
cerrado con D32. No escribas una segunda conversión de ejes.

### E4 — el veredicto

`videomesh publish --destino web` produce el paquete de producción, lo sella, y lo
pasa por la QA de SoftSight. Sale `PRODUCTION_READY` o sale `UNKNOWN` con la lista
de lo que falta.

---

## 7. Bloque F — el bucle del agente

**Qué cierra:** lo que hace que esto sea una cadena y no una lista de comandos.

Cuando E4 dice `UNKNOWN`, alguien tiene que decidir qué etapa rehacer. Ese alguien
puede ser un agente, y **puede serlo porque el informe emite números y no notas**:
cada fallo nombra la medida, su valor y su sitio.

### F1 — `videomesh next`

Lee el último informe y dice **qué etapa hay que rehacer y con qué parámetro**,
sin ejecutarla. Una línea por fallo:

```text
triángulos 180k > 60k del perfil web   → decimado --objetivo 60000
UV solapadas en 3 islas                → uv, sube el margen
LOD2 se sale del presupuesto de silueta → lod --niveles 4
```

**No lo ejecuta.** Dice qué haría. Un agente lo lee y decide; una persona también.

### F2 — el techo, y es obligatorio

Un bucle que reintenta sin límite acaba decimando a cero para cumplir un
presupuesto. Dos reglas:

```text
un máximo de vueltas, declarado
y si una vuelta no mejora la medida que la motivó, PARA y dilo
```

Lo segundo es lo que impide el desastre silencioso: bajar triángulos hasta pasar
la puerta habiendo destruido el objeto. **La distancia de superficie contra la
malla medida es el freno**, y por eso se publica en cada etapa desde B2.

---

## 8. El criterio de cierre del encargo entero

Uno solo, y es comprobable:

> Un vídeo de un objeto real entra, y sale un GLB que un motor abre, con un
> informe que dice `PRODUCTION_READY` contra un perfil declarado **y** la
> distancia de superficie contra la malla medida.

Si el GLB abre pero no hay distancia publicada, el encargo no está hecho: eso es
lo que cualquiera puede dar.

---

## 9. Trampas conocidas, para no descubrirlas dos veces

**Las etapas caducan en silencio.** Cambia el decimado y el mapa de normales que
se horneó contra la malla anterior ya no vale. Lo decide el hash de entrada, no
el estado — está escrito en `domain/stage.py` y es literal: *un COMPLETE cuya
entrada cambió no está hecho, está caducado*.

**Las versiones de los proveedores se mueven.** OpenMVS, Open3D e Instant Meshes
cambian resultados entre versiones. Por eso el stage guarda `version_del_proveedor`
y por eso el determinismo se declara.

**La malla densa no cabe en memoria alegremente.** Millones de triángulos en
Python con copias intermedias llenan 8 GB. Mide el RSS en las etapas B y decláralo;
si hay que trocear, que sea una decisión tomada con un número delante.

**No dupliques auditorías.** Todo lo que SoftSight ya juzga —UV, textura, LOD,
colisión, silueta— se produce aquí y se juzga allí. Dos criterios de qué es
válido acaban discrepando, y el día que lo hagan nadie sabrá cuál manda.

---

## 10. Orden y entregas

```text
A   import, procedencia, status            el paquete de Colab entra
B   limpieza, decimado                     ← primera entrega: se puede abrir
C   retopología, UV
D   textura, normales, material            ← segunda entrega: se puede usar
E   perfiles, LOD, colisión, GLB, publish
F   next, techo del bucle                  ← tercera entrega: se itera solo
```

Para en B y enséñalo antes de seguir. Hasta que no se vea una malla real limpia y
decimada, todo lo de C en adelante son parámetros elegidos a ciegas.
