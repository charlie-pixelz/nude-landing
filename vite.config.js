import { defineConfig } from 'vite';

export default defineConfig({
  // GitHub Pages publica el sitio en /<repo>/, no en la raíz del dominio.
  // Base relativa: funciona igual en localhost, en un project page o en un
  // dominio propio, sin tener que saber el nombre del repo de antemano.
  // Ver CLAUDE.md: "usar rutas relativas para los assets".
  base: './',
  // Por defecto vite escucha sólo en IPv6 (::1). Safari dentro del
  // Simulator de iOS resuelve "localhost" a 127.0.0.1 y no encuentra a
  // nadie: la página no carga y parece que el server estuviera caído.
  // 127.0.0.1 es loopback IPv4: sigue siendo sólo esta máquina, no expone
  // nada a la red local (para eso haría falta --host / 0.0.0.0).
  server: {
    host: '127.0.0.1',
  },
  preview: {
    host: '127.0.0.1',
  },
  build: {
    outDir: 'dist',
  },
});
