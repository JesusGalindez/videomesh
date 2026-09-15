# Revisión matemática adversarial — Mesh ↔ Gaussian Bridge

**Documento revisado:** `VIDEOMESH_MESH_GAUSSIAN_MATHEMATICAL_BRIDGE_RESEARCH_AND_ARCHITECTURE.md` (3196 líneas, §0–§111)
**Rol:** matemático teórico adversarial / geometría computacional
**Fecha:** 2026-08-13
**Estado:** revisión de investigación. No toca el camino de ejecución V1.1.

Notación: `M` malla, `G` representación gaussiana, `S` superficie latente, `Σ_t` covarianza tangencial (2×2), `S_p` operador de forma (shape operator, 2×2 simétrico en base ortonormal tangente), `κ_1,κ_2` curvaturas principales, `K = κ_1κ_2` curvatura de Gauss, `H = (κ_1+κ_2)/2`, `τ(p)` reach (alcance de Federer).

---

## 1. EXECUTIVE VERDICT

**El puente es recuperable, pero no es sólido como está escrito.** El error no es de detalle: es estructural, y aparece tres veces con la misma forma.

**El defecto central.** Las tres métricas nucleares del documento —`δ_i` (§11), `d_M,i` (§12), `r_⊥,i` (§14)— normalizan por una cantidad que **el propio optimizador controla**: la covarianza de la gaussiana que se está juzgando. En consecuencia:

```text
δ_i    = |d^s| / sqrt(nᵀΣn)     →  0   inflando σ_n
d_M,i² = min (μ-p)ᵀΣ⁻¹(μ-p)     →  0   inflando Σ
r_⊥,i  = nᵀΣn / tr(Σ)           →  0   inflando λ_1 tangencial
```

Ninguna mide fidelidad. Las tres miden *pertenencia*: «¿está la malla dentro de esta mancha?». Como diagnóstico es legítimo. Como término de la energía `L_MG` de §46 es degenerado — el mínimo global se alcanza haciendo las gaussianas infinitamente grandes, que es exactamente lo contrario de lo que se busca. **§46 tal como está escrito optimiza hacia el desastre.**

**El segundo defecto.** `M ≈ S ≈ G` compara objetos de dimensión distinta. La malla induce una medida 2-rectificable `H²⌞M`; la mezcla de gaussianas induce una densidad absolutamente continua respecto a Lebesgue en `R³`. Son **mutuamente singulares**: cualquier divergencia que exija densidad común (KL, χ², Hellinger) da `+∞` siempre, para cualquier malla y cualquier nube. El documento nunca lo dice y por eso el §99 propone `W2` sin advertir que `W2` es de las pocas distancias que sobreviven a esa singularidad — y sobrevive porque descarta la masa, que es información que sí importa.

**El tercer defecto.** Ninguna métrica per-primitiva del documento es invariante a división de gaussianas, y ninguna estadística de §40 (mediana, P95 sobre gaussianas) es invariante a poda. Un mismo campo de radiancia representado con 1M o 4M de splats produce puntuaciones distintas. Para una capa de QA eso es descalificatorio: la métrica mide el *presupuesto de primitivas*, no la calidad.

**Qué se salva, y es mucho.** La separación Geometry Twin / Appearance Twin (§59, §61), la negativa a colapsar apariencia en geometría (§47), la cámara como juez externo (§24), la regla de identidad por `sha256` (§33), y la intuición curvatura↔escala (§17–18) — esta última es correcta en el exponente y recuperable con una derivación honesta que además **produce dos cantidades que el documento trata como parámetros libres**.

**Veredicto:** REFORMULAR. Detalle en §20.

---

## 2. FOUNDATIONAL MODEL

### 2.1 Por qué `M ≈ S ≈ G` no basta

`≈` no está definido. Sin una topología en el espacio de objetos, la frase no tiene contenido falsable. Peor: `M` y `G` no viven en el mismo espacio, así que ni siquiera está claro qué espacio topologizar.

### 2.2 Qué debe ser `S`

**No un manifold liso.** Los objetos reales del alcance V1 (§2 del roadmap: objeto rígido, escena rígida) ya contienen bordes, aristas vivas y láminas finas; el alcance V2 añade vegetación y fibras. Un manifold liso encaja con ninguno.

**Recomendación: `S` es un 2-varifold rectificable con soporte de alcance positivo por trozos.**

```text
S  =  conjunto 2-rectificable  H²-medible
      +  campo de planos tangentes definido H²-c.t.p.
      +  reach τ(p) > 0 salvo en un conjunto singular Σ_sing de dimensión ≤ 1
```

Tres razones, ninguna estética:

1. **El reach es la cantidad que ya se necesita en cuatro sitios del documento** y no aparece en ninguno. Gobierna: unicidad de `Π_M` (§10), radio de validez de la aproximación por plano tangente (§17), ambigüedad de láminas finas (§56), y el umbral a partir del cual una gaussiana abarca dos hojas. Una sola cantidad cierra las cuatro secciones.
2. Los varifolds admiten aristas, bordes y no-manifold sin caso especial. `Σ_sing` es donde `τ = 0`.
3. La medida varifold es **invariante a la teselación** por construcción: `μ_M` depende de la superficie, no de cómo se trianguló. Es la propiedad que §82 pide y que ninguna métrica basada en `faceId` puede tener.

### 2.3 Qué es `G`, de verdad

**Una primitiva 3DGS no es una distribución de probabilidad.** Es un kernel sin normalizar multiplicado por una opacidad aprendida. El documento escribe (§2.1, §5)

```text
G_i(x) = exp(-1/2 (x-μ)ᵀ Σ⁻¹ (x-μ))
```

sin el factor `(2π)^{-3/2}|Σ|^{-1/2}`, y a partir de §12 empieza a usar lenguaje probabilístico (Mahalanobis, y en §99 directamente `N(μ,Σ)`). Los tres objetos hay que separarlos:

```text
kernel          k_i(x) = exp(-½ (x-μ)ᵀΣ⁻¹(x-μ))         adimensional, k_i(μ)=1
medida          ν_i = α_i (2π)^{3/2}|Σ_i|^{1/2} · N(μ_i,Σ_i)   masa m_i
probabilidad    N(μ_i, Σ_i)                              masa 1
```

`Σ` describe la **extensión espacial del splat**, no la incertidumbre de su centro. Confundirlas es la raíz del defecto central de §1: `δ_i` y `d_M,i` son distancias estandarizadas sólo si `Σ` fuera incertidumbre posicional, y no lo es.

Además, la masa `m_i` depende de `α_i` **y** de `|Σ_i|^{1/2}`. Cualquier métrica que normalice a probabilidad (todas las de §99–100) descarta `α_i` por completo: un splat casi transparente y uno opaco, mismo `μ`, misma `Σ`, dan `W2 = 0` entre sí y respecto a cualquier referencia. Para una capa de QA eso es un agujero.

### 2.4 La abstracción propuesta

Dos canales, nunca sumados en un escalar:

```text
CANAL GEOMÉTRICO      medidas sobre posición × orientación (varifolds)
                      μ_M  de la malla
                      μ_G  de las gaussianas con normal válida

CANAL DE APARIENCIA   observables renderizados por cámara
                      no admite representación puramente 3D
```

La razón de no sumarlos es la §18 de este informe: no son identificables el uno del otro sin priors, así que un escalar combinado no tiene interpretación.

---

## 3. EQUATION-BY-EQUATION AUDIT

Escala: **A** correcta / **B** idea correcta, formulación mal / **C** heurística útil, no intrínseca / **D** redundante, subsumida / **E** inválida o engañosa.

| § | Ecuación | Cl. | Motivo |
|---|---|---|---|
| 2.1 | `G_i(x) = exp(-½ ...)` | **B** | Kernel sin normalizar presentado como gaussiana. Separar kernel / medida / probabilidad. Ver §2.3. |
| 2.1 | `Σ = RΛRᵀ` | **A** | — |
| 4 | `ñ_f = (v2-v1)×(v3-v1)`, `A_f` | **A** | — |
| 4 | `p = Σβ_j v_j`, `Σβ=1` | **A** | Correcta como carta local. No global: ver §6 de este informe. |
| 5 | `n_G = e_3` (autovector de `λ_3`) | **B** | Válido sólo con gap espectral. El orden `λ_3 ≤ λ_2` **no basta**. Ver §5 de este informe. |
| 6 | `μ_i = Σβ_j v_j + h_i n_f` | **B** | Única sólo si `\|h\| < τ(p)` y `β` en el interior abierto. Degenera en aristas y vértices. |
| 7 | `Σ_i = R_f diag(σ_u²,σ_v²,σ_n²) R_fᵀ` | **B** | `t_1 = (v2-v1)/‖·‖` ata el marco a la **numeración de vértices**: re-indexar la cara rota el marco. Usar marco por transporte o parametrizar sólo invariantes. |
| 8 | `μ'=Aμ+b`, `Σ'=AΣAᵀ` | **A** | Correcto como pushforward lineal. Aviso en §7 de este informe: `A` discontinua entre caras, y estira el grosor. |
| 9 | `D(x)=Σ w_i k_i(x)`, `S_τ={D=τ}` | **C** | El level set no es invariante a escala de `w`, y `τ` es arbitrario. Sustituir por ocupación booleana, §15 de este informe. |
| 10 | `p_i = Π_M(μ_i)` | **B** | Bien definida sólo dentro del tubo de reach. Fuera, `Π_M` es multivaluada — no es un detalle numérico, es el eje medial. |
| 10 | `d_i^s = (n_i^M)ᵀ(μ_i - p_i)` | **A** | Correcta. Bien condicionada. Se conserva en la base mínima. |
| 11 | `δ^λ = \|d^s\|/sqrt(λ_min)` | **E** | `λ_min` puede corresponder a una dirección sin relación con `n_M`. Sin sentido geométrico. |
| 11 | `δ_i = \|d^s\|/sqrt(nᵀΣn)` | **C→E** | **C** como diagnóstico de pertenencia, **E** como pérdida: minimizable inflando `σ_n`. Ver §1. |
| 12 | `d_M² = min_p (μ-p)ᵀΣ⁻¹(μ-p)` | **D** | Test de pertenencia elipsoidal, subsumido por `(δ, alineación)`. Además la poda BVH es **incorrecta** bajo métrica no euclídea. Ver §3.2 abajo. |
| 13 | `a_n = \|n_Gᵀn_M\|` | **B** | Correcta la invariancia de signo. Mal condicionada cerca de 1 vía `arccos`. |
| 13 | `θ = arccos(\|n_Gᵀn_M\|)` | **B** | Pierde media precisión justo en el régimen bueno. Usar `atan2(‖n_G×n_M‖, \|n_Gᵀn_M\|)`. |
| 14 | `r_⊥ = nᵀΣn / tr(Σ)` | **E** | Ver contraejemplo en §3.1 abajo. No distingue orientación de razón de aspecto. |
| 15 | `P_i = 1 - λ_3/tr(Σ)` | **E** | Da planaridad **máxima** a una aguja (`λ=(1,ε,ε)`), cuyo normal está indefinido. Contraejemplo en §5 de este informe. |
| 16 | `Σ^local = R_MᵀΣR_M`, bloque `c` | **A** | La construcción es correcta y `‖c‖` **sí** es invariante a rotar `t_1,t_2` (`c → R_θᵀc`). El documento acierta aquí. |
| 16 | `E_cpl = ‖c‖/(tr Σ + ε)` | **D** | `c ≠ 0` ⟺ `n` no es autovector de `Σ` ⟺ desalineación. Mide lo mismo que `nᵀΣn - λ_3`. Normalizador otra vez dominado por `λ_1`. |
| 17 | `ε(u,v) ≈ ½\|κ_1u²+κ_2v²\|` | **B** | Truncamiento de Taylor sin resto. Falta la cota de tercer orden y el criterio de norma (sup vs L²). |
| 17 | `r ≲ sqrt(2ε/(κ_max+ε_κ))` | **B** | **Error dimensional**: `κ` es 1/longitud, `ε` es longitud; `ε_κ` debe tener unidades 1/longitud y ser `1/R_max`. Escrito como si fuera un número pequeño adimensional. |
| 18 | `σ_j ∝ sqrt(2ε_s/(\|κ_j\|+ε_κ))` | **B/E** | **B** en el punto elíptico leída como semiejes de la elipse de nivel (es correcta ahí). **E** en el punto hiperbólico: la región admisible es hiperbólica y no acotada, no una elipse. Ver §9 de este informe. |
| 19 | `ρ_G ∝ f(κ,E,V,C)` | **C** | Genérica, sin contenido comprobable. Aceptable como declaración de intención. |
| 20 | `R_f = Σ w φ(f)` | **C** | Idem. Pesos sin fijar; imposible de falsar. |
| 21 | `C_G(p) = Σ q_i k_i(p)` | **E** | **Doble conteo**: `N` copias de la misma gaussiana dan `N·C`. No acotada. `τ_C` con unidades de `q`. Sustituir, §15 de este informe. |
| 22 | `Coverage = ∫I[C≥τ]dA / ∫dA` | **B** | Indicador con umbral arbitrario. Versión continua en §15 de este informe. |
| 25 | `L_D` con máscara y Huber | **A** | Correcta y bien planteada. |
| 26 | `L_N = (1/N)Σ(1-\|N_MᵀN_G\|)` | **A** | — |
| 27 | `IoU` de siluetas | **A** | — |
| 28 | `ΔL_photo = L_M - L_G` | **B** | Comparar dos renderizadores distintos: la diferencia mezcla capacidad de apariencia con geometría. Sólo interpretable con capacidad angular igualada. Ver §18 de este informe. |
| 29 | `Σ_2D ≈ J R_c Σ_3D R_cᵀ Jᵀ` | **B** | Aproximación afín de EWA, válida cerca del eje. Falta el término de dilatación antialias (`+ s·I`, `s≈0.3px`) que 3DGS **sí** aplica: comparar contra una `Σ_2D` derivada de malla sin él compara objetos distintos. |
| 36 | `v_i = Σw_ic / (Σw_c + ε)` | **C** | Razonable. Pesos sin especificar. |
| 37 | `γ_c = \|nᵀv_c\|` | **A** | — |
| 41 | `E_area = Σ A_f E_f / Σ A_f` | **A** | Correcta y **es la forma que da invariancia a teselación**. Debería ser la regla, no una opción. |
| 42 | `E_V = Σ v_i E_i / Σ v_i` | **B** | Correcta en forma; para invariancia a split el peso debe ser **masa** (`α_i\|Σ_i\|^{1/2}`), no visibilidad sola. |
| 45 | `R_obs = R_geo+R_app+R_vis+R_noise+R_model` | **E** | No identificable y además no definida: no hay operador que descomponga un residual de imagen en esos sumandos. Ver §18 de este informe. |
| 46 | `L_MG = Σ λ_k L_k` | **E** | `L_d` y `L_Σ` son degeneradas: mínimo en `Σ → ∞`. Contraejemplo en §4 de este informe. |
| 48 | `r^S + r^A + r^U = 1` | **C** | Modelo de clases latentes no identificable bajo las mismas condiciones que §45. |
| 50 | `N_f ∝ A_f/(πσ_uσ_v)` | **C** | Dimensionalmente consistente (adimensional). Heurística razonable de inicialización. |
| 62 | `δ` invariante a escala uniforme | **A** | La afirmación es **correcta**: `d→sd`, `sqrt(nᵀΣn)→s·sqrt(...)`. Pero es invariante también a inflar un solo splat, que es el bug. |
| 79 | test `δ → δ` bajo escala | **A** | Buen test de conformidad. Se conserva. |
| 96 | `E_LOD = ‖p^master - p^LOD‖` | **A** | — |
| 97 | `E_transport = 1-\|n_mᵀn_L\|` | **A** | — |
| 99 | `W2²` entre gaussianas | **A** | Fórmula correcta (Bures–Wasserstein). Uso problemático: §11 de este informe. |
| 100 | `d_MG = W2(G_M, G_G)` | **B** | `Σ_M` de referencia es **arbitraria** — una superficie no tiene grosor. El término `(σ_n,G - σ_n,M)²` mide una convención. |

### 3.1 Contraejemplo a `r_⊥ = nᵀΣn/tr(Σ)` (§14)

Gaussiana isótropa `Σ = σ²I`. Entonces `r_⊥ = σ²/(3σ²) = 1/3` **sea cual sea la orientación de la malla**. Con un umbral típico `r_⊥ < 0.5 ⇒ alineada`, toda esfera pasa como «alineada con la superficie». Pero una gaussiana isótropa **no tiene normal**: no aporta información de orientación, y la métrica no lo señala, lo aprueba.

Segundo problema: `tr(Σ) = λ_1+λ_2+λ_3` está dominado por `λ_1`. Un disco correctamente alineado pero muy alargado (`λ_1 ≫ λ_2`) y un disco isótropo bien alineado dan valores de `r_⊥` distintos por su razón de aspecto, no por su alineación. La métrica **confunde forma con orientación**.

### 3.2 La poda BVH de §12 es incorrecta

`d_M² = min_p (μ-p)ᵀΣ⁻¹(μ-p)` es una distancia en la métrica de `Σ⁻¹`. El triángulo más cercano en euclídeo **no** es el más cercano en Mahalanobis. Con

```text
d_E / sqrt(λ_1)  ≤  d_M  ≤  d_E / sqrt(λ_3)
```

una poda correcta debe explorar todos los triángulos dentro de radio euclídeo `d_best · sqrt(λ_1/λ_3)`. Para un splat 3DGS típico (`λ_1/λ_3 ~ 10⁴`) eso es un radio **100×** mayor: la poda deja de podar. §85 («use a mesh BVH, query many Gaussian centers») describe un procedimiento que da respuestas equivocadas en silencio.

Arreglo correcto si se conserva la métrica: consulta por **solapamiento elipsoide–AABB** contra el BVH euclídeo, no consulta por radio. Coste aceptable, resultado exacto.

---

## 4. CRITICAL MATHEMATICAL ERRORS

Cuatro cosas a retirar de inmediato.

**E1 — `L_MG` (§46) es degenerada.** Con

```text
L_d = Σ w_i ρ(δ_i),   δ_i = |d_i^s| / sqrt(n_MᵀΣ_i n_M)
L_Σ = Σ w_i (n_MᵀΣ_i n_M) / tr(Σ_i)
```

el gradiente respecto a `σ_n` es negativo en `L_d` (crecer `σ_n` baja `δ`) y el gradiente respecto a `λ_1` es negativo en `L_Σ` (crecer la extensión tangencial baja el cociente). El mínimo conjunto es `Σ → ∞` con `α → 0`. Un optimizador honesto encuentra ese mínimo. **No usar ninguna cantidad normalizada por `Σ` como término de pérdida.**

**E2 — `P_i = 1 - λ_3/tr(Σ)` (§15) miente en el caso degenerado.** Con `λ = (1, ε, ε)` da `P ≈ 1` («máximamente planar») para una **aguja**, cuyo autovector mínimo está indefinido: el subespacio propio de `λ_2 = λ_3` es bidimensional y `e_3` es una elección arbitraria del algoritmo de eigen. La métrica certifica como fiable la única situación en la que el normal no existe.

**E3 — `C_G(p) = Σ q_i k_i(p)` (§21) es una suma, no una cobertura.** Dividir una gaussiana en dos idénticas con `q/2` conserva la suma, pero dividirla en dos con `q` cada una la duplica; y una región cubierta por 50 splats da `C_G ≈ 50`, mientras que el concepto que se quiere medir («¿hay soporte aquí?») está acotado por 1. El umbral `τ_C` entonces depende del presupuesto de primitivas del escenario, no de la geometría.

**E4 — `R_obs = R_geometry + R_appearance + ...` (§45) no es identificable ni está definida.** No existe un operador que descomponga un residual fotométrico en esos cinco sumandos, y aunque existiera, la ambigüedad forma-radiancia (un campo de radiancia con capacidad angular suficiente reproduce cualquier conjunto de imágenes sobre geometría *incorrecta*) garantiza que `R_geometry` y `R_appearance` no son separables sin priors. Detalle en §18.

Además, dos ítems para retirar por redundancia, no por error: `r_⊥` (§14) y `E_coupling` (§16), ambos subsumidos por la cantidad de §7 de este informe.

---

## 5. STRONGEST IDEAS

Lo que hay que conservar, y por qué es correcto y no sólo simpático.

1. **Geometry Twin ≠ Appearance Twin (§59, §61, §47).** Es correcto por la razón dura de §18: geometría y apariencia no son separables sin priors, así que forzar `d(μ_i, M) → 0` para todo splat destruye información recuperable. La advertencia de §47 es la observación más valiosa del documento.

2. **La cámara como juez externo (§24).** Correcto y **más fundamental de lo que el documento afirma**: malla y gaussianas se ajustaron a las mismas imágenes, así que su acuerdo mutuo está contaminado por el error compartido. La consistencia en espacio de observación es la única señal no circular. Ver §13.

3. **`d_i^s = n_MᵀΣ(μ - Π_M(μ))` (§10).** Bien condicionada, invariante rígida, equivariante a escala, sin normalizador libre. Sobrevive a la base mínima.

4. **La identidad por artifact (§33, §70, §94).** `faceId` sólo tiene sentido relativo a un `sha256` exacto. Es la aplicación correcta de D7 del contrato SoftSight y hay que mantenerla literal.

5. **La intuición curvatura↔escala (§17–18).** El exponente `σ ~ sqrt(ε/κ)` es **correcto**; se re-deriva en §9 con la constante exacta y con dos subproductos que el documento trata como parámetros libres.

6. **`E_area` (§41).** Ponderar por área es exactamente lo que da invariancia a teselación. Debería ser regla, no opción.

7. **Reflexión y transparencia no son fallo geométrico (§59, §60).** Correcto, y es la razón de no colapsar los dos canales.

---

## 6. MISSING MATHEMATICS

Lo que falta, ordenado por daño que causa su ausencia.

**M1 — El reach `τ(p)`.** Sin él, `Π_M` no está bien definida, la aproximación por plano tangente no tiene radio de validez, y §56 (láminas finas) no tiene criterio. Es una cantidad, no una heurística: `τ(p) ≥ 1/κ_max` localmente, y acotada por la mitad de la distancia entre dos hojas. Cierra cuatro secciones con una definición.

**M2 — El resto de Taylor.** §17 trunca a segundo orden sin cota del tercero. La cota honesta es
```text
z(u) = ½ uᵀS_p u + R(u),   |R(u)| ≤ (1/6) C_3 ‖u‖³
```
con `C_3` cota de `∇II`. Sin ella, «`ε`» no acota nada fuera de un entorno no especificado.

**M3 — El criterio de norma para `ε`.** §17 nunca dice si `ε` es error puntual máximo (`L^∞`) o cuadrático medio ponderado por el kernel (`L²`). **La respuesta cambia la constante en O(1)** y por tanto el número de gaussianas. Se resuelve en §9.

**M4 — La relación exacta entre `Σ_t` y el operador de forma.** El documento trata `h_i` (offset normal) y `σ_n` (grosor) como parámetros libres. **No lo son:** quedan determinados por `S_p` y `Σ_t`. Derivación en §9. Es el resultado más fuerte de esta revisión.

**M5 — Invariancia a división/fusión y a poda.** Ninguna sección la analiza. Principio general que falta: *una estadística es invariante a división de primitivas si y sólo si es una integral de un campo ponderada por masa.* Las medianas y percentiles sobre gaussianas de §40 no lo son.

**M6 — El gap espectral (Davis–Kahan).** La estabilidad de `e_3` como normal está gobernada por `λ_2 - λ_3`, no por `λ_3`. §5.

**M7 — Simetría.** Todas las métricas son `D(G|M)`. Ninguna detecta superficie de malla que ninguna gaussiana explica — es decir, **ninguna detecta alucinación de malla**, que es precisamente lo que `purelyReconstructed` existe para vigilar (D21 del contrato). §8.

**M8 — La masa.** `α_i` desaparece de todas las métricas geométricas. Un splat transparente pesa igual que uno opaco.

---

## 7. LOCAL CORRESPONDENCE MODEL

### 7.1 La cantidad primitiva: coste de aplanado normal

Propuesta central de esta revisión. Para la gaussiana `i` y el punto `p = Π_M(μ_i)` con normal `n = n_M(p)`, define

```text
E_⊥,i  :=  (d_i^s)²  +  nᵀ Σ_i n                          [longitud²]
```

**Interpretación exacta.** `E_⊥,i` es el coste cuadrático de transporte óptimo de aplanar la gaussiana `i` sobre el plano tangente en `p`:

```text
E_⊥,i = W2²( N(μ_i, Σ_i) ,  P_# N(μ_i, Σ_i) )
```

donde `P` es la proyección ortogonal sobre el plano tangente. La demostración es inmediata: el transporte óptimo bajo proyección mueve cada punto a distancia `|n ᵀ(x - p)|`, y `E[(nᵀ(X-p))²] = (nᵀ(μ-p))² + nᵀΣn = (d^s)² + nᵀΣn`.

**Por qué sustituye a tres métricas del documento.** Descompón `Σ_i = R diag(σ_1²,σ_2²,σ_{n0}²) Rᵀ` con el disco inclinado un ángulo `θ` respecto al plano tangente de la malla. Entonces

```text
nᵀΣ_i n = cos²θ · σ_{n0}²  +  sin²θ · σ_t²
```

de modo que `E_⊥` contiene, en un solo escalar y con la ponderación correcta:

```text
(d^s)²           desplazamiento fuera de superficie      §10, §11
cos²θ σ_{n0}²    grosor del splat                        §14 (r_⊥)
sin²θ σ_t²       desalineación, escalada por el tamaño   §13 (a_n), §16 (coupling)
```

La ponderación correcta importa: un splat diminuto mal orientado daña menos que uno enorme mal orientado, y `a_n = |n_Gᵀn_M|` no distingue los dos casos. `E_⊥` sí.

**Propiedades.**

| Propiedad | Comportamiento |
|---|---|
| Unidades | longitud² |
| Traslación | invariante |
| Rotación | invariante |
| Escala uniforme `s` | `E_⊥ → s² E_⊥` (equivariante, como debe) |
| Normalizador libre | **ninguno** — no se puede bajar inflando `Σ` |
| Nulo exacto | ⟺ el splat es un disco plano contenido en el plano tangente y centrado en `M` |
| Válida sin `n_G` | sí — no requiere gap espectral, funciona en splats isótropos |

La última fila es importante: `E_⊥` está definida para **toda** gaussiana, incluidas las isótropas y las lineales, mientras que toda métrica que use `n_G = e_3` requiere una puerta de validez.

**Versión adimensional.** Sólo cuando haga falta comparar entre escenas:
```text
ê_i = E_⊥,i / ε_geo²
```
con `ε_geo` una **tolerancia declarada del contrato** (longitud fija, del preset de calidad), nunca una cantidad derivada del propio splat.

### 7.2 La puerta de validez del normal

Antes de usar `n_G`, medir forma con los invariantes de Westin:

```text
c_lin  = (λ_1 - λ_2) / λ_1
c_plan = (λ_2 - λ_3) / λ_1        ←  planaridad
c_sph  =  λ_3 / λ_1
c_lin + c_plan + c_sph = 1
```

`c_plan` **es** el gap espectral relativo que gobierna la estabilidad de `e_3` por Davis–Kahan:
```text
sin ∠(e_3, ê_3)  ≤  ‖E‖ / (λ_2 - λ_3)
```
Regla: `n_G` sólo se reporta si `c_plan ≥ c_min`. Con `λ=(1,ε,ε)` (aguja) da `c_plan ≈ 0` y la puerta cierra — que es lo que `P_i = 1-λ_3/tr` no hace.

### 7.3 La correspondencia como objeto

`(faceId, β, h)` **no es la representación fundamental correcta**. Análisis del §6 del documento:

- **Unicidad.** Única sólo si `β` está en el interior abierto del triángulo y `|h| < τ(p)`. En una arista, dos caras dan el mismo punto con `β` distintas. En un vértice, `k` caras. No es un fallo numérico: es que `(faceId, β)` es una **carta**, no una parametrización global, y las funciones de transición son las identificaciones de aristas y vértices de la malla.
- **Láminas finas.** Si dos hojas distan `2t` y el splat tiene `3σ_t > t`, `Π_M` es ambigua y `faceId` es una elección arbitraria estable sólo hasta la siguiente perturbación.
- **Remallado.** Invalida los índices. §94 lo dice bien.
- **Deformación.** `p' = Σβ_j v'_j` es correcto **dentro** de la cara; el marco `R_f` de §7 salta en las aristas porque el mapa afín por trozos es discontinuo en su derivada.

**Representación recomendada:**

```text
CANÓNICO (persistido, sobrevive al remallado)
    μ_i                 centro en el frame canónico RECONSTRUCTION
    Σ_i                 covarianza
    q_i = Π_M(μ_i)      punto de superficie en coordenadas del mundo
    n(q_i)              normal en q_i
    E_⊥,i               la medida
    τ̂(q_i)              reach estimado — condiciona la validez de todo lo anterior
    ambiguo             bandera: ≥2 candidatos dentro de tolerancia relativa

DERIVADO (caché, con clave meshSha256)
    faceId, β_1..β_3, h
```

Encaja con D7 y D29 del contrato SoftSight sin maquinaria nueva: lo canónico es geométrico e independiente de índices; lo indexado es caché atado a un `sha256`, y si el hash cambia se recalcula en vez de mentir.

**Para deformación y rigging (§93)**, la corrección: transformar la parte tangencial por la diferencial de la deformación restringida al plano tangente, y **no** dejar que estire el grosor:

```text
Σ'_t = J_t Σ_t J_tᵀ,     σ'_n = σ_n
```
en vez de `Σ' = AΣAᵀ` completo. Con `AΣAᵀ`, estirar un triángulo al doble engorda el splat fuera de la superficie, que es exactamente lo contrario del objetivo.

---

## 8. GLOBAL REPRESENTATION MODEL

### 8.1 El problema de la simetría

`D(G|M)` no puede detectar malla no explicada. Contraejemplo: duplica una hoja de la malla desplazándola `10ε`. Toda gaussiana sigue teniendo su `E_⊥` pequeño respecto a *alguna* hoja. El puente reporta acuerdo perfecto sobre una malla con superficie inventada — el fallo que D21 (`purelyReconstructed`) existe para prevenir.

Se necesita `D(M,G)` simétrica.

### 8.2 Discrepancia varifold por núcleo

Ambos objetos como medidas sobre posición × orientación no orientada:

```text
μ_M = ∫_M δ_{(p, n(p))} dA(p)                        masa = área total
μ_G = Σ_i m_i δ_{(μ_i, n_{G,i})}   sobre splats con c_plan ≥ c_min
      m_i = α_i · 2π σ_{1,i} σ_{2,i}                 «área efectiva» del splat
```

Distancia por núcleo separable, con `k_dir` invariante al signo del normal:

```text
‖μ_M - μ_G‖²_k  =  ⟨μ_M,μ_M⟩ - 2⟨μ_M,μ_G⟩ + ⟨μ_G,μ_G⟩

k( (x,n), (y,m) )  =  exp(-‖x-y‖²/2σ_k²) · (nᵀm)²
```

`(nᵀm)²` es el núcleo varifold estándar sobre `RP²`: **resuelve la ambigüedad de signo sin caso especial**, que es la pregunta del §9 del prompt.

**Por qué éste y no otro.** Es el único candidato de la lista del documento que cumple las cuatro a la vez:

| | simétrica | sin correspondencia | invariante a teselación | invariante a split |
|---|---|---|---|---|
| Chamfer bidireccional | sí | sí | aprox. | **no** |
| `W2` mezcla-a-mezcla | sí | sí | sí | **no** (masa) |
| OT (Sinkhorn) | sí | sí | sí | sí | 
| **Varifold por núcleo** | **sí** | **sí** | **sí** | **sí** |

OT también las cumple, pero cuesta `O(N²)` por iteración y exige balance de masa que aquí **no existe** (opacidad no es área). Varifold cuesta `O(N log N)` con rejilla o truncamiento del núcleo, y no exige balance: `‖μ_M - μ_G‖²` está definida para medidas de masa distinta, y la diferencia de masa aparece como un término legítimo del resultado en vez de como una normalización arbitraria.

**Invariancia a división, demostrada.** Sustituir el splat `i` por `k` splats con `Σ m_j = m_i` en la misma posición y orientación deja `μ_G` **idéntica** como medida. Toda funcional de `μ_G` hereda la invariancia. Es la razón matemática, no estética, para adoptar el marco.

**Coste real.** `σ_k` fija el truncamiento; con `σ_k` del orden de la escala de splat, el número de pares no despreciables es lineal. Para 1M splats y 5M triángulos es del orden del árbol de triángulos que SoftSight ya midió en D24 (2,56 s / 5M, 85,6 MiB) — mismo orden de magnitud, factible.

### 8.3 Jerarquía de niveles

Nunca colapsar en un escalar:

```text
NIVEL 1   primitiva ↔ parche      E_⊥,i ; c_plan,i ; τ̂ ; bandera de ambigüedad
NIVEL 2   región ↔ región         E_⊥ ponderada por masa sobre parche;
                                  cobertura bidireccional sobre el parche
NIVEL 3   representación completa  ‖μ_M - μ_G‖_k  (simétrica, sin correspondencia)
NIVEL 4   observable de cámara     depth / silueta / fotométrico
```

Los cuatro se reportan por separado. §91 del documento ya avisa de esto y tiene razón.

---

## 9. CURVATURE ↔ GAUSSIAN DERIVATION

Sección de máxima prioridad. Se re-deriva desde cero.

### 9.1 Planteamiento

Coordenadas de curvaturas principales en `p ∈ S`, base ortonormal tangente `(e_1,e_2)`, normal `n`. Con `u = (u_1,u_2)` en el plano tangente:

```text
z(u)  =  ½ uᵀ S_p u  +  R(u),     |R(u)| ≤ (1/6) C_3 ‖u‖³
S_p   =  diag(κ_1, κ_2)      (operador de forma / segunda forma fundamental)
```

El documento se detiene aquí y aplica un criterio puntual. **El criterio correcto para una gaussiana no es puntual**: la gaussiana pondera el plano tangente con densidad `N(0, Σ_t)`, así que el error relevante es el error cuadrático medio ponderado por el kernel.

### 9.2 Los momentos, en forma cerrada

Sea `u ~ N(0, Σ_t)`. Usando la identidad de momentos cuárticos gaussianos `E[(uᵀAu)²] = (tr AΣ)² + 2 tr(AΣAΣ)` para `A` simétrica, y despreciando `R(u)`:

```text
E[z]    =  ½ tr(S_p Σ_t)                                        ①

E[z²]   =  ¼ [ (tr(S_p Σ_t))²  +  2 tr((S_p Σ_t)²) ]            ②

Var(z)  =  ½ tr((S_p Σ_t)²)                                     ③
```

**Consecuencia inmediata, y es el resultado principal.** Un splat superficial óptimo no es un disco plano centrado en la superficie. Debe tener:

```text
offset normal    h*    =  ½ tr(S_p Σ_t)                          [de ①]
grosor           σ_n*² =  ½ tr((S_p Σ_t)²)                       [de ③]
```

Es decir: **`h` y `σ_n`, que §6 y §7 del documento tratan como parámetros libres a ajustar, están determinados por la curvatura y la extensión tangencial.** `h = 0` (§6, «para una gaussiana estrictamente ligada a la superficie») es **incorrecto** salvo en el plano: sesga el splat hacia el lado convexo por `½tr(S_pΣ_t)`.

### 9.3 Valores exactos en las fixtures

Con `Σ_t = diag(σ_1², σ_2²)` en la base principal:

| Superficie | `S_p` | `h* = ½tr(S_pΣ_t)` | `σ_n* = sqrt(½tr((S_pΣ_t)²))` |
|---|---|---|---|
| Plano | `0` | `0` | `0` |
| Esfera `R` (isótropo `σ_t`) | `(1/R)I` | `σ_t²/R` | `σ_t²/R` |
| Cilindro `R` | `diag(1/R,0)` | `σ_1²/(2R)` | `σ_1²/(√2 R)` |
| Silla `κ_1=-κ_2=1/R`, isótropo | `diag(1/R,-1/R)` | `0` | `σ_t²/R` |

Dos predicciones falsables de primer orden:

- **El cilindro no depende de `σ_2`.** Alargar el splat a lo largo del eje no cambia ni el offset ni el grosor. Cualquier regla isótropa basada en `κ_max` falla este test.
- **La silla tiene `h* = 0` pero `σ_n* ≠ 0`.** La curvatura media es cero; el grosor requerido no lo es. **Cualquier regla basada en `H` o en la curvatura media da `σ_n = 0` aquí y es falsa.** Éste es el test que separa una regla correcta de una plausible.

### 9.4 La covarianza tangencial óptima

Ahora sí, el problema de §14 del prompt planteado y resuelto.

**Problema.** Maximizar el soporte tangencial sujeto a error de aproximación acotado:

```text
maximizar    det Σ_t                       (∝ área² de soporte)
sujeto a     E[z²] ≤ ε²                    (criterio L², kernel-ponderado)
             Σ_t ≻ 0
```

**Solución.** Sea `W = Σ_t^{1/2} S_p Σ_t^{1/2}`, simétrica, autovalores `w_1,w_2`. Entonces `tr(S_pΣ_t) = tr W`, `tr((S_pΣ_t)²) = tr(W²)`, y `det Σ_t = det W / det S_p`. La restricción ② queda

```text
3w_1² + 3w_2² + 2w_1w_2  ≤  4ε²
```

que es una elipse en `(w_1,w_2)`. Por la ley de inercia de Sylvester, `W` y `S_p` deben tener la misma signatura.

*Punto elíptico* (`K = det S_p > 0`, `W` definida). Maximizar `w_1w_2 > 0` sobre la elipse da `w_1 = w_2 = ε/√2`, luego

```text
Σ_t*  =  (ε/√2) · S_p⁻¹              ⇒     σ_j*  =  sqrt( ε / (√2 κ_j) )

det Σ_t*  =  ε² / (2K)
```

*Punto hiperbólico* (`K < 0`, `W` indefinida). Maximizar `|w_1w_2|` con `w_1 = -w_2 = w` da `4w² ≤ 4ε²`, `w = ε`:

```text
det Σ_t*  =  ε² / |K|
```

*Punto parabólico* (`K = 0`: cilindro, arista suave). `det Σ_t*` **no acotado**: la dirección asintótica es plana a segundo orden y la restricción no la limita. Aquí manda el reach: `σ ≤ c·τ(p)`.

**Resultados.**

```text
El presupuesto de área tangencial de un splat superficial está
gobernado por la curvatura de GAUSS, no por κ_max:

    área² admisible  ∝  ε² / |K|

    elíptico     det Σ_t* = ε²/(2|K|)
    hiperbólico  det Σ_t* = ε²/|K|          (el doble)
    parabólico   no acotado por curvatura → lo acota el reach
```

**Relación con el documento.** `σ_j ∝ sqrt(ε/κ_j)` de §18 **sobrevive en la forma funcional** y queda derivada en vez de postulada, con la constante `1/√2` y con el criterio de norma explícito (`L²` ponderado por kernel). Con criterio `L^∞` puntual la constante cambia a `sqrt(2)` — factor 2 en `σ`, factor 4 en el número de gaussianas. **Ésa es la razón de que §17 tenga que declarar qué norma usa: el presupuesto de primitivas depende de ello.**

**Y donde §18 falla.** En un punto hiperbólico la región `{½|κ_1u²+κ_2v²| ≤ ε}` es **hiperbólica y no acotada** — se extiende al infinito por las direcciones asintóticas `κ_1u² + κ_2v² = 0`. La regla de §18 aplica en silencio la respuesta elíptica (una elipse de semiejes `sqrt(2ε/|κ_j|)`) en un punto donde la geometría no es elíptica. El tratamiento correcto es el de arriba: `W` indefinida, y el corte por reach y por resto de tercer orden.

### 9.5 Fórmula final recomendada

```text
Σ_t*  determinada por  W = Σ_t^{1/2} S_p Σ_t^{1/2}  con  |det W| = ε²/2 (elíptico)
                                                          ε²   (hiperbólico)
h*    =  ½ tr(S_p Σ_t*)
σ_n*² =  ½ tr((S_p Σ_t*)²)

corte duro:   σ_1*, σ_2*  ≤  c · τ(p),   c ≤ 1/3
              (cubre aristas, láminas finas y curvatura nula con un solo criterio)

en Σ_sing (aristas, esquinas):  S_p no existe.
              no extrapolar curvatura: usar ángulo diedro y partir el splat.
```

---

## 10. COVARIANCE / SPD ANALYSIS

Recomendación con motivo físico, no catálogo.

**El hecho que decide.** Los splats 3DGS son **deliberadamente casi degenerados**: `λ_3/λ_1 ~ 10⁻³–10⁻⁴` es el régimen normal, no la patología. Un splat superficial ideal tiene `λ_3 → 0` exactamente. La geometría correcta es aquella en la que ese límite es un **punto regular del espacio**, no un punto al infinito.

| Geometría | Comportamiento con `λ_3 → 0` | Veredicto |
|---|---|---|
| Frobenius `‖Σ_1-Σ_2‖_F` | finito | Utilizable localmente; no invariante por congruencia; permite salir del cono al interpolar. **Aceptable para perturbaciones pequeñas, no como métrica.** |
| Log-euclídea `‖log Σ_1 - log Σ_2‖_F` | `→ ∞` | **Rechazar.** El caso de uso normal está en el infinito. |
| Afín-invariante `‖log(Σ_1^{-1/2}Σ_2Σ_1^{-1/2})‖_F` | `→ ∞` | **Rechazar,** y por una segunda razón: es invariante bajo `Σ → AΣAᵀ` para toda `A` invertible. Esa invariancia es *excesiva* aquí — hace que un disco y una esfera sean equidistantes bajo el escalado anisótropo adecuado, borrando justo la distinción que el puente necesita medir. |
| **Bures–Wasserstein** `B²=tr(Σ_1+Σ_2-2(Σ_1^{1/2}Σ_2Σ_1^{1/2})^{1/2})` | **finito y liso** | **Recomendada.** |

**Por qué Bures–Wasserstein.** Es la métrica geodésica de `W2` restringida a gaussianas. Los puntos degenerados son medidas perfectamente legítimas (un disco plano *es* una medida gaussiana sobre un plano), así que el borde del cono es alcanzable y la distancia se comporta bien allí. Escala correctamente: `B(s²Σ_1, s²Σ_2) = s·B(Σ_1,Σ_2)`, unidades de longitud. Y es exactamente la parte de covarianza de `W2` entre gaussianas, así que no introduce un objeto nuevo.

**Uso recomendado:** comparar `Σ_2D` en espacio de imagen (§29) — donde la degeneración por vista de canto es inevitable y las otras tres métricas explotan. En 3D, `E_⊥` ya captura lo que importa y `B` es redundante.

---

## 11. WASSERSTEIN ANALYSIS

Análisis profundo, que es lo que el prompt pide.

**Motivación.** Correcta en un sentido y equivocada en otro. `W2` entre gaussianas tiene forma cerrada, es invariante rígida, escala como longitud², y unifica desplazamiento y forma. Todo cierto.

**Problema 1 — la referencia es arbitraria.** `G_M = N(p, Σ_M)` con `Σ_M = R_M diag(σ_1²,σ_2²,σ_n²) R_Mᵀ` exige elegir `σ_n` para una superficie, que **no tiene grosor**. El término resultante `(σ_{n,G} - σ_{n,M})²` mide una convención, no la escena. Y `σ_1, σ_2` de la malla son igualmente arbitrarias salvo que se tomen del resultado de §9.4 — en cuyo caso `W2` no aporta nada que `E_⊥` no dé ya.

**Problema 2 — descarta la masa.** `W2` está definida entre medidas de probabilidad. Normalizar `G_G` a masa 1 descarta `α_i`. Dos splats con la misma geometría y opacidades 0,01 y 0,99 son indistinguibles. Para QA es inaceptable.

**Problema 3 — mezcla dos preguntas distintas en un escalar.** `W2² = ‖Δμ‖² + B²(Σ_1,Σ_2)`. Dimensionalmente consistente (ambos longitud²), así que la objeción del prompt («¿combina indebidamente?») **no** es una objeción dimensional. Pero sí diagnóstica: un `W2` alto no distingue «bien colocada, mal orientada» de «mal colocada, bien orientada», y esas dos tienen causas distintas (error de malla vs artefacto de optimización, casos C y D de §23). Colapsarlas destruye precisamente la matriz diagnóstica que el documento construye en §23.

**Problema 4 — no invariante a división.** Dividir un splat en dos hijos desplazados cambia `W2` per-primitiva de forma arbitraria.

**Qué se conserva.** La descomposición, no el escalar:

```text
‖Δμ‖²           →  ya está en E_⊥ (componente normal) + deriva tangencial
B²(Σ_G, Σ_M*)   →  útil SOLO con Σ_M* = la covarianza óptima de §9.4,
                    y entonces mide «¿es este splat del tamaño que la
                    curvatura permite?» — una pregunta legítima y nueva
```

Eso último sí es valioso y no está en el documento: `B²(Σ_G, Σ_t*)` es un **test de presupuesto de curvatura** falsable.

**Veredicto: MÉTRICA SECUNDARIA.** No núcleo, no rechazada. Concretamente:

```text
RECHAZADO   W2 como métrica global mezcla↔mezcla
RECHAZADO   W2 como reemplazo unificado de distancia + normal + covarianza (§99)
SECUNDARIO  B²(Σ_G, Σ_t*)  como test de escala frente a curvatura
CONSERVAR   Bures–Wasserstein como geometría SPD para Σ_2D  (§10)
```

---

## 12. VARIFOLD / OPTIMAL TRANSPORT ANALYSIS

El prompt pide explícitamente no recomendar por elegancia. Coste y beneficio para cada uno.

### Varifolds — **RECOMENDADO** como nivel 3

```text
beneficio matemático    única construcción de la lista que es simultáneamente
                        simétrica, sin correspondencia, invariante a teselación
                        e invariante a división. Resuelve el signo del normal
                        gratis vía RP².
coste computacional     O(N log N) con rejilla o truncamiento del núcleo;
                        mismo orden que el árbol de triángulos de D24
complejidad             media — un núcleo, una rejilla, sin optimización iterativa
valor práctico          ALTO. Es la única respuesta a la pregunta
                        «¿esta malla y esta nube describen la misma superficie?»
                        que no depende del presupuesto de primitivas
parámetro libre         σ_k (ancho del núcleo). Uno solo, con significado
                        físico: la escala espacial por debajo de la cual no
                        se distingue. Declarable en el contrato.
```

### Transporte óptimo — **RECHAZADO** como núcleo, investigación

```text
beneficio matemático    la correspondencia emerge del plan; métrica genuina
coste computacional     Sinkhorn O(N²) por iteración, decenas de iteraciones.
                        Para 10⁶ splats × 10⁶ muestras de malla, inviable
complejidad             alta — regularización entrópica, escalado, convergencia
valor práctico          BAJO en el estado actual
problema estructural    OT exige balance de masa. Opacidad NO es área
                        superficial: no existe normalización canónica entre
                        Σα_i y el área de M. Cualquier elección es un
                        parámetro arbitrario que contamina la métrica.
                        Varifolds no lo necesitan.
```

**Excepción, y es la que se usa.** El transporte óptimo **1D en la dirección normal** es trivial y de forma cerrada: es exactamente `E_⊥ = W2²(N(d^s,σ_n²), δ_0)`. Es decir, el marco de OT ya está en la base mínima, en la única dimensión donde es gratis.

### SDF como intermedio — **NO** como puente primario

```text
sign ambiguity    una malla reconstruida abierta o no-manifold NO tiene signo.
                  El alcance V1 produce exactamente esas mallas.
UDF               resuelve el signo pero su gradiente es discontinuo en la
                  superficie: los normales por gradiente no existen ahí,
                  que es donde se necesitan
Gaussianas→SDF    no canónico. GOF usa un level set de opacidad por rayo,
                  no la suma aditiva de §9 del documento. Elegir una
                  definición es introducir un tercer objeto que también
                  hay que certificar
coste             discretización volumétrica O(n³)
```

Uso legítimo: **distancia sin signo truncada a `M`** como campo compartido para visualización y regularización. Nunca como definición del puente.

---

## 13. CAMERA-EVIDENCE MODEL

La pregunta teórica clave del prompt: ¿`M ↔ observaciones ↔ G` o `M ↔ G`?

**Respuesta: las observaciones son más fundamentales, y por una razón que el documento roza en §24 sin desarrollar.**

`M` y `G` se ajustaron **a las mismas imágenes**. Su acuerdo mutuo está contaminado por el error compartido: una mala calibración, una escala equivocada o un sesgo del SfM producen una malla y una nube que coinciden bien entre sí y mal con la realidad. `D(M,G)` pequeña **no** es evidencia de corrección; es evidencia de origen común. Esto es exactamente lo que §24 dice y lo que el resto del documento (§10–§22, todas las métricas 3D) contradice al colocar `D(G|M)` como núcleo.

**Formulación correcta.** El puente se define por equivalencia de observables, no por proximidad euclídea:

```text
Para cada cámara c con visibilidad válida compartida W^c:

    r_D^c  =  ρ( D_M^c - D_G^c )            profundidad
    r_N^c  =  1 - |N_M^c ᵀ N_G^c|           normal
    r_S^c  =  1 - IoU(S_M^c, S_G^c)         silueta
```

y la proximidad 3D (`E_⊥`, varifold) es una **condición necesaria adicional**, no la definición. Motivo: los observables no determinan la geometría (§18), así que hacen falta las dos familias — pero la autoridad está en las imágenes.

**Correcciones al material de cámara del documento.**

- §25 `L_D`: correcta. Añadir que `D_G^c` debe declarar su `depthKind` — D20 del contrato exige `OPTICAL_AXIS | RAY_LENGTH` sin valor por defecto, y la profundidad de 3DGS es una **esperanza ponderada por alpha a lo largo del rayo**, que no es ninguna de las dos sin declararlo. Sin eso, `L_D` compara dos cosas distintas con precisión numérica alta.
- §26 `L_N`: correcta.
- §28 `ΔL_photo`: **interpretable sólo con capacidad angular igualada.** Un modelo de apariencia con SH de orden 3 explica reflexiones que uno de orden 0 no; la diferencia `L_M - L_G` mide entonces capacidad de apariencia, no geometría faltante. El documento avisa del riesgo en prosa pero la ecuación no lo controla. Corrección: reportar `ΔL_photo(orden)` como **curva** en el orden de SH, no como escalar. Si la ventaja de `G` desaparece al bajar el orden, era apariencia; si persiste, es geometría. Eso sí es falsable.
- §29 `Σ_2D`: añadir el término de dilatación antialias.

---

## 14. INVARIANCE TABLE

`inv` = invariante, `equiv(s^k)` = escala como `s^k`, `no` = cambia arbitrariamente.

| Cantidad | Trasl. | Rot. | Escala unif. | Escala anisótropa | Reteselado | Split gaussiano | Fusión |
|---|---|---|---|---|---|---|---|
| `d_i^s` (§10) | inv | inv | equiv(s) | no | inv* | no | no |
| `δ_i` (§11) | inv | inv | **inv** | no | inv* | no | no |
| `d_M,i` (§12) | inv | inv | inv | no | inv* | no | no |
| `a_n = \|n_Gᵀn_M\|` (§13) | inv | inv | inv | no | inv* | no | no |
| `r_⊥` (§14) | inv | inv | inv | no | inv* | no | no |
| `P_i` (§15) | inv | inv | inv | no | — | no | no |
| `E_coupling` (§16) | inv | inv | inv | no | inv* | no | no |
| `C_G(p)` (§21) | inv | inv | no | no | inv | **no (dobla)** | **no** |
| `Coverage` (§22) | inv | inv | no (τ) | no | inv | no | no |
| mediana/P95 sobre splats (§40) | inv | inv | según base | no | inv* | **no** | **no** |
| **`E_⊥,i`** | inv | inv | equiv(s²) | no | inv* | no | no |
| **`c_plan`** | inv | inv | inv | no | — | no | no |
| **`E_⊥` pond. por masa** | inv | inv | equiv(s²) | no | inv* | **inv** | **inv** |
| **`O(p) = 1-e^{-λ(p)}`** | inv | inv | no | no | inv | **inv** | **inv** |
| **Coverage continua** | inv | inv | no | no | inv | **inv** | **inv** |
| **`‖μ_M-μ_G‖_k`** | inv | inv | equiv(s^k) | no | **inv** | **inv** | **inv** |
| `W2(G_M,G_G)` (§99) | inv | inv | equiv(s) | no | inv* | no | no |
| Residuales de cámara (§25–28) | inv | inv | inv | no | inv | inv | inv |

`inv*` = invariante a la teselación **sólo** hasta el error de discretización del normal y del punto más próximo; los valores de `faceId` y `β` cambian legítimamente (§82 lo dice bien).

**El principio que falta en el documento y que explica toda la columna de split:**

> Una estadística es invariante a división/fusión de primitivas **si y sólo si** es una integral de un campo ponderada por masa. Toda media, mediana o percentil no ponderado sobre el conjunto de gaussianas depende del presupuesto de primitivas y no de la escena.

Corolario operativo, que corrige §40 y §42: todo agregado se pondera por `m_i = α_i·2π σ_1σ_2` (masa efectiva) o por área de malla. Las medianas sin ponderar del documento no pueden ser métricas de nivel de representación.

---

## 15. NUMERICAL STABILITY

Distinguiendo, como pide el prompt, entre arreglo numérico y cambio de definición.

**Cambios de definición (afectan el resultado, deben declararse):**

| Situación | Definición correcta |
|---|---|
| `C_G(p)` no acotada | Sustituir por intensidad `λ(p) = Σ α_i k_i(p)` y ocupación `O(p) = 1 - exp(-λ(p)) ∈ [0,1]`. **`O` es exactamente invariante a dividir un splat en `k` copias con `α/k`**, porque `λ` es aditiva y la suma se conserva. La forma producto `1-Π(1-α_ik_i)` sólo lo es asintóticamente. |
| Cobertura con umbral | `Coverage = ∫_M O(p) dA / ∫_M dA`, continua, sin `τ`. |
| `Π_M` multivaluada | No elegir en silencio. Reportar bandera `AMBIGUOUS` cuando ≥2 candidatos dentro de tolerancia relativa; desempatar por índice de triángulo ascendente (mismo patrón que D24 de SoftSight). |
| `n_G` sin gap espectral | Puerta `c_plan ≥ c_min`; si no pasa, `n_G` es `null` con motivo, no un vector arbitrario. |

**Arreglos numéricos (no cambian la definición):**

```text
Σ⁻¹              nunca formarla. Cholesky y resolver. κ(Σ)~10⁶ en splats
                 finos ⇒ Mahalanobis pierde ~6 dígitos decimales
eigen 3×3        Jacobi cíclico, no la fórmula cerrada por el discriminante:
                 ésta pierde precisión justo cuando λ_2≈λ_3, que es donde
                 el gap decide la validez del normal
ángulo normal    θ = atan2( ‖n_G × n_M‖ , |n_Gᵀn_M| )
                 NUNCA arccos(|·|): pierde media precisión cerca de 1,
                 que es el régimen bueno y por tanto el que más se mide
punto-triángulo  algoritmo por regiones de Voronoi (Ericson), no inversión
                 de la matriz baricéntrica: degenera con triángulos finos
triángulo degen. A_f ≤ ε_A ⇒ excluir de la superficie y registrarlo,
                 no regularizar en silencio (§83 del documento acierta)
reducciones      D28 del contrato aplica literal: bloques definidos por
                 índice de entrada y tamaño fijo, NUNCA por número de
                 workers; reducción final por índice de bloque ascendente.
                 La integral de cobertura es una suma sobre muestras y
                 cae de lleno en esta regla.
no finitos       D17: rechazar en origen. Un Σ con un Infinity produce
                 un E_⊥ = Infinity que se propaga a la mediana sin avisar
```

**Diagnóstico de condicionamiento a publicar junto a cada medida:** `κ(Σ_i) = λ_1/λ_3`, `c_plan,i`, y `d_i/τ̂(q_i)`. Sin ellos, un `E_⊥` pequeño no distingue «bien» de «mal condicionado».

---

## 16. MINIMAL MATHEMATICAL BASIS

Cinco cantidades. El documento propone del orden de veinte.

```text
B1   E_⊥,i = (d_i^s)² + n_MᵀΣ_i n_M                        [longitud²]
     coste W2 de aplanar el splat sobre el plano tangente
     SUBSUME: distancia con signo, alineación de normales, grosor,
              r_⊥, acoplamiento tangente-normal, δ, Mahalanobis

B2   c_plan,i = (λ_2-λ_3)/λ_1                              [adimensional]
     gap espectral; puerta de validez de n_G (Davis–Kahan)
     SUBSUME: planaridad, «flatness», la validez de todo lo que use n_G

B3   O(p) = 1 - exp(-Σ_i α_i k_i(p))                       [adimensional, [0,1]]
     ocupación booleana; cobertura = ∫_M O dA / ∫_M dA
     SUBSUME: campo de soporte, cobertura por umbral

B4   ‖μ_M - μ_G‖_k   sobre R³ × RP²                        [depende del núcleo]
     discrepancia varifold simétrica, sin correspondencia
     SUBSUME: acuerdo global, alucinación de malla, invariancia
              a teselación y a división

B5   {r_D^c, r_N^c, r_S^c, ΔL_photo(orden SH)}             [según canal]
     residuales en espacio de observación — el juez externo
     SUBSUME: toda la sección §24–§29
```

**Independencia, con testigo explícito para cada par** (esto es lo que convierte la lista en una base y no en un catálogo):

| Testigo | `B1` | `B2` | `B3` | `B4` |
|---|---|---|---|---|
| Splats isótropos correctamente colocados | bajo | **0** | alto | medio |
| Malla con una hoja duplicada a `10ε` | **bajo** | alto | alto | **alto** |
| Splats correctos pero sólo en la mitad del objeto | bajo | alto | **bajo** | alto |
| Un splat gigante bien alineado que cubre todo | alto | alto | **alto** | alto |
| Malla y nube coherentes entre sí, ambas con la escala mal | bajo | alto | alto | **bajo** (`B5` alto) |

Cada fila mueve una coordenada dejando las otras: ninguna es función de las demás. La última fila es la que justifica que `B5` no sea prescindible.

**Lo que se elimina:** `δ` (§11), `d_M` (§12), `a_n` y `θ` y `E_n` (§13), `r_⊥` y `r_∥` (§14), `P_i` (§15), `E_coupling` (§16), `C_G` como suma (§21), `Coverage` con umbral (§22), `L_MG` (§46), `W2` como métrica unificada (§99–100), la descomposición de residuales (§45).

De veinte a cinco. Las eliminadas siguen siendo **derivables** de la base para presentación humana (`θ` es legible, `E_⊥` no); pero no son cantidades independientes ni pueden ser puertas de certificación.

---

## 17. REVISED MATHEMATICAL ARCHITECTURE

```text
                        EVIDENCIA MULTIVISTA
                    imágenes · CameraSet · FrameGraph
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
         PIPELINE GEOMÉTRICO             PIPELINE DE APARIENCIA
                 │                               │
                 ▼                               ▼
              MALLA M                      GAUSSIANAS G
         2-varifold rectificable      medida con masa m_i=α_i·2πσ_1σ_2
                 │                               │
                 │  ┌────────────────────────────┘
                 │  │
                 ▼  ▼
        ╔═══════════════════════════════════════════════════╗
        ║   ACOPLAMIENTO DE MEDIDAS SUPERFICIALES           ║
        ║                                                   ║
        ║   NIVEL 1  primitiva ↔ parche                    ║
        ║     E_⊥,i    c_plan,i    τ̂(q_i)    ambiguo       ║
        ║                                                   ║
        ║   NIVEL 2  región ↔ región                       ║
        ║     E_⊥ pond. masa   ·   cobertura bidireccional  ║
        ║                                                   ║
        ║   NIVEL 3  representación ↔ representación       ║
        ║     ‖μ_M - μ_G‖_k    simétrica, sin corresp.     ║
        ╚═══════════════════════════════════════════════════╝
                 │                               │
                 └───────────────┬───────────────┘
                                 ▼
        ╔═══════════════════════════════════════════════════╗
        ║   NIVEL 4  CONSISTENCIA EN ESPACIO OBSERVADO      ║
        ║     r_D^c   r_N^c   r_S^c   ΔL_photo(orden SH)    ║
        ║     ── AUTORIDAD: no circular ──                  ║
        ╚═══════════════════════════════════════════════════╝
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
        propuesta de refinamiento         evidencia de QA
        (VideoMesh propone)               (SoftSight certifica)
```

**Definiciones formales.**

```text
DEF 1  Superficie latente
       S es un 2-varifold rectificable con reach τ(p) > 0 fuera de un
       conjunto singular Σ_sing de dimensión ≤ 1.

DEF 2  Medida varifold de la malla
       μ_M = ∫_M δ_{(p, n(p))} dA(p)   sobre  R³ × RP²

DEF 3  Medida varifold de las gaussianas
       μ_G = Σ_{i : c_plan,i ≥ c_min} m_i δ_{(μ_i, n_{G,i})}
       m_i = α_i · 2π σ_{1,i} σ_{2,i}

DEF 4  Coste de aplanado normal
       E_⊥,i = W2²( N(μ_i,Σ_i), P_{T_{q_i}}# N(μ_i,Σ_i) )
             = (d_i^s)² + n_MᵀΣ_i n_M
       con q_i = Π_M(μ_i), definido sólo si |d_i^s| < τ̂(q_i)

DEF 5  MeshGaussianCorrespondence — SEMIACOPLAMIENTO
       π : I × F → R≥0   con   Σ_f π_{if} = m_i    ∀i
       (marginal del lado gaussiano fijada por la masa;
        marginal del lado malla LIBRE — no hay balance de masa)

       Fase 1: π_{if} = m_i · 1[f = argmin d]        asignación dura
       Fase 2: π_{if} ∝ m_i · exp(-E_⊥,if / 2h²)     asignación blanda
       La misma estructura formal cubre las dos fases.

DEF 6  Ocupación
       λ(p) = Σ_i α_i k_i(p)          intensidad, aditiva
       O(p) = 1 - exp(-λ(p))          ocupación booleana, [0,1]
```

`DEF 5` responde a la pregunta de §33 del prompt: no es una tupla, ni un mapa, ni un plan de transporte completo. Es un **semiacoplamiento**: coupling con una sola marginal fijada. Es la formalización honesta porque la masa gaussiana y el área de malla **no son comparables** y forzar balance introduce un parámetro arbitrario. La asignación dura de la Fase 1 es el caso Dirac del mismo objeto, así que la evolución Fase 1 → Fase 2 que pide §35 del documento no cambia el tipo, sólo el soporte.

**Nombre.** `MeshGaussianBridge` describe una relación entre dos representaciones. Lo que la matemática soporta es un acoplamiento entre dos **medidas superficiales**, con la superficie latente como objeto central y las cámaras como autoridad. `SurfaceMeasureCoupling` sería más fiel. **Pero no recomiendo renombrar todavía**: el nombre no es el cuello de botella, y §104 del documento ya dice bien que no se congelen nombres públicos antes de tener medidas.

---

## 18. PROPOSED MG-R0 TEST SPECIFICATION

Cada fixture con el valor exacto esperado. Todas analíticas, todas deterministas, ninguna necesita reconstrucción.

### MG-F1 — Plano

```text
malla     cuadrado unitario, normal +z, teselado a 2 y a 512 triángulos
splats    disco σ_1=σ_2=σ_t, σ_n=0, centrado en z=0

esperado  E_⊥ = 0                              exacto a precisión de máquina
          c_plan = 1                            (λ_3=0)
          h* = 0,  σ_n* = 0                     de la derivación §9
          ‖μ_M-μ_G‖_k con teselado 2 vs 512:  IDÉNTICO a tolerancia de cuadratura
          cobertura → 1
```
Falsa: cualquier métrica dependiente de teselación.

### MG-F2 — Esfera de radio `R`

```text
esperado  h*    = σ_t²/R                        offset ≠ 0 en superficie curva
          σ_n*  = σ_t²/R
          det Σ_t* = ε² R²/2                    K = 1/R²
```
Falsa: `h = 0` de §6 del documento. Test: fijar `σ_t` y `R`, ajustar un splat por mínimos cuadrados a la superficie, comprobar que el offset óptimo es `σ_t²/R ± tol` y no cero.

### MG-F3 — Cilindro de radio `R`

```text
esperado  h*    = σ_1²/(2R)
          σ_n*  = σ_1²/(√2 R)
          INDEPENDIENTE de σ_2                  ← el test
          det Σ_t* no acotado (K=0) ⇒ manda el corte por reach
```
Falsa: toda regla isótropa basada en `κ_max`. Test: duplicar `σ_2` y comprobar que `σ_n*` **no cambia**.

### MG-F4 — Silla `κ_1 = -κ_2 = 1/R`

```text
esperado  h*    = 0                             (curvatura media nula)
          σ_n*  = σ_t²/R  ≠ 0                   ← el test
          det Σ_t* = ε² R²                      (el DOBLE del elíptico)
```
Falsa: **toda regla basada en la curvatura media `H`**, que aquí predice grosor cero. Es el test más discriminante del conjunto.

### MG-F5 — Cubo (aristas y esquinas)

```text
esperado  en Σ_sing (aristas): S_p NO EXISTE ⇒ la implementación debe
          devolver UNDEFINED con motivo, no extrapolar curvatura
          splat que cruza una arista de 90°: c_plan cae por debajo del umbral
          ⇒ n_G = null con motivo
          τ(p) = 0 en la arista ⇒ E_⊥ no definida ahí
```
Falsa: cualquier estimador de curvatura que devuelva un número finito en una arista viva sin declararlo aproximación.

### MG-F6 — Dos planos paralelos a distancia `2t`

```text
esperado  reach τ = t exactamente
          splat con 3σ_t > t: Π_M ambigua ⇒ bandera AMBIGUOUS, no elección
          silenciosa
          E_⊥ respecto de la hoja «equivocada» puede ser MENOR ⇒ el test
          comprueba que se reporta la ambigüedad, no que se acierte
          ‖μ_M-μ_G‖_k: DEBE distinguir «una hoja» de «dos hojas»,
          mientras que E_⊥ per-primitiva NO puede
```
Éste es el test que justifica el nivel 3. Es también el caso de §55 (topología) hecho falsable.

### MG-F7 — Toro `(R, r)`

```text
La mejor fixture del conjunto: contiene las tres regiones en un objeto

          exterior      K > 0    elíptico      det Σ_t* = ε²/(2K)
          círculos sup/inf  K = 0  parabólico  no acotado por curvatura
          interior      K < 0    hiperbólico   det Σ_t* = ε²/|K|

esperado  el presupuesto de área de splat, medido a lo largo del ángulo
          poloidal, debe seguir ε²/|K| con la discontinuidad en K=0
          gestionada por el corte de reach, y con el FACTOR 2 entre
          las ramas elíptica e hiperbólica
```
Falsa: cualquier regla monótona en `κ_max` — que predice un presupuesto continuo y sin el salto de factor 2.

### MG-F8 — Invariancia a división

```text
partir cada gaussiana en k copias colocadas con α/k
esperado  λ(p), O(p), cobertura, ‖μ_M-μ_G‖_k, E_⊥ ponderada por masa
              IDÉNTICOS a precisión de máquina
          mediana/P95 sin ponderar de E_⊥: CAMBIAN  ⇒ se documenta que
              esas estadísticas NO son de nivel de representación
```

### MG-F9 — Invariancia rígida y a escala

```text
x → Rx + b                E_⊥, c_plan, cobertura, ‖·‖_k  invariantes
x → sx, Σ → s²Σ           E_⊥ → s²E_⊥;  c_plan, cobertura invariantes;
                          δ (si se conserva para presentación) → δ
```
Conserva los tests §79–81 del documento, que están bien planteados.

### MG-F10 — Degeneración del optimizador (test negativo)

```text
Partiendo de un splat con E_⊥ correcto, inflar Σ por un factor 10:
esperado  E_⊥  AUMENTA
          δ (§11)      DISMINUYE      ← demuestra el defecto E1
          d_M (§12)    DISMINUYE      ← ídem
          r_⊥ (§14)    puede disminuir ← ídem
```
Este test debe **fallar deliberadamente** con las métricas del documento y pasar con la base mínima. Es la prueba que exige el criterio de cierre del contrato: *falla si la decisión se incumple*.

---

## 19. OPEN RESEARCH QUESTIONS

1. **¿Cuál es la constante correcta en `E[z²] ≤ ε²`?** Elegimos criterio `L²` ponderado por kernel. El criterio `L^∞` a `3σ` da otra constante y otro presupuesto de primitivas. La pregunta es empírica: ¿cuál correlaciona con el error de vista sintetizada? Medible con MG-F2/F7.

2. **¿Cómo se define `m_i` (masa efectiva)?** `α_i·2πσ_1σ_2` es una elección. Alternativas: masa integrada `α_i(2π)^{3/2}|Σ|^{1/2}`, o contribución renderizada acumulada sobre las cámaras. La segunda es la físicamente honesta pero depende de la vista. Sin resolver.

3. **El ancho de núcleo `σ_k` del varifold.** Determina la escala espacial por debajo de la cual las dos representaciones se consideran iguales. ¿Se fija por el preset de calidad, por el reach mediano, o por la escala mediana de splat? La tercera lo hace dependiente de `G`, que es lo que se quiere evitar.

4. **Estimación de `S_p` sobre malla ruidosa.** Toda la §9 supone `S_p` conocido. En malla reconstruida el estimador (Taubin, cuádrica ajustada, tensor de curvatura) tiene sesgo y varianza que no están caracterizados, y la fórmula `σ_n* = sqrt(½tr((S_pΣ_t)²))` es cuadrática en `S_p`: el ruido no se promedia a cero. **Es la mayor incógnita práctica de la propuesta.**

5. **Estimación del reach.** `τ(p)` es global (depende de hojas lejanas), no local. Aproximarlo requiere una consulta de eje medial. ¿Basta `min(1/κ_max, ½·distancia a la superficie no local más próxima)`?

6. **Identificabilidad cuantitativa.** ¿A partir de qué orden de SH y qué línea base angular queda `R_geometry` separable? Existe la formulación como test de modelos anidados; falta la potencia estadística.

7. **¿Es `E_⊥` una energía útil como pérdida diferenciable, o sólo como diagnóstico?** Es diferenciable y no degenerada, pero su mínimo empuja `σ_n → 0`, que puede dañar la calidad de renderizado. Probablemente necesita el término de §9.4 como referencia en vez de cero.

8. **Splats de apariencia legítimos.** La base mínima los mide como `E_⊥` alto. Distinguirlos de errores requiere el nivel 4 y la curva de SH del §13. Falta el estimador.

---

## 20. FINAL RECOMMENDATION

**REFORMULAR.** Ni KEEP ni REJECT.

La arquitectura conceptual —dos twins separados, superficie latente común, cámara como juez, artefacto de relación atado a `sha256`— es correcta y hay que conservarla íntegra. Las matemáticas que la implementan hay que rehacerlas: tres de las cuatro métricas nucleares son degeneradas como pérdida, ninguna métrica per-primitiva es invariante al presupuesto de primitivas, y la relación curvatura↔escala está postulada donde puede derivarse.

**Qué hacer, en orden:**

```text
1  RETIRAR    L_MG (§46) y toda cantidad normalizada por Σ como pérdida
              δ, d_M, r_⊥, E_coupling, P_i, C_G como suma,
              R_obs = ΣR (§45)

2  ADOPTAR    E_⊥ = (d^s)² + nᵀΣn        como cantidad primitiva
              c_plan = (λ_2-λ_3)/λ_1     como puerta de validez del normal
              O(p) = 1 - exp(-λ(p))      como ocupación
              ponderación por masa en TODO agregado

3  DERIVAR    h* = ½tr(S_pΣ_t)  y  σ_n*² = ½tr((S_pΣ_t)²)
              en vez de tratarlos como parámetros libres
              det Σ_t* = ε²/(2|K|) elíptico, ε²/|K| hiperbólico

4  AÑADIR     el reach τ(p) — cierra §10, §17, §55 y §56 con una definición
              simetría vía varifold (nivel 3)
              la autoridad del nivel 4 sobre los niveles 1–3

5  PROBAR     MG-F1..F10 antes de escribir una sola métrica de producción.
              MG-F4 (silla) y MG-F10 (degeneración) son los decisivos:
              el primero falsa toda regla de curvatura media, el segundo
              falsa las métricas actuales por construcción.
```

**Sobre el nombre `MeshGaussianBridge`:** conservarlo por ahora. La matemática soporta mejor `SurfaceMeasureCoupling`, pero renombrar antes de tener las medidas de MG-R0 sería exactamente el tipo de decisión de arquitectura sin evidencia que el contrato SoftSight prohíbe en §1.6.

**Encaje con el contrato existente.** La propuesta refuerza tres decisiones ya ACORDADAS en lugar de tensionarlas: D28 (`MeasurementClass`/`ReproducibilityMode` — `E_⊥` es `EXACT` + `BITWISE_EXACT`; la cobertura es `DETERMINISTIC_APPROXIMATION` + `BITWISE_EXACT` con bloques por índice; la curvatura es `DETERMINISTIC_APPROXIMATION` dependiente del estimador), D21 (`purelyReconstructed` — el nivel 3 es lo único capaz de detectar malla alucinada, que es justo lo que la bandera vigila), y D7 (identidad por `sha256` — lo canónico es geométrico, `faceId` es caché).

**Y una advertencia de alcance.** Nada de esto entra en V1.1. El camino crítico sigue siendo Sprint 0A y R0-B. Este documento es material de V1.x/V2 y su primer entregable falsable es MG-R0, que no necesita ni gaussianas reales ni reconstrucción: se ejecuta entero sobre las siete fixtures analíticas.
