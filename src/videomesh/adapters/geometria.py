"""La geometria que el horneado resuelve aqui, y por que no esta fuera — bloque D.

El encargo deja una decision abierta y pide escribirla: el horneado se hace aqui en
Python o se llama al trazador de rayos del vecino por el puente. La decision tomada
es **ninguna de las dos a medias, sino las dos mitades donde cada una vive**:

```text
la correspondencia   aqui: que punto de la malla medida le toca a cada vertice
la rasterizacion     en el proveedor: pymeshlab escribe los texeles del atlas
la medida            en el vecino: su diff mide y su R13 juzga el mapa
```

**No se reimplementa el trazador de rayos.** Lo que se hace aqui es un vecino mas
cercano sobre los vertices de la malla medida, que es la operacion que el horneado
necesita de verdad: cada vertice de la malla de trabajo busca el vertice mas cercano
de la densa y se queda con su normal. No es un trazador —no hay rayo ni cara, hay un
vertice— y por eso tampoco hay dos trazadores que puedan discrepar.

**La rasterizacion no se hace aqui** porque hacerla en Python texel a texel sobre una
malla de un millon y medio de triangulos es justo lo que el proveedor hace en C++, y
su filtro ya esta probado: se le dan los vectores por vertice y él los escribe en el
atlas. Lo que se le da es un **color** por vertice, y esa es la unica conversion que
el horneado hace por su cuenta.

**La aproximacion esta declarada y medida.** El vecino es un vertice y no el punto
mas cercano de una cara, asi que el error depende de lo juntos que esten los vertices
de la medida: en una malla de reconstruccion de un millon y medio de triangulos el
paso es de decimas de milimetros, por debajo del texel de un atlas de 2048, y en una
malla dispersa puede no serlo. El informe publica las dos cosas: el paso mediano
entre vertices vecinos de la medida, y el texel del atlas, para que la aproximacion se
pueda juzgar con numeros en vez de con la palabra «despreciable».

El vecino se prueba **contra fuerza bruta**: la rejilla que acelera la consulta tiene
que devolver exactamente lo mismo que recorrer los puntos uno a uno, y hay una prueba
que lo comprueba sobre una nube con la rejilla mal centrada a proposito.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from videomesh.domain.errores import ErrorDeProveedor

if TYPE_CHECKING:  # pragma: no cover - solo para el analisis de tipos
    from numpy.typing import NDArray

__all__ = [
    "Vecindad",
    "Vecinos",
    "es_marco",
    "marcos_de_uv",
    "medir_paso_de_la_malla",
    "normales_de_vertice",
]


@dataclass(frozen=True)
class Vecinos:
    """Lo que devuelve una consulta de vecindad, con lo que hay que declarar de ella.

    `sin_orientacion` cuenta las consultas que no encontraron ningun punto que mirase
    hacia el mismo lado y se quedaron con el mas cercano: son las que pueden haber
    cruzado una pared delgada, y por eso se publican en vez de esconderse en el exito de
    las demas.
    """

    indices: Any
    distancias: Any
    sin_orientacion: int


class Vecindad:
    """El vertice mas cercano de una nube, con una rejilla que es una consulta y no un resultado.

    La rejilla se guarda **ordenada por celda**, no en un diccionario de listas, y se
    consulta con `searchsorted`: asi el indice es memoria contigua y una nube de un
    millon y medio de puntos no se convierte en un millon y medio de objetos de
    Python, que es lo que hace que la etapa se pueda correr en esta maquina.

    Se busca en las 27 celdas de alrededor y, si no hay nada —una nube con huecos, un
    punto en una esquina del mundo—, se abre el radio hasta encontrarlo. La ultima
    salida es recorrer la nube entera: una consulta lenta es un problema, una consulta
    que devuelve un vertice equivocado es una medida falsa.
    """

    #: El radio maximo que se abre antes de rendirse y recorrer la nube entera.
    RADIO_MAXIMO = 8

    def __init__(self, puntos: "NDArray[Any]", normales: "NDArray[Any] | None" = None) -> None:
        import numpy as np

        self.normales = None if normales is None else np.asarray(normales, dtype="float64")
        if self.normales is not None and len(self.normales) != len(puntos):
            raise ErrorDeProveedor(
                f"la nube trae {len(puntos)} puntos y {len(self.normales)} normales: sin una por "
                "punto no se puede elegir el vecino por su orientacion"
            )
        self.puntos = np.asarray(puntos, dtype="float64")
        if self.puntos.ndim != 2 or self.puntos.shape[1] != 3 or len(self.puntos) == 0:
            raise ErrorDeProveedor(
                f"una vecindad necesita una nube de puntos (n, 3) y llegaron {self.puntos.shape}"
            )
        self.lado = max(float(medir_paso_de_la_malla(self.puntos)["mediano"]) * 2.0, 1e-12)
        # La base de las claves tiene que cubrir la nube entera **mas** el radio que se
        # abre al buscar: una celda desplazada fuera de ese margen se codificaria con la
        # misma clave que otra y la consulta devolveria un vertice que no es el cercano.
        self.origen = self.puntos.min(axis=0)
        self.celdas = np.floor((self.puntos - self.origen) / self.lado).astype("int64")
        self.base = self.celdas.min(axis=0)
        self.ancho = (
            int(self.celdas.max(axis=0).max() - self.base.max()) + 2 * self.RADIO_MAXIMO + 2
        )
        claves = self._claves(self.celdas)
        self.orden = np.argsort(claves, kind="stable")
        self.claves_ordenadas = claves[self.orden]

    def _claves(self, celdas: "NDArray[Any]") -> "NDArray[Any]":
        """Una clave entera por celda, en base `ancho` y con el radio como sesgo.

        El sesgo existe para que una celda desplazada hacia atras al buscar vecinos no
        de un componente negativo: una clave negativa se sale de la representacion en
        base y chocaria con la de otra celda.
        """
        import numpy as np

        relativa = celdas - self.base + self.RADIO_MAXIMO
        claves = (
            relativa[:, 0] * self.ancho * self.ancho + relativa[:, 1] * self.ancho + relativa[:, 2]
        )
        return np.asarray(claves, dtype="int64")

    def _en_rejilla(
        self, consultas: "NDArray[Any]", radio: int, referencia: "NDArray[Any] | None" = None
    ) -> tuple[Any, Any]:
        import numpy as np

        celdas = np.floor((consultas - self.origen) / self.lado).astype("int64")
        mejores = np.full(len(consultas), -1, dtype="int64")
        distancias = np.full(len(consultas), np.inf)
        desplazamientos = [
            (dx, dy, dz)
            for dx in range(-radio, radio + 1)
            for dy in range(-radio, radio + 1)
            for dz in range(-radio, radio + 1)
        ]
        for desplazamiento in desplazamientos:
            clave = self._claves(celdas + np.array(desplazamiento, dtype="int64"))
            inicio = np.searchsorted(self.claves_ordenadas, clave, side="left")
            fin = np.searchsorted(self.claves_ordenadas, clave, side="right")
            for indice in np.flatnonzero(fin > inicio):
                candidatos = self.orden[inicio[indice] : fin[indice]]
                delta = self.puntos[candidatos] - consultas[indice]
                lejania = (delta * delta).sum(axis=1)
                if referencia is not None and self.normales is not None:
                    # Solo los puntos que miran hacia el mismo lado que la consulta. Es lo
                    # que evita cruzar una pared delgada: el vertice de enfrente esta mas
                    # cerca en linea recta y no es el que corresponde.
                    de_frente = (self.normales[candidatos] * referencia[indice]).sum(axis=1) > 0.0
                    if not bool(de_frente.any()):
                        continue
                    candidatos = candidatos[de_frente]
                    lejania = lejania[de_frente]
                ganador = int(np.argmin(lejania))
                if float(lejania[ganador]) < float(distancias[indice]):
                    distancias[indice] = float(lejania[ganador])
                    mejores[indice] = int(candidatos[ganador])
        return mejores, distancias

    def mas_cercano(
        self, consultas: "NDArray[Any]", *, referencia: "NDArray[Any] | None" = None
    ) -> "Vecinos":
        """El indice del punto mas cercano de la nube y su distancia, por consulta.

        Devuelve las dos cosas porque las dos se publican: el indice da la normal que
        se transfiere y la distancia dice cuanto se movio la consulta, que en una malla
        limpia es zero y en una malla con piezas sueltas no.

        Con `referencia` —la normal de cada consulta— solo se consideran los puntos que
        **miran hacia el mismo lado**. Es la diferencia entre buscar un vertice y lanzar
        un rayo, y esta medida: sobre la malla real que llego de Colab, el vecino a secas
        salta al otro lado de las paredes delgadas —una distancia maxima de 0,22 frente a
        un paso mediano de 0,075, tres veces el paso— y el mapa sale con el 2,4 % de sus
        texeles mirando hacia dentro de la superficie, que es lo que R13 rechaza. No es
        un trazador de rayos: solo se descartan los candidatos que miran al reves.

        Si ninguna mira hacia el mismo lado, se coge el mas cercano igual y se declara: un
        vertice sin correspondencia orientada es un dato del informe, no un error.
        """
        import numpy as np

        consultas = np.asarray(consultas, dtype="float64")
        if referencia is not None and self.normales is None:
            raise ErrorDeProveedor(
                "se pidio elegir el vecino por su orientacion y la nube no trae normales"
            )
        mejores = np.full(len(consultas), -1, dtype="int64")
        lejanias = np.full(len(consultas), np.inf)

        # Una consulta no esta resuelta porque se haya encontrado **algo**: el mas cercano
        # puede estar una celda mas alla. Lo esta cuando lo encontrado cae dentro de la
        # bola que el radio buscado garantiza —la caja de `radio` celdas alrededor cubre
        # al menos `radio * lado` de distancia desde cualquier punto de la celda—, y por
        # eso se sigue abriendo mientras el candidato este fuera de esa bola. Se para por
        # agotar el radio maximo y entonces se recorre la nube: una consulta lenta es un
        # problema, un vertice equivocado es una medida falsa.
        pendientes = np.arange(len(consultas))
        for radio in (1, 2, 4, self.RADIO_MAXIMO):
            if len(pendientes) == 0:
                break
            encontrados, halladas = self._en_rejilla(
                consultas[pendientes], radio, None if referencia is None else referencia[pendientes]
            )
            hay = encontrados >= 0
            filas = pendientes[hay]
            mejora = halladas[hay] < lejanias[filas]
            mejores[filas[mejora]] = encontrados[hay][mejora]
            lejanias[filas[mejora]] = halladas[hay][mejora]
            garantizado = hay & (halladas <= (radio * self.lado) ** 2)
            pendientes = pendientes[~garantizado]

        sin_orientacion = 0
        if len(pendientes) > 0:
            delta = self.puntos[None, :, :] - consultas[pendientes][:, None, :]
            bruta = (delta * delta).sum(axis=2)
            buscada = bruta
            if referencia is not None and self.normales is not None:
                de_frente = (self.normales[None, :, :] * referencia[pendientes][:, None, :]).sum(
                    axis=2
                ) > 0.0
                # La consulta que no tiene **ningun** candidato orientado se queda con el
                # mas cercano a secas y se cuenta: un vertice sin correspondencia es un
                # dato del informe, no un error que pare la etapa.
                alguno = de_frente.any(axis=1)
                sin_orientacion = int((~alguno).sum())
                buscada = np.where(alguno[:, None], np.where(de_frente, bruta, np.inf), bruta)
            elegidos = np.argmin(buscada, axis=1)
            mejores[pendientes] = elegidos
            lejanias[pendientes] = buscada[np.arange(len(pendientes)), elegidos]

        return Vecinos(
            indices=mejores,
            distancias=np.sqrt(np.maximum(lejanias, 0.0)),
            sin_orientacion=sin_orientacion,
        )


def medir_paso_de_la_malla(puntos: "NDArray[Any]", *, muestras: int = 4096) -> "dict[str, float]":
    """El paso entre vertices vecinos, medido y no supuesto.

    Se mide y **no** se declara una constante: es el numero que decide si la
    aproximacion de vecino-vertice se puede despreciar o no, y depende de la densidad
    de la malla que llego.

    Aqui se mide por **fuerza bruta sobre una muestra**, y la muestra se toma con paso
    constante y no con los primeros: un PLY de reconstruccion viene en orden de
    recorrido, asi que los primeros mil vertices pueden ser una esquina de la pieza y
    su paso no es el de la malla. La muestra se declara en el informe junto al numero.
    """
    import numpy as np

    puntos = np.asarray(puntos, dtype="float64")
    if len(puntos) < 2:
        return {"mediano": 0.0, "p90": 0.0, "muestras": float(len(puntos))}
    paso = max(1, len(puntos) // max(1, muestras))
    toma = puntos[::paso][:muestras]
    if len(toma) < 2:
        toma = puntos[:2]

    # Distancias de cada punto de la muestra a **los demas** de la muestra: a si mismo
    # se le pone infinito, o el paso medido seria cero siempre.
    propios = np.full(len(toma), np.inf)
    for inicio in range(0, len(toma), 256):
        trozo = toma[inicio : inicio + 256]
        delta = trozo[:, None, :] - toma[None, :, :]
        lejania = np.sqrt((delta * delta).sum(axis=2))
        lejania[np.arange(len(trozo)), np.arange(inicio, inicio + len(trozo))] = np.inf
        propios[inicio : inicio + len(trozo)] = lejania.min(axis=1)
    finitos = propios[np.isfinite(propios)]
    if len(finitos) == 0:
        return {"mediano": 0.0, "p90": 0.0, "muestras": float(len(toma))}
    return {
        "mediano": float(np.median(finitos)),
        "p90": float(np.percentile(finitos, 90)),
        "muestras": float(len(toma)),
    }


def normales_de_vertice(vertices: "NDArray[Any]", caras: "NDArray[Any]") -> "NDArray[Any]":
    """La normal de cada vertice, ponderada por area y determinista.

    Se calcula aqui y no se le pide al proveedor por un motivo concreto: la normal que
    se escribe en el GLB tiene que ser **la misma** con la que se construyo el marco del
    horneado. Si el mapa se hornea con una normal y el visor deriva otra, el relieve
    sale desplazado y nada lo dice.
    """
    import numpy as np

    vertices = np.asarray(vertices, dtype="float64")
    caras = np.asarray(caras, dtype="int64")
    a, b, c = vertices[caras[:, 0]], vertices[caras[:, 1]], vertices[caras[:, 2]]
    # Sin normalizar: la longitud del producto vectorial es el doble del area, que es
    # justo la ponderacion que quiere una normal suave.
    por_cara = np.cross(b - a, c - a)
    acumulada = np.zeros_like(vertices)
    for esquina in range(3):
        for eje in range(3):
            acumulada[:, eje] += np.bincount(
                caras[:, esquina], weights=por_cara[:, eje], minlength=len(vertices)
            )
    normas = np.linalg.norm(acumulada, axis=1)
    fuera = normas > 0
    resultado = np.zeros_like(acumulada)
    resultado[fuera] = acumulada[fuera] / normas[fuera, None]
    return resultado


def marcos_de_uv(
    vertices: "NDArray[Any]", caras: "NDArray[Any]", uv: "NDArray[Any]"
) -> "dict[str, Any]":
    """El marco de cada vertice: tangente, bitangente y normal, con la UV como manda.

    La tangente sale de derivar la posicion respecto de la UV en cada triangulo, que
    es lo que hace un motor al dibujar: `dP/du` es la tangente y `dP/dv` la bitangente.
    Se ortogonalizan contra la normal del vertice —Gram-Schmidt— y se normalizan, asi
    que el marco es ortonormal y un vector escrito en el se puede deshacer exactamente.

    Se publica ademas **cuantos triangulos tienen la UV reflejada** (`det < 0`), que es
    la trampa del horneado y no se ve mirando el mapa: en esos triangulos la bitangente
    que sale de la UV apunta al contrario que `N x T`. El numero sale en el informe, y
    en el atlas de un cortador **salen casi todos** —medido el 2026-09-16 sobre el banco
    de pruebas: 198 de 200 triangulos—, porque empaquetar no conserva la orientacion. No
    es un error del mapa: el marco se escribe y se lee con la misma UV, asi que el mapa
    y las coordenadas siguen de acuerdo, y es justo lo que un visor tiene que derivar
    con el bit de handedness de la especificacion. Un numero de cero lo que diria es que
    alguien corto el atlas en un caso muy raro.
    """
    import numpy as np

    vertices = np.asarray(vertices, dtype="float64")
    caras = np.asarray(caras, dtype="int64")
    uv = np.asarray(uv, dtype="float64")
    triangulos = vertices[caras]
    coordenadas = uv[caras]

    d_p1 = triangulos[:, 1] - triangulos[:, 0]
    d_p2 = triangulos[:, 2] - triangulos[:, 0]
    d_u = coordenadas[:, 1] - coordenadas[:, 0]
    d_v = coordenadas[:, 2] - coordenadas[:, 0]
    determinante = d_u[:, 0] * d_v[:, 1] - d_u[:, 1] * d_v[:, 0]

    tangente = np.zeros_like(vertices)
    bitangente = np.zeros_like(vertices)
    validos = np.abs(determinante) > 1e-20
    inverso = np.zeros_like(determinante)
    inverso[validos] = 1.0 / determinante[validos]
    por_cara_t = (d_p1 * d_v[:, 1, None] - d_p2 * d_u[:, 1, None]) * inverso[:, None]
    por_cara_b = (d_p2 * d_u[:, 0, None] - d_p1 * d_v[:, 0, None]) * inverso[:, None]
    for esquina in range(3):
        for eje in range(3):
            tangente[:, eje] += np.bincount(
                caras[:, esquina], weights=por_cara_t[:, eje], minlength=len(vertices)
            )
            bitangente[:, eje] += np.bincount(
                caras[:, esquina], weights=por_cara_b[:, eje], minlength=len(vertices)
            )

    normal = normales_de_vertice(vertices, caras)
    t = tangente - normal * (tangente * normal).sum(axis=1)[:, None]
    t = _normalizar(t)
    b = bitangente - normal * (bitangente * normal).sum(axis=1)[:, None]
    b = b - t * (b * t).sum(axis=1)[:, None]
    b = _normalizar(b)
    # Donde la UV no da tangente —un vertice suelto, un triangulo de area nula— se deja
    # una cualquiera perpendicular a la normal: es un marco y no una medida, y esos
    # vertices no llegan a ningun texel.
    flojos = np.linalg.norm(b, axis=1) < 1e-9
    if np.any(flojos):
        b[flojos] = np.cross(normal[flojos], t[flojos])
        b[flojos] = _normalizar(b[flojos])
        # Y donde tampoco haya bitangente valida, el eje menos alineado con la normal.
        flojos = np.linalg.norm(b, axis=1) < 1e-9
        if np.any(flojos):
            menos_alineado = np.argmin(np.abs(normal[flojos]), axis=1)
            auxiliar = np.eye(3)[menos_alineado]
            b[flojos] = np.cross(normal[flojos], auxiliar)
            t[flojos] = np.cross(b[flojos], normal[flojos])
            b[flojos] = _normalizar(b[flojos])
            t[flojos] = _normalizar(t[flojos])

    return {
        "tangente": t,
        "bitangente": b,
        "normal": normal,
        "triangulos_reflejados": int(np.count_nonzero(determinante < 0)),
        "triangulos_sin_uv": int(np.count_nonzero(~validos)),
    }


def _normalizar(vectores: "NDArray[Any]") -> "NDArray[Any]":
    """Cada fila a longitud uno, y las que no tienen longitud se quedan en cero."""
    import numpy as np

    normas = np.linalg.norm(vectores, axis=1)
    fuera = normas > 1e-12
    resultado = np.zeros_like(vectores)
    resultado[fuera] = vectores[fuera] / normas[fuera, None]
    return resultado


def es_marco(marcos: "dict[str, Any]", *, tolerancia: float = 1e-6) -> bool:
    """Comprueba que los tres ejes son unitarios y perpendiculares entre si.

    Es una comprobacion de la propia construccion, y existe porque un marco que no lo
    sea no da un error: da un mapa con el relieve girado, que es un fallo que se ve en
    el resultado y no en el proceso. Recibe los tres vectores por argumento y no toca
    disco, asi que se puede ver en rojo con un marco torcido a proposito.
    """
    import numpy as np

    t = np.asarray(marcos["tangente"], dtype="float64")
    b = np.asarray(marcos["bitangente"], dtype="float64")
    n = np.asarray(marcos["normal"], dtype="float64")
    unitarios = np.linalg.norm(t, axis=1) + np.linalg.norm(b, axis=1) + np.linalg.norm(n, axis=1)
    if not np.all(np.isfinite(unitarios)):
        return False
    if not np.all(np.abs(unitarios - 3.0) <= tolerancia * 3.0):
        return False
    productos = np.stack([(t * b).sum(axis=1), (t * n).sum(axis=1), (b * n).sum(axis=1)], axis=1)
    return bool(np.all(np.abs(productos) <= tolerancia))
