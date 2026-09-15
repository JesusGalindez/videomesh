"""C1 y C2 — V6, V8 y D7: identidad del paquete e integridad de cada artifact.

`packageId` es la identidad canonica y **nunca se deduce del nombre del
directorio**, que es comodidad humana: mover una carpeta no cambia la identidad de
lo que hay dentro.

Cada artifact declara `path`, `bytes` y `sha256`. `package-integrity-v1` tiene los
casos del lado que los rechaza; aqui hay que **producirlos**, que es mas
exigente: no basta con no fallarlos.

Los identificadores `SS-PKG-*` no aparecen en este codigo a proposito. Cinco de
ellos estan PROPUESTOS esperando respuesta y no se fijan desde aqui; ademas,
juzgar es del consumidor. Este lado escribe y se niega a escribir mal.
"""

import hashlib
import pathlib

import pytest

from videomesh.project.package import (
    ErrorDeIntegridad,
    ErrorDeRuta,
    comprobar_integridad,
    comprobar_rutas,
    describir_artifact,
    identidad_de,
)

CONTENIDO = b"ply\nformato de mentira\n"


@pytest.fixture
def raiz(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "mesh.ply").write_bytes(CONTENIDO)
    (tmp_path / "images").mkdir()
    (tmp_path / "images" / "cam.png").write_bytes(b"png de mentira")
    return tmp_path


# --- C1: la identidad sale del manifest -------------------------------------


def test_la_identidad_sale_del_manifest_y_no_del_directorio(raiz: pathlib.Path) -> None:
    assert identidad_de({"packageId": "turret-recon-0004"}, raiz) == "turret-recon-0004"


def test_mover_la_carpeta_no_cambia_la_identidad(raiz: pathlib.Path) -> None:
    """La puerta de D7, dicha con el sistema de ficheros de verdad."""
    manifest = {"packageId": "turret-recon-0004"}
    antes = identidad_de(manifest, raiz)
    movida = raiz.parent / "otro-nombre-cualquiera"
    raiz.rename(movida)
    assert identidad_de(manifest, movida) == antes


def test_un_manifest_sin_packageId_no_se_completa_con_el_nombre_del_directorio(
    raiz: pathlib.Path,
) -> None:
    """Inferirlo seria justo lo que D7 prohibe, y el directorio se llama plausible."""
    with pytest.raises(ErrorDeIntegridad, match="packageId"):
        identidad_de({}, raiz)


# --- C2: bytes y sha256 salen del fichero -----------------------------------


def test_el_artifact_se_describe_leyendo_el_fichero(raiz: pathlib.Path) -> None:
    descrito = describir_artifact(
        raiz, "mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH", purely_reconstructed=True
    )
    assert descrito["bytes"] == len(CONTENIDO)
    assert descrito["sha256"] == hashlib.sha256(CONTENIDO).hexdigest()
    assert descrito["path"] == "mesh.ply"


def test_el_hash_se_escribe_en_hexadecimal_minuscula(raiz: pathlib.Path) -> None:
    descrito = describir_artifact(
        raiz, "mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH", purely_reconstructed=True
    )
    assert descrito["sha256"] == descrito["sha256"].lower()


def test_la_ruta_se_escribe_con_barras_aunque_el_sistema_use_otra_cosa(
    raiz: pathlib.Path,
) -> None:
    """Lo que viaja es la ruta del manifest, no la del sistema que la escribio."""
    descrito = describir_artifact(
        raiz, pathlib.Path("images") / "cam.png", identidad="img", tipo="IMAGE"
    )
    assert descrito["path"] == "images/cam.png"


def test_una_malla_declara_purely_reconstructed(raiz: pathlib.Path) -> None:
    """D21: requerida en TRIANGLE_MESH. Aqui se emite, no solo se acepta."""
    descrito = describir_artifact(
        raiz, "mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH", purely_reconstructed=False
    )
    assert descrito["purelyReconstructed"] is False


def test_una_nube_de_puntos_con_purely_reconstructed_no_se_escribe(raiz: pathlib.Path) -> None:
    """Prohibido en POINT_CLOUD. El escritor se niega en vez de dejarlo al consumidor."""
    with pytest.raises(ErrorDeIntegridad, match="purelyReconstructed"):
        describir_artifact(
            raiz, "mesh.ply", identidad="p", tipo="POINT_CLOUD", purely_reconstructed=True
        )


def test_una_malla_sin_purely_reconstructed_no_se_escribe(raiz: pathlib.Path) -> None:
    with pytest.raises(ErrorDeIntegridad, match="purelyReconstructed"):
        describir_artifact(raiz, "mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH")


def test_un_tamano_declarado_que_no_es_el_del_fichero_se_rechaza(raiz: pathlib.Path) -> None:
    descrito = describir_artifact(raiz, "mesh.ply", identidad="mesh", tipo="POINT_CLOUD")
    with pytest.raises(ErrorDeIntegridad, match="bytes"):
        comprobar_integridad(raiz, [dict(descrito, bytes=descrito["bytes"] - 1)])


def test_un_contenido_que_no_coincide_con_su_hash_se_rechaza(raiz: pathlib.Path) -> None:
    descrito = describir_artifact(raiz, "mesh.ply", identidad="mesh", tipo="POINT_CLOUD")
    with pytest.raises(ErrorDeIntegridad, match="sha256"):
        comprobar_integridad(raiz, [dict(descrito, sha256="bb" * 32)])


def test_un_hash_en_mayusculas_se_rechaza_por_no_ser_un_hash(raiz: pathlib.Path) -> None:
    """Codigo aparte del de «no coincide»: uno lo arregla quien escribe el manifest.

    El otro lo arregla el contenido, y quien automatice quiere distinguirlos.
    """
    descrito = describir_artifact(raiz, "mesh.ply", identidad="mesh", tipo="POINT_CLOUD")
    with pytest.raises(ErrorDeIntegridad, match="hexadecimal"):
        comprobar_integridad(raiz, [dict(descrito, sha256=descrito["sha256"].upper())])


def test_lo_que_se_describe_pasa_su_propia_comprobacion(raiz: pathlib.Path) -> None:
    descrito = describir_artifact(raiz, "mesh.ply", identidad="mesh", tipo="POINT_CLOUD")
    comprobar_integridad(raiz, [descrito])


# --- D6: la ruta se juzga antes de tocar el disco ---------------------------


def test_una_ruta_absoluta_se_rechaza(raiz: pathlib.Path) -> None:
    """Aunque apunte dentro: se juzga por lo que dice, no por donde resuelve hoy."""
    with pytest.raises(ErrorDeRuta, match="absoluta"):
        comprobar_rutas(raiz, [{"id": "x", "path": str(raiz / "mesh.ply")}])


def test_una_ruta_con_dos_puntos_se_rechaza_aunque_acabe_dentro(raiz: pathlib.Path) -> None:
    """Una regla que depende de a donde apunte hoy cambia de resultado manana."""
    with pytest.raises(ErrorDeRuta, match=r"\.\."):
        comprobar_rutas(raiz, [{"id": "x", "path": "images/../mesh.ply"}])


def test_un_enlace_que_resuelve_fuera_de_la_raiz_se_rechaza(raiz: pathlib.Path) -> None:
    """Con contenido identico: mismo tamano, mismo hash, y solo cambia donde vive.

    Un sandbox que solo normaliza cadenas lo deja pasar entero.
    """
    fuera = raiz.parent / "fuera.ply"
    fuera.write_bytes(CONTENIDO)
    (raiz / "enlace.ply").symlink_to(fuera)
    with pytest.raises(ErrorDeRuta, match="fuera de la raiz"):
        comprobar_rutas(raiz, [{"id": "x", "path": "enlace.ply"}])


def test_un_enlace_que_resuelve_dentro_pasa(raiz: pathlib.Path) -> None:
    """Lo que separa el sandbox de prohibir los enlaces."""
    (raiz / "alias.ply").symlink_to(raiz / "mesh.ply")
    comprobar_rutas(raiz, [{"id": "x", "path": "alias.ply"}])


def test_un_artifact_declarado_que_no_esta_se_rechaza(raiz: pathlib.Path) -> None:
    with pytest.raises(ErrorDeRuta, match="no existe"):
        comprobar_rutas(raiz, [{"id": "x", "path": "ausente.ply"}])


def test_un_enlace_roto_se_rechaza(raiz: pathlib.Path) -> None:
    (raiz / "roto.ply").symlink_to(raiz / "nunca-existio.ply")
    with pytest.raises(ErrorDeRuta):
        comprobar_rutas(raiz, [{"id": "x", "path": "roto.ply"}])


def test_dos_artifacts_con_el_mismo_identificador_se_rechazan(raiz: pathlib.Path) -> None:
    with pytest.raises(ErrorDeRuta, match="mesh"):
        comprobar_rutas(
            raiz, [{"id": "mesh", "path": "mesh.ply"}, {"id": "mesh", "path": "mesh.ply"}]
        )
