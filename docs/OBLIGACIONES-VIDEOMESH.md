# Obligaciones de VideoMesh en la frontera con SoftSight

**Este documento no es el contrato.** El contrato es
[`contrato-videomesh.md`](contrato-videomesh.md), enlace simbólico al original que
vive en `Dron/softsight/docs/`. Si los dos dicen cosas distintas, manda el contrato.

**Estado del original al extraerlo:** 2026-08-12, ronda de diseño cerrada.
sha256 `6dc06081b75317ae06d10c5489f74d89a78e199ca906ea7324c083caa5fba695`
(1138 líneas, D1–D34 + P1–P12). Si el hash cambia, esta tabla puede haber quedado
vieja: se comprueba con `shasum -a 256 docs/contrato-videomesh.md`.

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

| Dec | Qué debe existir en VideoMesh | Prueba que la cierra |
|---|---|---|
| D1 | escribir paquete en disco, pasar ruta del manifest; nunca base64 ni streaming | sin escribir |
| D2 | parsear el **identificador** `SS-XXX-NNN`, nunca el mensaje | responder a los cinco `SS-PKG-010..014` PROPUESTOS |
| D3 | leer los dos ejes por separado; no colapsar `execution` con `certification` | consumo del informe |
| D4 | `ColmapAdapter` real; falta `colmap-small-v1` con datos no sintéticos | `test:colmap` del otro lado |
| D7 | cada artifact declara `path`, `bytes`, `sha256`; `packageId` en el manifest, nunca del nombre del directorio | `hash-mismatch-v1` |
| D9 | `ScaleStatus` / `ScaleSource` / incertidumbre; rechazar presupuesto absoluto si `status != ABSOLUTE` | `unknown-scale-v1` |
| D10 | `CameraImageSpace` como unidad; `cameraAxes` sin valor por defecto; falta `imageArtifactHash` | `camera-projection-v1` |
| D11 | `FrameGraph` con marco origen, destino, matriz, motivo y productor | sin escribir |
| D12 | bloques `versions`, `models`, `capabilities` | sin escribir |
| D15 | modelos Pydantic **generados** de `contracts/*.schema.json`, nunca a mano | `test:contracts --check` |
| D16 | emitir `contractSchemaSha256`; opcional mientras DRAFT | registro generado |
| D17 | rechazar no finitos **en origen**, no confiar en Node | `test_json_rejects_non_finite_numbers` |
| D19 | distorsión con nombre; el adaptador convierte el vector de COLMAP | `colmap-small-v1` con tres modelos |
| D20 | `depthKind` explícito, sin inferirlo por proveedor | `depth-optical-axis-v1`, `depth-ray-length-v1` |
| D21 | `purelyReconstructed` **requerida** en cada `TRIANGLE_MESH`, **prohibida** en `POINT_CLOUD` | cuatro casos fijados el 2026-08-12 |
| D22 | fixtures < 1 MB en git; los pesados fuera con sha256 en manifiesto versionado | sin escribir |
| D23 | la columna de VideoMesh y la de `SoftSight ↔ VideoMesh` | `expected.json` + arnés de paridad |
| D28 | `MeasurementClass` y `ReproducibilityMode` en métricas, nunca en avisos; bloques por índice de entrada, no por número de workers | recuentos en dos plataformas |
| D29 | rename atómico, mismo volumen verificado **antes**, destino que no existe, manifest el último | prueba de VideoMesh — mitad pendiente |
| D30 | `additionalProperties: false` en el núcleo; `extensions` no existe en ningún esquema todavía | `unknown-field-v1` |
| D31 | el paquete declara `requires` y `provides` | `unknown-capability-v1` |
| D32 | álgebra canónica por filas, traslación en 3/7/11, solo `worldFromCamera`; conversión a glTF **exactamente una vez** en el adaptador | `transform-gltf-v1` |
| D33 | orientación horneada en los píxeles antes de exponer frames | `image-orientation-v1` |
| D34 | R0-B antes de cualquier fase que dependa de la frontera | es la prueba |

## Deuda de la otra mitad

Cosas que el contrato marca a medias y esperan a VideoMesh:

```text
D2    cinco identificadores SS-PKG-010..014 PROPUESTOS, sin respuesta
D4    colmap-small-v1 con datos reales; hoy es sintético
D10   imageArtifactHash; hoy viaja imageArtifactId
D23   dos de las tres comparaciones esperan al cube-v1 de VideoMesh
D29   rename atómico y mismo volumen — la prueba es de este lado
D30   extensions no existe en ningún esquema; dos filas NOT_RUN
```

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
1  R0-A PASS            HECHO — SoftSight cerró S6 el 2026-08-12
2  cube-v1 generado     pendiente, de VideoMesh
3  R0-B PASS            las tres comparaciones de D23
4  se desbloquea el trabajo dependiente del contrato
```
