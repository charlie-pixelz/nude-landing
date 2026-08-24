// Preguntas frecuentes, construidas desde src/data/faq.json. Sólo se activa
// si existe #faq en el DOM.
//
// Se dibuja con <details>/<summary> nativos: el teclado, el lector de
// pantalla y el estado abierto/cerrado vienen resueltos por el navegador.
// Escribir un acordeón a mano acá sería más código para peor accesibilidad.
//
// Una pregunta sin respuesta no se publica. Es lo que permite que el JSON
// también sea la lista de lo que falta preguntarle a la marca, sin que el
// sitio muestre una pregunta a medias.
//
// Nada de innerHTML: el contenido viene de un JSON que edita alguien más.

import datos from '../data/faq.json';

export function initFaq() {
  const raiz = document.getElementById('faq');
  if (!raiz) return;

  const lista = raiz.querySelector('.faq-lista');
  if (!lista) return;

  const preguntas = (datos.preguntas || []).filter(
    (item) => item.p && item.r && item.r.trim(),
  );

  // Sin preguntas publicables no queda una sección vacía: se saca entera.
  if (!preguntas.length) {
    const seccion = raiz.closest('section');
    if (seccion) seccion.hidden = true;
    return;
  }

  // Sin clase .rv acá: el IntersectionObserver de reveal.js captura la lista
  // de elementos una sola vez al arrancar, así que lo que se crea después
  // nunca se revelaría. El contenedor #faq sí lleva .rv en el markup y
  // arrastra a todo el bloque, igual que el listado de tiendas.
  preguntas.forEach((item) => {
    const fila = document.createElement('details');
    fila.className = 'faq-item';

    const titulo = document.createElement('summary');
    titulo.className = 'faq-p';
    titulo.textContent = item.p;

    const cuerpo = document.createElement('p');
    cuerpo.className = 'faq-r';
    cuerpo.textContent = item.r;

    fila.append(titulo, cuerpo);
    lista.appendChild(fila);
  });
}
