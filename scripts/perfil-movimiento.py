"""Mide cuánto cambia la imagen entre frames del hero y escribe el perfil
acumulado que usa hero-scrub.js para repartir el scroll.

    python3 scripts/perfil-movimiento.py

Por qué existe. El scrub mapeaba el scroll a los frames en partes iguales, y
la secuencia no se mueve en partes iguales: el giro de 360 concentra el 66%
del cambio visual pero con reparto lineal se llevaba sólo el 40% del
recorrido, así que giraba rápido. Entre los frames 44 y 65 el pack ya
aterrizó y apenas se asienta: 19% del scroll para 7% del cambio, o sea
scroll gastado en nada.

Repartiendo según el movimiento medido, el giro pasa de 40% a 66% del
recorrido: 1,65x más lento sin alargar la página ni sacar contenido.

Vuelve a correrse cada vez que cambien los frames.
"""
import subprocess, pathlib, numpy as np

BASE = pathlib.Path(__file__).resolve().parent.parent
SRC = BASE / 'src/assets/hero-frames/lg'
DEST = BASE / 'src/js/hero-perfil.js'
# Se mide en gris y chico: interesa cuánto cambia la imagen, no el detalle.
W, H = 135, 240


def leer(p):
    q = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-vf', f'scale={W}:{H}',
                        '-f', 'rawvideo', '-pix_fmt', 'gray', '-'],
                       capture_output=True, check=True).stdout
    return np.frombuffer(q, np.uint8).reshape(H, W).astype(np.float32)


frames = sorted(SRC.glob('*.webp'))
if not frames:
    raise SystemExit(f'no hay frames en {SRC}')

prev = leer(frames[0])
dif = []
for f in frames[1:]:
    cur = leer(f)
    dif.append(float(np.abs(cur - prev).mean()))
    prev = cur

cum = np.concatenate([[0.0], np.cumsum(dif)])
cum /= cum[-1]
# Se guarda en milésimas enteras: alcanza de sobra para 111 frames y el
# archivo queda legible en un diff.
mil = np.round(cum * 1000).astype(int)
mil[0], mil[-1] = 0, 1000

filas = [', '.join(f'{v:4d}' for v in mil[i:i + 12]) for i in range(0, len(mil), 12)]
cuerpo = ',\n  '.join(filas)

DEST.write_text(f'''// Generado por scripts/perfil-movimiento.py. No editar a mano.
//
// Cuánto del cambio visual total de la secuencia ya ocurrió al llegar a cada
// frame, en milésimas. Lo usa hero-scrub.js para repartir el scroll según el
// movimiento real en vez de en partes iguales.
//
// {len(frames)} frames medidos.
export const PERFIL = [
  {cuerpo},
];
''', encoding='utf-8')

print(f'{len(frames)} frames -> {DEST.relative_to(BASE)}')
# Los tramos se declaran como fracción del recorrido, no como índices: el
# número de frames cambia cada vez que se cambia el clip o el paso, y con
# índices fijos este reporte se caía (pasó al montar nude9, que trae 100
# frames donde el anterior tenía 111).
ult = len(frames) - 1
for etq, fa, fb in (('giro', 0.00, 0.63), ('asentado', 0.63, 0.73),
                    ('tapa y paño', 0.73, 0.93), ('cierre', 0.93, 1.00)):
    a, b = round(fa * ult), round(fb * ult)
    lin = (b - a) / ult * 100
    mov = (cum[b] - cum[a]) * 100
    print(f'  {etq:12} lineal {lin:5.1f}%  ->  por movimiento {mov:5.1f}%')
