"""Genera los frames del hero desde nude8.mp4, el clip de Higgsfield.

    python3 scripts/hero-frames-n8.py <carpeta-destino>
    CAL_SM=70 CAL_LG=74 FIN=210 python3 scripts/hero-frames-n8.py /tmp/frames

Hermano de hero-frames.py, que arma el hero de tres clips. Este parte de un
solo clip y hace dos correcciones que aquel no necesitaba.

El clip: 241 frames a 24 fps, 1080x1920, HEVC 10 bits. El pack flota, gira 360,
se abre y sale el paño. Se toma de INI a FIN de dos en dos.
  0..16    el pack de frente, casi quieto      <- se recorta
  20..150  gira 360 y aterriza
  150..165 se abre la tapa
  165..210 sube el paño
  210..228 el paño se sale por arriba del cuadro
  228..240 la tapa se cierra y el pack queda de frente

Se recorta el principio y no el final, decisión de Charlie. El arco completo
importa más que la pose inicial: el scrub termina en el pack cerrado de
frente, que es la misma pose del frame 0, así que el recorrido cierra donde
habría empezado.

INI=20 es lo más tarde que se puede entrar con el pack todavía legible: del
32 en adelante ya está de canto y no serviría de póster, que es el primer
frame y además el LCP.

Entre el 210 y el 228 el paño le pasa por encima al "Hasta hoy.". Es a
propósito: el titular es casi negro y el paño es blanco, así que la lectura
mejora en vez de empeorar, y el cruce da profundidad.

Las dos correcciones, ambas medidas contra nude2b.png (el render bueno):

1. Los blobs. Higgsfield sacó los blobs del envase en durazno (H24) en vez del
   rosa de marca (H346 en nude2b, H339 en nude5). Es una rotación de tono
   selectiva sobre la banda cálida, con pluma en los bordes: el resto del
   cuadro no se toca, y el fondo rosado vive en H353, fuera de la banda.

2. El fondo. El set trae un gradiente fuerte, de #FDDDE1 arriba a la izquierda
   a #C47A80 abajo: 47 niveles de diferencia contra el --rosa del CSS. El
   difuminado del borde izquierdo del canvas cubre un 10% del ancho y no
   alcanza para eso, así que en escritorio se vería un panel más oscuro pegado
   a la derecha. Se aplana modelando el fondo del set y corrigiendo cada pixel
   con ganancia multiplicativa, pesada para que no toque el producto: la sombra
   del piso se mantiene como sombra porque escala en proporción.
"""
import subprocess, pathlib, os, sys
import numpy as np

FF = os.path.expanduser('~/.local/bin/ffmpeg')
BASE = pathlib.Path(__file__).resolve().parent.parent
SRC = str(BASE / 'assets/verticales-hd/nude8.mp4')
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'lg').mkdir(exist_ok=True); (OUT / 'sm').mkdir(exist_ok=True)

W, H = 1080, 1920
ROSA = np.array([243., 201., 211.])       # --rosa #F3C9D3
INI = int(os.environ.get('INI', 20))
FIN = int(os.environ.get('FIN', 240))
PASO = 2
CAL_LG = int(os.environ.get('CAL_LG', 74))
CAL_SM = int(os.environ.get('CAL_SM', 70))

HUE_ORIG, HUE_DEST = 24.0, 344.0          # durazno de Higgsfield -> rosa de marca
BANDA, PLUMA = (4.0, 52.0), 10.0


# --- utilidades ----------------------------------------------------------

def rgb2hsv(a):
    mx = a.max(2); mn = a.min(2); d = mx - mn
    dd = np.where(d < 1e-6, 1.0, d)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    im = a.argmax(2)
    h = np.where(im == 0, ((g - b) / dd) % 6,
        np.where(im == 1, ((b - r) / dd) + 2, ((r - g) / dd) + 4)) * 60.0
    h = np.where(d < 1e-6, 0.0, h % 360)
    s = np.where(mx < 1e-6, 0.0, d / np.where(mx < 1e-6, 1.0, mx))
    return h, s, mx


def hsv2rgb(h, s, v):
    h = h % 360
    i = np.floor(h / 60).astype(np.int32)
    f = h / 60 - i
    p = v * (1 - s); q = v * (1 - s * f); t = v * (1 - s * (1 - f))
    out = np.empty(h.shape + (3,), np.float32)
    for k, tr in enumerate([(v, t, p), (q, v, p), (p, v, t),
                            (p, q, v), (t, p, v), (v, p, q)]):
        m = i == k
        out[m] = np.stack(tr, -1)[m]
    return out


def gblur(f, sigma):
    b = np.clip(f, 0, 255).astype(np.uint8).tobytes()
    q = subprocess.run([FF, '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                        '-s', f'{W}x{H}', '-i', '-', '-vf', f'gblur=sigma={sigma}:steps=3',
                        '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'],
                       input=b, capture_output=True, check=True).stdout
    return np.frombuffer(q, np.uint8).reshape(H, W, 3).astype(np.float32)


def frames(ini, fin, paso):
    sel = f"gte(n\\,{ini})*lte(n\\,{fin})*not(mod(n-{ini}\\,{paso}))"
    p = subprocess.Popen([FF, '-v', 'error', '-i', SRC, '-vf', f'select={sel}',
                          '-vsync', '0', '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-'],
                         stdout=subprocess.PIPE)
    while True:
        buf = p.stdout.read(W * H * 3)
        if len(buf) < W * H * 3:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
    p.stdout.close(); p.wait()


# --- 1. modelo del fondo del set ----------------------------------------

def modelo_fondo(paso=4):
    """El valor más claro que alcanza cada pixel, contando sólo los frames en
    que ese pixel es fondo rosado. Filtrar por rosado importa: sin eso el
    máximo se lleva el paño blanco, que sube por el centro desde el frame 200.
    Y el piso de brillo importa igual: el pack negro tiene sombras cálidas del
    mismo tono y saturación que el fondo, y sin él el modelo se traía un
    (46,32,31) al centro del cuadro. Los huecos donde el pack nunca se corre
    se rellenan difundiendo el fondo vecino: el gradiente es liso y aguanta."""
    acc = np.zeros((H, W, 3), np.float32)
    vis = np.zeros((H, W), np.float32)
    for a in frames(0, 240, paso):
        h, s, v = rgb2hsv(a)
        R, G, B = a[..., 0], a[..., 1], a[..., 2]
        # Ventana de tono ±14 y no ±22. Medido, el fondo del set vive entre
        # H352 y H357 en todo el cuadro, así que ±14 le sobra. Con ±22 entraban
        # los brillos especulares de los blobs del pack, que caen en H10-H17:
        # el máximo se quedaba con ellos y el modelo terminaba con la forma de
        # los blobs impresa en el fondo.
        pink = ((np.abs(((h - 353 + 180) % 360) - 180) < 14)
                & (s > 0.12) & (s < 0.60) & (v > 150))
        # El foco del set, arriba a la izquierda, quema el fondo hasta
        # (253,235,239): saturación 0,07, por debajo del piso de la rama de
        # arriba. Sin esta segunda rama el modelo no veía esa zona, la
        # rellenaba por difusión desde bordes más saturados y la ganancia le
        # quedaba corta: quedaba quemada, 35 niveles sobre --rosa contra los
        # 6 del resto del cuadro. El paño blanco no se cuela acá porque es
        # neutro (B ≈ G) y el fondo quemado sigue siendo magenta (R > B > G).
        quemado = (v > 235) & (R - G >= 12) & (B - G >= 2) & (B < R)
        pink = pink | quemado
        acc = np.where(pink[..., None], np.maximum(acc, a), acc)
        vis = np.maximum(vis, pink.astype(np.float32))
    m = vis[..., None].copy()
    f = acc.copy()
    for sigma in (80, 80, 60, 40, 25):
        fb = gblur(f * m, sigma)
        mb = gblur(np.repeat(m, 3, 2) * 255, sigma) / 255
        f = np.where(m > 0.5, f, fb / np.clip(mb, 3e-3, None))
        m = np.maximum(m, (mb[..., :1] > 0.02).astype(np.float32))
    f = gblur(f, 12)
    # Cinturón además de tirantes. Afinar la ventana de tono saca la fuga
    # conocida, pero el modelo es un máximo y cualquier máximo es frágil: le
    # basta un pixel del pack colado en un solo frame para dejar un bulto
    # permanente, y ese bulto sale después como una mancha en TODOS los
    # frames, porque la ganancia se calcula una vez.
    # El fondo real es liso a esta escala, así que se le prohíbe al modelo
    # sobresalir de su propio promedio local: lo que sube más de 2 niveles
    # sobre el desenfoque de sigma 45 es un bulto, no fondo. El foco del set
    # no se toca porque es ancho y el desenfoque lo conserva.
    for _ in range(2):
        f = np.minimum(f, gblur(f, 45) + 2)
    return f, vis.mean()


# --- 2. las dos correcciones --------------------------------------------

def blobs_a_rosa(a):
    h, s, v = rgb2hsv(a)
    lo, hi = BANDA
    w = np.clip((h - (lo - PLUMA)) / PLUMA, 0, 1) * np.clip(((hi + PLUMA) - h) / PLUMA, 0, 1)
    w *= np.clip((s - 0.08) / 0.10, 0, 1)      # el paño blanco no se tiñe
    delta = (HUE_DEST - HUE_ORIG) % 360 - 360  # -40
    return hsv2rgb(h + delta * w, s, v)


def fondo_plano(a, pl, gain):
    d = np.abs(a - pl).mean(2)
    h, s, v = rgb2hsv(a)
    rosado = (np.abs(((h - 353 + 180) % 360) - 180) < 30) & (s > 0.10) & (s < 0.55)
    w = np.clip(1 - (d - 12) / 45, 0, 1)                             # fondo puro
    w = np.maximum(w, rosado * np.clip(1 - (d - 30) / 90, 0, 1))     # y su sombra
    return a * (1 + (gain - 1) * w[..., None])


# --- 3. salida -----------------------------------------------------------

def escribir(a, idx):
    b = np.clip(a, 0, 255).astype(np.uint8).tobytes()
    for carpeta, ancho, alto, cal in (('lg', 1080, 1920, CAL_LG), ('sm', 810, 1440, CAL_SM)):
        # sin filtro de escala cuando ya está en tamaño: lanczos sobre 1:1 igual
        # resamplea y ablanda (-14% de contraste local, medido en hero-frames.py)
        vf = [] if (ancho, alto) == (W, H) else ['-vf', f'scale={ancho}:{alto}:flags=lanczos']
        subprocess.run(
            [FF, '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-i', '-',
             *vf, '-c:v', 'libwebp', '-quality', str(cal), '-preset', 'picture',
             '-frames:v', '1', '-y', str(OUT / carpeta / f'f_{idx:03d}.webp')],
            input=b, check=True)


print('modelando el fondo del set...', flush=True)
pl, cobertura = modelo_fondo()
gain = ROSA / np.clip(pl, 1, None)
print(f'  cobertura directa {cobertura*100:.1f}%, el resto por difusión')
print(f'  ganancia: arriba {gain[100, 540].round(3)}  abajo {gain[1850, 540].round(3)}')

print(f'frames {INI}..{FIN} paso {PASO}', flush=True)
idx = 0
desvios = []
for a in frames(INI, FIN, PASO):
    idx += 1
    c = fondo_plano(blobs_a_rosa(a), pl, gain)
    # Desvío del fondo ya corregido contra --rosa. Dos sondas: la banda alta,
    # donde el texto del hero se apoya sobre el cuadro, y la zona del foco del
    # set, que es la que se quemaba y por eso se vigila en cada corrida.
    alta = np.median(c[80:220, 60:1020].reshape(-1, 3), axis=0)
    foco = np.median(c[480:720, 20:300].reshape(-1, 3), axis=0)
    desvios.append((float(np.abs(alta - ROSA).max()), float(np.abs(foco - ROSA).max())))
    escribir(c, idx)
    if idx % 15 == 0:
        print(f'  {idx:>3} frames', flush=True)

print(f'\ntotal {idx} frames')
alt = [d[0] for d in desvios]; foc = [d[1] for d in desvios]
print(f'desvío contra --rosa, banda alta: max {max(alt):.0f}, promedio {sum(alt)/len(alt):.1f}')
print(f'desvío contra --rosa, zona del foco: max {max(foc):.0f}, promedio {sum(foc)/len(foc):.1f}')
