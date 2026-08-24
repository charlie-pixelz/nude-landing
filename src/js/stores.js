// Tiendas: pestañas por región + listado, construidos desde src/data/stores.json.
// Los datos NUNCA viven en el markup: es lo que permite que el cliente edite
// tiendas sin tocar código (PLAN.md, Fase 7). Solo se activa si existe
// #tiendas en el DOM.
//
// Nada de innerHTML acá: todo entra por textContent y por atributos, porque
// el contenido viene de un JSON que edita alguien más (CLAUDE.md).

import datos from '../data/stores.json';

// El enlace al mapa se arma con el nombre y la comuna, no se guarda en el
// JSON: así el cliente agrega una tienda escribiendo dos campos y no una URL.
function urlMapa(nombre, comuna) {
  const q = `${nombre} ${comuna}`.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(q)}`;
}

function filaTienda(tienda) {
  const fila = document.createElement('li');
  fila.className = 'tienda';

  const texto = document.createElement('div');
  const nombre = document.createElement('span');
  nombre.className = 'tienda-nombre';
  nombre.textContent = tienda.nombre;
  const comuna = document.createElement('span');
  comuna.className = 'tienda-comuna';
  comuna.textContent = tienda.comuna;
  texto.append(nombre, comuna);

  const enlace = document.createElement('a');
  enlace.className = 'btn btn-secundario tienda-mapa';
  enlace.href = urlMapa(tienda.nombre, tienda.comuna);
  enlace.target = '_blank';
  enlace.rel = 'noopener';
  // El evento que más importa del sitio entero (CLAUDE.md).
  enlace.dataset.track = 'click_jumbo';
  enlace.textContent = 'Ver en el mapa';
  enlace.setAttribute('aria-label', `Ver ${tienda.nombre} en el mapa`);

  fila.append(texto, enlace);
  return fila;
}

export function initStores() {
  const raiz = document.getElementById('tiendas');
  if (!raiz) return;

  const barra = raiz.querySelector('.tiendas-tabs');
  const panel = raiz.querySelector('.tiendas-panel');
  if (!barra || !panel) return;

  const regiones = datos.regiones || [];
  if (!regiones.length) return;

  const listas = new Map();
  const botones = [];

  regiones.forEach((region) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'tiendas-tab';
    btn.textContent = region.nombre;
    btn.setAttribute('role', 'tab');
    btn.id = `tab-${region.id}`;
    btn.setAttribute('aria-controls', `panel-${region.id}`);
    barra.appendChild(btn);
    botones.push(btn);

    const lista = document.createElement('ul');
    lista.className = 'tiendas-lista';
    lista.id = `panel-${region.id}`;
    lista.setAttribute('role', 'tabpanel');
    lista.setAttribute('aria-labelledby', `tab-${region.id}`);
    region.tiendas.forEach((t) => lista.appendChild(filaTienda(t)));
    panel.appendChild(lista);
    listas.set(region.id, lista);

    btn.addEventListener('click', () => mostrar(region.id));
  });

  function mostrar(id) {
    regiones.forEach((region, i) => {
      const activa = region.id === id;
      botones[i].classList.toggle('activa', activa);
      botones[i].setAttribute('aria-selected', activa ? 'true' : 'false');
      // Fuera de la pestaña activa el tab sale del orden de tabulación:
      // se navega entre pestañas con las flechas, como manda el patrón.
      botones[i].tabIndex = activa ? 0 : -1;
      listas.get(region.id).hidden = !activa;
    });
  }

  // Flechas entre pestañas.
  barra.addEventListener('keydown', (e) => {
    const i = botones.indexOf(document.activeElement);
    if (i < 0) return;
    let siguiente = null;
    if (e.key === 'ArrowRight') siguiente = (i + 1) % botones.length;
    if (e.key === 'ArrowLeft') siguiente = (i - 1 + botones.length) % botones.length;
    if (siguiente === null) return;
    e.preventDefault();
    botones[siguiente].focus();
    mostrar(regiones[siguiente].id);
  });

  barra.setAttribute('role', 'tablist');
  barra.setAttribute('aria-label', 'Regiones');
  mostrar(regiones[0].id);
}
