"""C3 — V5, V7 y D29: el paquete se publica entero o no se publica.

El orden es contrato, no recomendacion:

    escribir artifacts -> cerrarlos -> calcular bytes y sha256 -> construir
    manifest con los hashes -> state: SEALED -> escribir el manifest EL ULTIMO
    -> cerrarlo -> rename atomico del directorio

Con dos exigencias que son **de este lado y solo de este lado**: el temporal y el
destino resuelven al mismo volumen, verificado **antes** de empezar; y el destino
no puede existir ya con un paquete sellado de la misma identidad — no se reescribe
`turret-recon-0004`, se publica `0005`.

Lo que se promete es **visibilidad atomica** —el consumidor ve el estado anterior o
el paquete sellado completo—, no durabilidad ante caida. `fsync` y las semanticas
de sistemas en red quedan fuera del contrato.
"""

import json
import pathlib

import pytest

from videomesh.project.sellado import (
    ErrorDeSellado,
    PublicacionAtomicaNoDisponible,
    comprobar_mismo_volumen,
    publicar_paquete,
)

CUBO = b"ply\nun cubo de mentira\n"


def _publicar(destino: pathlib.Path, identidad: str = "cubo-0001") -> pathlib.Path:
    with publicar_paquete(destino, package_id=identidad, producer="videomesh/pruebas") as obra:
        (obra.raiz / "mesh.ply").write_bytes(CUBO)
        obra.anadir("mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH", purely_reconstructed=True)
        obra.manifest["requiredEvidence"] = ["mesh"]
    return destino


# --- lo que sale ------------------------------------------------------------


def test_el_paquete_publicado_queda_sellado(tmp_path: pathlib.Path) -> None:
    destino = _publicar(tmp_path / "paquete")
    manifest = json.loads((destino / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["state"] == "SEALED"
    assert manifest["packageId"] == "cubo-0001"
    assert manifest["artifacts"][0]["bytes"] == len(CUBO)
    assert (destino / "mesh.ply").read_bytes() == CUBO


def test_el_paquete_publicado_lleva_su_sobre(tmp_path: pathlib.Path) -> None:
    """D16: nada sale sin declarar contra que contrato se escribio."""
    destino = _publicar(tmp_path / "paquete")
    manifest = json.loads((destino / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["documentType"] == "videomesh.reconstruction-package"
    assert len(manifest["contractSchemaSha256"]) == 64


def test_el_manifest_se_escribe_el_ultimo(tmp_path: pathlib.Path) -> None:
    """Mientras el paquete se escribe, no hay manifest que nadie pueda leer a medias."""
    destino = tmp_path / "paquete"
    with publicar_paquete(destino, package_id="cubo-0001", producer="videomesh/pruebas") as obra:
        (obra.raiz / "mesh.ply").write_bytes(CUBO)
        obra.anadir("mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH", purely_reconstructed=True)
        assert not (obra.raiz / "manifest.json").exists()
    assert (destino / "manifest.json").exists()


def test_el_temporal_no_sobrevive_a_la_publicacion(tmp_path: pathlib.Path) -> None:
    destino = tmp_path / "paquete"
    with publicar_paquete(destino, package_id="cubo-0001", producer="videomesh/pruebas") as obra:
        temporal = obra.raiz
        (obra.raiz / "mesh.ply").write_bytes(CUBO)
        obra.anadir("mesh.ply", identidad="mesh", tipo="TRIANGLE_MESH", purely_reconstructed=True)
    assert not temporal.exists()


# --- lo que no llega a salir ------------------------------------------------


def test_un_fallo_a_mitad_no_deja_nada_en_el_destino(tmp_path: pathlib.Path) -> None:
    """Visibilidad atomica: se ve el estado anterior o el paquete sellado entero."""
    destino = tmp_path / "paquete"
    with pytest.raises(RuntimeError, match="a proposito"):
        with publicar_paquete(
            destino, package_id="cubo-0001", producer="videomesh/pruebas"
        ) as obra:
            (obra.raiz / "mesh.ply").write_bytes(CUBO)
            raise RuntimeError("se rompe a proposito")
    assert not destino.exists()


def test_un_fallo_a_mitad_tampoco_deja_el_temporal(tmp_path: pathlib.Path) -> None:
    destino = tmp_path / "paquete"
    visto: list[pathlib.Path] = []
    with pytest.raises(RuntimeError):
        with publicar_paquete(
            destino, package_id="cubo-0001", producer="videomesh/pruebas"
        ) as obra:
            visto.append(obra.raiz)
            raise RuntimeError("se rompe a proposito")
    assert not visto[0].exists()


def test_un_paquete_sin_artifacts_no_se_publica(tmp_path: pathlib.Path) -> None:
    destino = tmp_path / "paquete"
    with pytest.raises(ErrorDeSellado, match="sin artifacts"):
        with publicar_paquete(destino, package_id="cubo-0001", producer="videomesh/pruebas"):
            pass
    assert not destino.exists()


def test_un_destino_que_ya_existe_no_se_reescribe(tmp_path: pathlib.Path) -> None:
    """No se reescribe `turret-recon-0004`: se publica `0005`."""
    destino = _publicar(tmp_path / "paquete")
    antes = (destino / "manifest.json").read_bytes()
    with pytest.raises(ErrorDeSellado, match="ya existe"):
        _publicar(destino)
    assert (destino / "manifest.json").read_bytes() == antes


def test_publicar_la_misma_identidad_en_otro_destino_si_vale(tmp_path: pathlib.Path) -> None:
    """Lo que se prohibe es pisar un paquete sellado, no volver a construir."""
    _publicar(tmp_path / "0004")
    _publicar(tmp_path / "0005")


# --- el mismo volumen, comprobado antes -------------------------------------


def test_dos_volumenes_distintos_se_rechazan_antes_de_escribir() -> None:
    """La comparacion recibe los dispositivos, asi el caso rojo no necesita dos discos."""
    with pytest.raises(PublicacionAtomicaNoDisponible, match="PACKAGE_ATOMIC_PUBLISH_UNAVAILABLE"):
        comprobar_mismo_volumen(dispositivo_temporal=1, dispositivo_destino=2)


def test_el_mismo_volumen_pasa() -> None:
    comprobar_mismo_volumen(dispositivo_temporal=7, dispositivo_destino=7)


def test_nunca_se_cae_en_silencio_a_copiar_y_borrar(tmp_path: pathlib.Path) -> None:
    """Copiar y borrar manteniendo la etiqueta de atomico es el fallo que D29 nombra."""
    destino = tmp_path / "paquete"
    otro_volumen = tmp_path / "temporales"
    otro_volumen.mkdir()
    with pytest.raises(PublicacionAtomicaNoDisponible):
        with publicar_paquete(
            destino,
            package_id="cubo-0001",
            producer="videomesh/pruebas",
            temporal=otro_volumen,
            dispositivo_temporal=999,
        ):
            pass
    assert not destino.exists()
    assert list(otro_volumen.iterdir()) == []


# --- CONSUMED no es un estado ----------------------------------------------


def test_consumed_no_existe_en_este_repositorio() -> None:
    """Un paquete va WRITING -> SEALED, y SEALED para siempre.

    Si el consumidor marcara CONSUMED estaria modificando el paquete, contra P8 y
    P10. El ciclo del consumo pertenece al run, no al paquete. Se vigila como una
    ausencia porque escribirlo no romperia ninguna otra prueba.
    """
    codigo = pathlib.Path(__file__).resolve().parents[1] / "src" / "videomesh"
    assert not [
        ruta for ruta in codigo.rglob("*.py") if "CONSUMED" in ruta.read_text(encoding="utf-8")
    ]
