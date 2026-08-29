# Brief: animaciones CSS del personaje de marca (SVG)

## Contexto

Tres SVG de un personaje de marca (asterisco/estrella de la vida con brazos y
piernas), dibujados en line art plano B/N. Ya vienen con las **capas separadas
y nombradas** desde Affinity Designer.

El objetivo es animarlos con **CSS puro sobre el SVG inline** — nada de video,
nada de librerías de animación, nada de Lottie. Los SVG se insertan inline en el
HTML para poder alcanzar los grupos por su `id`.

---

## Inventario de capas

Todos los grupos son **hermanos a nivel raíz** (no hay anidamiento), lo que
facilita animarlos de forma independiente.

### `brand-character-back.svg` — viewBox `0 0 393 397`

Personaje de espaldas.

| `id` | transform propio |
|---|---|
| `Sombra` | — |
| `Brazo-Izquierdo` | — |
| `Brazo-derecho` | — |
| `Cuerpo` | — |
| `Nalgas` | — |

Este archivo está **limpio**: ningún grupo trae `transform` propio.

### `brand-character-front.svg` — viewBox `0 0 393 386`

Personaje de frente, cuerpo con manchas.

| `id` | transform propio |
|---|---|
| `Cuerpo` | `matrix(4.485791,0,0,4.485791,0,0)` |
| `Mugre` | `matrix(4.485791,0,0,4.485791,0,0)` |
| `Brazo-izquierdo` | `matrix(4.485791,0,0,4.485791,0,0)` |
| `Brazo-derecho` | `matrix(4.485791,0,0,4.485791,8.971583,-8.971583)` |

### `brand-character-front-02.svg` — viewBox `0 0 393 385`

Misma pose, cuerpo limpio + destellos.

| `id` | transform propio |
|---|---|
| `Cuerpo` | `matrix(4.465909,0,0,4.465909,0,0)` |
| `Brillo-1` | `matrix(0.491813,0,0,0.491813,0,-0.857772)` |
| `Brillo-2` | `matrix(4.465909,0,0,4.465909,0,0)` |
| `Brillo-3` | `matrix(4.465909,0,0,4.465909,0,0)` |
| `Brillo-4` | `matrix(4.465909,0,0,4.465909,0,0)` |
| `Brazo-izquierdo` | `matrix(4.465909,0,0,4.465909,0,0)` |
| `Brazo-derecho` | `matrix(4.465909,0,0,4.465909,8.931818,-8.931818)` |

---

## Trampas conocidas — leer antes de escribir CSS

### 1. Los `id` NO son consistentes entre archivos

En `back.svg` es **`Brazo-Izquierdo`** (I mayúscula).
En los dos `front` es **`Brazo-izquierdo`** (i minúscula).

Los selectores CSS de `id` son case-sensitive. Un selector compartido entre los
tres archivos va a fallar silenciosamente en uno de ellos. Usar selectores
separados, o normalizar los `id` al insertar el SVG inline.

### 2. NO usar la propiedad `transform` en los grupos de los `front`

El atributo `transform` de SVG mapea a la propiedad CSS `transform`. Si se
escribe `transform:` en el CSS de un grupo que ya trae `matrix(...)`, el matrix
se sobrescribe y el dibujo colapsa a 1/4.48 de su tamaño apenas arranca el
keyframe.

**Usar las propiedades individuales**, que se componen con el matrix en vez de
pisarlo:

```css
/* ✅ correcto — el matrix del grupo sobrevive */
@keyframes saludo {
  0%, 100% { rotate: 0deg; }
  50%      { rotate: -18deg; }
}

/* ❌ incorrecto — borra el matrix(4.48) */
@keyframes saludo {
  0%, 100% { transform: rotate(0deg); }
  50%      { transform: rotate(-18deg); }
}
```

Aplica a `rotate`, `scale` y `translate`. En `back.svg` no hay matrices, así que
ahí `transform` es seguro — pero por consistencia conviene usar el mismo estilo
en los tres.

### 3. `transform-origin` en SVG necesita `transform-box`

Por defecto el origen de transformación en SVG es el `(0,0)` del viewBox, no el
centro del elemento. Sin corregirlo, cualquier rotación manda la capa fuera de
cuadro.

```css
[id^="Brazo"], #Nalgas, #Mugre, [id^="Brillo"] {
  transform-box: fill-box;
}
```

Con `fill-box`, los porcentajes de `transform-origin` se leen respecto al
bounding box de cada grupo.

### 4. `Brillo-1` tiene una escala distinta al resto

`0.491813` contra `4.465909` de los otros tres destellos. Si se les aplica el
mismo `scale` en keyframes, `Brillo-1` va a crecer proporcionalmente distinto.
Verificar visualmente y compensar si hace falta.

### 5. Los `<svg>` vienen con `width="100%" height="100%"`

Van a estirarse al contenedor. Controlar el tamaño desde el contenedor padre con
un `aspect-ratio` explícito.

### 6. Las alturas de viewBox no coinciden

`397` / `386` / `385`. Si se intercambian los SVG dentro del mismo contenedor
(por ejemplo `front` → `front-02` al terminar la limpieza), hay un salto de
~12px. Fijar un `aspect-ratio` común en el contenedor.

---

## Animaciones a construir

### A. `back.svg` — idle con salto periódico

La referencia es un personaje quieto que cada varios segundos pega un salto
corto con rebote.

**Estructura:** el salto se aplica a un `<g>` raíz que envuelva todo (o al
`<svg>` mismo), no a `#Cuerpo` — así piernas y sombra suben juntas.

**Timing:** ciclo de ~7s, con el salto ocupando los últimos ~2s. El resto del
tiempo el personaje está quieto o con un sway mínimo.

**Fases del salto** (esto es lo que lo hace leer como salto y no como "div que
sube"):

1. **Anticipación** — squash previo (`scale(1.07, .90)`), muy breve. No omitir.
2. **Despegue** — stretch (`scale(.94, 1.12)`) + inicio de `translateY`.
3. **Aire** — punto alto, vuelve casi a proporción normal.
4. **Impacto** — squash más fuerte que la anticipación (`scale(1.09, .87)`).
   Esto es lo que da sensación de peso.
5. **Rebote** — overshoot suave y vuelta a reposo.

`transform-origin: bottom center` en el contenedor. Con origen al centro parece
que flota.

**Capas que se animan en contra:**

- `#Sombra` — se achica y baja opacity mientras el cuerpo está en el aire, y
  vuelve a full en el impacto. Es lo que más vende el salto.
- `#Nalgas` — misma animación de wobble pero con **~80ms de delay** respecto del
  contenedor. Ese desfase es el efecto de "física" buscado: la masa llega tarde.
- `#Brazo-Izquierdo` / `#Brazo-derecho` — leve rotación de arrastre, también
  con delay.

Todos los `translateY` en **porcentaje**, no en unidades de viewBox.

### B. `front.svg` — limpieza en loop

El personaje se pasa las manos por el cuerpo y las manchas desaparecen; después
vuelve a ensuciarse para cerrar el loop.

- `#Brazo-izquierdo` / `#Brazo-derecho` — barrido horizontal repetido sobre el
  cuerpo. Rotación desde el hombro (`transform-origin: 100% 40%` y `0% 40%`
  respectivamente) más un `translate` corto. Varios ciclos rápidos, no uno solo.
- `#Mugre` — `opacity` de 1 → 0 progresivo, sincronizado con los barridos. Ideal
  que baje "a saltos" (un escalón por pasada de mano) en vez de un fade lineal:
  se lee mucho mejor como limpieza.
- Al final del ciclo, `#Mugre` vuelve a 1 — pero de golpe no queda bien. Mejor
  dejar una pausa larga en limpio y que el retorno ocurra con el personaje fuera
  de foco, o resolverlo con un fade lento.
- `#Cuerpo` — sway leve acompañando cada barrido.

### C. `front-02.svg` — destellos

Estado "limpio" con `Brillo-1` a `Brillo-4`.

- Cada destello con `scale` + `opacity` en pop corto, y **delays escalonados**
  entre ellos (~120ms). Nunca todos al mismo tiempo.
- Se puede encadenar como remate de la animación B.

---

## Requisitos transversales

- **`prefers-reduced-motion`** — bloque `@media` que desactive todas las
  animaciones. Obligatorio.
- **`will-change: transform`** solo en los elementos que efectivamente se animan,
  no en todo.
- Animar únicamente propiedades compuestas (`transform`/`rotate`/`scale`/
  `translate` y `opacity`). Nada de `width`, `top`, `margin` ni `filter` en
  keyframes.
- Los tres SVG pueden convivir en la misma página: **prefijar los selectores**
  con la clase del contenedor para evitar colisiones de `id` (los `id` se
  repiten entre archivos: `Cuerpo`, `Brazo-derecho`, etc. aparecen en más de
  uno, y eso es HTML inválido si se insertan los tres inline en el mismo
  documento). Considerar renombrar con prefijo por personaje al insertarlos.

---

## Entregable esperado

1. Un HTML de prueba con los tres personajes lado a lado.
2. El CSS de animaciones en un archivo separado, comentado por bloque.
3. Controles simples para ajustar en vivo la duración del ciclo y la intensidad
   del salto — para calibrar sin recompilar.

Trabajar el `back.svg` primero y dejarlo aprobado antes de seguir con los otros
dos.
