// Formulario "avísame": correo + comuna. Sólo se activa si existe
// #notify-form en el DOM.
//
// El sitio no tiene backend (GitHub Pages), así que el envío va por POST a un
// servicio de terceros. El endpoint vive en VITE_FORM_ENDPOINT y no está
// escrito acá: cambiar de servicio es cambiar una variable de entorno, no
// tocar este archivo. Cualquier servicio que acepte un POST y responda 2xx
// sirve (Formspree, Basin, Web3Forms, un Google Form vía fetch no).
//
// Ojo con lo que se envía: correo + comuna de personas en Chile son datos
// personales. No se guardan en el navegador, no se mandan a los píxeles y el
// evento de medición viaja sin ningún campo del formulario.

import { trackEvent } from './analytics.js';

const ENDPOINT = import.meta.env.VITE_FORM_ENDPOINT || '';

// Deliberadamente permisiva: validar correos con regex estricta rechaza
// direcciones válidas. Acá sólo se atajan los errores de tipeo evidentes;
// quien valida de verdad es el servicio, mandando el correo.
const CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

const TEXTO = {
  enviar: 'Avísame',
  enviando: 'Enviando',
  ok: 'Listo. Te avisamos.',
  invalido: 'Revisa el correo y la comuna, algo quedó mal escrito.',
  falla: 'No se pudo enviar. Intenta de nuevo en un rato.',
  sinConectar: 'El formulario todavía no está conectado. Esto es una maqueta.',
};

export function initForm() {
  const form = document.getElementById('notify-form');
  if (!form) return;

  const email = form.querySelector('#notify-email');
  const comuna = form.querySelector('#notify-comuna');
  const boton = form.querySelector('button[type="submit"]');
  const msgOk = document.getElementById('notify-ok');
  const msgError = document.getElementById('notify-error');
  if (!email || !comuna || !boton || !msgOk || !msgError) return;

  // Trampa para bots: un campo que ninguna persona ve ni alcanza con Tab.
  // Si viene lleno, el envío se descarta en silencio.
  const trampa = document.createElement('input');
  trampa.type = 'text';
  trampa.name = 'sitio';
  trampa.tabIndex = -1;
  trampa.autocomplete = 'off';
  trampa.setAttribute('aria-hidden', 'true');
  trampa.className = 'trampa-bot';
  form.insertBefore(trampa, boton);

  function limpiar() {
    msgOk.hidden = true;
    msgError.hidden = true;
    [email, comuna].forEach((campo) => campo.removeAttribute('aria-invalid'));
  }

  function fallar(texto, campo) {
    msgError.textContent = texto;
    msgError.hidden = false;
    if (campo) {
      campo.setAttribute('aria-invalid', 'true');
      campo.focus();
    }
  }

  function ocupado(si) {
    boton.disabled = si;
    boton.textContent = si ? TEXTO.enviando : TEXTO.enviar;
    form.setAttribute('aria-busy', si ? 'true' : 'false');
  }

  // Al corregir, el mensaje de error se va solo: dejarlo puesto mientras la
  // persona reescribe convierte un aviso en un reproche.
  [email, comuna].forEach((campo) => {
    campo.addEventListener('input', () => {
      if (!msgError.hidden) limpiar();
    });
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    limpiar();

    if (trampa.value) return;

    const valorEmail = email.value.trim();
    const valorComuna = comuna.value.trim();

    if (!CORREO.test(valorEmail)) return fallar(TEXTO.invalido, email);
    if (valorComuna.length < 2) return fallar(TEXTO.invalido, comuna);

    if (!ENDPOINT) return fallar(TEXTO.sinConectar);

    ocupado(true);
    try {
      const r = await fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          email: valorEmail,
          comuna: valorComuna,
          origen: 'landing-nude',
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);

      form.hidden = true;
      msgOk.textContent = TEXTO.ok;
      msgOk.hidden = false;
      // Sin campos del formulario: el evento cuenta, no identifica.
      trackEvent('lead_avisame');
    } catch {
      fallar(TEXTO.falla);
    } finally {
      ocupado(false);
    }
  });
}
