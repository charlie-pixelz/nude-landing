# NUDE — landing de lanzamiento

One page de **NUDE**, papel higiénico húmedo que se degrada en el agua, recién
llegado a góndola Jumbo en Región Metropolitana, Viña del Mar y Concepción.

El sitio es una vitrina: no vende, no cotiza, no tiene carrito. Su trabajo es
que alguien que llega desde una story, con el teléfono en la mano, se vaya
sabiendo tres cosas: qué es, que se tira al WC, y que está en Jumbo.

**En revisión.** Esta versión es una propuesta de diseño, no el sitio final.

## Estado

| | |
|---|---|
| Hero con scroll-scrub | listo |
| Cuerpo, secciones 01 a 08 | listo |
| Tiendas desde JSON | listo, pendientes de confirmar con la marca |
| Preguntas frecuentes desde JSON | 7 publicadas, 6 esperando dato de la marca |
| Formulario "avísame" | listo, falta el endpoint del servicio de correo |
| Medición (GA4, Meta, TikTok) | instalada, sin IDs reales |
| Textos legales y 404 | pendiente |

## Desarrollo

```bash
npm install
npm run dev      # servidor de desarrollo
npm run build    # build de producción a dist/
npm run preview  # sirve el build, que no es igual al de desarrollo
npm run lint
```

Requiere Node 22 o superior. Para regenerar los frames del hero hace falta
ffmpeg, pero no para trabajar en el sitio.

## Cómo está armado

- **Vite + JavaScript vanilla, sin framework.** No hay estado compartido, ni
  CMS, ni rutas: un framework acá solo agrega kilobytes contra el requisito de
  Lighthouse 90.
- **Sin librerías de scroll.** El scrub del hero es `requestAnimationFrame` +
  `canvas` sobre un contenedor `sticky`. Nunca usa `<video>`: mover
  `currentTime` para hacer scrub falla en iOS Safari.
- **Fuentes autoalojadas y subseteadas** a latin + latin-ext, con
  `font-display: swap`.
- **Los datos editables viven en JSON**, no en el markup. `src/data/stores.json`
  y `src/data/faq.json` son lo que permite que la marca agregue una tienda o
  una pregunta sin tocar código. Una pregunta sin respuesta no se publica: el
  archivo sirve de lista de pendientes sin dejar huecos en el sitio.
- **El formulario no tiene backend.** Manda un POST a `VITE_FORM_ENDPOINT`, y
  cambiar de servicio es cambiar esa variable. Sin la variable el formulario
  valida y avisa que es una maqueta.
- **`prefers-reduced-motion` se respeta de verdad:** con la preferencia activa
  no hay scrub y los frames del hero ni siquiera se descargan.

```
src/
├── styles/   tokens.css · base.css · sections/
├── js/       hero-scrub.js · reveal.js · nav-zones.js · stores.js
│            faq.js · form.js · analytics.js
├── data/     stores.json · faq.json
└── assets/   fonts/ · img/ · hero-frames/
```

## Materiales crudos (no versionados)

`/assets/` y `/fonts/` en la raíz son materiales de origen —masters de video,
fotos HD, fuentes sin subsetear— y están en `.gitignore`. Solo los assets
finales, ya optimizados, entran a `src/assets/`.

La documentación interna del encargo tampoco se versiona en este repositorio
público. Vuelve al repo cuando migre a la cuenta de la marca.

## Despliegue

Cada push a `main` dispara el workflow de GitHub Actions que construye el sitio
y lo publica en GitHub Pages. `vite.config.js` usa `base: './'`, así que todas
las rutas del build son relativas y funcionan igual en un project page que en
un dominio propio.

**Limitación conocida:** GitHub Pages no permite configurar cabeceras HTTP, así
que el sitio va sin CSP ni X-Frame-Options.
