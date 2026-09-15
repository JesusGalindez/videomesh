# Obligaciones de VideoMesh en la frontera con SoftSight

**Este documento no es el contrato.** El contrato es
[`contrato-videomesh.md`](contrato-videomesh.md), enlace simbólico al original que
vive en `Dron/softsight/docs/`. Si los dos dicen cosas distintas, manda el contrato.

**Estado del original al revisar esta tabla:** 2026-09-15.
sha256 `43b305e3b5cea86fcf965f059b6a44fe96fa89a7bc5967782a4a251e0281acbc`
(1809 líneas, D1–D34 + P1–P12). Si el hash cambia, esta tabla puede haber quedado
vieja: se comprueba con `shasum -a 256 docs/contrato-videomesh.md`.

**Ya no hace falta acordarse.** `tests/test_contrato_no_ha_derivado.py` lee este
hash, calcula el del contrato y compara, y `scripts/verify.sh` lo ejecuta. La
versión anterior de esta línea declaraba el contrato del 2026-08-12 —`6dc06081…`,
1138 líneas— y el mecanismo para detectarlo estaba aquí escrito desde el primer
día: **nadie lo ejecutó en un mes**, mientras el contrato crecía 623 líneas y trece
decisiones pasaban a IMPLEMENTADAS. Que el aviso exista no sirve de nada si nadie
lo corre.

La puerta se estrenó el mismo día que se escribió: al cerrar D23, D29 y D34 en el
contrato, la verificación de este repositorio se puso roja sola —«declarado
b9e0e708… / real 43b305e3…»— sin que nadie tocara VideoMesh. Eso es lo que esta
línea tenía que haber hecho en agosto.

Aquí solo está **qué le toca escribir a VideoMesh y qué prueba lo cierra**. La
semántica de cada decisión no se copia; se lee en el contrato.

---

## Regla de cierre

Una decisión no está IMPLEMENTADA porque el código exista. Lo está cuando existe
una prueba que **falla si la decisión se incumple** (§1.2 del contrato).

---

## La lista de trabajo — §6 del contrato

Orden fijado por el contrato, no por conveniencia.

**Las diez están hechas el 2026-09-15**, cada una con la prueba que se pone roja
si se incumple. La columna de la derecha es el fichero que la cierra.

```text
V1   allow_nan=False en toda serialización JSON   test_a1_serializacion_estricta.py
V2   prueba de serialización no finita            test_json_rejects_non_finite_numbers
V3   generador de cube-v1                         test_d1_cube_v1.py
V4   expected.json                                test_d2_expected.py
V5   escritor con temporal y final en el mismo volumen   test_c3_sellado.py
V6   packageId                                    test_c1_c2_integridad.py
V7   manifest SEALED                              test_c3_sellado.py
V8   sha256 por artifact                          test_c1_c2_integridad.py
V9   CameraSet canónico                           test_b1_algebra_canonica.py
V10  arnés de paridad                             test_d3_paridad.py
```

Mapeo a los sprints del roadmap V1.1 §84:

```text
V1, V2         Sprint 0A
V9             Sprint 0B
V5, V6, V7, V8 Sprint 0C
V3, V4, V10    Sprint 0D
```

## Decisiones que obligan a código de VideoMesh

**La columna de la derecha nombra la puerta que se ejecuta**, no un fichero. La
versión anterior citaba fixtures por nombre y cuatro de ellos no existen con ese
nombre: `hash-mismatch-v1` se construyó como `package-integrity-v1`, y
`unknown-scale-v1`, `depth-optical-axis-v1`, `depth-ray-length-v1` e
`image-orientation-v1` acabaron dentro de una puerta en vez de como fichero
suelto. Quien buscara el fichero no encontraba nada y concluiría que la decisión
está sin cerrar, cuando sí lo está.

Los fixtures que **sí** existen como fichero van entre paréntesis, porque ésos se
pueden leer.

| Dec | Qué debe existir en VideoMesh | Puerta que la cierra del lado de SoftSight |
|---|---|---|
| D1 | escribir paquete en disco, pasar ruta del manifest; nunca base64 ni streaming | `test:package-transport` — **IMPLEMENTADA 2026-09-14** |
| D2 | parsear el **identificador** `SS-XXX-NNN`, nunca el mensaje | `test:codes`; falta responder a los **32** PROPUESTOS |
| D3 | leer los dos ejes por separado; no colapsar `execution` con `certification` | `test:reconstruction` |
| D4 | `ColmapAdapter` real | `test:colmap` con `colmap-real-v1` — **IMPLEMENTADA 2026-09-13** |
| D7 | cada artifact declara `path`, `bytes`, `sha256`; `packageId` en el manifest, nunca del nombre del directorio | `test:reconstruction` (`package-integrity-v1`) |
| D9 | `ScaleStatus` / `ScaleSource` / incertidumbre; rechazar presupuesto absoluto si `status != ABSOLUTE` | `test:reconstruction` |
| D10 | `CameraImageSpace` como unidad; `cameraAxes` sin valor por defecto; `imageArtifactHash` | `test:reconstruction` (`camera-projection-v1`) — el hash es **obligatorio** desde el envío 02 |
| D11 | `FrameGraph` con marco origen, destino, matriz, motivo y productor | `test:reconstruction` |
| D12 | bloques `versions`, `models`, `capabilities` | `test:contracts` |
| D15 | modelos Pydantic **generados** de `contracts/*.schema.json`, nunca a mano | `test:contracts` (`unknown-field-v1`, `unknown-capability-v1`, `unsealed-package-v1`) — **IMPLEMENTADA 2026-09-14** |
| D16 | emitir `contractSchemaSha256`; opcional mientras DRAFT | `test:contracts` |
| D17 | rechazar no finitos **en origen**, no confiar en Node | `test_json_rejects_non_finite_numbers`, **de VideoMesh** |
| D19 | distorsión con nombre; el adaptador convierte el vector de COLMAP | `test:reconstruction` (`reconstruction-package-v1`, `colmap-small-v1`) |
| D20 | `depthKind` explícito, sin inferirlo por proveedor | `test:reconstruction` — el error medido es **0 % en el centro y 12,5 % en la esquina** |
| D21 | `purelyReconstructed` **requerida** en cada `TRIANGLE_MESH`, **prohibida** en `POINT_CLOUD` | `test:reconstruction` (`reconstruction-package-v1`) |
| D22 | fixtures < 1 MB en git; los pesados fuera con sha256 en manifiesto versionado | `test:fixtures` — **IMPLEMENTADA 2026-09-14** |
| D23 | la columna de VideoMesh y la de `SoftSight ↔ VideoMesh` | `test:parity` (`package-parity-v1`, `camera-projection-v1`) — **IMPLEMENTADA 2026-09-15**, las dos columnas existen |
| D28 | `MeasurementClass` y `ReproducibilityMode` en métricas, nunca en avisos; bloques por índice de entrada, no por número de workers | `test:measurement` — media; la otra media pide **dos plataformas** |
| D29 | rename atómico, mismo volumen verificado **antes**, destino que no existe, manifest el último | `test:contracts` (`unsealed-package-v1`) cierra el lado consumidor — **IMPLEMENTADA 2026-09-15**, el escritor está |
| D30 | `additionalProperties: false` en el núcleo; `extensions` **ya existe** en el esquema del paquete | `test:contracts` (`unknown-field-v1`) — **IMPLEMENTADA 2026-09-13** |
| D31 | el paquete declara `requires` y `provides` | `test:contracts` — **IMPLEMENTADA 2026-09-13** |
| D32 | álgebra canónica por filas, traslación en 3/7/11, solo `worldFromCamera`; conversión a glTF **exactamente una vez** en el adaptador | `test:gltf-frame` (`transform-gltf-v1`) — **IMPLEMENTADA 2026-09-14** |
| D33 | orientación horneada en los píxeles antes de exponer frames | `test:reconstruction` — **IMPLEMENTADA 2026-09-13** |
| D34 | R0-B antes de cualquier fase que dependa de la frontera | `test:r0` cierra **R0-A** — **IMPLEMENTADA 2026-09-15**, R0-B pasa y se levanta la condición de parada |

## Lo que VideoMesh ya cierra, y con qué prueba

La tabla de arriba dice qué exige el consumidor. Ésta dice qué lo sujeta **de este
lado**, que es lo que faltaba: una decisión no está cerrada porque el código exista,
sino porque hay una prueba que se pone roja si se incumple.

| Dec | Prueba de VideoMesh |
|---|---|
| D6 | `test_c1_c2_integridad.py` — ruta absoluta, `..`, escape por symlink con contenido idéntico, enlace roto |
| D7 | `test_c1_c2_integridad.py` — `packageId` que sobrevive a renombrar el directorio; `bytes` y `sha256` leídos del fichero |
| D9 | `test_b4_escala.py` — las tres filas, con el presupuesto absoluto sobre escala relativa rechazado |
| D10 | `test_b2_camara.py` — el hash reapuntado a otra imagen del mismo paquete se rechaza |
| D11 | `test_b3_frame_graph.py` — ida y vuelta por dos saltos, arista no rígida, marco sin camino |
| D12 | `test_estado_publicado.py` — la combinación entera, no un campo suelto |
| D15 | `test_a2_modelos_generados.py` — se regenera y se compara byte a byte con lo commiteado |
| D16 | `test_a3_sobre.py` — sin sobre no se serializa; hash fuera del registro rechazado |
| D17 | `test_a1_serializacion_estricta.py` — `test_json_rejects_non_finite_numbers` |
| D19 | `test_a2_modelos_generados.py` — distorsión con nombre, del esquema |
| D21 | `test_a4_artifact_discriminado.py` — los cuatro casos, más el tipo inexistente |
| D23 | `test_d3_paridad.py` — las tres comparaciones, con las dos mutaciones comprobadas |
| D29 | `test_c3_sellado.py` — volumen comprobado antes, destino que no se pisa, manifest el último |
| D30 | `test_a2_modelos_generados.py` — campo desconocido en el núcleo rechazado |
| D32 | `test_b1_algebra_canonica.py` — los cinco casos del punto conocido y la puerta de un solo sitio |
| D33 | `test_b2_camara.py` — `sourceOrientation` vigilado por ausencia; la rejilla del PNG contra la declarada |
| D34 | `test_d3_paridad.py::test_r0_b` |

Lo que sigue abierto de este lado es **D2**: los 32 identificadores PROPUESTOS
siguen sin respuesta, y no se fijan desde aquí porque es decisión de criterio.

## Deuda de la otra mitad

Revisada el 2026-09-15 contra el contrato de hoy. **Cuatro de las seis filas
anteriores ya no eran ciertas** y se tachan con la fecha en que dejaron de serlo,
para que se vea qué desbloqueó a qué.

```text
D2    los identificadores PROPUESTOS, sin respuesta          SIGUE ABIERTA
      eran 5 en el envío 01 y 28 en el 02; hoy son 32
```

**Y dos que se cerraron el mismo 2026-09-15**, las dos escribiendo esta mitad:

```text
~~D23   la columna de VideoMesh, que pide su cube-v1~~
        RESUELTA 2026-09-15: el cube-v1 de aquí sale COMPLETE + PASS por el
        consumidor real y las tres comparaciones pasan. `expected.json` es el
        oráculo, y no lo lee quien mide: si lo leyera, sería el código
        comparándose consigo mismo

~~D29   el escritor atómico — esa mitad es de VideoMesh~~
        RESUELTA 2026-09-15: publicación por rename con el volumen comprobado
        antes de escribir un byte, destino que no se pisa, y nada que sobreviva a
        un fallo. Seis reglas rotas a propósito, seis pruebas rojas
```

```text
~~D4    colmap-small-v1 con datos reales~~
        RESUELTA 2026-09-13: `colmap-real-v1` vive fuera del repositorio con su
        sha256 versionado. Nuestro error medio de reproyección da 0,49697 px
        donde COLMAP declara 0,49703, sobre 61.514 puntos

~~D10   imageArtifactHash; hoy viaja imageArtifactId~~
        RESUELTA 2026-09-13: es campo **obligatorio** desde el envío 02, y un
        manifest escrito contra el esquema anterior ya no valida

~~D23   dos de las tres comparaciones esperan al cube-v1~~
        CORREGIDA 2026-09-14: las tres filas tienen puerta y valores dorados de
        nuestro lado. Lo que falta es **la columna de VideoMesh**, no las filas

~~D30   extensions no existe en ningún esquema; dos filas NOT_RUN~~
        RESUELTA 2026-09-13: el espacio existe, las tres filas están cerradas y
        `org.softsight.mascaras` es la primera extensión que este binario honra
```

**Y una que no estaba y ahora es la que más importa:** el transporte. Desde el
2026-09-14, `bridgeContractVersion: 2` acepta el paquete **por ruta**, así que
VideoMesh ya tiene por dónde entregarlo. No lo tenía desde el primer día —150 MB
de `dense.ply` son ~200 en base64 contra un tope de 256 ya codificados, así que no
era estrecho sino imposible—, y eso bloqueaba el handoff entero sin que ninguna
decisión lo dijera. Lo diagnosticó §84 del plan de reconstrucción.

## Lo que VideoMesh no hace

```text
no duplica la lógica de verdad geométrica de SoftSight    P1
no reimplementa cobertura para obtener paridad            P11
no manda blobs por el puente                              D1, P7
no infiere identidad del nombre del directorio            D7
no marca un paquete como CONSUMED                         D29
no trata INCONCLUSIVE como PASS                           D3
```

## Hitos compartidos

```text
1  R0-A PASS            HECHO — SoftSight cerró S6 el 2026-08-12, y desde el
                        2026-09-14 lo comprueba `test:r0`: las nueve etapas
                        dejan huella y el sobre ata el informe a su entrada
2  cube-v1 generado     HECHO 2026-09-15 — V3 y V4; sale COMPLETE + PASS con
                        salida 0 por el consumidor real
3  R0-B PASS            HECHO 2026-09-15 — las tres comparaciones de D23, con
                        sus tolerancias declaradas
4  se desbloquea el trabajo dependiente del contrato   DESBLOQUEADO
```

**Dónde está el bloqueo hoy, dicho sin rodeos.** En ningún sitio del camino de R0.
Del lado de SoftSight quedan 30 de 34 IMPLEMENTADAS, y las 4 abiertas esperan a un
consumidor que responda (D2), a un fichero EXR (D5), a un productor real con malla
sobre datos de verdad (D26) o a una segunda plataforma (D28). Ninguna bloquea el
Sprint 1.

Lo único accionable desde aquí es **D2**: 32 identificadores PROPUESTOS sin
respuesta. No se fijan desde este repositorio porque es decisión de criterio, no de
hecho.

## Cómo se mantiene esta tabla

No se relee entera cada vez. Se comprueba el hash de la cabecera contra el
contrato, y solo si ha cambiado se revisa lo que el contrato cambió:

```bash
shasum -a 256 docs/contrato-videomesh.md
```

Y ya no hace falta acordarse de correrlo: `scripts/verify.sh` lo hace en cada
verificación. La primera vez que la tabla quedó vieja, el hash llevaba un mes sin
comprobarse y había nueve filas caducadas con cuatro nombres de fixture que no
existían — **el mecanismo estaba escrito desde el primer día y no sirvió de nada
porque nadie lo ejecutó**. La segunda vez que el contrato cambió, la verificación
se puso roja en el mismo minuto.
