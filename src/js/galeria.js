// Carrusel de la galería de producto. Sólo se activa si existe #galeria en
// el DOM, como el resto de los módulos.
//
// En escritorio no hace nada: ahí la galería es una grilla movida por el
// scroll, y eso es CSS puro (view-timeline). Este archivo sólo existe por
// las dos cosas que el CSS no puede hacer en el carrusel de móvil: avanzar
// de a una foto exacta con las flechas, y avanzar solo cada tantos segundos.
//
// El arrastre con el dedo NO está acá y no debería estarlo: la pista es un
// scroller nativo con scroll-snap, así que el gesto, la inercia y el imán al
// centro los resuelve el navegador mejor que cualquier cosa que escribamos.

const SEGUNDOS = 3;

export function initGaleria() {
  const raiz = document.getElementById('galeria');
  if (!raiz) return;

  const pista = raiz.querySelector('.galeria-lista');
  const antes = raiz.querySelector('[data-galeria="antes"]');
  const despues = raiz.querySelector('[data-galeria="despues"]');
  if (!pista || !antes || !despues) return;

  const quieto = window.matchMedia('(prefers-reduced-motion: reduce)');
  // Mismo corte que el CSS: sobre 760px la galería es grilla y el carrusel
  // no existe. Si se cambia allá, se cambia acá.
  const enCarrusel = window.matchMedia('(max-width: 759.98px)');

  // Mover "una foto" es mover el ancho de una tarjeta más la separación. Se
  // mide del DOM en vez de recalcularlo de los vw, así sigue siendo correcto
  // si cambia el tamaño de la ventana.
  const paso = () => {
    const [a, b] = pista.children;
    return b ? b.getBoundingClientRect().left - a.getBoundingClientRect().left : 0;
  };
  const alFinal = () => pista.scrollLeft >= pista.scrollWidth - pista.clientWidth - 2;

  function mover(signo, volver = false) {
    pista.scrollTo({
      left: volver ? 0 : pista.scrollLeft + signo * paso(),
      behavior: quieto.matches ? 'auto' : 'smooth',
    });
    reiniciarReloj();
  }

  antes.addEventListener('click', () => mover(-1));
  despues.addEventListener('click', () => mover(1));

  // ── Avance solo ────────────────────────────────────────────────────
  // Cuatro condiciones, y las cuatro importan:
  //   · que la galería esté en pantalla — el PLAN pide que las piezas se
  //     detengan fuera de vista, y un temporizador invisible es batería
  //     regalada;
  //   · que el carrusel sea la maquetación activa (en escritorio no hay);
  //   · que nadie tenga movimiento reducido activo;
  //   · que el usuario no haya tocado nada hace poco. Cualquier movimiento,
  //     propio o ajeno, reinicia el reloj, así el avance nunca compite con
  //     el dedo.
  let reloj = null;
  let enPantalla = false;

  function reiniciarReloj() {
    clearTimeout(reloj);
    if (!enPantalla || !enCarrusel.matches || quieto.matches) return;
    reloj = setTimeout(() => {
      if (alFinal()) mover(0, true);
      else mover(1);
    }, SEGUNDOS * 1000);
  }

  new IntersectionObserver(([entrada]) => {
    enPantalla = entrada.isIntersecting;
    reiniciarReloj();
  }, { threshold: 0.4 }).observe(pista);

  // Un arrastre dispara cientos de eventos de scroll; el retardo evita
  // reprogramar el reloj en cada uno.
  let rebote = null;
  pista.addEventListener('scroll', () => {
    clearTimeout(rebote);
    rebote = setTimeout(reiniciarReloj, 120);
  }, { passive: true });

  ['pointerdown', 'keydown'].forEach((evento) =>
    pista.addEventListener(evento, reiniciarReloj, { passive: true }));

  quieto.addEventListener('change', reiniciarReloj);
  enCarrusel.addEventListener('change', reiniciarReloj);
}
