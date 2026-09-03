"""Genera la imagen de previsualización (Open Graph) del sitio.

    python3 scripts/og-image.py

Salida: public/og.jpg, 1200x630, el tamaño canónico que piden Facebook,
WhatsApp, LinkedIn y X. Cualquier otra proporción la recortan ellos, y el
recorte nunca cae donde uno quiere.

QUÉ TIENE QUE SOBREVIVIR. Esta imagen se ve casi siempre en miniatura, en el
hilo de un chat, a veces a 200px de ancho. Ahí no se lee una bajada: se lee
el pack, el logo y a lo sumo tres palabras. Por eso el texto es el del hero,
sin agregar copy nuevo, y va en cuerpo grande.

EL FONDO. El pack sale de assets/imagenes-nuevas/productos/producto-01.png,
cuyo fondo de set está en (239,173,191) y no en el --rosa del sitio. Se
corrige con una ganancia por canal hacia el token y se difumina el borde
izquierdo contra el rosa plano, que es la misma solución que usa el hero en
escritorio: el borde de una foto nunca calza exacto con un color plano, así
que en vez de pelear por el calce se disuelve la unión.

El texto se compone en un PDF intermedio para poder usar las fuentes reales
de la marca (Halloween Days y Archivo) y se rasteriza al tamaño final.
"""
import os
import pathlib
import subprocess
import sys

import numpy as np
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

BASE = pathlib.Path(__file__).resolve().parent.parent
FF = os.path.expanduser('~/.local/bin/ffmpeg')
FUENTES = BASE / 'src/assets/fonts'
ORIGEN = BASE / 'assets/imagenes-nuevas/productos/producto-01.png'
SALIDA = BASE / 'public/og.jpg'
TMP = pathlib.Path(os.environ.get('TMPDIR', '/tmp')) / 'nude-og'
TMP.mkdir(parents=True, exist_ok=True)

W, H = 1200, 630
ROSA = np.array([250., 184., 196.])       # --rosa #FAB8C4
ROSA_HEX = HexColor('#FAB8C4')
NEGRO_HEX = HexColor('#141110')
BAJADA_HEX = HexColor('#4A3A3E')

# Qué parte del ancho ocupa el pack, y sobre cuánto de ese ancho se difumina
# su borde izquierdo. El 12% es el mismo criterio del hero (allá es 10% sobre
# una columna más angosta).
FRAC_PACK = 0.52
FRAC_PLUMA = 0.12


def ffmpeg_a_array(ruta, w, h, filtros=None):
    cmd = [FF, '-nostdin', '-v', 'error', '-i', str(ruta)]
    if filtros:
        cmd += ['-vf', filtros]
    cmd += ['-pix_fmt', 'rgb24', '-f', 'rawvideo', '-']
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(h, w, 3).astype(np.float32)


def caja_del_pack(a):
    """El pack es lo oscuro; el fondo del set nunca baja de 150 en el máximo."""
    osc = a.max(2) < 150
    filas, cols = osc.sum(1), osc.sum(0)
    ys = np.where(filas > 15)[0]
    xs = np.where(cols > 15)[0]
    return xs.min(), xs.max(), ys.min(), ys.max()


def gblur(f, sigma):
    h, w = f.shape[:2]
    b = np.clip(f, 0, 255).astype(np.uint8).tobytes()
    q = subprocess.run(
        [FF, '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
         '-i', '-', '-vf', f'gblur=sigma={sigma}:steps=3', '-pix_fmt', 'rgb24',
         '-f', 'rawvideo', '-'], input=b, capture_output=True, check=True).stdout
    return np.frombuffer(q, np.uint8).reshape(h, w, 3).astype(np.float32)


def aplanar_fondo(rec):
    """Lleva el fondo del set al --rosa, punto por punto.

    El pack se recorta de la estimación y su hueco se rellena difundiendo el
    fondo vecino: el gradiente del set es liso a esta escala y aguanta que se
    interpole por debajo del producto. Después la corrección se aplica con
    peso, para que el negro del envase no se tiña de rosa."""
    esq = np.concatenate([rec[:70, :70].reshape(-1, 3), rec[:70, -70:].reshape(-1, 3),
                          rec[-70:, :70].reshape(-1, 3)])
    ref = np.median(esq, 0)
    # Fondo = lo que se parece a la referencia. El umbral es generoso porque
    # el gradiente del set se aleja bastante de las esquinas.
    es_fondo = (np.abs(rec - ref).mean(2) < 26).astype(np.float32)

    f = rec * es_fondo[..., None]
    m = es_fondo[..., None].copy()
    for sigma in (90, 70, 50, 30):
        fb = gblur(f * m, sigma)
        mb = gblur(np.repeat(m, 3, 2) * 255, sigma) / 255
        f = np.where(m > 0.5, f, fb / np.clip(mb, 3e-3, None))
        m = np.maximum(m, (mb[..., :1] > 0.02).astype(np.float32))
    modelo = gblur(f, 20)

    gain = ROSA / np.clip(modelo, 1, None)
    d = np.abs(rec - modelo).mean(2)
    w = np.clip(1 - (d - 14) / 46, 0, 1)
    return np.clip(rec * (1 + (gain - 1) * w[..., None]), 0, 255).astype(np.uint8)


def main():
    if not ORIGEN.exists():
        sys.exit(f'falta {ORIGEN}')
    for f in ('halloween-days', 'archivo-black', 'archivo-regular'):
        if not (FUENTES / f'{f}.woff2').exists():
            sys.exit(f'falta la fuente {f}')

    # --- 1. las fuentes, de woff2 a ttf (reportlab no lee woff2) ----------
    from fontTools.ttLib import TTFont as FTFont
    for nombre, arch in (('Display', 'halloween-days'), ('Black', 'archivo-black'),
                         ('Body', 'archivo-regular')):
        ttf = TMP / f'{arch}.ttf'
        if not ttf.exists():
            t = FTFont(str(FUENTES / f'{arch}.woff2'))
            t.flavor = None
            t.save(str(ttf))
        pdfmetrics.registerFont(TTFont(nombre, str(ttf)))

    # --- 2. el pack, recortado y con el fondo llevado al token -----------
    ancho_pack = int(W * FRAC_PACK)
    prueba = subprocess.run(
        [os.path.expanduser('~/.local/bin/ffprobe'), '-v', 'error',
         '-show_entries', 'stream=width,height', '-of', 'csv=p=0', str(ORIGEN)],
        capture_output=True, text=True, check=True).stdout.strip()
    ow, oh = (int(v) for v in prueba.split(','))
    a = ffmpeg_a_array(ORIGEN, ow, oh)

    x0, x1, y0, y1 = caja_del_pack(a)
    # Aire alrededor del pack: 6% del ancho del propio pack a cada lado, y lo
    # que haga falta arriba y abajo para llegar a la proporción de la caja.
    aire = int((x1 - x0) * 0.06)
    cx0, cx1 = max(0, x0 - aire), min(ow, x1 + aire)
    alto_obj = int((cx1 - cx0) * H / ancho_pack)
    cy = (y0 + y1) // 2
    cy0, cy1 = cy - alto_obj // 2, cy + alto_obj // 2
    if cy0 < 0:
        cy0, cy1 = 0, alto_obj
    if cy1 > oh:
        cy0, cy1 = oh - alto_obj, oh
    rec = a[cy0:cy1, cx0:cx1]

    # Se escala ANTES de aplanar: el aplanado hace varios desenfoques y sobre
    # los 3700px del original tarda de más sin cambiar el resultado, porque el
    # modelo del fondo es liso por definición.
    crudo = TMP / 'pack.raw'
    crudo.write_bytes(np.clip(rec, 0, 255).astype(np.uint8).tobytes())
    pack_png = TMP / 'pack.png'
    subprocess.run(
        [FF, '-nostdin', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
         '-s', f'{rec.shape[1]}x{rec.shape[0]}', '-i', str(crudo),
         '-vf', f'scale={ancho_pack}:{H}:flags=lanczos', '-frames:v', '1', '-y',
         str(pack_png)], check=True)

    # El fondo del set trae gradiente. Una ganancia global lo deja intacto y,
    # pegado al rosa plano de la izquierda, se lee como un panel más oscuro.
    # Se aplana por pixel con el mismo método que hero-frames-n9.py.
    pk = aplanar_fondo(ffmpeg_a_array(pack_png, ancho_pack, H)).astype(np.float32)

    # Alfa en rampa sobre el borde izquierdo: disuelve la unión con el plano.
    pluma = int(W * FRAC_PLUMA)
    alfa = np.ones((H, ancho_pack), np.float32)
    alfa[:, :pluma] = np.linspace(0, 1, pluma)[None, :]
    rgba = np.dstack([pk, alfa * 255]).astype(np.uint8)
    crudo_a = TMP / 'pack_rgba.raw'
    crudo_a.write_bytes(rgba.tobytes())
    pack_rgba = TMP / 'pack_rgba.png'
    subprocess.run(
        [FF, '-nostdin', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgba',
         '-s', f'{ancho_pack}x{H}', '-i', str(crudo_a), '-frames:v', '1', '-y',
         str(pack_rgba)], check=True)

    # --- 3. la composición, en un PDF del tamaño exacto ------------------
    pdf = TMP / 'og.pdf'
    c = canvas.Canvas(str(pdf), pagesize=(W, H))
    c.setFillColor(ROSA_HEX)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.drawImage(ImageReader(str(pack_rgba)), W - ancho_pack, 0,
                width=ancho_pack, height=H, mask='auto')

    M = 64
    logo = BASE / 'src/assets/img/logo-negro.png'
    if logo.exists():
        alto_logo = 78
        c.drawImage(ImageReader(str(logo)), M, H - M - alto_logo,
                    width=alto_logo * 300 / 175, height=alto_logo, mask='auto')

    # El titular del hero, textual. Halloween Days es el rol de portada.
    c.setFont('Display', 96)
    c.setFillColor(NEGRO_HEX)
    c.drawString(M, 268, 'Hasta hoy.')

    # La bajada del hero, textual. Es la que nombra Jumbo, que es el único
    # dato que el sitio no se puede permitir que nadie se lleve sin ver.
    # A 27pt se perdía en la miniatura de 240px de ancho de WhatsApp, que es
    # donde esta imagen se ve la mayor parte de las veces. A 33 se lee.
    c.setFont('Body', 33)
    c.setFillColor(BAJADA_HEX)
    c.drawString(M, 188, 'Papel higiénico húmedo,')
    c.drawString(M, 144, 'ya en Jumbo.')

    c.showPage()
    c.save()

    # --- 4. al tamaño final, en JPG --------------------------------------
    # JPG y no WebP: los rastreadores de WhatsApp y de varios clientes de
    # correo todavía no lo muestran, y una previsualización que no carga es
    # peor que una que pesa 40 KB de más.
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(pdf))
    img = doc[0].render(scale=1).to_pil().convert('RGB')
    img.save(SALIDA, 'JPEG', quality=88, optimize=True, progressive=True)
    peso = SALIDA.stat().st_size
    print(f'{SALIDA.relative_to(BASE)}  {img.size[0]}x{img.size[1]}  {peso // 1024} KB')
    if peso > 300 * 1024:
        print('  OJO: sobre 300 KB algunos clientes dejan de mostrar la miniatura')


if __name__ == '__main__':
    main()
