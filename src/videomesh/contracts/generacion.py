"""Generador de modelos Pydantic a partir de los esquemas publicados — D15.

Los modelos **no se escriben a mano**. La frontera es `contracts/*.schema.json`
del repositorio de SoftSight, y un modelo escrito a mano seria un segundo
original: diverge en el primer campo nuevo y nadie se entera hasta que el paquete
viaja y se cae al llegar.

Lo que este generador **no** copia son las descripciones del esquema. Son 566 y
estan ahi; duplicarlas aqui crearia justo el segundo original que D15 evita, solo
que en prosa. Lo que se copia es lo que el modelo tiene que hacer cumplir: tipos,
obligatoriedad, enumeraciones, longitudes y el cierre a campos desconocidos.

Los ocho esquemas de hoy no usan `$ref`, `$defs`, `allOf`, `oneOf` ni `const`:
son objetos con todo en linea. El generador solo entiende lo que hay, y **falla
en voz alta** ante cualquier construccion nueva, que es lo que queremos el dia que
SoftSight publique una — mejor que emitir un modelo que se la salta en silencio.
"""

import hashlib
import json
import keyword
import pathlib
import re
from typing import Any

from videomesh.domain.errores import ErrorDeContrato

__all__ = ["ESQUEMAS", "ErrorDeEsquema", "generar_modulos"]

#: Los esquemas publicados. Se leen, nunca se tocan.
ESQUEMAS = (
    pathlib.Path(__file__).resolve().parents[4] / "Dron" / "softsight" / "contracts"
).resolve()

CABECERA = '''"""Modelos de `{fichero}` — GENERADO, NO EDITAR A MANO.

Lo escribe `scripts/generar_modelos.py` a partir del esquema publicado por
SoftSight (D15). Para cambiarlo, cambia el esquema y vuelve a generar.

esquema sha256: {sha256}
"""

{importes}


'''


class ErrorDeEsquema(ErrorDeContrato, RuntimeError):
    """El esquema usa algo que este generador no sabe traducir. No se adivina."""


def _pascal(texto: str) -> str:
    partes = re.split(r"[^0-9a-zA-Z]+", texto)
    return "".join(p[:1].upper() + p[1:] for p in partes if p)


def _literal(valores: list[Any]) -> str:
    return "Literal[" + ", ".join(json.dumps(v, ensure_ascii=False) for v in valores) + "]"


class _Generador:
    """Traduce un esquema a clases Pydantic, hijas antes que padres."""

    def __init__(self, raiz: str) -> None:
        self.raiz = raiz
        self.clases: list[str] = []
        self.nombres: set[str] = set()

    def _nombrar(self, camino: list[str]) -> str:
        base = _pascal(self.raiz) + "".join(_pascal(p) for p in camino)
        nombre = base
        sufijo = 2
        while nombre in self.nombres:
            nombre = f"{base}{sufijo}"
            sufijo += 1
        self.nombres.add(nombre)
        return nombre

    def tipo(self, esquema: dict[str, Any], camino: list[str]) -> str:
        if "anyOf" in esquema:
            ramas = [
                self.tipo(rama, [*camino, f"Opcion{i}"]) for i, rama in enumerate(esquema["anyOf"])
            ]
            union = " | ".join(ramas)
            discriminante = _discriminante(esquema["anyOf"])
            if discriminante:
                # D21. Sin discriminar, un artifact de malla al que le falta
                # `purelyReconstructed` da cuatro errores de forma y ninguno dice
                # que falta: hay que mirar el literal del tipo primero y comprobar
                # solo esa alternativa. Del otro lado esta nota «resulto ser el
                # trabajo», asi que aqui se hace desde el primer commit.
                return f'Annotated[{union}, Field(discriminator="{discriminante}")]'
            return union

        clase = esquema.get("type")
        if clase == "string":
            return _literal(esquema["enum"]) if "enum" in esquema else "str"
        if clase == "number":
            # `int | float` y no `float`: asi un 626 vuelve a salir como 626 y no
            # como 626.0. El paquete que sale tiene que ser el que entro.
            return "int | float"
        if clase == "integer":
            return "int"
        if clase == "boolean":
            return "bool"
        if clase == "array":
            return f"list[{self.tipo(esquema['items'], [*camino, 'Item'])}]"
        if clase == "object":
            return self.objeto(esquema, camino)
        raise ErrorDeEsquema(f"tipo no soportado en {'.'.join(camino)}: {clase!r}")

    def objeto(self, esquema: dict[str, Any], camino: list[str]) -> str:
        if "patternProperties" in esquema:
            return self.mapa_con_patron(esquema, camino)
        propiedades = esquema.get("properties")
        if not propiedades:
            # Carga opaca a proposito, como `extensions[].data`: darle forma aqui
            # seria declarar frontera algo que todavia es experimento.
            return "dict[str, Any]"

        adicionales = esquema.get("additionalProperties")
        if adicionales is not False:
            raise ErrorDeEsquema(
                f"{'.'.join(camino)} no cierra additionalProperties; el nucleo se cierra (D30)"
            )

        nombre = self._nombrar(camino)
        obligatorios = set(esquema.get("required", []))
        lineas = [
            f"class {nombre}(BaseModel):",
            '    model_config = ConfigDict(extra="forbid", populate_by_name=True)',
            "",
        ]
        for campo, sub in propiedades.items():
            lineas.append("    " + self.campo(campo, sub, campo in obligatorios, camino))
        self.clases.append("\n".join(lineas) + "\n")
        return nombre

    def mapa_con_patron(self, esquema: dict[str, Any], camino: list[str]) -> str:
        patrones = esquema["patternProperties"]
        if len(patrones) != 1 or esquema.get("additionalProperties") is not False:
            raise ErrorDeEsquema(f"{'.'.join(camino)}: patternProperties que no se sabe traducir")
        ((patron, sub),) = patrones.items()
        valor = self.tipo(sub, [*camino, "Valor"])
        clave = f"Annotated[str, StringConstraints(pattern={patron!r})]"
        return f"dict[{clave}, {valor}]"

    def campo(
        self, nombre: str, esquema: dict[str, Any], obligatorio: bool, camino: list[str]
    ) -> str:
        tipo = self.tipo(esquema, [*camino, nombre])
        restricciones = []
        if "minItems" in esquema:
            restricciones.append(f"min_length={esquema['minItems']}")
        if "maxItems" in esquema:
            restricciones.append(f"max_length={esquema['maxItems']}")
        if restricciones:
            tipo = f"Annotated[{tipo}, Field({', '.join(restricciones)})]"

        # `from` y `with` son palabras reservadas de Python y nombres del contrato.
        # El alias manda: lo que viaja es el nombre del esquema.
        atributo = f"{nombre}_" if keyword.iskeyword(nombre) else nombre
        alias = f'alias="{nombre}"' if atributo != nombre else ""

        if obligatorio:
            return f"{atributo}: {tipo} = Field({alias})" if alias else f"{atributo}: {tipo}"
        partes = [p for p in (alias, "default=None") if p]
        return f"{atributo}: {tipo} | None = Field({', '.join(partes)})"


def _discriminante(ramas: list[dict[str, Any]]) -> str | None:
    """El campo que separa las ramas, si lo hay: un literal distinto en cada una.

    Declarado, no adivinado. Solo cuenta como discriminante el campo que en TODAS
    las ramas es obligatorio, tiene un unico valor de enumeracion, y ese valor no
    se repite entre ramas. Con eso, `type` discrimina los cuatro artifacts y nada
    mas lo hace por accidente.
    """
    if len(ramas) < 2 or not all(r.get("type") == "object" and "properties" in r for r in ramas):
        return None
    for campo in ramas[0]["properties"]:
        valores: list[Any] = []
        for rama in ramas:
            sub = rama["properties"].get(campo, {})
            enumeracion = sub.get("enum")
            if campo not in rama.get("required", []) or not enumeracion or len(enumeracion) != 1:
                valores = []
                break
            valores.append(enumeracion[0])
        if valores and len(set(valores)) == len(ramas):
            return str(campo)
    return None


def _importes(clases: list[str]) -> str:
    """Solo lo que el modulo usa de verdad: un import de sobra es un aviso del linter."""
    texto = "\n".join(clases)
    typing = [n for n in ("Annotated", "Any", "Literal") if re.search(rf"\b{n}\b", texto)]
    pydantic = ["BaseModel", "ConfigDict"]
    pydantic += [n for n in ("Field", "StringConstraints") if re.search(rf"\b{n}\b", texto)]
    lineas = []
    if typing:
        lineas.append("from typing import " + ", ".join(typing))
        lineas.append("")
    lineas.append("from pydantic import " + ", ".join(pydantic))
    return "\n".join(lineas)


def _modulo(ruta: pathlib.Path) -> tuple[str, str]:
    crudo = ruta.read_bytes()
    esquema = json.loads(crudo.decode("utf-8"))
    nombre = esquema["title"]
    generador = _Generador(nombre)
    raiz = generador.tipo(esquema, [])
    cuerpo = CABECERA.format(
        fichero=ruta.name,
        sha256=hashlib.sha256(crudo).hexdigest(),
        importes=_importes(generador.clases),
    )
    cuerpo += "\n\n".join(generador.clases)
    cuerpo += f"\n\n__all__ = [{raiz!r}]\n"
    return nombre.replace("-", "_") + ".py", cuerpo


def generar_modulos() -> dict[str, str]:
    """Devuelve `{nombre de fichero: contenido}` para todo el paquete `modelos`."""
    modulos: dict[str, str] = {}
    exportados: list[tuple[str, str]] = []
    for ruta in sorted(ESQUEMAS.glob("*.schema.json")):
        fichero, contenido = _modulo(ruta)
        modulos[fichero] = contenido
        exportados.append((fichero[:-3], _pascal(json.loads(ruta.read_text())["title"])))

    indice = '"""Modelos de la frontera — GENERADO, NO EDITAR A MANO.\n\n'
    indice += "Lo escribe `scripts/generar_modelos.py` de los esquemas de SoftSight (D15).\n"
    indice += '"""\n\n'
    for modulo, clase in exportados:
        indice += f"from videomesh.contracts.modelos.{modulo} import {clase}\n"
    indice += "\n__all__ = [\n"
    for _, clase in sorted(exportados, key=lambda par: par[1]):
        indice += f'    "{clase}",\n'
    indice += "]\n"
    modulos["__init__.py"] = indice
    return modulos
