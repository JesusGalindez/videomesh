# Obligaciones de VideoMesh en la frontera con SoftSight

**Este documento no es el contrato.** El contrato es
[`contrato-videomesh.md`](contrato-videomesh.md), enlace simbólico al original que
vive en `Dron/softsight/docs/`. Si los dos dicen cosas distintas, manda el contrato.

**Estado del original al revisar esta tabla:** 2026-09-15.
sha256 `b9e0e708e46723c5727b3a21a1b2bd95fa7a43167439e189ee44a04adc71613f`
(1761 líneas, D1–D34 + P1–P12). Si el hash cambia, esta tabla puede haber quedado
vieja: se comprueba con `shasum -a 256 docs/contrato-videomesh.md`.

**Y quedó vieja.** La versión anterior de esta línea declaraba el contrato del
2026-08-12 —`6dc06081…`, 1138 líneas— y el mecanismo para detectarlo estaba aquí
escrito desde el primer día. **Nadie lo ejecutó en un mes**, mientras el contrato
crecía 623 líneas y trece decisiones pasaban a IMPLEMENTADAS. Que el aviso exista
no sirve de nada si nadie lo corre; conviene comprobarlo antes de usar la tabla,
no después de haber escrito código contra ella.

Aquí solo está **qué le toca escribir a VideoMesh y qué prueba lo cierra**. La
semántica de cada decisión no se copia; se lee en el contrato.

---

## Regla de cierre

Una decisión no está IMPLEMENTADA porque el código exista. Lo está cuando existe
una prueba que **falla si la decisión se incumple** (§1.2 del contrato).

---

## La lista de trabajo — §6 del contrato

Orden fijado por el contrato, no por conveniencia.

```text
V1   allow_nan=False en toda serialización JSON
V2   prueba de serialización no finita   test_json_rejects_non_finite_numbers
V3   generador de cube-v1
V4   expected.json
V5   escritor con temporal y final en el mismo volumen
V6   packageId
V7   manifest SEALED
V8   sha256 por artifact
V9   CameraSet canónico
V10  arnés de paridad
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
| D23 | la columna de VideoMesh y la de `SoftSight ↔ VideoMesh` | `test:parity` (`package-parity-v1`, `camera-projection-v1`); **falta la columna de VideoMesh** |
| D28 | `MeasurementClass` y `ReproducibilityMode` en métricas, nunca en avisos; bloques por índice de entrada, no por número de workers | `test:measurement` — media; la otra media pide **dos plataformas** |
| D29 | rename atómico, mismo volumen verificado **antes**, destino que no existe, manifest el último | `test:contracts` (`unsealed-package-v1`) cierra el lado consumidor; **el escritor es de VideoMesh** |
| D30 | `additionalProperties: false` en el núcleo; `extensions` **ya existe** en el esquema del paquete | `test:contracts` (`unknown-field-v1`) — **IMPLEMENTADA 2026-09-13** |
| D31 | el paquete declara `requires` y `provides` | `test:contracts` — **IMPLEMENTADA 2026-09-13** |
| D32 | álgebra canónica por filas, traslación en 3/7/11, solo `worldFromCamera`; conversión a glTF **exactamente una vez** en el adaptador | `test:gltf-frame` (`transform-gltf-v1`) — **IMPLEMENTADA 2026-09-14** |
| D33 | orientación horneada en los píxeles antes de exponer frames | `test:reconstruction` — **IMPLEMENTADA 2026-09-13** |
| D34 | R0-B antes de cualquier fase que dependa de la frontera | `test:r0` cierra **R0-A**; R0-B sigue abierto |

## Deuda de la otra mitad

Revisada el 2026-09-15 contra el contrato de hoy. **Cuatro de las seis filas
anteriores ya no eran ciertas** y se tachan con la fecha en que dejaron de serlo,
para que se vea qué desbloqueó a qué.

```text
D2    los identificadores PROPUESTOS, sin respuesta          SIGUE ABIERTA
      eran 5 en el envío 01 y 28 en el 02; hoy son 32
D23   la columna de VideoMesh, que pide su cube-v1           SIGUE ABIERTA
D29   el escritor atómico — esa mitad es de VideoMesh        SIGUE ABIERTA
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
2  cube-v1 generado     PENDIENTE, de VideoMesh — V3 y V4 de la lista
3  R0-B PASS            las tres comparaciones de D23, que esperan a 2
4  se desbloquea el trabajo dependiente del contrato
```

**Dónde está el bloqueo hoy, dicho sin rodeos.** Del lado de SoftSight no queda
ninguna decisión accionable: 27 de 34 están IMPLEMENTADAS y las 7 abiertas esperan
a un consumidor que responda, a un fichero EXR, a valores dorados, a un productor
con malla, o a una segunda plataforma.

Tres de esas siete —D23, D26 y D34— cuelgan del **hito 2**, que son `V3` y `V4` de
la lista de trabajo. Ése es el trabajo que más desbloquea por línea escrita.

## Cómo se mantiene esta tabla

No se relee entera cada vez. Se comprueba el hash de la cabecera contra el
contrato, y solo si ha cambiado se revisa lo que el contrato cambió:

```bash
shasum -a 256 docs/contrato-videomesh.md
```

Esta vez el hash llevaba un mes sin comprobarse y la tabla había quedado vieja en
nueve filas, con cuatro nombres de fixture que no existían. **El mecanismo estaba
escrito desde el primer día y no sirvió de nada porque nadie lo ejecutó.**
