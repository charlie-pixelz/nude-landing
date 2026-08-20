// Zonas de color de la nav: cambia el color de la barra según la sección
// que cruza el centro vertical de la nav. Portado de legacy/index.html
// (líneas 916-940). Solo se activa si existe #nav en el DOM.

export function initNavZones() {
  const nav = document.getElementById('nav');
  if (!nav) return;

  let zones = [];

  function measureZones() {
    zones = [...document.querySelectorAll('[data-nav]')].map((section) => {
      const top = section.getBoundingClientRect().top + window.scrollY;
      return { top, bottom: top + section.offsetHeight, mode: section.dataset.nav };
    });
  }

  function onScroll() {
    const y = window.scrollY;
    nav.classList.toggle('scrolled', y > 10);
    const line = y + nav.offsetHeight / 2;
    const zone = zones.find((z) => line >= z.top && line < z.bottom);
    const mode = zone?.mode ?? '';
    nav.classList.toggle('on-peri', mode === 'peri');
    nav.classList.toggle('on-pink', mode === 'pink');
  }

  measureZones();
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      measureZones();
      onScroll();
    }, 200);
  });

  // los frames de imagen del hero y las fuentes pueden llegar tarde y
  // correr el alto real de las secciones: se remide una vez más.
  setTimeout(() => {
    measureZones();
    onScroll();
  }, 800);
}
