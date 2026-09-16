"""El proveedor de malla de las etapas B: pymeshlab — encargo 04, bloque B.

**Elegido y declarado**: la limpieza y el decimado van por `pymeshlab`, y no se
mezcla con otro por etapa. Los dos candidatos del encargo —Open3D y pymeshlab—
resuelven lo mismo, y tener la mitad de las etapas en cada uno daria dos
resultados que no se pueden comparar entre si ni reproducir juntos.

Vive en `adapters/` porque traduce a convenciones de fuera —el PLY que lee, el
OBJ que escribe, la rejilla en la que piensa— y no decide nada del contrato.

Dos cosas que se hacen aqui y conviene saber por que:

`limpiar` convierte el umbral **relativo** que pide el encargo en uno absoluto
—caras— porque es lo unico que el proveedor entiende, y lo calcula midiendo el
componente mayor primero. El numero que viaja al informe es el relativo, que es
el que vale para cualquier tamano de malla.

`a_obj` existe por una dependencia de fuera: `diffMeshes` de SoftSight lee `.obj`
y `.glb`, no `.ply`. La conversion la hace el proveedor —no se escribe un escritor
de OBJ a mano— y las dos mallas pasan por ella, asi que la ida y la vuelta son
simetricas y la medida sigue siendo de SoftSight.
"""

import importlib.metadata
import importlib.util
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from videomesh.domain.errores import ErrorDeProveedor, ProveedorNoDisponible

if TYPE_CHECKING:  # pragma: no cover - solo para el analisis de tipos
    # numpy se importa **solo** para anotar: en tiempo de ejecucion no se toca, y asi
    # `doctor`, que importa este modulo en un entorno sin el extra `malla`, sigue
    # funcionando. Los tipos de los arreglos los declara numpy, que los trae.
    from numpy.typing import NDArray

__all__ = [
    "PROVEEDOR",
    "INSTALACION",
    "Atlas",
    "Horneado",
    "Limpieza",
    "Medidas",
    "a_obj",
    "comprobar_objetivo",
    "decimar",
    "exigir",
    "hornear_colores",
    "instalado",
    "a_arreglos",
    "leer_atlas",
    "limpiar",
    "medir",
    "puntos_y_normales",
    "version",
]

PROVEEDOR = "pymeshlab"

INSTALACION = "uv pip install 'videomesh[malla]'"


def instalado() -> bool:
    """Se pregunta por el modulo, no se importa: `status` no puede depender de esto."""
    return importlib.util.find_spec(PROVEEDOR) is not None


def version() -> str:
    """La version instalada, que es un dato del registro y no una constante."""
    try:
        return importlib.metadata.version(PROVEEDOR)
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - sin instalar
        return "no instalado"


def exigir() -> None:
    """Falla antes de tocar un byte, diciendo que falta, para que y como se instala."""
    if instalado():
        return
    raise ProveedorNoDisponible(
        f"falta `{PROVEEDOR}`, que hace falta para limpiar y decimar la malla.\n"
        f"  se instala con: {INSTALACION}\n"
        "  `videomesh doctor` dice el resto del entorno de una vez"
    )


@dataclass(frozen=True)
class Medidas:
    """Lo que el proveedor sabe de una malla, con los nombres del informe."""

    vertices: int
    caras: int
    componentes: int
    aristas_de_borde: int
    triangulos_degenerados: int
    vertices_sueltos: int


@dataclass(frozen=True)
class Limpieza:
    """Antes, despues, y cuanto se quito de cada cosa."""

    antes: Medidas
    despues: Medidas
    componentes_quitados: int
    triangulos_quitados: int
    vertices_quitados: int
    triangulos_degenerados: int
    vertices_sueltos: int
    caras_que_el_proveedor_no_cargo: int


def _conjunto(ruta: pathlib.Path) -> object:
    """Un `MeshSet` con esa malla dentro. El import de pymeshlab es de aqui.

    Un PLY que el proveedor no sabe leer —una cara con el mismo indice repetido, por
    ejemplo, que el contrato llama arista nula— falla aqui, y falla **tipado**: un
    `RuntimeError` de una libreria de C++ obliga a quien lo lee a interpretar un
    texto, que es lo que D2 prohibe un nivel mas adentro.
    """
    import pymeshlab

    conjunto = pymeshlab.MeshSet()
    try:
        conjunto.load_new_mesh(str(ruta))
    except RuntimeError as fallo:
        raise ErrorDeProveedor(
            f"el proveedor de malla no puede leer {ruta}: {fallo}. Si el fichero trae una "
            "cara con un indice repetido, el proveedor la rechaza al cargar y hay que "
            "quitarla antes de llegar aqui"
        ) from fallo
    return conjunto


def _medidas(conjunto: object) -> Medidas:
    medir_ = getattr(conjunto, "get_topological_measures")  # noqa: B009 - API externa
    medidas: dict[str, int] = medir_()
    return Medidas(
        vertices=medidas["vertices_number"],
        caras=medidas["faces_number"],
        componentes=medidas["connected_components_number"],
        aristas_de_borde=medidas["boundary_edges"],
        # El proveedor **no** publica el numero de caras de area cero en sus medidas
        # topologicas, asi que ese lo cuenta quien las quita, midiendo alrededor de
        # la operacion. Inventarse aqui un cero seria publicar una cifra que nadie
        # ha comprobado.
        triangulos_degenerados=0,
        vertices_sueltos=medidas["unreferenced_vertices"],
    )


def medir(ruta: pathlib.Path) -> Medidas:
    """Las medidas de una malla, sin tocarla."""
    exigir()
    return _medidas(_conjunto(ruta))


def _caras_declaradas(ruta: pathlib.Path) -> int | None:
    """Las caras que el fichero PLY dice tener, o `None` si no se puede saber.

    Existe para cazar una perdida silenciosa: el proveedor **descarta al cargar**
    las caras con un indice repetido —las «aristas nulas» del encargo— y no dice
    nada. Comparar lo declarado con lo cargado convierte esa perdida en un numero,
    que es lo unico que la hace visible. Un PLY binario o un fichero raro no dan un
    error por esto: se declara que no se sabe, y se sigue.
    """
    if ruta.suffix.lower() != ".ply":
        return None
    from videomesh.formatos.ply import leer_cabecera_ply

    try:
        return leer_cabecera_ply(ruta).get("face", 0)
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def _escribir(conjunto: object, destino: pathlib.Path) -> None:
    """Escribe la malla en PLY **ASCII**, por lo mismo que el paquete lo escribe asi.

    Un PLY binario pesa la mitad y no se puede leer: el asset de una etapa es algo
    que alguien tiene que poder abrir para comprobar que dice lo que afirma. El
    formato lo elige el proveedor —`binary=False`, que es parametro de PLY y de
    ningun otro— y no se escribe un PLY a mano.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    escribir = getattr(conjunto, "save_current_mesh")  # noqa: B009 - API externa
    if destino.suffix.lower() == ".ply":
        escribir(str(destino), binary=False)
    else:
        escribir(str(destino))


def _caras_por_componente(conjunto: object) -> list[int]:
    """El tamano de cada pieza, medido separandolas.

    Se hace sobre un `MeshSet` **aparte** y no sobre el que se esta limpiando: la
    particion es una consulta, y dejar el conjunto partido obligaria a juntarlo
    otra vez. Se paga una carga extra de la malla a cambio de no inventar una
    union de mallas que el proveedor no ofrece.
    """
    separar = getattr(conjunto, "generate_splitting_by_connected_components")  # noqa: B009
    tamano = getattr(conjunto, "mesh_number")  # noqa: B009
    pieza = getattr(conjunto, "mesh")  # noqa: B009

    # Las piezas se **anaden** al conjunto: la malla original sigue en su sitio y
    # debajo aparecen una por componente. Contarlas todas metia la malla entera en
    # la lista de tamanos, y con eso «el componente mayor» pasaba a ser el total —que
    # no es un componente— y el umbral se calculaba sobre un numero que no existe.
    ya_estaban = int(tamano())
    separar()
    return [int(pieza(indice).face_number()) for indice in range(ya_estaban, int(tamano()))]


def limpiar(origen: pathlib.Path, destino: pathlib.Path, *, minimo_relativo: float) -> Limpieza:
    """Tres operaciones, y ninguna decide donde va un vertice.

    ```text
    vertices sueltos      sin ninguna cara
    triangulos nulos      area cero o aristas nulas
    componentes conexos   se quedan los que superan el umbral RELATIVO al mayor
    ```

    El umbral es relativo porque una mota de tres triangulos es basura al lado de
    una esfera de dieciseis mil y tambien al lado de un cubo de doce. Un numero
    absoluto habria que elegirlo distinto para cada malla, y elegirlo seria una
    decision escondida.
    """
    exigir()
    if not 0.0 < minimo_relativo <= 1.0:
        raise ValueError(
            f"el umbral relativo tiene que estar en (0, 1] y es {minimo_relativo}: "
            "1 se queda solo con el componente mayor y 0 no quita ninguno"
        )

    conjunto = _conjunto(origen)
    antes = _medidas(conjunto)

    # Cada operacion se mide **alrededor de si misma** y no por la diferencia total:
    # asi el informe puede decir cuanto quito cada una, y no un total del que nadie
    # sabe que parte fue la basura y que parte un componente entero que se fue con
    # ella. Primero los sueltos, no vaya a ser que el proveedor los arrastre.
    getattr(conjunto, "meshing_remove_unreferenced_vertices")()  # noqa: B009
    caras_antes_de_los_nulos = _medidas(conjunto).caras
    getattr(conjunto, "meshing_remove_null_faces")()  # noqa: B009
    nullas = caras_antes_de_los_nulos - _medidas(conjunto).caras

    provisional = pathlib.Path(f"{destino}.parcial.ply")
    _escribir(conjunto, provisional)
    try:
        tamanos = sorted(_caras_por_componente(_conjunto(provisional)), reverse=True)
        componentes = len(tamanos)
        umbral = minimo_relativo * tamanos[0]
        conservados = [tamano for tamano in tamanos if tamano >= umbral]
        if len(conservados) < componentes:
            # El proveedor quita por numero de caras, y como los tamanos son enteros,
            # «menos que el mas pequeno que se queda» es exactamente «por debajo del
            # umbral». `removeunref` deja limpios los vertices de lo que se fue.
            getattr(conjunto, "meshing_remove_connected_component_by_face_number")(  # noqa: B009
                mincomponentsize=min(conservados), removeunref=True
            )
    finally:
        provisional.unlink(missing_ok=True)

    despues = _medidas(conjunto)
    _escribir(conjunto, destino)

    declaradas = _caras_declaradas(origen)
    no_cargadas = 0 if declaradas is None else max(0, declaradas - antes.caras)

    return Limpieza(
        antes=antes,
        despues=despues,
        componentes_quitados=antes.componentes - despues.componentes,
        triangulos_quitados=antes.caras - despues.caras,
        vertices_quitados=antes.vertices - despues.vertices,
        triangulos_degenerados=nullas,
        vertices_sueltos=antes.vertices_sueltos,
        caras_que_el_proveedor_no_cargo=no_cargadas,
    )


def comprobar_objetivo(antes: int, despues: int, objetivo: int) -> None:
    """Falla si el decimado se quedo corto. Quedarse corto no es haber decimado.

    El presupuesto de un destino se declara en triangulos. Una etapa que se queda
    en 2.915 habiendo pedido 800 y sale HECHA deja que el veredicto de produccion
    se apoye en una cifra que nadie cumplio.

    Recibe los tres numeros **por argumento** y no toca disco: asi se la puede ver
    en rojo sin una malla que no exista. Una comprobacion que solo sabe mirar el
    resultado de verdad no se distingue de una que no mira nada.
    """
    if despues > objetivo:
        raise ErrorDeProveedor(
            f"el proveedor no llego al objetivo: se pidieron {objetivo} triangulos, "
            f"entraron {antes} y salieron {despues}. La malla puede no ser variedad, "
            "o el objetivo ser inalcanzable para su topologia"
        )


def decimar(
    origen: pathlib.Path, destino: pathlib.Path, *, objetivo: int
) -> tuple[Medidas, Medidas]:
    """Colapso de aristas por error cuadratico hasta el objetivo de triangulos.

    El objetivo es de **triangulos** y no una fraccion: una fraccion esconde el
    numero que importa, y el presupuesto de un destino se declara en triangulos.
    """
    exigir()
    if objetivo < 1:
        raise ValueError(f"el objetivo de triangulos tiene que ser al menos 1, y es {objetivo}")

    # Las medidas salen de un `MeshSet` **aparte**, por el mismo motivo que
    # `_caras_por_componente`: medir es una consulta, y esta no es inocente.
    # `get_topological_measures` marca los vertices no-variedad que encuentra, y
    # el colapso de aristas se rinde **en silencio** sobre una malla marcada: ni
    # excepcion ni aviso, devuelve la misma malla. Medido el 2026-09-15 sobre la
    # malla que llego de Colab —1481 vertices, 2 vertices no-variedad— y sobre dos
    # cubos unidos por un vertice: 1536 caras pedidas a 200 salen 200 midiendo
    # aparte y 1536 midiendo encima.
    #
    # Las esferas y los planos de las pruebas son variedad, asi que ahi no pasaba
    # nada. Una malla de reconstruccion real casi nunca lo es.
    antes = _medidas(_conjunto(origen))
    conjunto = _conjunto(origen)
    if antes.caras > objetivo:
        getattr(conjunto, "meshing_decimation_quadric_edge_collapse")(  # noqa: B009
            targetfacenum=objetivo
        )
    _escribir(conjunto, destino)
    # Y las de despues, releyendo lo que se escribio: es la malla que la etapa
    # siguiente va a leer, no la que quedo en memoria.
    despues = _medidas(_conjunto(destino))

    comprobar_objetivo(antes.caras, despues.caras, objetivo)
    return antes, despues


def casco_convexo(origen: pathlib.Path, destino: pathlib.Path) -> dict[str, int]:
    """El casco convexo de la malla, escrito en `destino`, con su cierre medido.

    Es la pieza que SoftSight **se niega a proponer**: calcular un casco es modelar,
    y en cuanto decide donde va un vertice deja de poder afirmar que sus numeros son
    exactos. Por eso vive aqui — modelar es del productor — y juzgar la contencion
    es del vecino.

    El cierre se **comprueba y no se promete**: un casco es cerrado por construccion,
    pero las medidas topologicas del fichero escrito lo dicen, y `aristas_de_borde`
    es lo que la contencion del vecino mira antes de negarse a correr.
    """
    exigir()
    conjunto = _conjunto(origen)
    getattr(conjunto, "generate_convex_hull")()  # noqa: B009 - API externa
    _escribir(conjunto, destino)
    medidas = _medidas(_conjunto(destino))
    return {
        "vertices": medidas.vertices,
        "caras": medidas.caras,
        "cerrado": medidas.aristas_de_borde == 0,
        "aristas_de_borde": medidas.aristas_de_borde,
    }


def geometria_de(ruta: pathlib.Path) -> tuple[Any, Any]:
    """Los vértices y las caras de un fichero que el proveedor lee, como arreglos.

    Abre **su propio `MeshSet`**: la vista de `current_mesh()` muere con el conjunto
    que la produjo — medido en el bloque C, un `MeshSet` sin referencias deja la
    malla leída con 98 vértices y 0 caras, sin un error. Releer del fichero es la
    única forma de que lo que se declara sea lo que hay en disco.
    """
    import numpy as np

    exigir()
    # La vista y el conjunto viven en variables locales del mismo alcance: el binding
    # de pymeshlab devuelve una vista sobre el objeto de C++, y si el `MeshSet` se
    # recoge antes de copiar los arreglos, la malla sale vacía sin un error.
    conjunto = _conjunto(ruta)
    malla = getattr(conjunto, "current_mesh")()  # noqa: B009 - API externa
    vertices = np.asarray(malla.vertex_matrix(), dtype="float64").reshape(-1, 3)
    caras = np.asarray(malla.face_matrix(), dtype="int64").reshape(-1, 3)
    del conjunto, malla
    if len(caras) == 0:
        raise ErrorDeProveedor(
            f"{ruta} se lee sin triangulos: la vista del `MeshSet` se corto antes de tiempo"
        )
    return vertices, caras


@dataclass(frozen=True)
class Atlas:
    """La malla con su atlas, tal y como la dejo el cortador de UV.

    `uv` es por vertice **y se comprueba que lo sea**: el cortador duplica los vertices
    de las costuras, asi que cada vertice tiene una sola coordenada y el marco del
    horneado se puede construir por vertice y no por esquina. El dia que una malla
    llegue con dos UV para el mismo vertice, esto lo dice en vez de elegir una.
    """

    vertices: Any
    caras: Any
    uv: Any
    triangulos: int
    vertices_por_esquina: int


@dataclass(frozen=True)
class Horneado:
    """Lo que el proveedor devolvio del horneado: el mapa, y lo que el mapa dice de si mismo.

    `colores_de_vuelta` son los colores que el mapa tiene **en el baricentro de cada
    triangulo**, leidos del mapa ya escrito. Es lo que permite publicar el error de la
    etapa con un numero: la comparacion entre lo que se pidio hornear y lo que quedo en
    el fichero, que incluye la rasterizacion y el redondeo a ocho bits del formato.

    Se lee en el baricentro y no en el vertice por una razon medida: el texel de la
    esquina de una isla puede no estar cubierto por los triangulos de esa esquina —la
    regla de la arista decide— y entonces lo que se lee es lo que dejo el relleno, que
    es de otro sitio. Medido el 2026-09-16 con un campo conocido —color = la propia UV—:
    leido en los baricentros el error medio es 0,004 por canal, un texel justo, y leido
    en los vertices el error se dispara en las esquinas de las islas.
    """

    resolucion: int
    colores_de_vuelta: Any


def leer_atlas(ruta: pathlib.Path) -> Atlas:
    """Los vertices, las caras y la UV de cada vertice de una malla con atlas.

    Se lee con el proveedor y no con un lector propio del GLB: el formato lo escribio
    esta casa, pero leerlo aqui con las mismas reglas con las que se escribe seria
    comprobar el escritor contra si mismo.
    """
    import numpy as np

    exigir()
    conjunto = _conjunto(ruta)
    malla = getattr(conjunto, "current_mesh")()  # noqa: B009 - API externa
    vertices = np.array(malla.vertex_matrix(), dtype="float64")
    caras = np.array(malla.face_matrix(), dtype="int64")
    if not malla.has_vertex_tex_coord():
        raise ErrorDeProveedor(
            f"{ruta} no trae coordenadas de textura por vertice: la etapa de UV tiene que "
            "correr antes que la de normales, que hornea sobre su atlas"
        )
    uv = np.array(malla.vertex_tex_coord_matrix(), dtype="float64")
    if malla.has_wedge_tex_coord():
        por_esquina = np.array(malla.wedge_tex_coord_matrix(), dtype="float64").reshape(
            len(caras), 3, 2
        )
        if not np.allclose(por_esquina, uv[caras], atol=1e-9):
            raise ErrorDeProveedor(
                f"{ruta} trae una UV por esquina que no coincide con la del vertice: el marco "
                "del horneado no se puede construir sin elegir cual de las dos manda, y "
                "elegir seria una decision escondida"
            )
    return Atlas(
        vertices=vertices,
        caras=caras,
        uv=uv,
        triangulos=int(len(caras)),
        vertices_por_esquina=int(len(vertices)),
    )


def puntos_y_normales(ruta: pathlib.Path) -> "tuple[Any, Any]":
    """Los vertices de la malla medida y la normal **unitaria** de cada uno.

    Es la mitad «a» del horneado: la verdad que se quiere meter en el mapa. La normal
    sale del proveedor y no se recalcula aqui a proposito: es la malla densa, con la
    que se va a comparar, y dos normales suaves distintas de la misma malla darian dos
    mapas que no se pueden comparar entre si.

    Y se normaliza porque el proveedor las da ponderadas por area y **sin normalizar**
    —medido el 2026-09-16 sobre la malla del banco de pruebas: longitud media 6,05—.
    Una normal de longitud seis metida en un mapa tangente da un vector de longitud
    seis, y el angulo que la etapa publica saldria de dividir un vector largo entre uno
    corto: un numero plausible y falso.
    """
    import numpy as np

    exigir()
    conjunto = _conjunto(ruta)
    malla = getattr(conjunto, "current_mesh")()  # noqa: B009 - API externa
    normales = np.array(malla.vertex_normal_matrix(), dtype="float64")
    longitudes = np.linalg.norm(normales, axis=1)
    fuera = longitudes > 0
    normales[fuera] = normales[fuera] / longitudes[fuera, None]
    return np.array(malla.vertex_matrix(), dtype="float64"), normales


def hornear_colores(
    coloreada: pathlib.Path,
    destino: pathlib.Path,
    *,
    resolucion: int,
    pullpush: bool,
) -> Horneado:
    """Hornea el color por vertice de una malla sobre su propio atlas, y lo relee.

    La malla que entra tiene que traer **las UV y el color en el mismo fichero**: es lo
    que el proveedor necesita para escribir el atlas, y es la razon de ser de
    `formatos/obj.py`. El color no se interpreta aqui —es un vector codificado en
    R,G,B— y por eso esta funcion no sabe de normales ni de marcos: eso es de la etapa
    que la llama.

    `pullpush` rellena los texeles que ningun triangulo toca con lo que tienen al lado.
    Es una decision declarada y no un detalle: sin él esos texeles se quedan con el valor
    de la textura de partida, y lo que hay en ellos no es superficie de nadie. Va en el
    informe con ese nombre.
    """

    exigir()
    if resolucion < 1:
        raise ValueError(f"la resolucion del mapa es un lado en texeles y es {resolucion}")

    conjunto = _conjunto(coloreada)
    malla = getattr(conjunto, "current_mesh")()  # noqa: B009 - API externa
    if not malla.has_vertex_color():
        raise ErrorDeProveedor(
            f"{coloreada} no trae color por vertice: el horneado lee el color de la malla y "
            "escribe el atlas con él"
        )
    if not malla.has_wedge_tex_coord():
        raise ErrorDeProveedor(
            f"{coloreada} no trae coordenadas de textura: sin atlas no hay donde hornear"
        )

    getattr(conjunto, "set_texture_per_mesh")(  # noqa: B009 - API externa
        use_dummy_texture=True, dummy_img_size=resolucion
    )
    getattr(conjunto, "transfer_attributes_to_texture_per_vertex")(  # noqa: B009
        sourcemesh=0,
        targetmesh=0,
        attributeenum="Vertex Color",
        textname=destino.name,
        textw=resolucion,
        texth=resolucion,
        overwrite=True,
        pullpush=pullpush,
    )
    imagenes = list(malla.textures().values())
    if not imagenes:
        raise ErrorDeProveedor(
            "el proveedor horneo y no dejo ninguna imagen: no hay mapa que publicar"
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    imagenes[0].save(str(destino))

    # Y el mapa se lee **de vuelta**, en el baricentro de cada triangulo: es la unica
    # forma de decir cuanto del vector que se pidio llego al fichero sin escribir aqui un
    # lector de textura. La rejilla de baricentros es una malla con un vertice por cara
    # —su posicion es el baricentro y su UV la media de las tres esquinas— y con caras
    # porque el filtro las exige: lo que se lee es el texel de cada vertice, y eso esta
    # comprobado con un campo conocido en vez de supuesto.
    return Horneado(
        resolucion=resolucion,
        colores_de_vuelta=_leer_el_mapa_en_los_baricentros(coloreada, mapa=destino),
    )


def _leer_el_mapa_en_los_baricentros(coloreada: pathlib.Path, *, mapa: pathlib.Path) -> Any:
    """El color del mapa en el baricentro de cada triangulo de la malla horneada."""
    import numpy as np

    conjunto = _conjunto(coloreada)
    malla = getattr(conjunto, "current_mesh")()  # noqa: B009 - API externa
    caras = np.array(malla.face_matrix(), dtype="int64")
    vertices = np.array(malla.vertex_matrix(), dtype="float64")
    uv = np.array(malla.vertex_tex_coord_matrix(), dtype="float64")
    puntos = vertices[caras].mean(axis=1)
    centros = uv[caras].mean(axis=1)

    lineas = [f"v {p[0]:.9g} {p[1]:.9g} {p[2]:.9g}" for p in puntos]
    lineas += [f"vt {t[0]:.9g} {t[1]:.9g}" for t in centros]
    cuantos = len(puntos)
    lineas += [
        f"f {i + 1}/{i + 1} {(i + 1) % cuantos + 1}/{(i + 1) % cuantos + 1} "
        f"{(i + 2) % cuantos + 1}/{(i + 2) % cuantos + 1}"
        for i in range(cuantos)
    ]
    rejilla = mapa.parent / "_baricentros.obj"
    rejilla.write_text("\n".join(lineas) + "\n", encoding="ascii")
    try:
        lectura = _conjunto(rejilla)
        # Por `getattr`, como el resto del modulo: el analisis de tipos no ve la API del
        # proveedor —es de C++— y una llamada directa sale como un atributo de `object`.
        getattr(lectura, "set_texture_per_mesh")(textname=str(mapa))  # noqa: B009
        getattr(lectura, "transfer_texture_to_color_per_vertex")(  # noqa: B009 - API externa
            sourcemesh=0, targetmesh=0
        )
        leida = getattr(lectura, "current_mesh")()  # noqa: B009 - API externa
        return np.array(leida.vertex_color_matrix(), dtype="float64")[:, :3]
    finally:
        rejilla.unlink(missing_ok=True)


def a_obj(origen: pathlib.Path, destino: pathlib.Path) -> None:
    """Escribe la malla como OBJ, que es el formato que lee `diffMeshes` hoy."""
    exigir()
    conjunto = _conjunto(origen)
    _escribir(conjunto, destino)


#: La anotacion va entre comillas para que el nombre de numpy **no** se evalue al
#: definir la funcion: el import vive bajo `TYPE_CHECKING` y en tiempo de ejecucion no
#: existe, que es justo lo que mantiene a `doctor` funcionando sin el extra `malla`.
def a_arreglos(ruta: pathlib.Path) -> "tuple[NDArray[Any], NDArray[Any]]":
    """Los vertices y las caras como arreglos, que es lo que pide el cortador de UV.

    Los lee el proveedor de malla —es el que sabe leer los PLY que el mismo
    escribe— y se devuelven en el orden en que los pide quien los pide, para que el
    cortador no tenga que saber de formatos. numpy se importa aqui dentro y no
    arriba: `doctor` importa este modulo en un entorno donde el extra `malla` puede
    no estar puesto, y no tiene por que fallar por eso.

    Una malla con caras que no son triangulos se rechaza **con su nombre**: cortar
    un poligono no es cortar tres triangulos, y adivinar la triangulacion seria
    tomar una decision de geometria donde solo hace falta un mensaje.

    El `MeshSet` se guarda en una variable **antes** de pedirle la malla, y no es
    estilo: `current_mesh()` devuelve una vista sobre el objeto de C++, asi que si el
    conjunto se queda sin ninguna referencia la vista se lee vacia. Medido el
    2026-09-16 con un cubo de 98 vertices: con el conjunto vivo, 98; sin el, 0 — y sin
    un error, que es lo que lo hace peligroso.
    """
    import numpy as np

    exigir()
    conjunto = _conjunto(ruta)
    malla = getattr(conjunto, "current_mesh")()  # noqa: B009 - API externa
    vertices = np.array(malla.vertex_matrix(), dtype="<f4")
    caras = np.array(malla.face_matrix(), dtype="<u4")
    if caras.ndim != 2 or caras.shape[1] != 3:
        raise ErrorDeProveedor(
            f"{ruta} trae caras que no son triangulos ({caras.shape[1] if caras.ndim == 2 else 0} "
            "vertices por cara): esta cadena corta triangulos, y triangulizar es una decision que "
            "no se toma aqui"
        )
    return vertices, caras
