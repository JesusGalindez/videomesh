"""Los perfiles de destino — encargo 04, E1.

Un asset «bueno» no existe en abstracto. Existe **bueno para web** o **bueno para
juego**, y son topes distintos; aqui viven los dos primeros, y **no se inventan:
estan medidos** — el 2026-09-15, sobre un GLB de Hunyuan3D de 88,6 MB y 1.500.086
triangulos, con `gltfpack` 1.2 binario nativo:

```text
perfil  triangulos  textura    fichero   distancia contra el original
hero        90.004  KTX2 2048  4,08 MB   0,089 % de la diagonal (max)
fondo       23.288  KTX2 1024  0,72 MB   no medida
```

Los presupuestos se declaran **en el vocabulario del vecino** — los nombres de
`BUDGET_TERMS`, las unidades `ABSOLUTE` y `RELATIVE_TO_DIAGONAL` — porque su
`evaluateBudgets` es el que los juzga. Un nombre que no conoce deja el veredicto en
NO_EVALUADO, que es peor que no declararlo.

**La regla de R15 es la que justifica este modulo**: un destino que no declara nada
no obtiene PRODUCTION_READY — el asset mas vacio seria el mas listo. No declarar no
es no pedir: es dejar los topes sin juzgar, y un asset entero sin juzgar no esta
listo. El caso rojo de este modulo esta en su prueba: un asset con textura y un
destino mudo sale `UNKNOWN · tope-de-textura: NOT_RUN · EL_DESTINO_NO_LO_DECLARA`,
y con el perfil declarado ese mismo tope se juzga.

Un perfil declara **solo lo que midio**: el hero declara su tope de triangulos y el
lado de su textura; la distancia contra el original es un numero del viaje, no un
tope del destino, y el dia que se mida la del fondo, se declara la del fondo.
"""

from dataclasses import dataclass, field
from typing import Any

from videomesh.domain.errores import ErrorDeVideoMesh

__all__ = [
    "DESTINOS",
    "DESTINO_POR_DEFECTO",
    "PERFIL_POR_DEFECTO",
    "PERFILES",
    "PIEZAS_POR_DEFECTO",
    "PIEZA_MAESTRA",
    "PIEZA_MAPA",
    "PIEZA_REPARTO",
    "Destino",
    "destino_de_reparto",
    "destino_declarado",
    "destino_publicado",
    "perfil_de",
    "piezas_de_reparto",
]

#: El tope de triangulos del hero: lo que dejo `-si 0.06` sobre el GLB de 1.500.086.
_TOPE_HERO = 90_004

#: El del fondo, con `-si 0.015`. Menos de la sexta parte del hero.
_TOPE_FONDO = 23_288

#: El lado del mapa que se midio en cada perfil, en texeles.
_LADO_HERO = 2048
_LADO_FONDO = 1024


def _perfil(nombre: str, *, triangulos: int, lado: int) -> dict[str, Any]:
    """El `target` de un perfil, en el vocabulario del vecino.

    Los presupuestos van con su nombre y su unidad; los topes de textura van en su
    campo. Lo que no se midio no se declara: un tope inventado seria una promesa
    nueva disfrazada de medida.
    """
    return {
        "preset": nombre,
        "budgets": [
            {"name": "triangulos", "units": "ABSOLUTE", "max": triangulos},
        ],
        "textureMaxSize": lado,
        "texturePowerOfTwo": True,
    }


#: Los dos perfiles medidos. Ni uno mas: el dia que se mida el de juego, se declara.
PERFILES: dict[str, dict[str, Any]] = {
    "hero": _perfil("hero", triangulos=_TOPE_HERO, lado=_LADO_HERO),
    "fondo": _perfil("fondo", triangulos=_TOPE_FONDO, lado=_LADO_FONDO),
}

#: El que se usa cuando nadie dice otro. El hero es el perfil de mas detalle de los dos,
#: y el defecto tiene que ser el que **mas** pide: un asset empaquetado de mas se puede
#: bajar despues, y uno empaquetado de menos ya perdio lo que no estaba.
PERFIL_POR_DEFECTO = "hero"


def perfil_de(nombre: str) -> dict[str, Any]:
    """El perfil pedido, o un error que nombra los que hay."""
    perfil = PERFILES.get(nombre)
    if perfil is None:
        raise ErrorDeVideoMesh(
            f"no hay perfil {nombre!r}: los declarados son {', '.join(sorted(PERFILES))}. "
            "Un perfil no medido no se declara"
        )
    return perfil


def destino_declarado(nombre: str) -> dict[str, Any]:
    """El destino completo del perfil, listo para el manifiesto de produccion.

    Es una copia: el perfil es del modulo y el `target` del asset es de la etapa que
    lo declara — que una etapa mute su copia no debe cambiar lo que el perfil dice.
    """
    import copy

    devuelto: dict[str, Any] = copy.deepcopy(perfil_de(nombre))
    return devuelto


#: Las identidades de las piezas que un destino puede pedir. Son las mismas palabras
#: que el manifiesto usa para citarlas, y por eso no se inventa un tercer vocabulario:
#: `maestra` es el artifact de la malla, `mapa` la textura y `reparto` la variante
#: empaquetada con KTX2 que viaja al motor.
PIEZA_MAESTRA = "maestra"
PIEZA_MAPA = "mapa"
PIEZA_REPARTO = "reparto"


@dataclass(frozen=True)
class Destino:
    """Un destino de reparto: qué perfil lo mide, qué piezas publica y qué declara.

    Los tres campos son la respuesta a las tres preguntas del bloque E, y el tercero
    es el que R15 vigila: **un destino que no declara nada no aprueba**. Lo que un
    asset trae decide qué declaraciones le hacen falta, así que `declara` solo lleva
    los topes de lo que `piezas` publica — declarar el tope de silueta de una entrega
    sin niveles de detalle dejaría un `PASS` sobre algo que no existe.
    """

    nombre: str
    perfil: str
    piezas: tuple[str, ...]
    declara: dict[str, Any] = field(default_factory=dict)


#: Los destinos declarados. Uno, y con su motivo escrito: el encargo pide `web`, que
#: es lo que describe su caja de E1 —triángulos bajos, textura comprimida y **un solo
#: fichero**—, y el que pide varios LOD y proxy de colisión se declarará el día que
#: sus topes se midan, porque un tope de silueta inventado aprueba o rechaza por un
#: número que nadie eligió.
DESTINOS: dict[str, Destino] = {
    "web": Destino(
        nombre="web",
        perfil="hero",
        # Un solo fichero: la maestra auditada, su mapa y la variante de reparto. Los
        # niveles y el proxy son de la entrega de juego, y no se publican aquí.
        piezas=(PIEZA_MAESTRA, PIEZA_MAPA, PIEZA_REPARTO),
        # R15 y R13: el asset trae coordenadas de textura y un mapa que se lee **contra
        # ellas**, así que el destino las exige. Sin declararlo, su readiness deja
        # `exigencia-de-uv` en `EL_DESTINO_NO_LO_DECLARA` y no hay aprobación.
        declara={"uvRequired": True},
    ),
}


#: Lo que se publica cuando el destino no dice su forma: la maestra, su mapa y la
#: variante de reparto. Es el mínimo de una entrega, y no depende de ningún perfil: un
#: destino que no se declara no puede decidir qué se publica, pero la publicación sigue
#: teniendo que decir qué lleva.
PIEZAS_POR_DEFECTO: tuple[str, ...] = (PIEZA_MAESTRA, PIEZA_MAPA, PIEZA_REPARTO)


#: El destino que se publica cuando nadie dice otro. Es el del encargo —`videomesh
#: publish --destino web`— y el único con sus topes medidos.
DESTINO_POR_DEFECTO = "web"


def piezas_de_reparto(nombre: str) -> tuple[str, ...]:
    """Qué piezas publica ese destino, o las mínimas si no es un destino declarado."""
    destino = DESTINOS.get(nombre)
    return destino.piezas if destino is not None else PIEZAS_POR_DEFECTO


def destino_publicado(nombre: str) -> Destino:
    """El destino de reparto pedido, o un error que nombra los declarados."""
    destino = DESTINOS.get(nombre)
    if destino is None:
        raise ErrorDeVideoMesh(
            f"no hay destino {nombre!r}: los declarados son {', '.join(sorted(DESTINOS))}. "
            "Un destino sin sus topes medidos no se declara"
        )
    return destino


def destino_de_reparto(nombre: str) -> dict[str, Any]:
    """El `target` del manifiesto de publicación: el perfil, con lo que el destino declara.

    El `preset` es el nombre del destino y no el del perfil, porque es lo que se pidió
    y lo que el informe del vecino va a citar; el perfil del que salen los números
    viaja en el informe de la etapa, que es donde se puede leer de dónde vienen.
    """
    destino = destino_publicado(nombre)
    objetivo = destino_declarado(destino.perfil)
    objetivo["preset"] = destino.nombre
    objetivo.update(destino.declara)
    return objetivo
