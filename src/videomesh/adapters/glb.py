"""El GLB minimo que esta cadena escribe — encargo 04, bloque C.

Lo escribe VideoMesh y no el proveedor de malla, y el motivo es de una linea:
`pymeshlab` **lee** GLB —comprobado el 2026-09-16 con un GLB de 96 vertices y 124
caras: los carga con UV por vertice y por wedge— y **no tiene exportador**. Su
unica salida es `save_current_mesh`, que escribe por extension y no admite glTF.
La otra mitad del motivo esta en el vecino: un PLY no puede expresar coordenadas de
textura, lo dice su propio informe, asi que sin este fichero el bloque C no tiene
nada que ensenar a la auditoria.

El formato es **minimo a proposito**, y lo que no lleva esta razonado:

```text
sin KTX2 ni EXT_meshopt_compression   el cargador del vecino rechaza por su nombre
                                      las extensiones que no declara soportadas, y
                                      el empaquetado final es del bloque E
sin normales                          su lector las calcula cuando faltan, y una
                                      normal calculada aqui seria un dato que nadie
                                      midio — y el bloque D tiene que hornearlo
sin matriz de nodo                    la identidad. La conversion de convencion de
                                      glTF vive en `adapters/gltf_transforms.py`
                                      (D32) y no se escribe una segunda
```

Los tipos son los de glTF y van en crudo porque son parte del fichero: `5126` es
float de 32 bits con `componentType` en el JSON, y se declara una vez aqui en vez de
en cada llamada.
"""

import json
import pathlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

__all__ = ["Pieza", "escribir_glb", "leer_glb"]

#: La firma del fichero, que son cuatro bytes ASCII: `glTF`.
_CABECERA = 0x46546C67

_VERSION = 2

_PIEZA_JSON = 0x4E4F534A
_PIEZA_BIN = 0x004E4942

#: Tipos de componente de glTF. Los numeros son del contrato.
_FLOTANTE = 5126
_ENTERO_SIN_SIGNO = 5125

#: A que se destina cada vista de bufer. Es una pista para el motor, no un dato.
_ARREGLO_DE_ATRIBUTOS = 34962
_ARREGLO_DE_INDICES = 34963


def _acolchar(datos: bytearray, relleno: int) -> None:
    """Lleva la longitud a multiplo de cuatro. El formato lo exige y no se adivina."""
    while len(datos) % 4 != 0:
        datos.append(relleno)


def _documento(
    *,
    nombre: str,
    vertices: int,
    triangulos: int,
    vistas: Sequence[tuple[int, int, int]],
    minimo: Sequence[float],
    maximo: Sequence[float],
    con_normales: bool = False,
) -> dict[str, Any]:
    """El bloque JSON del GLB. Una pieza, un primitivo, y la normal cuando la hay.

    `NORMAL` no es decorativa: un mapa de normales horneado se lee **contra la normal
    de la malla**. Si la pieza no la trae, el visor se la inventa —plana o suavizada a
    su manera— y el relieve sale desplazado sin que nada lo diga. Por eso la etapa que
    hornea la escribe, y la escribe con la misma normal con la que construyo el marco.
    """
    indice_vertices, indice_uv, indice_caras = 0, 1, 2
    indice_normales = 3
    atributos: dict[str, int] = {"POSITION": indice_vertices, "TEXCOORD_0": indice_uv}
    if con_normales:
        atributos["NORMAL"] = indice_normales
    return {
        "asset": {"version": "2.0", "generator": "videomesh"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": nombre, "mesh": 0}],
        "meshes": [
            {
                "name": nombre,
                "primitives": [
                    {
                        "attributes": atributos,
                        "indices": indice_caras,
                        "mode": 4,
                    }
                ],
            }
        ],
        "accessors": [
            # `min` y `max` son obligatorios para POSITION en la especificacion, y
            # ademas son lo que permite a un motor encuadrar sin recorrer la malla.
            {
                "bufferView": 0,
                "componentType": _FLOTANTE,
                "count": vertices,
                "type": "VEC3",
                "min": list(minimo),
                "max": list(maximo),
            },
            {"bufferView": 1, "componentType": _FLOTANTE, "count": vertices, "type": "VEC2"},
            {
                "bufferView": 2,
                "componentType": _ENTERO_SIN_SIGNO,
                "count": triangulos * 3,
                "type": "SCALAR",
            },
            *(
                [{"bufferView": 3, "componentType": _FLOTANTE, "count": vertices, "type": "VEC3"}]
                if con_normales
                else []
            ),
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": desplazamiento, "byteLength": largo, "target": destino}
            for desplazamiento, largo, destino in vistas
        ],
        "buffers": [{"byteLength": vistas[-1][0] + vistas[-1][1]}],
    }


def escribir_glb(
    destino: pathlib.Path,
    *,
    vertices: Sequence[Sequence[float]],
    triangulos: Sequence[Sequence[int]],
    uv: Sequence[Sequence[float]],
    normales: Sequence[Sequence[float]] | None = None,
    nombre: str = "pieza",
) -> None:
    """Escribe una pieza con posiciones, triangulos, coordenadas de textura y normales.

    Las tres listas tienen que ser coherentes entre si, y se comprueba **aqui**:
    un indice fuera de rango o una UV de menos produce un fichero que el vecino lee
    a medias —o no lee— y el fallo aparece en su auditoria en vez de en la etapa que
    lo escribio.
    """
    import numpy as np

    posiciones = np.asarray(vertices, dtype="<f4").reshape(-1, 3)
    texturas = np.asarray(uv, dtype="<f4").reshape(-1, 2)
    caras = np.asarray(triangulos, dtype="<u4").reshape(-1, 3)

    if len(posiciones) != len(texturas):
        raise ValueError(
            f"hay {len(posiciones)} vertices y {len(texturas)} coordenadas de textura: "
            "una malla con UV tiene una por vertice"
        )
    if len(caras) == 0:
        raise ValueError("un GLB sin triangulos no describe una superficie")
    if int(caras.max()) >= len(posiciones):
        raise ValueError(
            f"un triangulo usa el vertice {int(caras.max())} y hay {len(posiciones)}: "
            "un indice fuera de rango no es un fichero que se pueda leer"
        )
    vectores = None if normales is None else np.asarray(normales, dtype="<f4").reshape(-1, 3)
    if vectores is not None and len(vectores) != len(posiciones):
        raise ValueError(
            f"hay {len(posiciones)} vertices y {len(vectores)} normales: la normal es un atributo "
            "por vertice y sin ella el mapa no se puede leer"
        )

    crudo = bytearray()
    vistas: list[tuple[int, int, int]] = []
    arreglos = [
        (posiciones, _ARREGLO_DE_ATRIBUTOS),
        (texturas, _ARREGLO_DE_ATRIBUTOS),
        (caras, _ARREGLO_DE_INDICES),
    ]
    if vectores is not None:
        arreglos.append((vectores, _ARREGLO_DE_ATRIBUTOS))
    for datos, destino_de_la_vista in arreglos:
        _acolchar(crudo, 0)
        desplazamiento = len(crudo)
        contenido = datos.tobytes()
        crudo += contenido
        vistas.append((desplazamiento, len(contenido), destino_de_la_vista))

    documento = _documento(
        nombre=nombre,
        vertices=len(posiciones),
        triangulos=len(caras),
        vistas=vistas,
        minimo=[float(x) for x in posiciones.min(axis=0)],
        maximo=[float(x) for x in posiciones.max(axis=0)],
        con_normales=vectores is not None,
    )

    texto = bytearray(json.dumps(documento, separators=(",", ":")).encode("utf-8"))
    # El JSON se rellena con espacios y el binario con ceros: son las dos reglas del
    # formato, y el relleno es parte del bloque —de su longitud—, no un adorno.
    _acolchar(texto, 0x20)
    _acolchar(crudo, 0x00)

    total = 12 + 8 + len(texto) + 8 + len(crudo)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("wb") as fichero:
        fichero.write(_CABECERA.to_bytes(4, "little"))
        fichero.write(_VERSION.to_bytes(4, "little"))
        fichero.write(total.to_bytes(4, "little"))
        fichero.write(len(texto).to_bytes(4, "little"))
        fichero.write(_PIEZA_JSON.to_bytes(4, "little"))
        fichero.write(texto)
        fichero.write(len(crudo).to_bytes(4, "little"))
        fichero.write(_PIEZA_BIN.to_bytes(4, "little"))
        fichero.write(crudo)


@dataclass(frozen=True)
class Pieza:
    """Lo que un GLB de esta cadena contiene, releído del fichero.

    Es lo que las etapas que **visten o comprueban** necesitan: los vértices que se
    escribieron, sus triángulos, sus UV y sus normales cuando las hay. Las normales
    entran desde E3 y no son un adorno: el mapa horneado en la etapa anterior se lee
    **contra la normal de la malla**, y el empaquetado final tiene que transportar la
    misma con la que se construyó el marco — recalcularla allí sería otro dato. Un GLB
    con extensiones o con imágenes no es de este escritor, y la lectura lo dice en vez
    de adivinar.
    """

    vertices: Any
    triangulos: Any
    uv: Any
    normales: Any | None = None


def leer_glb(ruta: pathlib.Path) -> Pieza:
    """Relee un GLB escrito por `escribir_glb`: posiciones, triángulos y UV.

    Se lee el JSON del fichero y se reensamblan los arreglos desde el chunk binario,
    con los tipos que este escritor declara. No es un lector glTF general: es la
    mitad que falta del escritor, para que una etapa pueda comprobar lo que hay en
    disco antes de declararlo — copiarlo a mano y declarar otra cosa sería la clase
    de contradicción que el propio vecino caza.
    """
    import numpy as np

    datos = ruta.read_bytes()
    if datos[:4] != _CABECERA.to_bytes(4, "little"):
        raise ValueError(f"{ruta} no es un GLB: su firma no es `glTF`")
    largo_json = int.from_bytes(datos[12:16], "little")
    documento: dict[str, Any] = json.loads(datos[20 : 20 + largo_json])
    if documento.get("extensionsUsed"):
        raise ValueError(
            f"{ruta} lleva extensiones y este escritor no las escribe: no es una pieza "
            "de esta cadena"
        )
    # El chunk binario va tras el JSON, alineado a cuatro.
    inicio_bin = 20 + ((largo_json + 3) & ~3)
    if datos[inicio_bin + 4 : inicio_bin + 8] != _PIEZA_BIN.to_bytes(4, "little"):
        raise ValueError(f"{ruta} no lleva chunk binario donde el formato lo pone")
    largo_bin = int.from_bytes(datos[inicio_bin - 4 : inicio_bin], "little")
    binario = datos[inicio_bin + 8 : inicio_bin + 8 + largo_bin]

    primitiva = documento["meshes"][0]["primitives"][0]
    atributos = primitiva["attributes"]

    #: Cuantas componentes lleva cada tipo de accesor. El largo se calcula con **esto**
    #: y no con lo que espere quien llama: un accesor `SCALAR` de 576 indices no pesa
    #: 576 x 12 bytes, y leer mas de lo que hay es lo que hace que la vista de indices
    #: se coma los bytes de la siguiente.
    _COMPONENTES = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}

    def _arreglo(accesor_indice: int, tipo: int) -> Any:
        acceso = documento["accessors"][accesor_indice]
        if acceso["componentType"] != tipo:
            raise ValueError(
                f"{ruta}: el accesor {accesor_indice} no es del tipo que este escritor declara"
            )
        componentes = _COMPONENTES[acceso["type"]]
        ancho = 4 * componentes
        largo = int(acceso["count"]) * ancho
        vista = documento["bufferViews"][acceso["bufferView"]]
        # Hasta donde acaba **la vista**, que no es donde acaba el bufer: la vista de
        # indices de una pieza con normales no es la ultima, y leer de mas metia los
        # bytes de la normal dentro de los indices —un vertice 3212836864 en una malla
        # de 150— sin que nada lo dijera. El largo de la vista se respeta.
        if largo > int(vista["byteLength"]):
            raise ValueError(
                f"{ruta}: el accesor {accesor_indice} pide {largo} bytes y su vista declara "
                f"{vista['byteLength']}: el fichero no tiene lo que dice tener"
            )
        inicio = int(vista.get("byteOffset", 0))
        crudo = binario[inicio : inicio + largo]
        if len(crudo) != largo:
            raise ValueError(
                f"{ruta}: el accesor {accesor_indice} empieza en {inicio} y el bloque binario "
                f"acaba antes de sus {largo} bytes"
            )
        arreglo = np.frombuffer(crudo, dtype="<f4" if tipo == _FLOTANTE else "<u4")
        return arreglo.reshape(-1, componentes)

    posiciones = _arreglo(atributos["POSITION"], _FLOTANTE)
    uv = _arreglo(atributos["TEXCOORD_0"], _FLOTANTE)
    triangulos = _arreglo(primitiva["indices"], _ENTERO_SIN_SIGNO).reshape(-1, 3)
    normales = _arreglo(atributos["NORMAL"], _FLOTANTE) if "NORMAL" in atributos else None
    return Pieza(vertices=posiciones, triangulos=triangulos, uv=uv, normales=normales)
