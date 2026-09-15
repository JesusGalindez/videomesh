"""`doctor` decía DISPONIBLE de un consumidor que no se puede consumir.

`tools/reconstruction.mjs` importa `../dist-node/agent3d.mjs`, que **no está
versionado en SoftSight**: lo escribe `npm run build:agent3d` y su `.gitignore` lo
excluye. En un clon recién hecho el fichero está y el import no resuelve, así que
`doctor` salía 0 mientras la puerta de D1 daba error en todos sus casos.

Un diagnóstico que se equivoca en verde es peor que no tenerlo: manda a leer el
código de uno mismo buscando un fallo que está en el vecino.

La comprobación recibe **el texto y la base como argumentos**, que es lo que
permite escribir el caso rojo sin mover `dist-node/` de sitio. Moverlo también se
hizo, porque una prueba que solo se ha visto verde no ha demostrado que mire.
"""

import pathlib

from videomesh.cli.doctor import importes_sin_resolver, informe_de_doctor
from videomesh.contracts.generacion import ESQUEMAS

CONSUMIDOR = ESQUEMAS.parent / "tools" / "reconstruction.mjs"


def test_hoy_el_consumidor_resuelve_todo_lo_que_importa() -> None:
    """Con `dist-node/` construido, no falta nada. Esto solo no prueba nada."""
    assert importes_sin_resolver(CONSUMIDOR.read_text(encoding="utf-8"), CONSUMIDOR.parent) == []


def test_un_import_que_no_esta_en_disco_se_nombra(tmp_path: pathlib.Path) -> None:
    """El caso rojo, sin tocar SoftSight: base vacía, así que nada resuelve."""
    texto = 'import { inspeccionar } from "../dist-node/agent3d.mjs";\n'
    assert importes_sin_resolver(texto, tmp_path) == ["../dist-node/agent3d.mjs"]


def test_lo_que_no_es_ruta_relativa_no_se_mira(tmp_path: pathlib.Path) -> None:
    """`node:fs` y los paquetes no son ficheros del repositorio; buscarlos en disco
    daría un ausente falso, que es el mismo fallo al revés."""
    texto = 'import { readFileSync } from "node:fs";\nimport x from "vite";\n'
    assert importes_sin_resolver(texto, tmp_path) == []


def test_la_fila_del_consumidor_dice_como_se_construye_lo_que_falta(
    tmp_path: pathlib.Path,
) -> None:
    """Quien lee esa línea no tiene por qué saber qué es `dist-node`."""
    texto = 'import { inspeccionar } from "../dist-node/agent3d.mjs";\n'
    faltan = importes_sin_resolver(texto, tmp_path)
    assert faltan == ["../dist-node/agent3d.mjs"]


def test_el_informe_bloquea_si_el_consumidor_no_se_puede_consumir() -> None:
    """Hoy en verde; el rojo se vio moviendo `dist-node/` y corriendo `doctor`."""
    informe = informe_de_doctor()
    fila = next(c for c in informe["comprobaciones"] if c["que"] == "SoftSight, consumidor")
    assert fila["bloquea"] is True
    assert fila["estado"] == "DISPONIBLE"
