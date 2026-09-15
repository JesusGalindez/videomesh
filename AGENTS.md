# AGENTS.md

VideoMesh escribe paquetes de reconstruccion; **SoftSight los consume y los rechaza si
estan mal**. No se escribe contra una especificacion: se escribe contra un programa que
corre en esta maquina. Esto es lo que hay que saber antes del primer comando; corto a
proposito —el techo son 120 lineas y una prueba lo comprueba— y lo demas son punteros.

## Lo primero

```bash
bash scripts/instalar_hooks.sh   # una vez por clon
bash scripts/verify.sh
```

El hook de `pre-commit` corre la verificacion entera y para el commit si esta en
rojo. Vive en `scripts/hooks/` y no en `.git/hooks`, que no se versiona; una
prueba comprueba que la copia instalada sigue siendo la del repositorio. Para
saltarselo a proposito: `git commit --no-verify`.

**No hay CI remoto, y es deliberado:** este repositorio no tiene remoto, asi que un
workflow seria un fichero que parece una puerta y no se ejecuta nunca. Cuando lo
haya, el workflow tiene que clonar SoftSight: doce de los diecinueve ficheros de
prueba leen sus esquemas, sus fixtures y su consumidor.

Si esto esta en rojo, no sigas. Y antes de fiarte de la tabla de obligaciones:

```bash
node ../Dron/softsight/tools/reconstruction.mjs inspect <ruta>/manifest.json --human
```

Un paquete que SoftSight rechaza esta mal aunque el codigo de aqui crea que no.

## Donde va un cambio

Tres capas, de dentro hacia fuera. Confundirlas es la causa habitual de que un cambio
rompa lo que no tocaba.

1. **Dominio** — `src/videomesh/domain/`. Algebra, camaras, marcos, escala. No sabe que es
   un fichero ni que es glTF.
2. **Contratos** — `src/videomesh/contracts/`. La frontera: serializacion estricta, sobre,
   estado publicado y los modelos **generados**. `modelos/` no se edita a mano.
3. **Adaptadores** — `src/videomesh/adapters/`. Traducen a convenciones de fuera, y solo
   ahi.

**La regla:** si necesita saber que convencion usa otro programa, no va en la capa 1.

## Las cuatro invariantes que rompen el producto

1. **Los modelos se generan** de `../Dron/softsight/contracts/*.schema.json` (D15). Uno
   escrito a mano es un segundo original que diverge en el primer campo nuevo.
2. **Nada se serializa sin pasar por `volcar_json`** (D17). `NaN` e `Infinity` se rechazan
   en origen; no se confia en que los cace Node.
3. **La matriz es 4x4 por filas**, traslacion en 3, 7 y 11, vectores columna (D32). La de
   glTF va por columnas y **no es intercambiable**: la conversion vive solo en
   `adapters/gltf_transforms.py`, y una prueba comprueba que no aparece en ningun otro
   sitio. Dos transposiciones se cancelan y la geometria sale bien por casualidad.
4. **La version del contrato no es una constante**: se lee del bloque de
   `contracts/estado.json` (D12). Dos fuentes del mismo numero divergen en la primera
   subida, y ya paso.

## Lo que este repositorio no hace

```text
no duplica la verdad geometrica de SoftSight     P1
no reimplementa cobertura para dar paridad       P11
no manda blobs por el puente — viaja por ruta    D1
no infiere identidad del nombre del directorio   D7
no marca un paquete como CONSUMED                D29
no trata INCONCLUSIVE como PASS                  D3
no copia codigo de SoftSight
```

Lo ultimo no es celo: el segundo productor existe para demostrar que el contrato es
escribible por quien solo leyo el esquema publicado. Compartir codigo lo convierte en el
primero disfrazado. Leerlo si — `tools/cubeV1.mjs` hace lo mismo del otro lado.

## Ordenes

<!-- generado: comandos -->
`bash scripts/verify.sh` — **lo primero y lo ultimo**: linter, tipos, pruebas y que lo publicado este al dia.

Vuelven a generar lo que este repositorio publica: `scripts/agents_md.py` · `scripts/generar_cube_v1.py` · `scripts/generar_estado.py` · `scripts/generar_expected.py` · `scripts/generar_modelos.py` · `scripts/instalar_hooks.sh`. Con `--check` dicen si lo commiteado se ha quedado atras.
<!-- /generado: comandos -->

## Las pruebas, y que cubre cada una

<!-- generado: pruebas -->
| Prueba | Que cubre |
|---|---|
| `test_a0_esqueleto.py` | A0 — el repositorio existe como proyecto Python instalable. |
| `test_a1_serializacion_estricta.py` | A1 — V1 y V2: ninguna serializacion de este repositorio emite un no finito. |
| `test_a2_modelos_generados.py` | A2 — D15: los modelos salen del esquema publicado, nunca de la mano. |
| `test_a3_sobre.py` | A3 — D16: todo lo que se escriba lleva sobre, y se comprueba antes de disco. |
| `test_a4_artifact_discriminado.py` | A4 — D21: `purelyReconstructed` requerida en TRIANGLE_MESH, prohibida en POINT_CLOUD. |
| `test_agents_md.py` | `AGENTS.md` no se queda corto porque la lista se genera — y `--check` la vigila. |
| `test_b1_algebra_canonica.py` | B1 — V9 y D32: 4x4 por filas, traslacion en 3, 7 y 11, vectores columna. |
| `test_b2_camara.py` | B2 — D10, D19 y D33: la camara dice de que imagen habla, y se comprueba. |
| `test_b3_frame_graph.py` | B3 — D11: cada transformacion entre marcos queda registrada, y se comprueba. |
| `test_b4_escala.py` | B4 — D9: un presupuesto en unidades absolutas sobre una escala que no lo es se rechaza. |
| `test_c1_c2_integridad.py` | C1 y C2 — V6, V8 y D7: identidad del paquete e integridad de cada artifact. |
| `test_c3_sellado.py` | C3 — V5, V7 y D29: el paquete se publica entero o no se publica. |
| `test_contrato_no_ha_derivado.py` | La tabla de obligaciones declara contra que contrato se escribio. Aqui se comprueba. |
| `test_d1_cube_v1.py` | D1 — V3: el `cube-v1` de VideoMesh, consumido por SoftSight de verdad. |
| `test_d1_imagenes.py` | D1, segunda pieza — las imagenes son evidencia, no relleno. |
| `test_d1_malla_y_ply.py` | D1, primera pieza — la geometria del cubo y su PLY. |
| `test_d2_expected.py` | D2 — V4: lo que VideoMesh afirma de su propio cubo. |
| `test_d3_paridad.py` | D3 y D4 — V10, D23: las tres comparaciones, y R0-B. |
| `test_estado_publicado.py` | VideoMesh declara la combinacion entera de versiones que habla — D12. |
| `test_puerta_local.py` | La verificación se ejecuta sola, y dice qué falta cuando no puede. |
<!-- /generado: pruebas -->

## Entorno

<!-- generado: dependencias -->
Python `>=3.11,<3.13`, con `uv`.

En produccion: `pydantic>=2.9`.

Para trabajar: `pytest>=8.3` · `ruff>=0.7` · `mypy>=1.13`.
<!-- /generado: dependencias -->

El `python3` del sistema es 3.9.6 y **no sirve**. COLMAP y FFmpeg no estan instalados y no
hacen falta: R0 es JSON, hashes y algebra de matrices.

## A que documento ir

| Para | Lee |
|---|---|
| que dice la frontera | `docs/contrato-videomesh.md`, que manda sobre todo lo demas |
| que le toca escribir a este repositorio | `docs/OBLIGACIONES-VIDEOMESH.md` |
| que se construye ahora y en que orden | `docs/encargo-agente-01.md` |
| donde esta el proyecto entero | `VIDEOMESH_V1_1_IMPLEMENTATION_ROADMAP.md` |

La tabla de obligaciones declara contra que contrato se escribio, y
`test_contrato_no_ha_derivado.py` lo comprueba en cada verificacion. Estuvo un mes vieja
con el aviso escrito dentro porque nadie lo ejecutaba.
