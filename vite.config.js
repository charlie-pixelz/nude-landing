import { defineConfig } from 'vite';

export default defineConfig({
  // GitHub Pages publica el sitio en /<repo>/, no en la raíz del dominio.
  // Base relativa: funciona igual en localhost, en un project page o en un
  // dominio propio, sin tener que saber el nombre del repo de antemano.
  // Ver CLAUDE.md: "usar rutas relativas para los assets".
  base: './',
  build: {
    outDir: 'dist',
  },
});
