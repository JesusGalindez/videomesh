"""El validador de Khronos — encargo 04, E4. Se **ejecuta** y se ingiere; no se copia.

R15 lo dice con todas las letras: el validador de Khronos «es la autoridad sobre si un
GLB es un GLB, y no vamos a reimplementarlo ni a envolverlo: se ingiere su informe» —
y sin él **no hay `PRODUCTION_READY`**. Decir «es un GLB válido» sin que nadie lo haya
validado es exactamente el sobreanuncio que D31 impide, así que esta etapa lo ejecuta
de verdad, guarda su informe en el paquete, y ese informe es lo que el vecino lee por
`--external`.

**Por qué se llama a `node` y no a un binario.** El validador se publica como librería
de npm (`gltf-validator`) y **no trae `bin`**: su entrada es un módulo que exporta
`validateBytes`. Así que la orden es un `node --input-type=module -e <guion>` con la
ruta del módulo absoluta — la del paquete instalado en `tools-bin/`, que no viaja en
el repositorio —, y el guion es de tres líneas: leer el fichero, validarlo, escribir
el informe por la salida estándar. Nada de eso es una segunda validación: es el
validador, con otro nombre de fichero delante.
"""

import json
import pathlib
import shutil
import subprocess
from typing import Any

from videomesh.domain.errores import MedicionNoDisponible

__all__ = [
    "PROVEEDOR",
    "instalacion",
    "instalado",
    "motivo_de_ausencia",
    "validar",
]

#: El nombre del validador, tal y como el vecino lo escribe en su informe externo.
PROVEEDOR = "khronos-gltf-validator"

RAIZ = pathlib.Path(__file__).resolve().parents[3]

#: El módulo del validador dentro del paquete de npm. La ruta es la del paquete
#: instalado: el validador no se versiona en este repositorio, igual que el binario
#: nativo de `gltfpack`.
MODULO = RAIZ / "tools-bin" / "gltf-validator" / "node_modules" / "gltf-validator" / "module.mjs"

#: Cómo se consigue, cuando falta. La citan el mensaje de error y `doctor`.
INSTALACION = (
    "el paquete de npm del validador de Khronos, instalado en tools-bin/gltf-validator "
    "(npm install --prefix tools-bin/gltf-validator gltf-validator)"
)

#: El guion que se le pasa a `node`. Se escribe aquí y no en un `.mjs` del repositorio
#: porque es un transporte —abrir, validar, imprimir— y no una pieza de este programa:
#: el validador es del vecino y este repositorio no escribe JavaScript.
_GUION = """
import {{ readFileSync }} from "node:fs";
import * as validador from "{modulo}";
const ruta = process.argv[1];
const informe = await validador.validateBytes(new Uint8Array(readFileSync(ruta)), {{ uri: ruta }});
process.stdout.write(JSON.stringify(informe));
"""


def instalado() -> bool:
    """Si el validador está donde se espera. No ejecuta nada."""
    return MODULO.is_file()


def instalacion() -> str:
    """Cómo se pone el validador, en una línea."""
    return INSTALACION


def motivo_de_ausencia() -> str | None:
    """Por qué no se puede validar hoy, o `None` si sí."""
    if shutil.which("node") is None:
        return "no hay `node`, y el validador de Khronos se publica como modulo de npm"
    if not instalado():
        return f"falta el validador de Khronos en {MODULO}: {INSTALACION}"
    return None


def _exigir() -> pathlib.Path:
    """El módulo del validador, o un `MedicionNoDisponible` con sus tres partes."""
    sin_node = shutil.which("node") is None
    if sin_node or not MODULO.is_file():
        raise MedicionNoDisponible(
            f"falta el validador de Khronos ({MODULO}), que es lo que convierte «este GLB "
            "es valido» en algo que alguien comprobo: sin el, la QA de produccion no puede "
            "aprobar el asset.\n"
            f"  se instala con: {INSTALACION}\n"
            "  `videomesh doctor` dice el resto del entorno de una vez"
        )
    return MODULO


def validar(ruta: pathlib.Path) -> dict[str, Any]:
    """Valida un GLB y devuelve su informe, tal cual lo escribió el validador.

    Se devuelve el informe **entero** y no un resumen: es lo que se guarda junto al
    paquete y lo que el vecino lee por `--external`, y él ya sabe leer las dos formas
    que el validador produce. Traducirlo aquí sería una segunda versión de sus números.
    """
    modulo = _exigir()
    orden = [
        "node",
        "--input-type=module",
        "-e",
        _GUION.format(modulo=modulo),
        str(pathlib.Path(ruta)),
    ]
    ejecucion = subprocess.run(orden, capture_output=True, text=True, check=False)
    if ejecucion.returncode != 0:
        raise MedicionNoDisponible(
            f"el validador de Khronos fallo ({ejecucion.returncode}): "
            f"{ejecucion.stderr.strip()[-400:] or ejecucion.stdout.strip()[-400:]}"
        )
    informe: dict[str, Any] = json.loads(ejecucion.stdout)
    return informe


def resumen(informe: dict[str, Any], *, fichero: str) -> dict[str, Any]:
    """Lo que el informe dice de sí mismo: quién validó, con qué versión y qué encontró.

    Se leen `issues` y no un campo inventado: es la forma que el propio validador
    escribe, y la misma que el vecino acepta.
    """
    problemas = informe.get("issues") or {}
    return {
        "proveedor": PROVEEDOR,
        "fichero": fichero,
        "version": informe.get("validatorVersion"),
        "errores": int(problemas.get("numErrors", 0)),
        "avisos": int(problemas.get("numWarnings", 0)),
        "informes": int(problemas.get("numInfos", 0)),
        "mensajes": [
            {"codigo": m.get("code"), "severidad": m.get("severity"), "mensaje": m.get("message")}
            for m in (problemas.get("messages") or [])[:12]
        ],
    }
