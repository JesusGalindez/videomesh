# Prompt de ejecución — bloque C

Pegar tal cual como primer mensaje al agente, en la raíz de `VideoMesh`.

---

```text
Trabajas en VideoMesh, en /Users/albertogalindez/Documents/VideoMesh, rama main.

El encargo es docs/encargo-agente-04.md. Los bloques A y B están hechos y
verificados. Ahora toca el bloque C, y arranca con dos hechos ya comprobados para
que no los vuelvas a comprobar tú:

  Los dos proveedores que el encargo nombra para la retopología —Instant Meshes y
  QuadriFlow— no están y no se pueden instalar en esta máquina: no están en PyPI,
  no hay brew y no hay cmake.

  La auditoría de UV del vecino vive en su informe de producción y solo audita
  GLB. Sobre un PLY dice, literalmente, que el formato no admite coordenadas de
  textura, así que un PLY no se puede juzgar por sus UV.

Las cifras del bloque B que hay en /tmp son de antes del arreglo del decimado: no
las uses como referencia. Empieza con `bash scripts/verify.sh` y `videomesh doctor`
—que ya declara los dos instrumentos de malla— y apunta el recuento.

Las reglas de trabajo son las del encargo 01, sección 1, y no se repiten: la prueba
primero, la ves fallar, cambio mínimo, verificación entera, commit.

IDIOMA: español, en el código, en los comentarios, en los commits y conmigo.

LO QUE HAY QUE HACER, EN ORDEN:

  1. Declarar C1 como NOT_RUN por instrumento, con su motivo escrito y
     comprobable: falta el proveedor de retopología. No lo sustituyas por el que sí
     está. Lo único que ese proveedor sabe hacer con quads conserva los vértices
     originales: no alinea con la forma, no mueve un vértice y no tendría ninguna
     pérdida que publicar. Una etapa de quads que no dice cuánto costó es peor que
     una etapa declarada sin instrumento.

  2. Añadir xatlas —está en PyPI, 0.0.11— al extra `malla`, con su versión en el
     registro y en el hash de entrada, como se hizo con pymeshlab.

  3. Etapa `uv`. Corta y empaqueta el atlas. NO escribe su propia auditoría: la
     juzga el vecino. Lo que publica es lo que la auditoría no puede deducir sola:
     cuántas islas, qué área ocupan, y su distancia de superficie contra la malla
     medida —que en esta etapa mueve por construcción y tiene que decirlo con su
     número, no con una promesa—.

  4. El GLB mínimo, sin KTX2. Es la única forma de que la etapa 3 tenga juez, y el
     encargo ya declara esa variante para E3 porque el cargador del vecino rechaza
     KHR_texture_basisu. Las convenciones de ejes ya viven en un solo sitio,
     `adapters/gltf_transforms.py` (D32): no escribas una segunda conversión.

  5. El caso rojo de C2, y es el que decide si la etapa está hecha: un asset cuyas
     UV se solapan a propósito tiene que salir **rechazado por la auditoría del
     vecino**, no por código de aquí. Si el rechazo lo produce una comprobación
     tuya, la etapa está duplicando un criterio y esa comprobación se quita.

DÓNDE PARAR Y ENSEÑARME:

  Cuando un asset pase la auditoría del vecino y otro salga rechazado por ella.

  Enséñame: islas, solape y uso de UV tal y como los publica su auditoría, y el
  comando exacto que produjo cada veredicto.

LO QUE NO ES TU TRABAJO:

  - No reimplementes las auditorías del vecino. Están y funcionan.
  - No sustituyas un proveedor que falta por otro que da menos, sin decirlo.
  - No metas la densa en esta máquina.
  - No toques research/.
  - Si encuentras algo roto fuera del encargo, apúntalo al final y sigue.

CUANDO ACABES, dime: qué etapas añadiste, qué publica cada una, cómo viste fallar
sus pruebas, y el recuento de verify.sh antes y después.
```
