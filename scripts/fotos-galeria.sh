#!/usr/bin/env bash
#
# Convierte las fotos de producto editadas a WebP en dos anchos.
#
# Por qué dos anchos y no uno: el presupuesto de la Fase 5 del PLAN es de
# 600 KB en total y está medido EN MÓVIL. Un solo archivo obliga a elegir
# entre una grilla de escritorio pixelada o un móvil fuera de presupuesto.
# Con `srcset` cada dispositivo baja solo el suyo:
#
#   560w  →  ~325 KB las diez juntas   (móvil, una foto a la vez en el blob)
#   880w  →  ~590 KB las diez juntas   (escritorio, grilla scroll-driven)
#
# La fuente son los PNG que Charlie ya editó (luz, contraste, color) y
# comprimió en línea. Vienen paletizados a 256 colores: el reencodeo a WebP
# no agrega banding, pero tampoco puede quitar el que ya traen. Si algún día
# aparece banding visible en los fondos rosados, la solución es rehacer la
# edición desde los originales de `assets/imagenes-nuevas/` (que sí son de
# color completo) y volver a correr este script, no subirle la calidad acá.
#
# Uso:  bash scripts/fotos-galeria.sh
# Requiere ffmpeg con libwebp (ya instalado en el equipo de Charlie).

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORIGEN="$RAIZ/assets/imagenes-nuevas/editadas"
DESTINO="$RAIZ/src/assets/img/galeria"

CALIDAD=72
ANCHOS=(560 880)

# Nombre de archivo ← contenido de la foto. Los hf_* son ids de Higgsfield y
# no dicen nada; el nombre que queda en el repo sí tiene que decirlo, porque
# es lo que se lee en el `srcset` y en el alt cuando haya que cambiar una.
declare -a MAPA=(
  "hf_20260821_175245_0531f093-aa6d-4ca1-88ca-f054839bcd79:cajas-xl"
  "hf_20260821_180431_e270d9ad-49ae-4d46-885b-54a71fb3f998:bolsillo"
  "hf_20260821_180443_2bcd3a5e-1761-458d-8701-6293a2214f89:tendedero"
  "hf_20260821_181314_5e9bf442-3a21-4ea2-b5c9-7217aacb5de2:duo"
  "hf_20260826_163359_c0d8dc1c-9337-4ea4-b842-fa0aeaa062bd:bano"
  "hf_20260827_025048_fad3aef3-7b83-4869-a996-c906491a752f:cabeza"
  "hf_20260827_034943_34b2066f-e06c-4848-92ca-b4525ec70793:bolso"
  "hf_20260827_035004_8cf2e231-2995-4f97-83ab-ae74725c94f3:gimnasio"
  "hf_20260828_031841_8f46c61d-e506-4e17-9ef6-f833de6a9304:manos"
  "nude1:pack"
)

mkdir -p "$DESTINO"

total=0
for par in "${MAPA[@]}"; do
  origen_base="${par%%:*}"
  destino_base="${par##*:}"
  entrada="$ORIGEN/$origen_base.png"

  if [[ ! -f "$entrada" ]]; then
    echo "FALTA: $entrada" >&2
    exit 1
  fi

  for ancho in "${ANCHOS[@]}"; do
    salida="$DESTINO/$destino_base-$ancho.webp"
    ffmpeg -y -loglevel error \
      -i "$entrada" \
      -vf "scale=$ancho:-2:flags=lanczos" \
      -c:v libwebp -quality "$CALIDAD" -compression_level 6 \
      "$salida"
    peso=$(stat -f%z "$salida")
    total=$((total + peso))
    printf '%-22s %4sw  %5s KB\n' "$destino_base" "$ancho" "$((peso / 1024))"
  done
done

echo
echo "Total en disco (los dos anchos): $((total / 1024)) KB"
for ancho in "${ANCHOS[@]}"; do
  suma=$(find "$DESTINO" -name "*-$ancho.webp" -exec stat -f%z {} \; | paste -sd+ - | bc)
  echo "Lo que baja un cliente de ${ancho}w:  $((suma / 1024)) KB"
done
