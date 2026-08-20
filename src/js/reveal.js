// Animación de titulares por línea (splitLines) + reveal por IntersectionObserver.
// Portado de legacy/index.html (líneas 861-914), adaptado a módulo ES.
// Solo se activa si existen elementos [data-split] o .rv / .rv-split en el DOM.

function splitLines(el) {
  if (!el.dataset.orig) el.dataset.orig = el.textContent.trim();
  const words = el.dataset.orig.split(/\s+/);

  el.textContent = '';
  const wordSpans = words.map((w) => {
    const span = document.createElement('span');
    span.className = 'w';
    span.textContent = w;
    return span;
  });
  wordSpans.forEach((span, i) => {
    el.appendChild(span);
    if (i < wordSpans.length - 1) el.appendChild(document.createTextNode(' '));
  });

  const lines = [];
  let cur = [];
  let top = null;
  wordSpans.forEach((w) => {
    const t = w.offsetTop;
    if (top === null || Math.abs(t - top) < 4) {
      cur.push(w);
      if (top === null) top = t;
    } else {
      lines.push(cur);
      cur = [w];
      top = t;
    }
  });
  if (cur.length) lines.push(cur);

  el.textContent = '';
  lines.forEach((line, i) => {
    const mask = document.createElement('span');
    mask.className = 'mask';
    const ln = document.createElement('span');
    ln.className = 'ln';
    ln.style.transitionDelay = `${i * 100}ms`;
    ln.textContent = line.map((w) => w.textContent).join(' ');
    mask.appendChild(ln);
    el.appendChild(mask);
  });
}

export function initReveal() {
  const splitEls = document.querySelectorAll('[data-split]');
  const revealEls = document.querySelectorAll('.rv, .rv-split');
  if (!splitEls.length && !revealEls.length) return;

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function splitAll() {
    if (reduced) return;
    splitEls.forEach((el) => {
      const wasIn = el.classList.contains('in');
      splitLines(el);
      if (wasIn) el.classList.add('in');
    });
  }

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in');
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15, rootMargin: '0px 0px -5% 0px' }
  );

  function observeAll() {
    revealEls.forEach((el) => {
      if (reduced) el.classList.add('in');
      else if (!el.classList.contains('in')) io.observe(el);
    });
  }

  splitAll();
  observeAll();

  if (document.fonts?.ready) {
    document.fonts.ready.then(splitAll);
  }

  let resizeTimer = null;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(splitAll, 200);
  });
}
