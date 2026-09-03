"""Genera el favicon y los íconos de aplicación desde el logotipo.

    python3 scripts/favicon.py

Salida, toda en public/:
    favicon.ico          16, 32 y 48 en un archivo
    favicon-32.png       el que usan los navegadores modernos
    apple-touch-icon.png 180x180, para "agregar a la pantalla de inicio" en iOS
    icon-192.png         Android
    icon-512.png         Android

POR QUÉ EL ÍCONO LLEVA FONDO ROSA Y NO ES SOLO EL LOGO. El favicon vive en la
pestaña, y ahí el fondo lo pone el navegador según el tema del sistema. Un
logotipo negro desaparece en tema oscuro y uno blanco desaparece en tema
claro. Con fondo propio se ve igual en los dos, y el brandbook ya dice cuál
corresponde: versión negra sobre rosa. El color hace además de identificador
a tamaños donde la forma ya no se distingue.

POR QUÉ VA SIN "WIPES". Medido: el logotipo completo a 16px es una mancha sin
forma reconocible, y el descriptor no se lee hasta los 48. Dejando solo la
palabra que identifica, esta gana todo el cuadro y se lee limpia a 32.
Decisión de Charlie el 3/9/2026. No se deforma, no se rota ni se recolorea
nada: se omite el descriptor, que es la reducción habitual de una marca.

El logotipo se separa por componentes conectados y se descartan los trozos
chicos, que son los de "wipes". El umbral está holgado: el trozo más chico
que se conserva tiene 1930px y el más grande que se descarta, 907.
"""
import os
import pathlib
import struct
import subprocess
import sys
from collections import deque

import numpy as np

BASE = pathlib.Path(__file__).resolve().parent.parent
FF = os.path.expanduser('~/.local/bin/ffmpeg')
FFPROBE = os.path.expanduser('~/.local/bin/ffprobe')
LOGO = BASE / 'src/assets/img/logo-negro.png'
OUT = BASE / 'public'
TMP = pathlib.Path(os.environ.get('TMPDIR', '/tmp')) / 'nude-favicon'
TMP.mkdir(parents=True, exist_ok=True)

ROSA = np.array([250, 184, 196], np.float32)   # --rosa #FAB8C4
MIN_COMPONENTE = 1500

# Cuánto aire alrededor de la marca, por destino. iOS recorta las esquinas
# del apple-touch-icon con un radio generoso, así que ahí el margen es mayor
# o la marca queda mordida.
MARGENES = {'favicon': 0.10, 'apple': 0.20, 'android': 0.14}


def dimensiones(ruta):
    salida = subprocess.run(
        [FFPROBE, '-v', 'error', '-show_entries', 'stream=width,height',
         '-of', 'csv=p=0', str(ruta)], capture_output=True, text=True, check=True).stdout
    return (int(v) for v in salida.strip().split(','))


def leer_rgba(ruta, w, h):
    out = subprocess.run(
        [FF, '-nostdin', '-v', 'error', '-i', str(ruta), '-pix_fmt', 'rgba',
         '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(h, w, 4).astype(np.float32)


def solo_la_palabra(a):
    """Descarta los componentes chicos del logotipo, que son el descriptor."""
    h, w = a.shape[:2]
    tinta = a[..., 3] > 60
    visto = np.zeros((h, w), bool)
    conservar = np.zeros((h, w), bool)
    for j in range(h):
        for i in range(w):
            if not tinta[j, i] or visto[j, i]:
                continue
            cola = deque([(j, i)])
            visto[j, i] = True
            grupo = [(j, i)]
            while cola:
                cj, ci = cola.popleft()
                for dj in (-1, 0, 1):
                    for di in (-1, 0, 1):
                        nj, ni = cj + dj, ci + di
                        if 0 <= nj < h and 0 <= ni < w and tinta[nj, ni] and not visto[nj, ni]:
                            visto[nj, ni] = True
                            cola.append((nj, ni))
                            grupo.append((nj, ni))
            if len(grupo) >= MIN_COMPONENTE:
                for gj, gi in grupo:
                    conservar[gj, gi] = True
    b = a.copy()
    b[..., 3] *= conservar
    return b


def icono(marca, tam, margen):
    """La marca centrada en un cuadrado rosa del tamaño pedido."""
    ys, xs = np.where(marca[..., 3] > 60)
    rec = marca[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    ch, cw = rec.shape[:2]

    crudo = TMP / 'marca.raw'
    crudo.write_bytes(np.clip(rec, 0, 255).astype(np.uint8).tobytes())

    interior = tam * (1 - 2 * margen)
    escala = min(interior / cw, interior / ch)
    nw, nh = max(1, round(cw * escala)), max(1, round(ch * escala))
    chico = TMP / f'marca-{tam}.png'
    subprocess.run(
        [FF, '-nostdin', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
         '-s', f'{cw}x{ch}', '-i', str(crudo),
         '-vf', f'scale={nw}:{nh}:flags=lanczos', '-frames:v', '1', '-y', str(chico)],
        check=True)
    s = leer_rgba(chico, nw, nh)

    lienzo = np.empty((tam, tam, 3), np.float32)
    lienzo[:] = ROSA
    ox, oy = (tam - nw) // 2, (tam - nh) // 2
    alfa = s[..., 3:4] / 255.0
    lienzo[oy:oy + nh, ox:ox + nw] = (s[..., :3] * alfa
                                      + lienzo[oy:oy + nh, ox:ox + nw] * (1 - alfa))
    return np.clip(lienzo, 0, 255).astype(np.uint8)


def escribir_png(arr, destino):
    tam = arr.shape[0]
    crudo = TMP / f'ico-{tam}-{destino.stem}.raw'
    crudo.write_bytes(arr.tobytes())
    subprocess.run(
        [FF, '-nostdin', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', f'{tam}x{tam}', '-i', str(crudo), '-frames:v', '1', '-y', str(destino)],
        check=True)


def escribir_ico(pngs, destino):
    """Empaqueta varios PNG en un .ico.

    El formato admite PNG embebido desde Windows Vista, así que no hace falta
    convertir a BMP: cabecera de 6 bytes, una entrada de 16 por imagen, y los
    archivos enteros a continuación."""
    datos = [p.read_bytes() for p in pngs]
    n = len(datos)
    cab = struct.pack('<HHH', 0, 1, n)
    desplazamiento = 6 + 16 * n
    entradas, cuerpo = b'', b''
    for png, bruto in zip(pngs, datos):
        tam = int(png.stem.split('-')[-1])
        entradas += struct.pack('<BBBBHHII', tam if tam < 256 else 0,
                                tam if tam < 256 else 0, 0, 0, 1, 32,
                                len(bruto), desplazamiento)
        desplazamiento += len(bruto)
        cuerpo += bruto
    destino.write_bytes(cab + entradas + cuerpo)


def main():
    if not LOGO.exists():
        sys.exit(f'falta {LOGO}')
    w, h = dimensiones(LOGO)
    marca = solo_la_palabra(leer_rgba(LOGO, w, h))

    sueltos = []
    for tam in (16, 32, 48):
        p = TMP / f'favicon-{tam}.png'
        escribir_png(icono(marca, tam, MARGENES['favicon']), p)
        sueltos.append(p)
    escribir_ico(sueltos, OUT / 'favicon.ico')
    escribir_png(icono(marca, 32, MARGENES['favicon']), OUT / 'favicon-32.png')
    escribir_png(icono(marca, 180, MARGENES['apple']), OUT / 'apple-touch-icon.png')
    escribir_png(icono(marca, 192, MARGENES['android']), OUT / 'icon-192.png')
    escribir_png(icono(marca, 512, MARGENES['android']), OUT / 'icon-512.png')

    for f in ('favicon.ico', 'favicon-32.png', 'apple-touch-icon.png',
              'icon-192.png', 'icon-512.png'):
        print(f'  {f:<22} {(OUT / f).stat().st_size / 1024:6.1f} KB')


if __name__ == '__main__':
    main()
