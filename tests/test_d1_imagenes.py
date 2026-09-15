"""D1, segunda pieza — las imagenes son evidencia, no relleno.

D18 lo dice del otro lado: la puerta mira los pixeles «para que ninguna sea un
lienzo del color de fondo, que pasaria los hashes igual de bien y seria evidencia
falsa». Y D33 abre la imagen y compara su rejilla real con lo que la camara
declara: una foto con los intrinsecos girados **se ve bien en miniatura**.

Asi que el PNG se escribe de verdad y el cubo se rasteriza de verdad.
"""

import pathlib
import struct
import zlib

import pytest

from videomesh.application.cube_v1 import CAMARAS, LADO, render_de
from videomesh.formatos.png import escribir_png, leer_dimensiones_png

ROJO = (200, 60, 60)


def _pixeles(ruta: pathlib.Path) -> list[tuple[int, int, int]]:
    """Decodifica el PNG que escribimos, para mirarlo sin creernos nada."""
    crudo = ruta.read_bytes()
    assert crudo[:8] == b"\x89PNG\r\n\x1a\n"
    datos, posicion, ancho, alto = b"", 8, 0, 0
    while posicion < len(crudo):
        (longitud,) = struct.unpack(">I", crudo[posicion : posicion + 4])
        tipo = crudo[posicion + 4 : posicion + 8]
        cuerpo = crudo[posicion + 8 : posicion + 8 + longitud]
        if tipo == b"IHDR":
            ancho, alto = struct.unpack(">II", cuerpo[:8])
        elif tipo == b"IDAT":
            datos += cuerpo
        posicion += 12 + longitud

    plano = zlib.decompress(datos)
    pixeles = []
    for fila in range(alto):
        inicio = fila * (ancho * 3 + 1)
        assert plano[inicio] == 0, "se escribe sin filtro por fila"
        tira = plano[inicio + 1 : inicio + 1 + ancho * 3]
        pixeles += [(tira[i], tira[i + 1], tira[i + 2]) for i in range(0, len(tira), 3)]
    return pixeles


def test_el_png_declara_la_rejilla_que_tiene(tmp_path: pathlib.Path) -> None:
    destino = tmp_path / "x.png"
    escribir_png(destino, ancho=7, alto=3, pixeles=[ROJO] * 21)
    assert leer_dimensiones_png(destino) == (7, 3)


def test_el_png_se_puede_volver_a_leer_pixel_a_pixel(tmp_path: pathlib.Path) -> None:
    destino = tmp_path / "x.png"
    pixeles = [(i, i * 2 % 256, 0) for i in range(12)]
    escribir_png(destino, ancho=4, alto=3, pixeles=pixeles)
    assert _pixeles(destino) == pixeles


def test_el_png_es_determinista(tmp_path: pathlib.Path) -> None:
    uno, otro = tmp_path / "a.png", tmp_path / "b.png"
    for ruta in (uno, otro):
        escribir_png(ruta, ancho=4, alto=3, pixeles=[ROJO] * 12)
    assert uno.read_bytes() == otro.read_bytes()


def test_un_numero_de_pixeles_que_no_cuadra_con_la_rejilla_se_rechaza(
    tmp_path: pathlib.Path,
) -> None:
    with pytest.raises(ValueError, match="rejilla"):
        escribir_png(tmp_path / "x.png", ancho=4, alto=3, pixeles=[ROJO] * 11)


@pytest.mark.parametrize("camara", [c["id"] for c in CAMARAS])
def test_ninguna_vista_es_un_lienzo_del_color_de_fondo(camara: str) -> None:
    """El caso que D18 obliga a mirar: los hashes cuadrarian igual de bien."""
    pixeles = render_de(camara)
    assert len(set(pixeles)) > 1


@pytest.mark.parametrize("camara", [c["id"] for c in CAMARAS])
def test_el_cubo_ocupa_una_parte_razonable_del_encuadre(camara: str) -> None:
    """Ni tan lejos que sean cuatro pixeles, ni tan cerca que se salga."""
    pixeles = render_de(camara)
    fondo = pixeles[0]
    ocupacion = sum(1 for p in pixeles if p != fondo) / len(pixeles)
    assert 0.05 < ocupacion < 0.75


@pytest.mark.parametrize("camara", [c["id"] for c in CAMARAS])
def test_el_cubo_no_toca_el_borde_de_la_imagen(camara: str) -> None:
    """Si tocara, estaria recortado y la imagen dejaria de mostrar el objeto entero."""
    pixeles = render_de(camara)
    fondo = pixeles[0]
    for fila in range(LADO):
        for columna in (0, LADO - 1):
            assert pixeles[fila * LADO + columna] == fondo
    for columna in range(LADO):
        for fila in (0, LADO - 1):
            assert pixeles[fila * LADO + columna] == fondo


def test_las_cuatro_vistas_son_distintas_entre_si() -> None:
    """Cuatro camaras que dieran la misma imagen no son cuatro puntos de vista."""
    vistas = [tuple(render_de(camara["id"])) for camara in CAMARAS]
    assert len(set(vistas)) == len(CAMARAS)


def test_la_vista_frontal_ve_una_sola_cara() -> None:
    """Un cubo de frente es un cuadrado de un color: si salen tres, la pose esta mal."""
    colores = {p for p in render_de("frontal")}
    assert len(colores) == 2


def test_la_vista_oblicua_ve_tres_caras() -> None:
    """Y es la que delata una convencion equivocada: con el cubo alineado no se nota."""
    colores = {p for p in render_de("oblicua")}
    assert len(colores) == 4
