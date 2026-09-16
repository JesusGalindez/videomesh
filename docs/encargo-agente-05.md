# Encargo 05 — separar piezas de una malla fundida, sin ojos

**Objetivo del encargo entero, en una frase:** que un agente pueda coger una
malla de una sola pieza —la que sale de cualquier generativo— y sacarle las
partes que se mueven, **sabiendo con números si lo hizo bien**, sin mirar
ninguna captura.

Eso último es lo que falta. Lo demás ya está.

---

## 0. De dónde sale este encargo

El 2026-09-15 se hizo a mano lo que aquí se automatiza: separar los cuatro
rotores de un VTOL generado con Hunyuan3D para que giraran. Salió, pero mal, y
las horas que costó son el argumento entero de este documento.

Lo que se midió por el camino, y no hay que volver a medir:

```text
892.729 vértices, 1.500.086 triángulos, 6.765 componentes conexos
tras soldar por posición:  749.967 vértices y UN solo componente
```

Los 6.765 trozos eran una ilusión de vértices sin soldar. **Geométricamente es
una piel continua**: cuerpo, aros, palas y patas, todo fundido. No hay piezas que
encontrar, hay piezas que decidir.

### 0.1 Los cinco fallos, porque cada uno señala una regla

**El eje escrito a mano.** Se midieron los cuatro ejes una vez y se dejaron como
constantes. Estaban desplazados, y el rotor giraba descentrado con la maza
saliéndose del hueco. *Regla: un eje se deriva del dato, no se escribe.*

**El radio del corte, elegido a ojo.** Corto, partía las palas y dejaba muñones;
largo, se llevaba la pared del conducto y se veía el hueco del tubo. Seis
combinaciones probadas a base de captura y entrecerrar los ojos. *Regla: si el
criterio de aceptación es una captura, no hay criterio.*

**El histograma que encontró lo que no era.** Buscaba «la pared interior del
conducto» por acumulación de triángulos y encontraba la **superficie exterior**,
que concentra mucho más. El radio con el que se centra y el radio con el que se
corta tuvieron que separarse. *Regla: un pico no es una identidad; hay que
comprobar cuál es.*

**Los marcos de referencia, tres veces.** El GLB venía con
`KHR_mesh_quantization` —enteros de 0 a 16383 y la escala en el nodo—, así que
restar posiciones entre marcos distintos daba cero coincidencias la primera vez,
piezas disparadas la segunda y piezas invisibles pegadas al origen la tercera.
*Regla: toda medida declara su marco, y pasar de uno a otro es una operación con
nombre, no una resta.*

**Y el que más tiempo costó: no había puerta.** Cada intento era cambiar una
constante, recargar, mirar. Sin un número que dijera «mejor» o «peor», no hay
forma de iterar, y menos para un agente que no ve.

---

## 1. Lo que este encargo NO es

No es un segmentador mejor. Hay literatura de sobra y algoritmos que funcionan.

Es **la puerta que convierte la segmentación en un problema resoluble**: tres
medidas que dicen, sin ojos, si un corte está bien. Con ellas, cualquier
algoritmo —y cualquier agente— puede iterar solo. Sin ellas, el mejor algoritmo
del mundo sigue dependiendo de que alguien mire.

Y no inventa geometría. Segmentar es **repartir**: cada triángulo cae en
exactamente una parte, y la unión es el original triángulo a triángulo. Eso es lo
único que esta cadena se permite hacer sobre una malla que no escribió.

---

## 2. Las tres medidas — en SoftSight

Van en el verificador y no en el productor, por lo de siempre: quien mide no
modela. Son tres puertas nuevas junto a `mesh-topology` y `mesh-diff`.

### 2.1 Conservación — la barata, y la que nunca falla sola

```text
triángulos de las partes  +  triángulos que quedan  ==  triángulos del original
ningún índice aparece dos veces
ningún vértice se mueve
```

Ya se hace a mano en la página del VTOL. Aquí pasa a ser función con puerta.
**No basta por sí sola** —un reparto que mande todo a una parte la cumple— pero
es la que caza los errores de marco: el primer intento de aquel día dio «0 de
90.004 apartados» y lo dijo este número, no un error.

### 2.2 Longitud del borde del corte — **la medida que faltaba**

Es la clave del encargo. Un corte genera aristas de borde nuevas: las que antes
tenían dos triángulos y ahora tienen uno a cada lado del reparto.

```text
corte por una costura real      pocas aristas nuevas, y en una curva cerrada
corte a través de una superficie muchas, y dentadas
```

**Ese número es el que sustituye a mirar la captura.** Minimizarlo es el objetivo
de cualquier segmentador, y con él un agente puede probar cien combinaciones de
parámetros en un minuto y quedarse con la mejor, sin ver ninguna.

Se publica en bruto y relativizado al perímetro de la parte, que es lo que
permite comparar piezas de tamaños distintos.

### 2.3 Estabilidad del eje bajo giro — para las partes que rotan

Un eje bien puesto tiene una propiedad exacta y comprobable: **girar la pieza
alrededor de él no cambia su caja envolvente**, más allá del error de coma
flotante.

```text
se gira la parte a 16 ángulos repartidos
se mide la caja envolvente en cada uno
eje bueno   la caja no crece
eje malo    crece con el descentramiento, y cuánto lo dice
```

Ese crecimiento **es** el descentramiento, medido en unidades del paquete. Con
esta puerta, el eje escrito a mano de aquel día se habría caído en el primer
intento en vez de a las dos horas.

### 2.4 Y la que ya existe y hay que usar

`diffMeshes` compara la unión de las partes con el original. Si el reparto es
honesto, la distancia tiene que quedar **bajo el suelo de ruido publicado** en
las dos direcciones: no se movió nada. Cualquier otra cosa significa que alguien
tocó geometría creyendo que repartía.

---

## 3. La etapa — en VideoMesh

### 3.1 `videomesh segmentar <proyecto>`

```text
1  soldar por posición          de 6.765 componentes a 1: el dato real
2  grafo dual de la malla       triángulo ↔ triángulo por arista compartida
3  criterio de corte            por concavidad del ángulo diedro
4  etiquetar componentes        cada parte, su conjunto de triángulos
5  ajustar ejes                 a las partes que el destino declare móviles
6  publicar                     partes, ejes y las tres medidas
```

**El paso 3 es el que cambia todo respecto a lo que se hizo a mano.** Aquel corte
era un cilindro: una regla geométrica que no sabe nada de la malla, y que por eso
atraviesa superficies y deja bordes dentados. Cortar por **concavidad** sigue las
costuras que la forma ya tiene —donde la pala se junta con el aro hay un valle—,
y un corte por una costura deja pocas aristas nuevas. Que sea mejor no es una
opinión: lo dice la medida 2.2.

### 3.2 Los ejes se publican, no se reinventan

Esto es la mitad de «que no se pierda la coherencia», y es concreto: aquel día
los cuatro ejes se midieron en una página de Three.js y se quedaron ahí. Cualquier
otro consumidor —Unity, Blender, otro visor— habría tenido que medirlos otra vez,
y le habrían salido otros.

El paquete tiene que llevar, por cada parte móvil:

```text
identidad de la parte
punto del eje y dirección, en el marco del paquete
qué tipo de movimiento admite: giro continuo, giro limitado, deslizamiento
```

Con eso, colocar un rotor deja de ser un problema de nadie: se lee.

### 3.3 El marco, declarado siempre

Toda medida de este encargo lleva el marco en el que está, sin excepción. Fue el
fallo que más veces se repitió y el único que se disfrazó de tres síntomas
distintos: cero coincidencias, piezas disparadas y piezas invisibles.

---

## 4. Cómo se ve en rojo cada cosa

Ninguna de estas puertas vale si solo se ha visto verde.

```text
conservación     un reparto que se deja un triángulo, y otro que lo duplica
borde del corte  el mismo objeto cortado por su costura y cortado por la mitad:
                 el segundo tiene que dar un número mucho mayor. Si no los
                 distingue, la medida no mide
eje              un eje desplazado a propósito: la caja tiene que crecer, y lo
                 que crezca tiene que parecerse a lo que se desplazó
distancia        una parte a la que se le mueve un vértice: `diffMeshes` tiene
                 que salirse del suelo de ruido
```

El segundo es el importante. **Una medida que no distingue un corte bueno de uno
malo no sirve de nada**, y es exactamente el fallo que se pasaría por alto si solo
se comprueba que la función devuelve un número.

---

## 5. Lo que esto le da a un agente

Hoy, un agente que intente esto se queda sin salida: cambia un parámetro, y para
saber si mejoró tiene que pedirle a alguien que mire.

Con las tres medidas, el bucle se cierra solo:

```text
segmentar con unos parámetros
leer borde del corte, conservación y estabilidad del eje
si el borde bajó, seguir por ahí; si subió, volver
parar cuando deje de bajar, o al tope de vueltas declarado
```

Eso es todo lo que hace falta para que «cualquier IA llegue y haga un buen
trabajo»: no un algoritmo mejor, **un criterio que no necesite ojos**. El resto
—soldar, grafo dual, concavidad— es trabajo conocido.

Y el freno del bucle es el mismo del encargo 04 §F2: si una vuelta no mejora la
medida que la motivó, se para y se dice. Un segmentador sin freno acaba partiendo
el objeto en mil piezas para bajar un número.

---

## 6. Orden, y dónde parar

```text
A  SoftSight: conservación y borde del corte        ← primera entrega
B  SoftSight: estabilidad del eje
C  VideoMesh: soldar, grafo dual, concavidad
D  VideoMesh: ajuste de ejes y publicación en el paquete
E  el bucle con su freno
```

**Para al final de A y enséñalo.** Con la medida del borde ya se puede decidir si
el enfoque vale, probándola sobre dos cortes conocidos del mismo objeto. Si esa
medida no distingue, lo demás sobra.

---

## 7. Lo que NO hay que hacer

No escribir un segmentador antes que las medidas. Es el orden que costó las horas
del 2026-09-15: sin puerta, cada mejora es una opinión.

No usar reglas geométricas —cilindros, cajas, planos— como criterio de corte
definitivo. Valen como semilla; no como decisión.

No reimplementar `diffMeshes`, `boundsTree` ni `meshTopology`. Están y funcionan.

Y no dar por bueno un corte porque la captura se vea bien. Es precisamente el
hábito que este encargo existe para quitar.
