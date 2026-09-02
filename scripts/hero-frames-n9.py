"""Genera los frames del hero desde nude9-4k.mp4, el clip nuevo de Higgsfield.

    python3 scripts/hero-frames-n9.py <carpeta-destino>
    CAL_SM=70 CAL_LG=74 PASO=3 python3 scripts/hero-frames-n9.py /tmp/frames

Reemplaza a hero-frames-n8.py. Ese partía de nude8.mp4 y quedó bloqueado por
el texto del envase: Higgsfield inventaba palabras y no se podía subir la
resolución sin que el invento se leyera mejor. El clip nuevo trae menos texto
y legible, así que el bloqueo se levantó.

El clip: 300 frames a 30 fps, 2160x3840, H264. El mismo arco que el anterior
pero más largo y a más cuadros por segundo.
    0..190   el pack de frente gira 360 y aterriza
  190..220   se asienta de frente
  220..230   se abre la tapa
  230..280   sube el paño
  280..290   la tapa se cierra
  290..299   el pack queda de frente, en la pose del frame 0

No se recorta ni la entrada ni la salida, a diferencia del anterior. El frame
0 ya es una pose de frente legible —sirve de póster y es el LCP— y el 299 es
esa misma pose, así que el recorrido cierra donde empezó sin tener que buscar
un punto de corte.

DE DÓNDE SALE LA MEJORA. La fuente es 2160x3840 real y la salida sigue siendo
1080x1920: es un supermuestreo 2:1. El frame final se promedia desde cuatro
pixeles de origen en vez de copiarse uno a uno, así que sale más limpio y más
nítido que el de nude8 SIN pesar más. Subir la resolución de salida no era
opción: el presupuesto del hero en móvil son 2,5 MB y ya estaba en 2,3.

Las dos correcciones son las mismas que necesitaba el clip anterior, con los
números remedidos sobre este:

1. Los blobs. Siguen saliendo en durazno. Medido sobre el frame 0, el blob del
   envase está en H19 contra el H346 del rosa de marca: 33 grados de desvío.
   Es una rotación de tono selectiva sobre la banda cálida, con pluma en los
   bordes; el fondo rosado vive en H348 y queda fuera de la banda.

2. El fondo. El set trae gradiente, de (242,195,204) arriba a la izquierda a
   (230,144,162) abajo a la derecha: 35 niveles de diferencia. Menos que los
   80 del clip anterior, pero suficiente para que en escritorio se note un
   panel más oscuro pegado a la derecha. Se aplana igual que antes.
"""
import subprocess, pathlib, os, sys
import numpy as np

FF = os.path.expanduser('~/.local/bin/ffmpeg')
BASE = pathlib.Path(__file__).resolve().parent.parent
SRC = str(BASE / 'assets/verticales-hd/nude9-4k.mp4')
# La fuente es 4K: se baja a 1080x1920 al leerla. El promedio de cuatro
# pixeles por uno es justamente la mejora que trae el master nuevo.
ESCALA_LECTURA = ['-vf', 'scale=1080:1920:flags=lanczos']
OUT = pathlib.Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'lg').mkdir(exist_ok=True); (OUT / 'sm').mkdir(exist_ok=True)

W, H = 1080, 1920
ROSA = np.array([243., 201., 211.])       # --rosa #F3C9D3
INI = int(os.environ.get('INI', 0))
FIN = int(os.environ.get('FIN', 299))
# 300 cuadros de tres en tres dan 100 frames, en el orden de los 111 que
# tenía el hero anterior. De dos en dos serían 150 y el móvil se saldría
# del presupuesto.
PASO = int(os.environ.get('PASO', 3))
# Calidad más baja que la del clip anterior (74/70) y aun así mejor imagen:
# el supermuestreo 2:1 deja los frames más limpios, así que aguantan más
# compresión. Con 70/74 el móvil quedaba en 2508 KB contra un tope de 2560,
# sin margen; con 62/68 baja a 2292 KB, por debajo incluso de lo que pesaba
# el hero anterior.
CAL_LG = int(os.environ.get('CAL_LG', 68))
CAL_SM = int(os.environ.get('CAL_SM', 62))

HUE_ORIG, HUE_DEST = 19.0, 346.0          # durazno de Higgsfield -> rosa de marca
H_FONDO = 348.0                           # el rosado del set, remedido en este clip
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
    p = subprocess.Popen([FF, '-nostdin', '-v', 'error', '-i', SRC,
                          '-vf', f'select={sel},scale={W}:{H}:flags=lanczos',
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
    for a in frames(0, FIN, paso):
        h, s, v = rgb2hsv(a)
        R, G, B = a[..., 0], a[..., 1], a[..., 2]
        # Ventana de tono ±14 y no ±22. Medido, el fondo del set vive entre
        # H352 y H357 en todo el cuadro, así que ±14 le sobra. Con ±22 entraban
        # los brillos especulares de los blobs del pack, que caen en H10-H17:
        # el máximo se quedaba con ellos y el modelo terminaba con la forma de
        # los blobs impresa en el fondo.
        pink = ((np.abs(((h - H_FONDO + 180) % 360) - 180) < 14)
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
    delta = (HUE_DEST - HUE_ORIG) % 360 - 360  # -33
    return hsv2rgb(h + delta * w, s, v)


def fondo_plano(a, pl, gain):
    d = np.abs(a - pl).mean(2)
    h, s, v = rgb2hsv(a)
    rosado = (np.abs(((h - H_FONDO + 180) % 360) - 180) < 30) & (s > 0.10) & (s < 0.55)
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
