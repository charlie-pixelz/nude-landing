// Scroll-scrub del hero: canvas + sticky + secuencia de imágenes.
// Nunca usa <video>: hacer scrub con currentTime falla en iOS Safari
// (seek lento sobre MP4 con GOP largo). Ver HERO_SPEC.md Parte 3.
// Solo se activa si existe .hero-track en el DOM.

// import.meta.glob resuelve las URLs finales (hasheadas, con el base
// correcto para GitHub Pages) en build time — evita el problema de
// rutas absolutas que rompe en un project page.
// Dos sets, uno por caso de uso, porque la geometría es distinta:
//   sm 810x1440  -> móvil, el frame llena el alto. Ampliación 1,13x.
//                   2,4 MB, dentro del presupuesto de 2,5 MB del hero.
//   lg 1080x1920 -> escritorio, el frame llena el 46% del ancho pegado a
//                   la derecha, o sea ~1324px reales en una pantalla
//                   retina de 1440. Con el set chico eso era 1,63x de
//                   ampliación; con éste baja a 1,23x. 3,4 MB, que sólo
//                   descarga escritorio: el presupuesto duro es el móvil.
// 1080x1920 es la resolución nativa del máster; más grande sería inventar
// pixeles que la fuente no tiene.
import { PERFIL } from './hero-perfil.js';

const SM_FRAMES = import.meta.glob('../assets/hero-frames/sm/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
});
const LG_FRAMES = import.meta.glob('../assets/hero-frames/lg/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
});

function orderedUrls(globResult) {
  return Object.keys(globResult)
    .sort()
    .map((k) => globResult[k]);
}

export function initHeroScrub() {
  const track = document.querySelector('.hero-track');
  if (!track) return;

  const sticky = track.querySelector('.hero-sticky');
  const canvas = track.querySelector('.hero-canvas');
  const poster = track.querySelector('.hero-poster');
  if (!sticky || !canvas || !poster) return;

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const saveData = navigator.connection?.saveData;

  // caso borde obligatorio: cero descarga, el poster se queda fijo,
  // el track colapsa a 100svh — se implementa primero, no al final.
  if (reduced || saveData) {
    track.classList.add('hero-static');
    return;
  }

  const urls = orderedUrls(window.matchMedia('(min-width: 760px)').matches ? LG_FRAMES : SM_FRAMES);
  const N = urls.length;
  if (!N) return;

  const THRESHOLD = Math.ceil(Math.min(N, Math.max(N * 0.6, N / 3)));
  const frames = new Array(N);
  let loaded = 0;
  let ready = false;
  let currentFrame = -1;
  let active = true; // corta el trabajo fuera del viewport

  const ctx = canvas.getContext('2d');

  function sizeCanvas() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.round(rect.width * dpr);
    canvas.height = Math.round(rect.height * dpr);
    // Cambiar el tamaño del canvas resetea el contexto, así que esto va acá y
    // no una sola vez al arrancar. El frame siempre se dibuja más grande que
    // su tamaño real (1,23x en escritorio, 1,18x en móvil) y por defecto el
    // canvas amplía con el filtro barato. Medido en el navegador: 'high' da
    // +2,9% de nitidez. Es poco, pero no cuesta un solo byte.
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
  }

  // Proporción del ancho que ocupa el frame en escritorio, pegado a la
  // derecha. Tiene que coincidir con el width del .hero-poster en hero.css:
  // si no coinciden, se ve un salto al activarse el scrub.
  const COL_ESCRITORIO = 0.46;
  const mqEscritorio = window.matchMedia('(min-width: 760px)');

  function draw(bitmap) {
    if (!bitmap) return;
    const cw = canvas.width;
    const ch = canvas.height;
    ctx.clearRect(0, 0, cw, ch);

    let x, y, w, h;
    if (mqEscritorio.matches) {
      // Escritorio: el pack manda a la derecha y el texto vive a la
      // izquierda. Llena el ancho de su columna y recorta arriba/abajo,
      // que es donde el frame sólo tiene fondo.
      w = cw * COL_ESCRITORIO;
      h = bitmap.height * (w / bitmap.width);
      x = cw - w;
      y = (ch - h) / 2;
    } else {
      // Móvil: llena el alto y desborda a lo ancho; los bordes laterales
      // del frame quedan fuera de pantalla, así que no hay costura.
      h = ch;
      w = bitmap.width * (ch / bitmap.height);
      x = (cw - w) / 2;
      y = 0;
    }
    ctx.drawImage(bitmap, x, y, w, h);

    if (mqEscritorio.matches) {
      // Difuminado del borde izquierdo. El fondo del video trae un gradiente
      // de luz de ~13 unidades RGB a lo ancho, así que su borde nunca calza
      // exacto con el --rosa del CSS: sin esto se ve una línea vertical.
      // destination-out borra con un degradado en vez de pintar encima, así
      // el rosa que queda detrás es el del CSS, no una aproximación.
      const f = w * 0.1;
      const g = ctx.createLinearGradient(x, 0, x + f, 0);
      g.addColorStop(0, 'rgba(0,0,0,1)');
      g.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.globalCompositeOperation = 'destination-out';
      ctx.fillStyle = g;
      ctx.fillRect(x, 0, f, ch);
      ctx.globalCompositeOperation = 'source-over';
    }
  }

  // Cuánto del reparto por movimiento se aplica: 0 es el mapeo lineal, 1 es
  // el reparto completo. Calibrado probando los dos en local, decisión de
  // Charlie del 29 de agosto de 2026:
  //
  //   móvil       0,4  el swipe es rápido y ahí el giro sí se sentía acelerado
  //   escritorio  0    con rueda o trackpad el scroll ya es lento y
  //                    controlado, el giro nunca molestó, y comprimir los
  //                    tramos quietos hace saltar más frames, que en pantalla
  //                    grande se nota
  //
  // No es una inconsistencia: la queja de origen era sobre deslizar rápido,
  // que es un gesto de móvil. El arreglo va donde está el problema.
  //
  // Se puede forzar desde la URL con ?reparto=0.7 para comparar en vivo sin
  // reconstruir. Sólo se lee un número y se acota — nunca entra al DOM
  // (ver CLAUDE.md).
  const REPARTO_MOVIL = 0.4;
  const REPARTO_ESCRITORIO = 0;

  const REPARTO_FORZADO = (() => {
    const crudo = new URLSearchParams(window.location.search).get('reparto');
    const v = parseFloat(crudo);
    return Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : null;
  })();

  function reparto() {
    if (REPARTO_FORZADO !== null) return REPARTO_FORZADO;
    return mqEscritorio.matches ? REPARTO_ESCRITORIO : REPARTO_MOVIL;
  }

  // El scroll se repartía en partes iguales entre los frames, pero la
  // secuencia no se mueve en partes iguales. Medido con
  // scripts/perfil-movimiento.py: el giro de 360 concentra el 66% del cambio
  // visual y se llevaba sólo el 40% del recorrido — por eso giraba rápido. Y
  // entre los frames 44 y 65 el pack ya aterrizó y sólo se asienta: gastaba
  // 19% del scroll en 7% del cambio.
  //
  // La mezcla va sobre la curva acumulada, no sobre el índice del frame. Es
  // la diferencia entre que la perilla haga lo que dice y que no: mezclando
  // índices, en 0,4 la zona muerta quedaba en 20% (intacta) y el scroll salía
  // de la tapa y el paño, que es justo lo que hay que conservar. Sobre la
  // acumulada el reparto interpola de verdad — 0,4 deja la zona muerta en
  // 14% y devuelve ese scroll al giro.
  const usaPerfil = PERFIL && PERFIL.length === N;

  function acumulado(i, mezcla) {
    return (1 - mezcla) * (i / (N - 1)) + mezcla * (PERFIL[i] / 1000);
  }

  function frameForProgress(progress) {
    const mezcla = reparto();
    if (!usaPerfil || mezcla === 0) return Math.round(progress * (N - 1));

    let i = 1;
    while (i < N - 1 && acumulado(i, mezcla) < progress) i++;
    const a = acumulado(i - 1, mezcla);
    const b = acumulado(i, mezcla);
    const t = b > a ? (progress - a) / (b - a) : 0;

    return Math.round(i - 1 + t);
  }

  function onScroll() {
    if (!ready || !active) return;
    const rect = track.getBoundingClientRect();
    const trackTop = window.scrollY + rect.top;
    const trackHeight = track.offsetHeight;
    const viewportH = window.innerHeight;
    const progress = Math.max(0, Math.min(1, (window.scrollY - trackTop) / (trackHeight - viewportH)));
    const frame = frameForProgress(progress);
    if (frame === currentFrame) return;
    currentFrame = frame;

    let bitmap = frames[frame];
    if (!bitmap) {
      // el frame todavía no cargó: nunca se deja el canvas en blanco,
      // se dibuja el último disponible.
      for (let i = frame; i >= 0; i--) {
        if (frames[i]) {
          bitmap = frames[i];
          break;
        }
      }
    }
    draw(bitmap);
  }

  let raf = null;
  function requestScroll() {
    if (raf) return;
    raf = requestAnimationFrame(() => {
      raf = null;
      onScroll();
    });
  }

  function loadFrames() {
    const CONCURRENCY = 6;
    let next = 0;

    function loadOne() {
      if (next >= N) return;
      const idx = next++;
      fetch(urls[idx])
        .then((r) => r.blob())
        .then((blob) => createImageBitmap(blob))
        .then((bitmap) => {
          frames[idx] = bitmap;
          loaded++;
          if (!ready && loaded >= THRESHOLD) {
            ready = true;
            poster.classList.add('hide');
            sizeCanvas();
            onScroll();
          }
        })
        .catch(() => {
          // fallo de carga de un frame: el poster se queda si nunca
          // se activa el scrub, el sitio sigue funcionando.
        })
        .finally(loadOne);
    }

    for (let i = 0; i < CONCURRENCY; i++) loadOne();
  }

  // nunca compite con el LCP: recién después de `load`.
  window.addEventListener('load', loadFrames);
  window.addEventListener('scroll', requestScroll, { passive: true });

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      sizeCanvas();
      currentFrame = -1;
      onScroll();
    }, 200);
  });

  sizeCanvas();

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        active = entry.isIntersecting;
        if (active) onScroll();
      });
    },
    { threshold: 0 }
  );
  io.observe(track);
}
