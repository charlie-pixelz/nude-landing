"""Regenera los 96 frames del hero desde los tres clips.

    python3 scripts/hero-frames.py <carpeta-destino>
    CAL_SM=70 CAL_LG=74 python3 scripts/hero-frames.py /tmp/frames

Los másters viven en assets/verticales-hd/, que está en .gitignore: este
script no corre en un clon limpio, y no tiene por qué. Está versionado
porque la receta de abajo se perdió una vez y reconstruirla costó una
sesión entera de comparar frames contra los clips.


Receta, reconstruida comparando los frames actuales contra los clips:
  nude6   frames 72..120 paso 2  -> 25 frames
  nude6-5 frames  0.. 70 paso 2  -> 36 frames   (el puente)
  nude5   frames  0.. 68 paso 2  -> 35 frames
  total 96 a 12 fps = 8,0 s

Graduación selectiva: cada frame mide su propio fondo (mediana de un anillo
de borde, para que un pixel de producto no arrastre la medida) y se corrige
contra el token --rosa #F3C9D3. La corrección se aplica con peso: completa
en los tonos cercanos al fondo, nula en los oscuros del producto. Así no se
tiñe el pack, que fue justo el defecto de la primera versión.
"""
import subprocess, pathlib, os, sys

FF = os.path.expanduser('~/.local/bin/ffmpeg')
BASE = pathlib.Path('/Users/charlie/Desktop/Charlie/Trabajos/NUDE/Nueva landing')
SRC = BASE / 'assets/verticales-hd'
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
(OUT/'lg').mkdir(exist_ok=True); (OUT/'sm').mkdir(exist_ok=True)

W, H = 1080, 1920
PLANO = W * H
ROSA = (243, 201, 211)          # --rosa #F3C9D3
SPREAD = 70                      # hasta dónde llega la corrección, en niveles
CAL_LG = int(os.environ.get('CAL_LG', 80))
CAL_SM = int(os.environ.get('CAL_SM', 78))

TRAMOS = [
    ('nude6.mp4',   72, 120),
    ('nude6-5.mp4',  0,  70),
    ('nude5.mp4',    0,  68),
]

def leer_tramo(nombre, ini, fin):
    """Devuelve los frames del tramo como bytes gbrp, uno por uno."""
    sel = f"gte(n\\,{ini})*lte(n\\,{fin})*not(mod(n-{ini}\\,2))"
    p = subprocess.Popen(
        [FF,'-v','error','-i',str(SRC/nombre),'-vf',f'select={sel}',
         '-vsync','0','-pix_fmt','gbrp','-f','rawvideo','-'],
        stdout=subprocess.PIPE)
    while True:
        buf = p.stdout.read(PLANO*3)
        if len(buf) < PLANO*3: break
        yield buf
    p.stdout.close(); p.wait()

def fondo(planos):
    """Mediana de un anillo de borde, por canal. planos = (G, B, R)."""
    out = []
    for pl in planos:
        m = []
        for y in range(0, H, 17):
            base = y*W
            for x in (3, 9, W-10, W-4):
                m.append(pl[base+x])
        m.sort()
        out.append(m[len(m)//2])
    return out

def tabla(bg, objetivo):
    """LUT de 256 entradas: corrige hacia el objetivo con peso por cercanía."""
    off = objetivo - bg
    t = bytearray(256)
    for v in range(256):
        w = 1.0 - abs(v - bg) / SPREAD
        if w < 0: w = 0.0
        nv = int(round(v + off * w))
        t[v] = 0 if nv < 0 else (255 if nv > 255 else nv)
    return bytes(t)

def escribir(buf, idx):
    for carpeta, ancho, alto, cal in (('lg',1080,1920,CAL_LG), ('sm',810,1440,CAL_SM)):
        dest = OUT/carpeta/f'f_{idx:03d}.webp'
        # Sin filtro de escala cuando el tamaño ya es el correcto: aunque
        # scale=1080:1920 sobre una fuente de 1080x1920 no cambie el tamaño,
        # lanczos igual resamplea y ablanda la imagen (medido: -14% de
        # contraste local en el set grande, y no se recupera subiendo la
        # calidad del webp, que fue lo que delató que no era compresión).
        vf = [] if (ancho, alto) == (W, H) else ['-vf', f'scale={ancho}:{alto}:flags=lanczos']
        subprocess.run(
            [FF,'-v','error','-f','rawvideo','-pix_fmt','gbrp','-s',f'{W}x{H}','-i','-',
             *vf,'-c:v','libwebp','-quality',str(cal),'-preset','picture',
             '-frames:v','1','-y',str(dest)],
            input=buf, check=True)

idx = 0
desvios = []
for nombre, ini, fin in TRAMOS:
    n = 0
    for buf in leer_tramo(nombre, ini, fin):
        idx += 1; n += 1
        G = buf[0:PLANO]; B = buf[PLANO:2*PLANO]; R = buf[2*PLANO:3*PLANO]
        bg = fondo((G, B, R))                      # orden gbrp
        # ROSA viene en RGB; el anillo mide en orden G,B,R
        objetivo = (ROSA[1], ROSA[2], ROSA[0])
        nuevo = (G.translate(tabla(bg[0], objetivo[0]))
                 + B.translate(tabla(bg[1], objetivo[1]))
                 + R.translate(tabla(bg[2], objetivo[2])))
        # recalcula el fondo ya corregido, para el informe
        g2 = fondo((nuevo[0:PLANO], nuevo[PLANO:2*PLANO], nuevo[2*PLANO:3*PLANO]))
        desvio = max(abs(g2[0]-objetivo[0]), abs(g2[1]-objetivo[1]), abs(g2[2]-objetivo[2]))
        desvios.append(desvio)
        escribir(nuevo, idx)
        if idx % 12 == 0: print(f'  frame {idx:>3}/96  desvio max {desvio}', flush=True)
    print(f'{nombre}: {n} frames', flush=True)

print(f'\ntotal {idx} frames')
print(f'desvio contra --rosa: max {max(desvios)}, promedio {sum(desvios)/len(desvios):.2f}')
