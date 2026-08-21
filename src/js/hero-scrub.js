// Scroll-scrub del hero: canvas + sticky + secuencia de imágenes.
// Nunca usa <video>: hacer scrub con currentTime falla en iOS Safari
// (seek lento sobre MP4 con GOP largo). Ver HERO_SPEC.md Parte 3.
// Solo se activa si existe .hero-track en el DOM.

// import.meta.glob resuelve las URLs finales (hasheadas, con el base
// correcto para GitHub Pages) en build time — evita el problema de
// rutas absolutas que rompe en un project page.
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

  const urls = window.innerWidth <= 760 ? orderedUrls(SM_FRAMES) : orderedUrls(LG_FRAMES);
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
  }

  function draw(bitmap) {
    if (!bitmap) return;
    const cw = canvas.width;
    const ch = canvas.height;
    const scale = Math.max(cw / bitmap.width, ch / bitmap.height);
    const w = bitmap.width * scale;
    const h = bitmap.height * scale;
    ctx.clearRect(0, 0, cw, ch);
    ctx.drawImage(bitmap, (cw - w) / 2, (ch - h) / 2, w, h);
  }

  function frameForProgress(progress) {
    return Math.round(progress * (N - 1));
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
