# Mesh ↔ Gaussian — Ronda 3

**Responde a:** `VIDEOMESH_MESH_GAUSSIAN_ROUND2_MATHEMATICAL_RESPONSE.md` (3920 líneas)
**Fecha:** 2026-08-13
**Estado:** investigación. No toca V1.1.

Estructura: concesiones primero, refutación después, resultados nuevos, y al final el filtro
de lo que sirve para VideoMesh y lo que se descarta.

---

## 0. Resumen

La ronda 2 es buena. Tres de sus objeciones son correctas y las concedo sin matices.
Una de sus propuestas —`E_surf` como CORE-A— **reintroduce exactamente el defecto que la
ronda 1 identificó**, y lo demuestro con un contraejemplo numérico dentro de su propio
régimen de validez.

Y de su corrección sale, sin que ninguno de los dos lo dijera, la ley más simple y más
falsable de todo el programa:

```
σ_n*  =  ε        siempre, en todo punto, sea cual sea la curvatura
```

Con dos consecuencias: el grosor deja de ser un parámetro aprendido y pasa a ser una
constante declarada del contrato; y la curvatura solo determina los **ejes tangenciales**.

Hay además un efecto que ninguna de las dos rondas vio y que importa para un producto de
metrología: el offset `h*` introduce un **sesgo sistemático de escala** de orden `ε`.

---

## 1. CONCEDIDO — C4: el factor 2 no existe

Su corrección es correcta y la concedo entera.

Mi error fue interno, no de cálculo: derivé `h* = ½tr(S_pΣ_t)` como centro óptimo y acto
seguido usé `E[z²]` —el segundo momento **no centrado**— como restricción. Si el centro
puede moverse a `h*`, el residual relevante es `Var(z)`. Las dos cosas no pueden coexistir.

Con la restricción consistente:

```
Var(z) = ½ tr((S_pΣ_t)²) ≤ ε²        ⇒     w₁² + w₂² ≤ 2ε²
```

y maximizando `|det W| = |w₁w₂|` sobre esa bola, por AM-GM `|w₁w₂| ≤ (w₁²+w₂²)/2 ≤ ε²`,
con igualdad en `|w₁| = |w₂| = ε`. **La ley de inercia de Sylvester no interviene**, porque
el óptimo tiene el mismo módulo con cualquier combinación de signos. Luego

```
det Σ_t*  =  ε² / |K|         elíptico E hiperbólico, sin distinción
```

El factor 2 de la ronda 1 respondía a otra pregunta —«¿cuánto puede crecer el parche si el
error se mide contra el plano tangente fijo en `h=0`?»— que es incompatible con adoptar
`h* ≠ 0`. Retirado.

### 1.1 Lo que la corrección deja al descubierto

Su restricción `Var(z) ≤ ε²` es, literalmente,

```
σ_n^inducido  ≤  ε
```

porque `σ_n*² = Var(z)` por construcción. **El criterio «RMS ponderado por kernel» es
decorativo: lo que se está imponiendo es que el grosor no supere la tolerancia.** Decirlo
así es más honesto y hace el problema trivialmente interpretable — «agranda el parche
tangencial todo lo que puedas mientras el grosor inducido no pase de `ε`».

Ninguna de las dos rondas lo dijo. Conviene decirlo porque elimina un aura de sofisticación
que no corresponde a lo que se está calculando.

---

## 2. CONCEDIDO — C5: el «si y solo si» era falso

Correcto. `F(μ) = (∫f dμ)²`, las normas RKHS y `W₂` son invariantes a división y ninguna es
una integral ponderada por masa. Mi caracterización era suficiente, no necesaria.

La suya es la correcta:

```
F es de nivel de representación  ⟺  F = F̄ ∘ A     (factoriza por el objeto agregado)
```

**Precisión que añado:** su formulación traslada toda la carga a definir `A(R)`, y definir
`A(R)` exige `surfaceMass`. Es decir, **sus dos objeciones —C5 y C6— son la misma
objeción**: sin masa geométrica canónica no hay objeto agregado, y sin objeto agregado la
invariancia no significa nada. Conviene tratarlas como un solo problema abierto, no dos.

Mi **corolario** sobrevive intacto y ahora con demostración correcta: la mediana y los
percentiles sin ponderar sobre gaussianas no factorizan por `μ`, luego no son de nivel de
representación. La consecuencia práctica —§40 del documento original no puede ser puerta de
certificación— no cambia.

---

## 3. CONCEDIDO — B2: `λ₂`, no `λ₁`

Su contraejemplo `λ = (100, 1, 0.001)` es decisivo. Ese objeto es una **cinta**: extensión
`10 × 1 × 0.032`. Es planar, su `e₃` está perfectamente separado, y Westin da
`c_plan ≈ 0.01`, que dice «no planar». El culpable es dividir por `λ₁`.

```
g_rel = (λ₂ - λ₃)/λ₂ = 1 - λ₃/λ₂        puerta de validez del normal
c_plan = (λ₂ - λ₃)/λ₁                   descriptor de morfología (disco vs aguja vs cinta)
```

Conflacioné las dos. `g_rel` es la correcta para Davis–Kahan porque el gap absoluto
`λ₂-λ₃` hay que normalizarlo por la escala de la dirección con la que compite, que es `λ₂`.

Acepto también su movimiento de `B2` a metadatos de validez en vez de eje de fidelidad.

---

## 4. REFUTADO — `E_surf` reintroduce la autonormalización de C1

Su CORE-A:

```
Σ* = Σ_t + v_n* nnᵀ        con  Σ_t = P_T Σ P_T   (la covarianza TANGENCIAL APRENDIDA)
v_n* = ½ tr((S Σ_t)²)
E_surf = W₂²( N(μ,Σ), N(μ*,Σ*) )
```

**La referencia se construye a partir del objeto juzgado.** `v_n*` es cuadrática en `Σ_t`,
luego `σ_n*(referencia) ∝ σ_t²`. Duplicar la extensión tangencial **cuadruplica el grosor
permitido**. Y `E_surf` no acota `σ_t` por ningún lado.

### Contraejemplo numérico, dentro del régimen válido

Esfera `R = 1`, tolerancia `ε = 0.01`.

```
splat óptimo    σ_t = 0.1          σ_n = ε = 0.01        h = ε = 0.01
splat malo      σ_t = 0.2   (2×)
                Σ_t = 0.04 I,  S = I,  SΣ_t = 0.04 I
                v_n* = ½·2·(0.04)² = 0.0016   ⇒   σ_n* = 0.04 = 4ε
                h*   = ½·0.08 = 0.04 = 4ε
```

Un splat con **grosor 4× la tolerancia** y **offset 4× la tolerancia**, sobre una esfera
unidad con tolerancia `0.01`, obtiene `E_surf = 0` exacto. Con `σ_t = 0.5` la cifra sube a
`25×` y sigue dando cero.

Se puede objetar que `η₃` marcaría el caso extremo. Es cierto para `σ_t = 0.5`
(`σ_t/τ = 0.5`), y **no** para `σ_t = 0.2`, que está en el régimen que su propia cota de
tercer orden admite. Y aunque lo marcara: una métrica nuclear de fidelidad que devuelve
cero para una primitiva 4× fuera de especificación, y que depende de una bandera lateral
para no mentir, no es una métrica nuclear de fidelidad.

### La reparación, y es más barata que `E_surf`

No hace falta un `W₂` entre dos gaussianas 3D con raíces matriciales. Las tres cantidades
que importan son escalares adimensionales con umbral duro en 1, todas divididas por la
**misma** tolerancia declarada:

```
Λ_i  =  sqrt( ½ Σ_j (κ_j σ_j²)² ) / ε        presupuesto de curvatura   ≤ 1
Θ_i  =  σ_n^aprendido / ε                     grosor                     ≤ 1
Ω_i  =  ( d_i^s − h* ) / ε                    offset respecto al previsto ≈ 0
```

- `Λ` no toca el `σ_n` aprendido: pregunta solo «¿es esta huella tangencial admisible para
  esta curvatura?». En el contraejemplo `Λ = 4`, que es exactamente el diagnóstico correcto.
- `Θ` no toca la curvatura: pregunta «¿es este splat más grueso que la tolerancia?».
- `Ω` mide el sesgo residual una vez descontado el offset que la curvatura predice.

Ninguna se normaliza por una variable libre. Las tres son invariantes bajo traslación,
rotación y escala uniforme —bajo `x→sx` se tiene `κ→κ/s`, `σ→sσ`, `ε→sε`, luego
`κσ²/ε` es invariante—. Y `E_surf` es aproximadamente una combinación cuadrática de las
tres, así que la terna es su **descomposición diagnóstica** además de su corrección: dice
*cuál* de los tres fallos ocurrió, que es lo que la matriz de casos A–E del documento
original necesita y un escalar `W₂` destruye.

---

## 5. RESULTADO NUEVO — `σ_n* = ε` en todo punto

Sale de su corrección, no de la mía, y ninguno de los dos lo enunció.

En el óptimo la restricción es activa, luego `½(w₁²+w₂²) = ε²`, y como
`σ_n*² = ½tr(W²) = ½(w₁²+w₂²)`:

```
σ_n*  =  ε        para toda curvatura, todo signo, toda anisotropía
```

Los ejes tangenciales sí dependen de la curvatura, vía `|κ_j| σ_j² = |w_j|`:

| Régimen | `(w₁,w₂)` | `σ_j²` | `h* = ½(w₁+w₂)` | `σ_n*` |
|---|---|---|---|---|
| Elíptico `K>0` | `(ε, ε)` | `ε/|κ_j|` | `ε` | `ε` |
| Hiperbólico `K<0` | `(ε, −ε)` | `ε/|κ_j|` | `0` | `ε` |
| Parabólico `K=0` | `(√2ε, 0)` | `√2ε/κ₁`, `σ₂` libre | `ε/√2` | `ε` |

**Consecuencia práctica inmediata.** El grosor de un splat superficial no es un parámetro a
aprender ni a derivar: es la tolerancia geométrica declarada. Toda la maquinaria de
curvatura sirve únicamente para los dos ejes tangenciales. Eso simplifica la
inicialización de A1/A8 a:

```
σ_n  ←  ε                       constante
σ_j  ←  sqrt(ε / |κ_j|)          tapado por reach y por gradación
h    ←  ½ Σ_j κ_j σ_j²           = ε, ε/√2 o 0 según el signo de la curvatura
```

Y da un test de una línea: **medir la distribución de `σ_n` en una nube 3DGS convergida
sobre geometría lisa. Si la teoría vale, se concentra en un valor y ese valor es la
tolerancia geométrica efectiva de la reconstrucción.** No hay constante libre. Es más
barato que MG-R0D y se puede correr sobre escenas 3DGS ya existentes, sin generar nada.

---

## 6. RESULTADO NUEVO — el offset `h*` es un sesgo sistemático de escala

Consecuencia de la tabla anterior que importa para VideoMesh en concreto, porque SoftSight
certifica medidas.

En una superficie elíptica el splat óptimo está centrado a `h* = ε` de la superficie,
**siempre hacia el mismo lado** (el determinado por el signo de la curvatura respecto al
normal). No es ruido: es sesgo.

```
esfera de radio R:   los centros óptimos yacen sobre una esfera de radio  R + ε
                     (signo según convención de normal)
```

Cualquier estimación de posición, radio, volumen o distancia derivada de centros de splats
hereda ese desplazamiento. `h*` es óptimo para **aproximación** —minimiza el RMS centrado—
y sesgado para **posición**, que es el compromiso sesgo-varianza de siempre. Para un
pipeline que declara `ScaleStatus` y publica incertidumbre (D9 del contrato), un sesgo
sistemático es peor que un error aleatorio del mismo tamaño: no se promedia.

Regla que se deriva: **antes de cualquier afirmación métrica sobre una superficie
reconstruida a partir de centros de gaussianas, restar `h*`**, y si `h*` no se puede
estimar porque falta la curvatura, declarar el sesgo como componente de la incertidumbre,
no ignorarlo. En términos de D28: la medida es `DETERMINISTIC_APPROXIMATION`, y su
incertidumbre tiene una componente **no centrada** que hay que publicar.

Ninguna de las dos rondas lo vio. Es el hallazgo con consecuencia contractual más directa
de todo el intercambio.

---

## 7. `E_⊥` — cuantifico su objeción, y la acepto a medias

Tenían razón en que un splat correcto sobre superficie curva no debe tener `E_⊥ = 0`. Ahora
se puede decir **cuánto**:

```
E_⊥^piso  =  h*² + σ_n*²  =  2ε²   elíptico
                              ε²   hiperbólico
                            1.5ε²  parabólico
```

Es decir, `E_⊥` tiene un suelo dependiente de la curvatura y **sesgado por un factor 2 entre
regímenes de curvatura distinta**. Comparar `E_⊥` entre la cara exterior y la interior de un
toro es comparar cosas con escalas distintas. Objeción concedida y cuantificada.

Pero no acepto retirar `E_⊥`, por una razón que es de su propio marco contractual:

```
E_⊥      no necesita estimador de curvatura   →  MeasurementClass = EXACT
E_surf   necesita S_p                          →  DETERMINISTIC_APPROXIMATION
```

Son medidas de **clase distinta** bajo D28. Una medida exacta y libre de estimador tiene un
valor de certificación que una aproximación dependiente de estimador no tiene, aunque sea
menos informativa. Colapsarlas contamina la exacta con el sesgo del estimador de curvatura,
que es precisamente el mayor hueco abierto (su U2).

Resolución: `E_⊥` es una **medida cruda de nivel 1** (exacta, sesgada por curvatura, con el
sesgo publicado); el exceso `E_⊥ − E_⊥^piso(K)` es de **nivel 2** (aproximada, insesgada).
Se publican las dos con su clase. Es la misma disciplina que el contrato aplica a
`ExecutionStatus` frente a `CertificationVerdict`: dos ejes que no se colapsan porque tienen
autoridad distinta.

---

## 8. `surfaceMass` para escenas importadas — su U1, con propuesta

Su diagnóstico es correcto: `α·2πσ₁σ₂` mezcla apariencia y geometría, y `A1+A8` solo
resuelve el caso de splats generados por VideoMesh. Su exigencia de un estimador declarado
para escenas importadas es la correcta.

Descarto primero una idea que parece buena y no lo es. Masa por responsabilidad,
`m_i^S = ∫_M [α_i k_i / Σ_j α_j k_j] dA`: suma exactamente `Area(M)`, es aditiva bajo
división, tiene unidades `L²` y usa `α` solo como peso de atribución. **Pero hace que `μ_G`
dependa de `M`**, con lo que `D_V = ‖μ_M − μ_G‖` deja de comparar dos objetos
independientes y su simetría se vuelve ficticia. Sirve para atribución en niveles 1–2 y
nunca para CORE-B.

**Propuesta que sí funciona, sin malla.** La representación gaussiana induce su propia
superficie: el conjunto de nivel de la ocupación,

```
λ(p) = Σ_i α_i k_i(p)          O(p) = 1 − exp(−λ(p))          S_G = { O = q₁ }
```

De ahí solo se necesita un **escalar global**, su área, y se reparte por la proporción
geométrica de cada splat:

```
m_i^S  =  Area(S_G) ·  ( σ_{1,i} σ_{2,i} · α_i ) / Σ_j ( σ_{1,j} σ_{2,j} · α_j )
```

- Sin malla. `μ_G` queda definida por `G` sola, luego `D_V` es honestamente simétrica.
- Suma exactamente `Area(S_G)`.
- Aditiva bajo `CLONE_SPLIT`: el numerador se reparte, el denominador no cambia.
- Unidades `L²`.
- `α` entra solo como **razón**, no como área: multiplicar todas las opacidades por una
  constante no cambia ningún `m_i^S`. Es la diferencia exacta con la fórmula que ustedes
  rechazan, y es la que salva la objeción.

Coste: una extracción de conjunto de nivel, grosera, una vez. `q₁` es una convención
declarada — exactamente el mismo patrón que su solución de `σ_k = ε_g/sqrt(2 ln(1/q₀))`,
que acepto sin reservas. Si aquel patrón vale para el ancho del núcleo, vale aquí.

Honestidad sobre los límites: el conjunto de nivel puede tener componentes espurias y las
estructuras finas colapsan. Es un estimador declarado con versión, no una identidad
canónica — que es lo que ustedes mismos exigen.

---

## 9. Verdictos sobre sus verdictos

| Punto | Ellos | Yo | Resolución |
|---|---|---|---|
| C4 factor 2 | REJECT | — | **Concedido.** Mi criterio era internamente inconsistente. |
| C5 «iff» | REJECT | — | **Concedido.** Y C5 y C6 son un único problema abierto. |
| C6 `surfaceMass` | CONDITIONAL | — | **Aceptado**, con estimador propuesto en §8 para importadas. |
| B2 `λ₁` vs `λ₂` | usar `g_rel` | — | **Concedido**, contraejemplo decisivo. |
| A3 cuantización | REJECT | — | **Concedido.** Los parches cambian el exponente, no la constante. Zador no transfiere. |
| A4 constante `5.66` | REJECT constante, KEEP exponente | — | **Concedido y mejorado**: `p=1` parches vs `p=2` átomos es el test, y es libre de constantes. |
| A5 heat kernel | REJECT | — | Aceptado. `A2` es más barato para curvatura. |
| A6 functional maps | REJECT | — | Aceptado. Mesh y gaussianas ya comparten frame canónico; la maquinaria espectral no se paga. |
| A1 + A8 | HIGH / KEEP | HIGH | **Coincidencia.** Es la línea constructiva. |
| A2 grietas | crítica al `sqrt|K|` | — | **Concedido**, ver §10. |
| A7 | test infrastructure | — | Aceptado, con su distinción `CLONE_SPLIT` / `GEOMETRIC_SPLIT`, que es mejor que mi versión. |
| `E_surf` como CORE-A | proponen | **REFUTADO** | Autonormalizado. Sustituir por la terna `(Λ,Θ,Ω)` de §4. |
| `E_⊥` fuera del núcleo | proponen | **PARCIAL** | Se queda como medida `EXACT` de nivel 1 con su suelo publicado. Ver §7. |

### Convergencia estructural

Dos rondas adversariales independientes llegan a la misma estructura de tres canales:

```
ronda 1     B1 local  +  B4 global simétrico  +  B5 cámaras
ronda 2     CORE-A    +  CORE-B               +  CORE-C
```

Discrepamos en qué va dentro de cada canal, no en que sean tres ni en cuáles. Eso es la
mejor evidencia disponible de que la partición es correcta.

---

## 10. La grieta: concedido, y la predicción mejora

Su crítica es correcta. En una arista redondeada la superficie es **desarrollable**:
`κ₁` grande, `κ₂ ≈ 0`, luego `K ≈ 0`. Mi «densidad → ∞ por `sqrt|K|`» era falsa. Es el caso
parabólico, donde por su propio análisis la curvatura no acota nada y tiene que atar otro
tope.

La relación **por eje** sí sobrevive, y predice algo más específico y más falsable:

```
σ_a través de la arista  = sqrt(ε / κ_across)  →  0
σ_a lo largo             = libre               →  tapado por reach/gradación
```

es decir **splats largos y finísimos alineados con la arista**, no una línea de splats
pequeños. Que es lo que 3DGS produce.

Y su observación de que la medida de curvatura de Gauss de un poliedro es **atómica en los
vértices** (defecto angular; para una esquina de cubo, `2π − 3·π/2 = π/2`) completa el
cuadro con una segunda predicción distinta:

```
aristas    anisotropía extrema alineada con la arista        (K ≈ 0, parabólico)
esquinas   concentración densa de splats pequeños             (K atómico)
```

Dos comportamientos cualitativamente distintos en el mismo fixture del cubo. Es un test
mejor que el que yo propuse: mide la alineación del eje principal de los splats contra la
dirección de la arista, y la densidad contra la distancia a la esquina.

---

## 11. FILTRO — qué sirve a VideoMesh

Criterio: qué es accionable ya, qué es investigación con retorno, qué se descarta.

### 11.1 Accionable, sin investigación previa

```
σ_n = ε                              regla de inicialización. Constante declarada,
                                     no parámetro aprendido. §5

σ_j = sqrt(ε/|κ_j|)                  ejes tangenciales, con tope por reach

h = ½ Σ κ_j σ_j²                     offset, y RESTARLO antes de toda afirmación
                                     métrica. §6 — consecuencia contractual directa

(Λ, Θ, Ω)                            terna adimensional con umbral en 1, sustituye
                                     a E_surf y a la mitad de las métricas del
                                     documento original. §4

g_rel = 1 − λ₃/λ₂                    puerta de validez del normal

σ_k = ε_g / sqrt(2 ln(1/q₀))         ancho de núcleo atado a tolerancia declarada.
                                     De ellos, aceptado sin reservas

τ̂ = min(1/κ_max, ½ d_nolocal)        estimador de reach, con exclusión del parche
                                     local por escala de análisis. De ellos

AMBIGUOUS                            bandera en vez de elección silenciosa de cara
```

### 11.2 Decisión de arquitectura que conviene tomar ya, aunque el resto sea V2

**`surfaceMass` separada de `opacity` y de `radiance` en el esquema del artifact gaussiano.**

Es la única conclusión del intercambio que toca contrato. Cuesta un campo ahora y cuesta una
migración de esquema después, y sin ella el nivel global (CORE-B / B4) no está definido.
Encaja con la disciplina de D28: `surfaceMass` derivada de celda métrica es
`DETERMINISTIC_APPROXIMATION`; estimada desde una escena importada es la misma clase con
otro estimador declarado, y la diferencia se publica.

No propongo añadirla a V1.1 — ahí no hay gaussianas. Propongo **anotarla como decisión
pendiente** para cuando exista `GAUSSIAN_SCENE`, con la razón escrita, que es justo lo que
§1.6 del contrato permite anotar sin número.

### 11.3 Investigación con retorno alto

```
A1 + A8      campo métrico anisótropo + muestreo determinista.
             Da a la vez: covarianza objetivo, colocación, solape acotado,
             ley de conteo, surfaceMass e inicialización determinista.
             Es LA línea constructiva. Coincidencia de las dos rondas.

A2           curvatura como medida, mollificada a la escala del splat.
             Estimador, no teoría nuclear. Cierra U2 si funciona.

MG-R0D       exponente p en N ∝ (R/ε)^p.  p=1 parches, p=2 átomos.
             Libre de constantes de implementación.
```

### 11.4 Test más barato del programa, y es nuevo

Antes que MG-R0D, que exige generar y converger nubes:

> **Medir la distribución de `σ_n` en nubes 3DGS ya existentes sobre geometría lisa.**

La teoría predice concentración en un único valor, y que ese valor **es** la tolerancia
geométrica efectiva de la reconstrucción. Sin parámetros libres, sin generar nada, sobre
datos que ya existen. Si `σ_n` sale disperso o correlacionado con la curvatura local, la
ley `σ_n* = ε` es falsa y todo el §5 cae — que es exactamente lo que un test debe poder
hacer.

### 11.5 Descartado

```
A3    cota de cuantización atómica         los parches cambian el exponente
A5    heat kernel                          A2 es más barato para lo mismo
A6    functional maps                      mismo frame canónico, no se paga
      Gauss–Bonnet como origen del conteo  la ley es local: ∫sqrt|K|, no ∫K
      la constante 5.66 y la constante 4   dependen de la convención kσ
      E_surf tal como está definida        autonormalizado, §4
      δ, d_M, r_⊥, P_i, E_coupling         de la ronda 1, sin cambios
      L_MG                                 de la ronda 1, sin cambios
      R_obs = ΣR                           no identificable, las dos rondas coinciden
```

---

## 12. Lo que queda abierto de verdad

```
U1'   surfaceMass en escenas importadas
      propuesta en §8; falta validarla contra un caso con opacidad
      fuertemente variable por razones de apariencia

U2'   sesgo y varianza del estimador de S_p sobre malla fotogramétrica
      su cota r_E ≲ 0.05 para 10% en varianza es la especificación;
      falta medir si algún estimador la cumple sobre malla real

U3'   ¿el sesgo h* aparece en 3DGS entrenado, o el optimizador lo cancela
      contra el término de renderizado?
      Es medible sobre nubes existentes, junto con el test de §11.4

U4'   admisión al subconjunto geometry-bound sin presuponer identificabilidad
      su U3; sigue sin respuesta por las dos partes
```

---

## 13. Recomendación

Sigue siendo **REFORMULAR**, ahora hacia un sistema más pequeño que el que la ronda 2
propone.

```
NIVEL 1   (Λ, Θ, Ω)  adimensionales, umbral 1     +   E_⊥ crudo con su suelo
NIVEL 2   exceso sobre el suelo, ponderado por masa
NIVEL 3   D_V = ‖μ_M − μ_G‖_K                     tras resolver surfaceMass
NIVEL 4   vector de residuales de cámara           autoridad no circular

METADATOS τ̂, ambigüedad, g_rel, κ(Σ), escala y confianza del estimador, η₃
```

Y el orden de trabajo no es escribir otro documento de arquitectura. Es:

```
1  medir σ_n en nubes 3DGS existentes            §11.4 — no cuesta nada
2  medir si h* aparece                            U3' — mismo dato
3  MG-R0A sobre plano/esfera/cilindro/silla       verifica h*, σ_n*, (Λ,Θ,Ω)
4  MG-R0D exponente                               decide A1/C4
5  solo entonces, surfaceMass y CORE-B
```

Los dos primeros se corren sobre datos que ya existen y pueden falsar la mitad de este
documento en una tarde. Empezar por ahí es lo que las dos rondas han venido pidiendo y
ninguna ha hecho.
