import './styles/fonts.css';
import './styles/tokens.css';
import './styles/base.css';
import './styles/sections/hero.css';
import './styles/sections/cuerpo.css';

import { initReveal } from './js/reveal.js';
import { initNavZones } from './js/nav-zones.js';
import { initHeroScrub } from './js/hero-scrub.js';
import { initStores } from './js/stores.js';
import { initFaq } from './js/faq.js';
import { initForm } from './js/form.js';
import './js/analytics.js';

initReveal();
initNavZones();
initHeroScrub();
initStores();
initFaq();
initForm();
