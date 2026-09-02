#!/usr/bin/env bash
#
# Convierte a WebP las cuatro fotos de producto de la sección 06.
#
# Charlie las recortó a mano y quedaron en proporciones distintas (0.80, 0.85,
# 0.70 y 0.89). Acá se llevan todas a 4:5 recortando desde el centro, que es
# lo que hace `object-fit: cover`: la tarjeta necesita que las cuatro midan lo
# mismo o la grilla queda despareja.
#
# Un solo ancho y no dos como en la galería: la tarjeta mide 285px en
# escritorio y no más de ~350px en móvil, así que 640w cubre los dos casos con
# densidad de sobra y no vale la pena partir el archivo en dos.
#
# El orden de los nombres es el orden de izquierda a derecha en la sección.
#
# Uso:  bash scripts/fotos-formatos.sh

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORIGEN="$RAIZ/assets/imagenes-nuevas/productos"
DESTINO="$RAIZ/src/assets/img/formatos"
FF="${FF:-$HOME/.local/bin/ffmpeg}"

ANCHO=640
ALTO=800          # 4:5
CALIDAD=72

mkdir -p "$DESTINO"

total=0
for n in 01 02 03 04; do
  entrada="$ORIGEN/producto-$n.png"
  salida="$DESTINO/formato-$n.webp"
  if [[ ! -f "$entrada" ]]; then
    echo "FALTA: $entrada" >&2
    exit 1
  fi
  # increase/decrease para llenar la caja y después recortar al centro: es
  # cover, no fit, así que nunca quedan franjas vacías.
  "$FF" -nostdin -y -v error -i "$entrada" \
    -vf "scale=$ANCHO:$ALTO:force_original_aspect_ratio=increase:flags=lanczos,crop=$ANCHO:$ALTO" \
    -c:v libwebp -quality "$CALIDAD" -compression_level 6 \
    "$salida"
  peso=$(stat -f%z "$salida")
  total=$((total + peso))
  printf '%-14s %5s KB\n' "formato-$n" "$((peso / 1024))"
done

echo
echo "Las cuatro: $((total / 1024)) KB"
