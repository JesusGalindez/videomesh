"""`videomesh next` — encargo 04, bloque F. Dice qué rehacer, y **para** cuando toca.

Cuando la publicación dice `UNKNOWN` o `NOT_PRODUCTION_READY`, alguien tiene que decidir
qué etapa rehacer. Puede decidirlo un agente, y puede decidirlo **porque el informe emite
números y no notas**: cada fallo nombra la medida, su valor y su sitio. Eso es lo que
esta etapa lee, y lo que escribe es una línea por fallo:

```text
triangulos 180000 > 60000 del destino web   → videomesh decimado --objetivo 60000
UV solapadas en 0.31 del area               → videomesh uv --margen 8
un nivel se sale de la silueta              → videomesh lod --niveles 3
```

**No lo ejecuta.** Dice qué haría. Un agente lo lee y decide; una persona también. Lo
único que escribe es su propio intento, en el registro del bucle —una nota de qué
propuso y qué valía el asset entonces—, y eso no es ejecutar una etapa.

**El techo (F2) es obligatorio**, porque un bucle que reintenta sin límite acaba
decimando a cero para cumplir un presupuesto. Son dos reglas:

```text
un maximo de vueltas, declarado
si una vuelta no mejora la medida que la motivo, PARA y lo dice
```

Y el freno que las sostiene es **la distancia de superficie contra la malla medida**,
que se publica en cada etapa desde B2. Una vuelta que mejora los triángulos y empeora
esa distancia para el bucle con los dos números delante: bajar triángulos hasta pasar la
puerta habiendo destruido el objeto es exactamente el desastre silencioso que esto
impide, y seguir a partir de ahí es una decisión de quien lee —`next --olvidar`—, no un
descuido de la máquina.

Lo que este módulo **no** hace es juzgar si un fallo es grave: copia los veredictos del
vecino y los traduce a una etapa y un parámetro. Los criterios son suyos.
"""

import pathlib
from dataclasses import dataclass, field
from typing import Any

from videomesh.adapters import xatlas
from videomesh.application import (
    cadena,
    decimado,
    glb_final,
    lod,
    normales,
    perfiles,
    publicacion,
    uv,
)
from videomesh.application.cadena import Situacion
from videomesh.application.densa import ETAPA as DENSA
from videomesh.project.bucle import Intento, anotar_intento, intentos_de, olvidar_intentos
from videomesh.project.informe import leer_informe

__all__ = [
    "Decision",
    "MAX_VUELTAS",
    "Rehacer",
    "decidir",
    "propuestas",
]

#: El máximo de vueltas que se intentan sin que nadie lo diga. Se declara —no se
#: descubre al agotarse— y es un número pequeño a propósito: cada vuelta cuesta una
#: etapa entera y su auditoría, y a la tercera sin mejora lo que falta no es otra vuelta.
MAX_VUELTAS = 3

#: Las etapas que **pierden geometría**. Son las únicas donde el freno de la distancia
#: tiene sentido: una vuelta de UV o de material no mueve un vértice, y su distancia no
#: dice nada de lo que costó.
_CON_PERDIDA = (decimado.ETAPA, lod.ETAPA, "limpieza")

#: El camino a la publicación, en el orden de la cadena. Lo que `next` propone cuando
#: todavía no hay nada que juzgar es la primera de estas que toca, y no cualquier otra:
#: los niveles de detalle y el proxy de colisión los pide **el destino** cuando los
#: quiere, y sin publicación no hay destino que lo diga. No se esconden —`status` los
#: enseña a todos, con su estado—: simplemente no son lo que falta para publicar.
_CAMINO_A_LA_PUBLICACION = (
    DENSA,
    "limpieza",
    decimado.ETAPA,
    uv.ETAPA,
    normales.ETAPA,
    glb_final.ETAPA,
    publicacion.ETAPA,
)

#: La bandera de la CLI para cada parámetro del registro de etapas. Lo que no está aquí
#: no se puede escribir como comando, y por eso no se inventa: se dice con su motivo.
_BANDERAS: dict[str, str] = {
    "objetivo": "--objetivo",
    "margen": "--margen",
    "iteraciones": "--iteraciones",
    "solape_maximo": "--solape-maximo",
    "niveles": "--niveles",
    "destino": "--destino",
    "resolucion": "--resolucion",
    "minimo_relativo": "--minimo-relativo",
}

#: Qué se dice de cada comprobación del `readiness` del vecino cuando no pasa. Las que
#: no están aquí se publican con su motivo y sin comando: una línea que no propone nada
#: es mejor que una que proponga la etapa equivocada.
_TOPE_QUE_DECLARA = {
    "tope-de-textura": "el lado maximo de su textura",
    "tope-de-silueta": "el tope de silueta de sus niveles",
    "tope-de-holgura": "el tope de holgura de su proxy",
    "exigencia-de-uv": "si exige coordenadas de textura",
}

#: Comparaciones con números medidos: por debajo de esto, dos cifras son la misma.
_EPSILON = 1e-12


@dataclass(frozen=True)
class Rehacer:
    """Un fallo y lo que lo arreglaría, con la medida que lo dice."""

    medida: str
    valor: float | None
    limite: float | None
    etapa: str
    parametros: dict[str, Any] = field(default_factory=dict)
    motivo: str = ""

    def comando(self, proyecto: pathlib.Path) -> str:
        """La orden que haría esto, con la ruta del proyecto delante.

        Se escribe y **no se ejecuta**: es lo que el agente lee para decidir, y una
        orden que no se puede copiar a la terminal no sirve para eso.
        """
        partes = ["videomesh", self.etapa, str(proyecto)]
        for clave, valor in self.parametros.items():
            bandera = _BANDERAS.get(clave)
            if bandera is None:
                continue
            if isinstance(valor, dict):  # un destino viaja con su forma entera
                valor = valor.get("preset")
            if valor is None:
                continue
            if isinstance(valor, list):
                valor = ",".join(str(x) for x in valor)
            partes += [bandera, str(valor)]
        return " ".join(partes)

    def linea(self, proyecto: pathlib.Path) -> str:
        """La línea que se imprime: qué se midió, qué tope se pasó y qué lo arregla."""
        if self.valor is None or self.limite is None:
            medida = self.motivo
        else:
            medida = f"{self.medida} {self.valor:g} > {self.limite:g} · {self.motivo}"
        return f"{medida}  → {self.comando(proyecto)}"


@dataclass(frozen=True)
class Decision:
    """Qué rehacer, si algo, y si el bucle debe parar y por qué."""

    rehacer: tuple[Rehacer, ...]
    parada: str | None
    vueltas: int


def _valor_de(medida: str, proyecto: pathlib.Path) -> float | None:
    """El valor de ahora de esa medida, leído del informe del vecino. `None` si no es numérica.

    Una medida que no se puede leer no se compara: el bucle queda entonces sujeto solo
    al techo de vueltas, que es lo honesto —decir que mejoró sin poder medirlo sería el
    tipo de afirmación que este repositorio no hace—.
    """
    informe = publicacion.informe_del_vecino(proyecto)
    if informe is None:
        return None
    if medida == "triangulos":
        for presupuesto in informe.get("budgets") or []:
            if presupuesto.get("name") == "triangulos" and presupuesto.get("observed") is not None:
                return float(presupuesto["observed"])
        for medicion in informe.get("measurements") or []:
            if medicion.get("triangles") is not None:
                return float(medicion["triangles"])
        return None
    if medida == "silueta":
        peores = [
            max(
                float(
                    (nivel.get("silhouette") or {}).get("worstMissing", {}).get("missingRatio", 0)
                ),
                float((nivel.get("silhouette") or {}).get("worstExtra", {}).get("extraRatio", 0)),
            )
            for nivel in informe.get("lods") or []
        ]
        return max(peores) if peores else None
    if medida == "uv-solape":
        ratios = [
            float((medicion.get("uv") or {}).get("overlapRatio", 0))
            for medicion in informe.get("measurements") or []
        ]
        return max(ratios) if ratios else None
    return None


def _distancia_contra_la_medida(proyecto: pathlib.Path) -> float | None:
    """La peor distancia publicada contra la malla medida por las etapas que deciman.

    Es el freno de F2, y se lee **del informe**, no se recalcula: la cifra que ya está
    publicada es la que el bucle está mirando, y recalcularla daría otra.
    """
    peores: list[float] = []
    informe = leer_informe(proyecto, decimado.ETAPA)
    if informe is not None:
        medida = (informe.get("medidas") or {}).get("distancia_contra_la_malla_medida") or {}
        falta = (medida.get("falta") or {}).get("maximo")
        if falta is not None:
            peores.append(float(falta))
    niveles = leer_informe(proyecto, lod.ETAPA)
    if niveles is not None:
        for nivel in (niveles.get("medidas") or {}).get("niveles") or []:
            distancia = (
                (nivel.get("distancia_contra_la_malla_medida") or {}).get("falta") or {}
            ).get("maximo")
            if distancia is not None:
                peores.append(float(distancia))
    return max(peores) if peores else None


def _de_la_cadena(proyecto: pathlib.Path) -> list[Rehacer]:
    """Lo primero que **toca** cuando todavía no hay nada que juzgar.

    Sin publicación no hay auditoría que leer, así que lo que falta es la etapa: la
    primera en el orden de la cadena cuyas entradas ya están.
    """
    for paso in cadena.estado_de_la_cadena(proyecto):
        if paso.situacion is not Situacion.TOCA:
            continue
        if paso.etapa not in _CAMINO_A_LA_PUBLICACION:
            continue
        return [
            Rehacer(
                medida=paso.etapa,
                valor=None,
                limite=None,
                etapa=paso.etapa,
                parametros=dict(cadena.DEFECTOS_POR_DEFECTO.get(paso.etapa, {})),
                motivo=paso.motivo,
            )
        ]
    return []


def _de_la_publicacion(proyecto: pathlib.Path) -> list[Rehacer] | None:
    """Los fallos de la última publicación, traducidos a etapa y parámetro.

    `None` cuando no hay publicación que leer: eso lo distingue de «hay publicación y no
    falla nada», que es una respuesta distinta y no se pueden confundir.
    """
    informe = leer_informe(proyecto, publicacion.ETAPA)
    vecino = publicacion.informe_del_vecino(proyecto)
    if informe is None or vecino is None:
        return None
    destino = str((informe.get("medidas") or {}).get("destino", ""))
    propuestas: list[Rehacer] = []

    # 1. Los presupuestos que se pasan. Es el fallo que el encargo pone de ejemplo, y el
    #    único que tiene un parámetro exacto: el tope del destino es el objetivo.
    for presupuesto in vecino.get("budgets") or []:
        if presupuesto.get("verdict") != "FAIL":
            continue
        nombre = str(presupuesto.get("name"))
        observado = float(presupuesto.get("observed") or 0)
        maximo = float(presupuesto.get("max") or 0)
        if nombre == "triangulos":
            propuestas.append(
                Rehacer(
                    medida=nombre,
                    valor=observado,
                    limite=maximo,
                    etapa=decimado.ETAPA,
                    parametros={"objetivo": int(maximo)},
                    motivo=f"el destino {destino} no admite mas de {maximo:g} triangulos",
                )
            )
        else:
            propuestas.append(
                Rehacer(
                    medida=nombre,
                    valor=observado,
                    limite=maximo,
                    etapa="",
                    motivo=(
                        f"el destino {destino} no admite mas de {maximo:g} de {nombre}, y ninguna "
                        "etapa de esta cadena baja esa medida"
                    ),
                )
            )

    # 2. Los niveles de detalle fuera de tolerancia. Menos niveles es lo que se puede
    #    hacer aquí; el tope lo puso el destino y no se toca.
    niveles = vecino.get("lods") or []
    malos = [nivel for nivel in niveles if "FAIL" in (nivel.get("verdicts") or {}).values()]
    if malos:
        actuales = max(len(niveles) - 1, 1)
        propuestas.append(
            Rehacer(
                medida="silueta",
                valor=_valor_de("silueta", proyecto),
                limite=None,
                etapa=lod.ETAPA,
                parametros={"niveles": actuales},
                motivo=(
                    f"el nivel {malos[0].get('level')} se sale del presupuesto del destino: "
                    f"con {actuales} niveles, cada uno baja menos"
                ),
            )
        )

    # 3. Las UV que se pisan. Subir el margen es lo que esta cadena puede hacer, y el
    #    margen de ahora se lee del informe de la etapa de UV.
    if any(
        ((medicion.get("uvVerdicts") or {}).get("overlap") == "FAIL")
        for medicion in vecino.get("measurements") or []
    ):
        parametros_uv = (leer_informe(proyecto, uv.ETAPA) or {}).get("parametros") or {}
        margen = float(parametros_uv.get("margen", xatlas.MARGEN_POR_DEFECTO))
        propuestas.append(
            Rehacer(
                medida="uv-solape",
                valor=_valor_de("uv-solape", proyecto),
                limite=None,
                etapa=uv.ETAPA,
                parametros={"margen": int(margen * 2)},
                motivo=f"las islas se pisan con un margen de {margen:g}: el doble los separa",
            )
        )

    # 4. Un mapa que no parece lo que dice ser. Se rehornea a la misma resolución: lo que
    #    falla es el contenido, no el tamaño.
    for textura in vecino.get("textures") or []:
        if not textura.get("reason"):
            continue
        parametros_normales = (leer_informe(proyecto, normales.ETAPA) or {}).get("parametros") or {}
        propuestas.append(
            Rehacer(
                medida=str(textura.get("artifactId")),
                valor=None,
                limite=None,
                etapa=normales.ETAPA,
                parametros={"resolucion": int(parametros_normales.get("resolucion", 0)) or None},
                motivo=f"el vecino dice de esa textura: {textura['reason']}",
            )
        )

    # 5. Los materiales declarados que se contradicen con el manifiesto.
    if vecino.get("materialIssues"):
        propuestas.append(
            Rehacer(
                medida="material",
                valor=None,
                limite=None,
                etapa="material",
                parametros={},
                motivo="; ".join(
                    str(problema.get("message") or problema.get("reason"))
                    for problema in vecino["materialIssues"][:3]
                ),
            )
        )

    # 6. Lo que el `readiness` deja sin declarar o sin poder comprobar. Es de quien
    #    publica, y por eso lo que se propone es volver a publicar con un destino que lo
    #    declare — o, cuando lo que falta es una comprobación, la etapa que la produce.
    readiness = vecino.get("readiness") or {}
    for comprobacion in readiness.get("checks") or []:
        identificador = str(comprobacion.get("id"))
        estado = comprobacion.get("state")
        if estado not in ("FAIL", "NOT_RUN") or identificador == "medidas-del-asset":
            continue
        if identificador in _TOPE_QUE_DECLARA:
            propuestas.append(
                Rehacer(
                    medida=identificador,
                    valor=None,
                    limite=None,
                    etapa=publicacion.ETAPA,
                    parametros={
                        "destino": perfiles.destino_de_reparto(perfiles.DESTINO_POR_DEFECTO)
                    },
                    motivo=(
                        f"el destino {destino} no declara {_TOPE_QUE_DECLARA[identificador]}: "
                        "sin declararlo no hay aprobacion posible (R15)"
                    ),
                )
            )
            continue
        if identificador == "validador-externo":
            propuestas.append(
                Rehacer(
                    medida=identificador,
                    valor=None,
                    limite=None,
                    etapa=publicacion.ETAPA,
                    parametros={
                        "destino": perfiles.destino_de_reparto(perfiles.DESTINO_POR_DEFECTO)
                    },
                    motivo=(
                        "no hay informe de un validador externo que ingerir: sin el, «este GLB "
                        "es valido» es algo que nadie comprobo"
                    ),
                )
            )
            continue
        if identificador == "contencion":
            propuestas.append(
                Rehacer(
                    medida=identificador,
                    valor=None,
                    limite=None,
                    etapa="colision",
                    parametros={},
                    motivo=str(comprobacion.get("reason") or ""),
                )
            )

    # Si el asset suspendió y nada de lo anterior lo explica, se dice lo que el vecino
    # dijo, sin proponer una etapa que quizá no sea: una línea sin comando es mejor que
    # una que proponga la equivocada.
    if not propuestas:
        for comprobacion in readiness.get("checks") or []:
            if comprobacion.get("state") in ("FAIL", "NOT_RUN"):
                propuestas.append(
                    Rehacer(
                        medida=str(comprobacion.get("id")),
                        valor=None,
                        limite=None,
                        etapa="",
                        parametros={},
                        motivo=str(comprobacion.get("reason") or ""),
                    )
                )
    return propuestas


def propuestas(proyecto: pathlib.Path) -> tuple[Rehacer, ...]:
    """Qué habría que rehacer ahora mismo, en el orden en que conviene mirarlo."""
    de_la_publicacion = _de_la_publicacion(proyecto)
    if de_la_publicacion is not None:
        return tuple(de_la_publicacion)
    return tuple(_de_la_cadena(proyecto))


def decidir(
    proyecto: pathlib.Path, *, vueltas: int = MAX_VUELTAS, olvidar: bool = False
) -> Decision:
    """La decisión completa: qué rehacer, o por qué para.

    El registro se mira **antes** de proponer nada: el techo y el freno mandan sobre
    cualquier propuesta, que es lo que los hace un techo y no un aviso.
    """
    ruta = pathlib.Path(proyecto)
    if olvidar:
        olvidar_intentos(ruta)

    hechos = intentos_de(ruta)
    if len(hechos) >= vueltas:
        return Decision(
            (),
            (
                f"se han agotado las {vueltas} vueltas declaradas y el asset sigue sin pasar: "
                "para y dimelo, que insistir no es lo que falta"
            ),
            len(hechos),
        )

    pendientes = propuestas(ruta)
    if not pendientes:
        return Decision((), None, len(hechos))

    # Las dos reglas del techo, y en este orden: primero la medida que motivó la vuelta
    # anterior, y después el freno de la distancia.
    anterior = hechos[-1] if hechos else None
    if anterior is not None:
        actual = _valor_de(anterior.medida, ruta)
        if (
            actual is not None
            and anterior.valor is not None
            and actual >= anterior.valor - _EPSILON
        ):
            return Decision(
                (),
                (
                    f"la vuelta {len(hechos)} no mejoro {anterior.medida}: "
                    f"{anterior.valor:g} antes, {actual:g} ahora. Para"
                ),
                len(hechos),
            )
        if anterior.etapa in _CON_PERDIDA and anterior.distancia is not None:
            distancia = _distancia_contra_la_medida(ruta)
            if distancia is not None and distancia > anterior.distancia + _EPSILON:
                return Decision(
                    (),
                    (
                        "la distancia contra la malla medida empeoro: "
                        f"{anterior.distancia:g} antes, {distancia:g} ahora. Seguir desde aqui "
                        "es bajar triangulos habiendo destruido el objeto, y es una decision de "
                        "quien lee: `next --olvidar`"
                    ),
                    len(hechos),
                )

    primera = pendientes[0]
    anotar_intento(
        ruta,
        Intento(
            medida=primera.medida,
            valor=primera.valor,
            limite=primera.limite,
            etapa=primera.etapa,
            parametros=dict(primera.parametros),
            distancia=_distancia_contra_la_medida(ruta),
        ),
    )
    return Decision(tuple(pendientes), None, len(hechos) + 1)
