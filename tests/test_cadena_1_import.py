"""Encargo 04, bloque A — el paquete que llega de Colab.

La malla densa **no se hace aqui**: exige CUDA y la hace un cuaderno en Colab. Lo
que entra es un producto de un proveedor no determinista, de otra maquina y de
otra version, y por eso se trata como lo que es: un paquete sellado que se
**comprueba** al entrar y no se recalcula.

Tres cosas se comprueban, y en este orden:

```text
1  el manifest valida contra el esquema publicado de SoftSight
2  cada artifact pesa y hashea lo que el manifest declara
3  el paquete esta SEALED — consumir uno a medias es de D29
```

El paso 2 es el que importa. Un paquete que viajo 300 MB por la red y llego con
un byte cambiado tiene que morir aqui, y no tres etapas mas tarde cuando el
sintoma sea una malla con un pico.

Y lo que **no** se hace, porque tambien es la prueba: no se recalcula geometria,
no se copia el blob y no se deduce la identidad del nombre del directorio.
"""

import hashlib
import json
import pathlib
from typing import Any

import pytest

from videomesh.application.densa import importar_paquete
from videomesh.cli.app import main
from videomesh.domain.errores import (
    ManifestNoValido,
    PaqueteSinSellar,
    ProcedenciaIncompleta,
    SinSuperficie,
)
from videomesh.domain.malla import Malla, cubo_unidad
from videomesh.domain.procedencia import EstadoDeProcedencia
from videomesh.domain.stage import Determinismo, EstadoDeStage
from videomesh.formatos.ply import escribir_ply_malla
from videomesh.project.package import ErrorDeIntegridad
from videomesh.project.procedencia import procedencia_de
from videomesh.project.sellado import publicar_paquete
from videomesh.project.stages import ultima_de
from videomesh.project.store import crear_proyecto

CUBO = cubo_unidad()

#: El nombre real del productor de la malla densa. Lleva la descripcion pegada
#: detras de un `·`, y por eso el proveedor del stage no es este texto entero.
PRODUCTOR = "producers/colmap · las 8 vistas registradas"

MAQUINA = "colab-t4"


def _movido(malla: Malla, desplazamiento: float) -> Malla:
    """La misma malla en otro sitio: sirve para cambiar el contenido sin cambiar la forma."""
    return Malla(
        vertices=[(x + desplazamiento, y, z) for x, y, z in malla.vertices],
        triangulos=list(malla.triangulos),
    )


def _paquete(
    destino: pathlib.Path,
    *,
    identidad: str = "densa-0001",
    productor: str = PRODUCTOR,
    version: str = "0.1.0",
    maquina: str | None = None,
    malla: bool = True,
) -> pathlib.Path:
    """Un paquete sellado por la via de verdad, que es `publicar_paquete`."""
    with publicar_paquete(
        destino, package_id=identidad, producer=productor, version_del_productor=version
    ) as obra:
        if malla:
            escribir_ply_malla(obra.raiz / "mesh.ply", CUBO)
            obra.anadir(
                "mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH", purely_reconstructed=True
            )
        (obra.raiz / "sparse.ply").write_bytes(b"ply\nuna nube de mentira\n")
        obra.anadir("sparse.ply", identidad="sparse", tipo="POINT_CLOUD")
        obra.manifest["requiredEvidence"] = ["mesh", "sparse"] if malla else ["sparse"]
        if maquina is not None:
            obra.manifest["extensions"] = {
                "videomesh.procedencia.maquina": {
                    "required": False,
                    "data": {"maquina": maquina},
                }
            }
    return destino


def _proyecto(tmp_path: pathlib.Path) -> pathlib.Path:
    ruta = tmp_path / "proyecto"
    crear_proyecto(ruta, nombre="prueba")
    return ruta


def _manifest(destino: pathlib.Path) -> dict[str, Any]:
    documento: dict[str, Any] = json.loads((destino / "manifest.json").read_text(encoding="utf-8"))
    return documento


def _escribir_manifest(destino: pathlib.Path, documento: dict[str, Any]) -> None:
    (destino / "manifest.json").write_text(json.dumps(documento, indent=2) + "\n", encoding="utf-8")


def _reescribir_manifest(destino: pathlib.Path, cambios: dict[str, Any]) -> None:
    documento = _manifest(destino)
    documento.update(cambios)
    _escribir_manifest(destino, documento)


def _correr(*argumentos: str) -> tuple[int, str]:
    from contextlib import redirect_stdout
    from io import StringIO

    salida = StringIO()
    with redirect_stdout(salida):
        codigo = main(list(argumentos))
    return codigo, salida.getvalue()


# --- A1: lo que entra -------------------------------------------------------


def test_el_paquete_importado_se_registra_como_la_etapa_densa(tmp_path: pathlib.Path) -> None:
    """El paquete no se reejecuta: se registra lo que ya paso en la otra maquina."""
    proyecto = _proyecto(tmp_path)
    importar_paquete(proyecto, _paquete(tmp_path / "densa-0001"), maquina=MAQUINA)

    ultima = ultima_de(proyecto, "densa")
    assert ultima is not None
    assert ultima.estado is EstadoDeStage.COMPLETE
    assert ultima.determinismo is Determinismo.NO_DETERMINISTA
    assert ultima.version_del_proveedor == "0.1.0"
    assert ultima.hash_de_entrada and ultima.hash_de_salida


def test_el_proveedor_del_stage_es_el_productor_sin_su_descripcion(
    tmp_path: pathlib.Path,
) -> None:
    """`producers/colmap · …` es COLMAP con una nota al lado, y la nota no es el proveedor.

    El nombre entero vive en la procedencia, que es donde cabe: el registro del
    stage quiere un identificador con el que se pueda agrupar.
    """
    proyecto = _proyecto(tmp_path)
    importar_paquete(proyecto, _paquete(tmp_path / "densa-0001"), maquina=MAQUINA)

    ultima = ultima_de(proyecto, "densa")
    assert ultima is not None
    assert ultima.proveedor == "colmap"
    assert procedencia_de(proyecto)[0].productor == PRODUCTOR


def test_el_import_no_toca_la_geometria_ni_copia_el_blob(tmp_path: pathlib.Path) -> None:
    """D1: los blobs viajan por ruta. Copiar 300 MB para no mirarlos es perder 300 MB.

    Se comprueba por lo que **no** aparece: ni un fichero nuevo en el paquete, ni
    una copia de la malla dentro del proyecto.
    """
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001")
    antes = {ruta.name: ruta.read_bytes() for ruta in sorted(fuente.rglob("*")) if ruta.is_file()}

    importar_paquete(proyecto, fuente, maquina=MAQUINA)

    despues = {ruta.name: ruta.read_bytes() for ruta in sorted(fuente.rglob("*")) if ruta.is_file()}
    assert despues == antes
    assert not list(proyecto.rglob("*.ply"))


# --- A1, lo que tiene que morir aqui ----------------------------------------


def test_un_byte_cambiado_en_la_malla_mata_el_import_nombrando_el_artifact(
    tmp_path: pathlib.Path,
) -> None:
    """La prueba que el encargo pide ver en rojo: no un error de parseo, el artifact."""
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001")
    (fuente / "mesh.ply").write_bytes((fuente / "mesh.ply").read_bytes().replace(b"0", b"9", 1))

    with pytest.raises(ErrorDeIntegridad) as fallo:
        importar_paquete(proyecto, fuente, maquina=MAQUINA)

    assert "mesh" in str(fallo.value)
    assert ultima_de(proyecto, "densa") is None


def test_un_paquete_sin_sellar_no_se_consume(tmp_path: pathlib.Path) -> None:
    """D29: un paquete SEALED lo esta para siempre, y uno a medias no se lee."""
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001")
    _reescribir_manifest(fuente, {"state": "WRITING"})

    with pytest.raises(PaqueteSinSellar) as fallo:
        importar_paquete(proyecto, fuente, maquina=MAQUINA)

    assert "WRITING" in str(fallo.value)


def test_un_manifest_que_no_valida_contra_el_esquema_se_rechaza(
    tmp_path: pathlib.Path,
) -> None:
    """D15: la frontera es el esquema publicado, no una idea de lo que deberia decir."""
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001")
    _reescribir_manifest(fuente, {"inventado": 1})

    with pytest.raises(ManifestNoValido) as fallo:
        importar_paquete(proyecto, fuente, maquina=MAQUINA)

    assert "inventado" in str(fallo.value)


def test_un_paquete_sin_malla_no_sirve_para_la_cadena(tmp_path: pathlib.Path) -> None:
    """Sin superficie no hay nada que limpiar, y decirlo pronto ahorra tres etapas."""
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001", malla=False)

    with pytest.raises(SinSuperficie) as fallo:
        importar_paquete(proyecto, fuente, maquina=MAQUINA)

    assert "TRIANGLE_MESH" in str(fallo.value)


def test_el_sha256_declarado_tiene_que_ser_un_sha256(tmp_path: pathlib.Path) -> None:
    """Un hash que no es un hash deja la comprobacion entera en nada."""
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001")
    documento = _manifest(fuente)
    documento["artifacts"][0]["sha256"] = "no-soy-un-hash"
    _escribir_manifest(fuente, documento)

    with pytest.raises(ErrorDeIntegridad):
        importar_paquete(proyecto, fuente, maquina=MAQUINA)


# --- A2: de donde salio -----------------------------------------------------


def test_la_procedencia_declara_maquina_version_y_productor(tmp_path: pathlib.Path) -> None:
    """Dos densas de dos versiones no son comparables, y nadie se acordara de cual era."""
    proyecto = _proyecto(tmp_path)
    importar_paquete(proyecto, _paquete(tmp_path / "densa-0001"), maquina=MAQUINA)

    (anotada,) = procedencia_de(proyecto)
    assert anotada.estado is EstadoDeProcedencia.RECONSTRUIDO
    assert anotada.maquina == MAQUINA
    assert anotada.version_del_productor == "0.1.0"
    assert anotada.productor == PRODUCTOR


def test_sin_maquina_el_import_falla_y_dice_como_declararla(tmp_path: pathlib.Path) -> None:
    """Un campo vacio aqui es peor que no tenerlo: parece dato."""
    proyecto = _proyecto(tmp_path)

    with pytest.raises(ProcedenciaIncompleta) as fallo:
        importar_paquete(proyecto, _paquete(tmp_path / "densa-0001"))

    assert "--maquina" in str(fallo.value)
    assert ultima_de(proyecto, "densa") is None


def test_si_el_manifest_trae_la_maquina_no_hace_falta_el_argumento(
    tmp_path: pathlib.Path,
) -> None:
    """El manifiesto no tiene campo para ella, pero `extensions` existe para esto."""
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001", maquina="colab-a100")

    importar_paquete(proyecto, fuente)

    assert procedencia_de(proyecto)[0].maquina == "colab-a100"


def test_la_procedencia_no_se_pierde_al_importar_dos_veces(tmp_path: pathlib.Path) -> None:
    """Se anade, no se reemplaza: borrar el intento anterior es borrar la pista."""
    proyecto = _proyecto(tmp_path)
    una = _paquete(tmp_path / "densa-0001", identidad="densa-0001")
    otra = _paquete(tmp_path / "densa-0002", identidad="densa-0002")

    importar_paquete(proyecto, una, maquina=MAQUINA)
    importar_paquete(proyecto, otra, maquina=MAQUINA)

    assert [anotada.package_id for anotada in procedencia_de(proyecto)] == [
        "densa-0001",
        "densa-0002",
    ]


# --- A3: la CLI cuenta la verdad de la cadena -------------------------------


def test_la_orden_import_registra_la_etapa(tmp_path: pathlib.Path) -> None:
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001")

    codigo, texto = _correr("import", str(proyecto), str(fuente), "--maquina", MAQUINA)

    assert codigo == 0, texto
    assert ultima_de(proyecto, "densa") is not None


def test_la_ayuda_nombra_la_orden_import() -> None:
    _, texto = _correr("--help")
    assert "videomesh import" in texto


def test_un_paquete_corrupto_por_la_cli_sale_uno_y_sin_traceback(tmp_path: pathlib.Path) -> None:
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001")
    (fuente / "mesh.ply").write_bytes((fuente / "mesh.ply").read_bytes().replace(b"0", b"9", 1))

    codigo, texto = _correr("import", str(proyecto), str(fuente), "--maquina", MAQUINA)

    assert codigo == 1
    assert "mesh" in texto


def test_status_dice_que_etapa_toca_en_una_cadena_vacia(tmp_path: pathlib.Path) -> None:
    proyecto = _proyecto(tmp_path)

    codigo, texto = _correr("status", str(proyecto))

    assert codigo == 0
    assert "densa" in texto
    assert "TOCA" in texto


def test_status_marca_hecha_la_etapa_importada(tmp_path: pathlib.Path) -> None:
    proyecto = _proyecto(tmp_path)
    importar_paquete(proyecto, _paquete(tmp_path / "densa-0001"), maquina=MAQUINA)

    _, texto = _correr("status", str(proyecto))

    assert "densa" in texto
    assert "HECHA" in texto


def test_status_marca_caducada_la_etapa_cuya_entrada_cambio(tmp_path: pathlib.Path) -> None:
    """§9 del encargo: las etapas caducan en silencio, y eso es lo que hay que ver.

    Llega otra densa al mismo sitio —otra malla, otro `packageId`— y el registro
    que habia deja de describir lo que hay: no esta hecho, esta caducado.
    """
    proyecto = _proyecto(tmp_path)
    fuente = _paquete(tmp_path / "densa-0001")
    importar_paquete(proyecto, fuente, maquina=MAQUINA)

    escribir_ply_malla(fuente / "mesh.ply", _movido(CUBO, 0.25))
    contenido = (fuente / "mesh.ply").read_bytes()
    documento = _manifest(fuente)
    documento["packageId"] = "densa-0002"
    documento["artifacts"][0]["bytes"] = len(contenido)
    documento["artifacts"][0]["sha256"] = hashlib.sha256(contenido).hexdigest()
    _escribir_manifest(fuente, documento)

    _, texto = _correr("status", str(proyecto))

    assert "CADUCADA" in texto
