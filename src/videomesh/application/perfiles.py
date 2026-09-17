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

from typing import Any

from videomesh.domain.errores import ErrorDeVideoMesh

__all__ = ["PERFIL_POR_DEFECTO", "PERFILES", "destino_declarado", "perfil_de"]

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
