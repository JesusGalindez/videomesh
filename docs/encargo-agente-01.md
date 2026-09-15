# Encargo 01 — arrancar VideoMesh hasta R0-B

**Objetivo del encargo entero, en una frase:** que `cube-v1` salga de VideoMesh,
lo consuma SoftSight de verdad y pasen las tres comparaciones de D23.

Eso es R0-B, y de él cuelgan tres decisiones del contrato —D23, D26 y D34— que
llevan un mes esperando. No hay nada antes que valga más, y el propio roadmap lo
fija: **no se empieza el Sprint 1 hasta R0-B PASS**.

---

## 0. Antes del primer comando

### 0.1 Lo que hay que leer, en este orden

```text
docs/contrato-videomesh.md          §1, §2 y las decisiones que cada tarea nombre
docs/OBLIGACIONES-VIDEOMESH.md      qué le toca a este repositorio, tabla entera
VIDEOMESH_V1_1_IMPLEMENTATION_ROADMAP.md   §3.1, §7 y §84
```

El contrato **manda sobre este encargo** en todo lo que sea semántica. Este
documento solo dice qué se construye y en qué orden.

### 0.2 La comprobación que no se salta

`OBLIGACIONES-VIDEOMESH.md` declara contra qué versión del contrato se escribió.
Antes de usar su tabla:

```bash
shasum -a 256 docs/contrato-videomesh.md
```

Si no cuadra con el hash de su cabecera, **la tabla puede estar vieja y hay que
revisarla antes de escribir código contra ella**. Esto no es celo: en septiembre
de 2026 la tabla llevaba un mes sin comprobarse y tenía nueve filas caducadas y
cuatro nombres de fixture que no existían.

### 0.3 La ventaja que no existía en agosto

**El consumidor ya está construido y es ejecutable.** SoftSight vive en
`../Dron/softsight`, tiene 57 puertas verdes y consume paquetes de verdad:

```bash
node ../Dron/softsight/tools/reconstruction.mjs inspect <ruta>/manifest.json --human
```

Eso cambia cómo se trabaja: **cada tarea de este encargo se puede verificar contra
el consumidor real desde el primer día**, en vez de contra una interpretación del
esquema. Un paquete que SoftSight rechaza está mal aunque el código de aquí crea
que está bien.

Los esquemas publicados —la frontera— están en `../Dron/softsight/contracts/`.

### 0.4 El entorno, comprobado el 2026-09-15

```text
python3.12   ~/.local/bin/python3.12   3.12.13, vía uv   ✓
uv           0.11.17                                     ✓
colmap       NO instalado                                no hace falta
ffmpeg       NO instalado                                no hace falta
```

**El sistema trae Python 3.9.6 y el roadmap pide 3.11/3.12.** No se usa el del
sistema. `uv` ya tiene el 3.12 y es con el que se crea el entorno.

Que COLMAP y FFmpeg falten **no bloquea nada de este encargo**: los cuatro sprints
de R0 son JSON, hashes y álgebra de matrices. La fotogrametría empieza en el
Sprint 2 y es otro encargo.

---

## 1. Reglas de trabajo — no negociables

### 1.1 Una tarea está hecha cuando una prueba falla sin ella

Es §1.2 del contrato y la regla de cierre de OBLIGACIONES. Literalmente:

```text
Escribe PRIMERO la prueba. Ejecútala. COMPRUEBA QUE FALLA.
Luego el cambio mínimo que la pone en verde.
```

Una prueba escrita después pasa a la primera y no demuestra nada. Esto no es
ceremonia: en SoftSight, tres puertas nacieron verdes en un solo día y a las tres
hubo que añadirles el caso que las rompe a propósito, porque **una puerta que
nunca ha fallado no ha demostrado que mire nada**.

### 1.2 Los modelos se generan, nunca se escriben a mano

D15. Los modelos Pydantic salen de `contracts/*.schema.json` de SoftSight, que es
la frontera pública. Escribir un modelo a mano crea un segundo original que
diverge en el primer campo nuevo — y el envío 02 ya metió cuatro campos
obligatorios de golpe.

### 1.3 Lo que no se hace, nunca

```text
no duplicar la lógica de verdad geométrica de SoftSight     P1
no reimplementar cobertura para obtener paridad             P11
no mandar blobs por el puente — el paquete viaja por RUTA   D1
no inferir identidad del nombre del directorio              D7
no marcar un paquete como CONSUMED                          D29
no tratar INCONCLUSIVE como PASS                            D3
```

### 1.4 Cuándo se para y se pregunta

Solo en estos casos. En los demás: construir y decir qué se supuso.

```text
· la suite se pone roja y no lo arregla el propio cambio
· SoftSight rechaza un paquete que el código de aquí cree correcto, y el motivo
  apunta a que el contrato se puede leer de dos formas
· dos lecturas del enunciado dan trabajos distintos y elegir mal tira el trabajo
· la decisión es de criterio y no de hecho
```

Una pregunta cada vez, con la respuesta recomendada y por qué. **Si el dato se
puede averiguar mirando el código, el git o el disco, se mira.**

---

## 2. El orden

Cuatro bloques, que son los sprints 0A–0D del roadmap. No se adelantan: cada uno
usa lo que construyó el anterior.

### Bloque A — el esqueleto y la frontera (Sprint 0A)

**A0. El repositorio existe como proyecto Python.**
`pyproject.toml` con `uv`, `src/videomesh/` según §7 del roadmap, `pytest`, y un
comando único de verificación —`scripts/verify.sh` o equivalente— que corra
linter, tipos y pruebas. Todo lo demás cuelga de que esto exista.
*Cierra:* el comando de verificación sale verde sobre un repositorio vacío de
lógica. Es la línea base.

**A1. Serializador JSON estricto — V1 y V2.**
`allow_nan=False` en **toda** serialización. Un `NaN` serializado como `NaN` no es
JSON válido y el consumidor lo rechaza; peor, un `Infinity` que sobreviva se
convierte en una medida que nadie puede interpretar.
*Cierra:* `test_json_rejects_non_finite_numbers`, que intenta serializar `NaN`,
`Infinity` y `-Infinity` y exige que los tres fallen **en origen**. D17 dice
explícitamente que no se confía en que lo cace Node.

**A2. Los modelos, generados del esquema — D15.**
Un generador que lea `../Dron/softsight/contracts/*.schema.json` y emita modelos
Pydantic. Ocho esquemas hoy.
*Cierra:* una prueba que regenera y compara con lo commiteado, al estilo de
`contracts --check` de SoftSight: si el esquema cambia y los modelos no, rojo.

**A3. El sobre del documento — D16.**
`documentType`, `contractVersion` y `contractSchemaSha256` en todo lo que se
escriba.
*Cierra:* un manifest sin sobre es rechazado por el propio escritor, antes de
llegar a disco.

**A4. El modelo de artifact discriminado — D21.**
`purelyReconstructed` **requerida** en cada `TRIANGLE_MESH` y **prohibida** en
`POINT_CLOUD`. No es un campo opcional con default: los cuatro casos están fijados
en el contrato desde el 2026-08-12.
*Cierra:* los cuatro casos, cada uno con su veredicto.

### Bloque B — cámaras, marcos y escala (Sprint 0B)

**B1. CameraSet canónico — V9, D32.**
Matriz 4×4 **por filas**, traslación en 3, 7 y 11, vectores columna, y solo
`worldFromCamera`. No es la convención de glTF y no son intercambiables.
*Cierra:* el fixture `transform-gltf-v1` de SoftSight —
`../Dron/softsight/contracts/fixtures/transform-gltf-v1.json`— consumido desde
aquí. Sus cinco casos traen **un punto conocido a su punto transformado conocido**,
que es lo único que caza una transposición de más: dos transposiciones se cancelan
y la ida y vuelta sale idéntica.

**B2. La cámara declara de qué imagen habla — D10, D19, D33.**
`imageSpace` como unidad, `imageArtifactHash` —**obligatorio desde el envío 02**,
no basta el id—, `cameraAxes` sin valor por defecto, distorsión con nombre, y la
orientación horneada en los píxeles antes de exponer nada.
*Cierra:* `camera-projection-v1`, y un caso propio: reapuntar el hash a otra
imagen del mismo paquete tiene que ser rechazado. Con el id solo, pasaba.

**B3. FrameGraph — D11.**
Marco origen, destino, matriz, motivo y productor. Un marco sin camino desde donde
se mide se rechaza.
*Cierra:* ida y vuelta por un camino de dos saltos da identidad exacta; una arista
no rígida se rechaza por su nombre.

**B4. Escala — D9.**
`ScaleStatus`, `ScaleSource`, incertidumbre. Un presupuesto en unidades absolutas
sobre una escala que no es `ABSOLUTE` **se rechaza**.
*Cierra:* ese caso exacto.

### Bloque C — integridad del paquete (Sprint 0C)

**C1. `packageId` en el manifest — V6, D7.**
Nunca deducido del nombre del directorio. Mover una carpeta no cambia la identidad
de lo que hay dentro.

**C2. `bytes` y `sha256` por artifact — V8, D7.**
*Cierra:* `package-integrity-v1` de SoftSight tiene los casos; aquí hay que
producirlos, no solo no fallarlos.

**C3. Sellado atómico — V5, V7, D29.**
El orden es contrato, no recomendación:

```text
escribir artifacts → cerrarlos → calcular bytes y sha256 → construir manifest
con los hashes → state: SEALED → escribir el manifest EL ÚLTIMO → cerrarlo
→ rename atómico del directorio
```

Con dos exigencias que son de este lado y **solo de este lado**: el temporal y el
destino final resuelven al **mismo volumen**, verificado **antes** de empezar; y el
destino no puede existir ya con un paquete sellado de la misma identidad — no se
reescribe `turret-recon-0004`, se publica `0005`.
*Cierra:* la prueba que SoftSight no puede escribir. Un temporal en otro volumen
falla con `PACKAGE_ATOMIC_PUBLISH_UNAVAILABLE`, nunca cae en silencio a copiar y
borrar manteniendo la etiqueta de atómico.

**C4. Los paquetes que deben ser rechazados.**
`unknown-field-v1`, `unsealed-package-v1`, `unknown-capability-v1` y un
`invalid-path-v1` propio.
*Cierra:* los cuatro, **rechazados por los dos lados**. Es el riesgo que D15 asume
y la única forma de cerrarlo: dos validadores pueden discrepar, y un documento que
uno acepta y el otro no es un paquete que viaja y se cae al llegar.

Nota que ahorra tiempo: SoftSight descubrió al escribir esos fixtures que **el
esquema acepta `state: WRITING` y acepta un `requires` desconocido**. El rechazo
de esos dos casos no es de validación sino de **consumo**, y cada lado rechaza una
cosa distinta — VideoMesh no puede *publicar* sin sellar; SoftSight no puede
*consumir* sin sellar.

### Bloque D — el corte vertical (Sprint 0D)

**D1. Generador de `cube-v1` — V3.**
Un cubo, cuatro cámaras, sus imágenes, su PLY. Lo **fabrica**, no lo reconstruye:
la reconstrucción es del Sprint 2.
Referencia útil: `../Dron/softsight/tools/cubeV1.mjs` hace lo mismo del otro lado.
**No se copia** —sería el primer productor disfrazado de segundo— pero se puede
leer para saber qué tiene que salir.
*Cierra:* el paquete generado sale `COMPLETE + PASS` con salida 0 en:

```bash
node ../Dron/softsight/tools/reconstruction.mjs inspect <ruta>/manifest.json
```

**D2. `expected.json` — V4.**
Lo que VideoMesh afirma de su propio cubo: recuentos, caja, cámaras registradas.
Es la columna que a D23 le falta desde agosto.
*Cierra:* existe y es determinista entre dos generaciones.

**D3. Arnés de paridad — V10, D23.**
Las tres comparaciones, cada una con su tolerancia declarada:

```text
recuentos de vértices y triángulos        exactos
caja envolvente tras normalizar el marco  tolerancia declarada, no supuesta
cámaras registradas                       exactas
```

**D4. R0-B.**
Las tres pasan. Con eso se cierran D23, D26 y D34, y **se desbloquea todo lo que
depende del contrato compartido**.

---

## 3. Qué reportar, y dónde

Después de cada tarea, tres líneas: qué se hizo, qué prueba lo sujeta, qué
sorprendió. Y **cuando una tarea cierre una decisión**, tres sitios:

```text
docs/OBLIGACIONES-VIDEOMESH.md    la fila, con la fecha
el registro del contrato          solo si la decisión pasa a IMPLEMENTADA
CHANGELOG.md                      si existe ya
```

El registro del contrato vive en el repositorio de SoftSight y **se toca con
cuidado**: es la fuente única de las dos partes. Una decisión pasa a IMPLEMENTADA
cuando hay una prueba que falla si se viola, no cuando el código existe.

---

## 4. Lo que este encargo no cubre

```text
Sprint 1 y siguientes     motor, DAG, SQLite, CLI — después de R0-B
fotogrametría             COLMAP y FFmpeg, Sprint 2
mesh ↔ gaussian           research/, explícitamente fuera de V1.1
```

**No se empieza el Sprint 1 hasta R0-B PASS.** Lo dice el roadmap y lo dice D34:
si R0-B falla por proyección de cámara, transformación de matrices,
interpretación del esquema o identidad de artifacts, se arregla la frontera
primero y no se avanza nada que dependa de ella.
