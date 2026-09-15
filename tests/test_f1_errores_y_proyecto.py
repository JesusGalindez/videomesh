"""Core Foundation, primera pieza — errores tipados y modelo de proyecto.

§22: «no usar excepciones genéricas como estado de pipeline». Un `ValueError`
suelto obliga a quien lo recibe a leer el mensaje para saber qué pasó, que es el
mismo error que D2 prohíbe en la frontera — un nivel más adentro.

§8: el ciclo de vida se mantiene **deliberadamente pequeño**, y la preparación
—`readiness`— **se deriva** de lo que hay, nunca se asigna. Un proyecto que se
declara listo a sí mismo no es un estado: es una opinión.
"""

import json
import pathlib

import pytest

from videomesh.domain.errores import (
    CapacidadNoSoportada,
    ErrorDeContrato,
    ErrorDePaquete,
    ErrorDeProyecto,
    ErrorDeVideoMesh,
    ProveedorNoDisponible,
)
from videomesh.domain.project import CicloDeVida, Preparacion, Proyecto, preparacion_de
from videomesh.project.store import abrir_proyecto, crear_proyecto

# --- errores ---------------------------------------------------------------


def test_todo_error_del_pipeline_cuelga_de_una_raiz() -> None:
    """Quien llama puede capturar lo de VideoMesh sin capturar lo que no es suyo."""
    for clase in (ErrorDeContrato, ErrorDePaquete, ErrorDeProyecto, ProveedorNoDisponible):
        assert issubclass(clase, ErrorDeVideoMesh)


def test_un_error_de_paquete_es_un_error_de_contrato() -> None:
    """La jerarquía dice de qué frontera se habla, no solo que algo falló."""
    assert issubclass(ErrorDePaquete, ErrorDeContrato)


def test_los_errores_que_ya_existian_tambien_cuelgan_de_la_raiz() -> None:
    """Sin esto habria dos jerarquias y quien capture una se comeria la otra."""
    from videomesh.contracts.serialization import ErrorNumeroNoFinito
    from videomesh.contracts.sobre import ErrorDeSobre
    from videomesh.domain.camera import ErrorDeCamara
    from videomesh.domain.frames import ErrorDeMarco
    from videomesh.domain.scale import ErrorDeEscala
    from videomesh.project.package import ErrorDeIntegridad, ErrorDeRuta
    from videomesh.project.sellado import ErrorDeSellado

    for clase in (
        ErrorNumeroNoFinito,
        ErrorDeSobre,
        ErrorDeCamara,
        ErrorDeMarco,
        ErrorDeEscala,
        ErrorDeIntegridad,
        ErrorDeRuta,
        ErrorDeSellado,
    ):
        assert issubclass(clase, ErrorDeVideoMesh), clase.__name__


def test_siguen_siendo_los_errores_de_python_que_ya_eran() -> None:
    """Cambiar la jerarquía no puede romper a quien ya capturaba `ValueError`."""
    from videomesh.contracts.serialization import ErrorNumeroNoFinito

    assert issubclass(ErrorNumeroNoFinito, ValueError)


def test_una_capacidad_no_soportada_no_es_un_fallo_de_software() -> None:
    """§22: no confundir fallo del proveedor con veredicto de certificación.

    «Esto no lo sé hacer» y «esto está mal» son respuestas distintas, y quien
    automatice quiere distinguirlas sin leer el mensaje.
    """
    assert not issubclass(CapacidadNoSoportada, ProveedorNoDisponible)
    assert issubclass(CapacidadNoSoportada, ErrorDeVideoMesh)


# --- proyecto --------------------------------------------------------------


def test_el_ciclo_de_vida_es_pequeno() -> None:
    """§8: no duplicar la máquina de estados de los stages en un enum global."""
    assert [e.value for e in CicloDeVida] == [
        "CREADO",
        "ACTIVO",
        "COMPLETADO",
        "FALLIDO",
        "ARCHIVADO",
    ]


def test_crear_un_proyecto_lo_deja_en_disco(tmp_path: pathlib.Path) -> None:
    proyecto = crear_proyecto(tmp_path / "torreta", nombre="torreta")
    assert proyecto.estado is CicloDeVida.CREADO
    assert (tmp_path / "torreta" / "project.json").is_file()


def test_el_manifest_del_proyecto_lleva_sobre(tmp_path: pathlib.Path) -> None:
    """D16 también aquí: un documento que no dice qué es no se puede leer luego."""
    crear_proyecto(tmp_path / "torreta", nombre="torreta")
    crudo = json.loads((tmp_path / "torreta" / "project.json").read_text(encoding="utf-8"))
    assert crudo["documentType"] == "videomesh.project"
    assert crudo["contractVersion"]


def test_un_proyecto_se_vuelve_a_abrir_igual(tmp_path: pathlib.Path) -> None:
    creado = crear_proyecto(tmp_path / "torreta", nombre="torreta")
    assert abrir_proyecto(tmp_path / "torreta") == creado


def test_crear_sobre_un_proyecto_que_ya_existe_se_rechaza(tmp_path: pathlib.Path) -> None:
    """Pisar un proyecto es perder su historia, y eso no se hace por accidente."""
    crear_proyecto(tmp_path / "torreta", nombre="torreta")
    with pytest.raises(ErrorDeProyecto, match="ya existe"):
        crear_proyecto(tmp_path / "torreta", nombre="torreta")


def test_abrir_lo_que_no_es_un_proyecto_lo_dice(tmp_path: pathlib.Path) -> None:
    with pytest.raises(ErrorDeProyecto, match="project.json"):
        abrir_proyecto(tmp_path)


def test_abrir_un_documento_que_no_es_de_proyecto_se_rechaza(tmp_path: pathlib.Path) -> None:
    """Un manifest de paquete en la carpeta no convierte la carpeta en proyecto."""
    (tmp_path / "project.json").write_text(
        json.dumps({"documentType": "videomesh.reconstruction-package"}), encoding="utf-8"
    )
    with pytest.raises(ErrorDeProyecto, match="documentType"):
        abrir_proyecto(tmp_path)


# --- preparación derivada ---------------------------------------------------


def test_un_proyecto_recien_creado_no_esta_preparado_para_nada() -> None:
    assert preparacion_de(Proyecto(nombre="x", estado=CicloDeVida.CREADO, artifacts=())) == ()


def test_la_preparacion_se_deriva_de_los_artifacts_que_hay() -> None:
    """§8: se deriva de puertas y artifacts válidos; no se asigna."""
    con_malla = Proyecto(
        nombre="x", estado=CicloDeVida.ACTIVO, artifacts=("MEDIA", "SPARSE", "MESH")
    )
    derivada = preparacion_de(con_malla)
    assert Preparacion.MEDIA in derivada
    assert Preparacion.DISPERSA in derivada
    assert Preparacion.RECONSTRUCCION in derivada
    assert Preparacion.DENSA not in derivada


def test_la_preparacion_no_se_puede_declarar_a_mano() -> None:
    """Un proyecto que se declara listo a si mismo no es un estado: es una opinion."""
    import dataclasses

    campos = {c.name for c in dataclasses.fields(Proyecto)}
    assert "preparacion" not in campos
    assert "readiness" not in campos
