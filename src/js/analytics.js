// dataLayer + banner de consentimiento + los tres píxeles (GA4, Meta, TikTok),
// cargando solo después del consentimiento. IDs desde variables de entorno:
// nunca hardcodeados, nunca commiteados en claro (ver .env.example).
//
// Patrón de eventos: cualquier elemento con [data-track="nombre_evento"]
// se reporta solo al hacer click, sin tocar este archivo. El evento que
// más importa es click_jumbo, en el bloque "Dónde encontrarlo" (Fase 4).

const CONSENT_KEY = 'nude_consent';

window.dataLayer = window.dataLayer || [];
function pushDataLayer(data) {
  window.dataLayer.push(data);
}

function trackEvent(name, params = {}) {
  pushDataLayer({ event: name, ...params });
}

function loadScript(src, attrs = {}) {
  const s = document.createElement('script');
  s.src = src;
  s.async = true;
  Object.entries(attrs).forEach(([k, v]) => s.setAttribute(k, v));
  document.head.appendChild(s);
}

function loadGA4(id) {
  if (!id) return;
  loadScript(`https://www.googletagmanager.com/gtag/js?id=${id}`);
  window.gtag = window.gtag || function () { pushDataLayer(arguments); };
  window.gtag('js', new Date());
  window.gtag('config', id);
}

function loadMetaPixel(id) {
  if (!id) return;
  !function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
  n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}(window,
  document,'script','https://connect.facebook.net/en_US/fbevents.js');
  window.fbq('init', id);
  window.fbq('track', 'PageView');
}

function loadTikTokPixel(id) {
  if (!id) return;
  !function (w, d, t) {
    w.TiktokAnalyticsObject = t; var ttq = w[t] = w[t] || [];
    ttq.methods = ["page","track","identify","instances","debug","on","off","once","ready","alias","group","enableCookie","disableCookie"];
    ttq.setAndDefer = function (t, e) { t[e] = function () { t.push([e].concat(Array.prototype.slice.call(arguments, 0))) } };
    for (var i = 0; i < ttq.methods.length; i++) ttq.setAndDefer(ttq, ttq.methods[i]);
    ttq.load = function (e, n) {
      var i = "https://analytics.tiktok.com/i18n/pixel/events.js";
      ttq._i = ttq._i || {}; ttq._i[e] = []; ttq._i[e]._u = i;
      ttq._t = ttq._t || {}; ttq._t[e] = +new Date;
      ttq._o = ttq._o || {}; ttq._o[e] = n || {};
      var o = d.createElement("script"); o.type = "text/javascript"; o.async = !0; o.src = i + "?sdkid=" + e + "&lib=" + t;
      var a = d.getElementsByTagName("script")[0]; a.parentNode.insertBefore(o, a)
    };
    ttq.load(id); ttq.page();
  }(window, document, 'ttq');
}

function loadAllPixels() {
  loadGA4(import.meta.env.VITE_GA4_ID);
  loadMetaPixel(import.meta.env.VITE_META_PIXEL_ID);
  loadTikTokPixel(import.meta.env.VITE_TIKTOK_PIXEL_ID);
  trackEvent('consent_granted');
}

function getConsent() {
  try {
    return localStorage.getItem(CONSENT_KEY);
  } catch {
    return null;
  }
}

function setConsent(value) {
  try {
    localStorage.setItem(CONSENT_KEY, value);
  } catch {
    /* localStorage no disponible: el banner vuelve a aparecer, no rompe nada */
  }
}

function buildBanner() {
  const banner = document.createElement('div');
  banner.className = 'consent-banner';
  banner.setAttribute('role', 'dialog');
  banner.setAttribute('aria-label', 'Consentimiento de cookies');

  const text = document.createElement('p');
  text.textContent = 'Usamos cookies para medir cómo funciona el sitio. Puedes aceptarlas o rechazarlas.';

  const actions = document.createElement('div');
  actions.className = 'consent-banner-actions';

  const accept = document.createElement('button');
  accept.className = 'btn btn-primario';
  accept.type = 'button';
  accept.textContent = 'Aceptar';

  const reject = document.createElement('button');
  reject.className = 'btn btn-secundario';
  reject.type = 'button';
  reject.textContent = 'Rechazar';

  accept.addEventListener('click', () => {
    setConsent('granted');
    loadAllPixels();
    banner.remove();
  });
  reject.addEventListener('click', () => {
    setConsent('denied');
    banner.remove();
  });

  actions.append(accept, reject);
  banner.append(text, actions);
  return banner;
}

function initConsentBanner() {
  const consent = getConsent();
  if (consent === 'granted') {
    loadAllPixels();
    return;
  }
  if (consent === 'denied') return;
  document.body.appendChild(buildBanner());
}

function initTrackClicks() {
  document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-track]');
    if (!el) return;
    trackEvent(el.dataset.track);
  });
}

pushDataLayer({ event: 'dataLayer_ready' });
initConsentBanner();
initTrackClicks();

export { trackEvent };
