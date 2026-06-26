#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# FPGA Reflex Game — Script de Síntese Completa (ISE 14.7)
# Placa: Bionexus TX-LED R27 / Spartan-3 XC3S200-4TQG144
#
# Fluxo de síntese:
#   [1] XST      : reflex_game.vhd  →  .ngc  (síntese lógica)
#   [2] NGDBuild  : .ngc + .ucf      →  .ngd  (netlist + constraints de pinos)
#   [3] MAP       : .ngd             →  _map.ncd  (mapeado para LUTs/FFs reais)
#   [4] PAR       : _map.ncd         →  .ncd  (place & route no silício)
#   [5] BitGen    : .ncd + .ut       →  .bit  (bitstream binário para o FPGA)
#
# O arquivo .ucf define QUAL pino físico do FPGA corresponde a cada porta VHDL.
# Mudar o UCF e recompilar = testar novo mapeamento de pinos.
# ──────────────────────────────────────────────────────────────────────────────
set -e

# ─── Caminhos do ISE ─────────────────────────────────────────────────────────
XILINX_DIR="${XILINX_DIR:-/opt/Xilinx/14.7/ISE_DS}"
ISE_BIN="$XILINX_DIR/ISE/bin/lin64"
PROJ_DIR="$(cd "$(dirname "$0")" && pwd)"
DEVICE="xc3s200-4-tq144"
TOP="reflex_game"

# Fallback: procurar ISE em locais alternativos
if [ ! -d "$ISE_BIN" ]; then
    for alt in \
        "$HOME/Downloads/Xilinx_ISE_DS_Lin_14.7_1015_1/ISE_DS/ISE/bin/lin64" \
        "/opt/Xilinx/ISE_DS/ISE/bin/lin64"; do
        if [ -d "$alt" ]; then ISE_BIN="$alt"; XILINX_DIR="$(dirname "$(dirname "$alt")")"; break; fi
    done
fi

if [ ! -d "$ISE_BIN" ]; then
    echo "ERRO: ISE 14.7 nao encontrado em $ISE_BIN"
    echo "      Defina: export XILINX_DIR=/caminho/para/ISE_DS"
    exit 1
fi

# Licença ISE
export XILINXD_LICENSE_FILE="${XILINXD_LICENSE_FILE:-$HOME/Downloads/Xilinx.lic}"
source "$XILINX_DIR/settings64.sh" 2>/dev/null || true

cd "$PROJ_DIR"
mkdir -p xst/projnav.tmp xst/work _ngo _xmsgs

echo ""
echo "=== [1/5] XST — Sintese logica ==="
echo "    VHDL → NGC (netlist de portas logicas)"
"$ISE_BIN/xst" -ifn "$TOP.xst" -ofn "$TOP.syr"

echo ""
echo "=== [2/5] NGDBuild — Traducao + UCF ==="
echo "    NGC + UCF → NGD (aplica constraints de pinos)"
"$ISE_BIN/ngdbuild" -dd _ngo -nt timestamp \
    -uc "$TOP.ucf" -p "$DEVICE" \
    "$TOP.ngc" "$TOP.ngd"

echo ""
echo "=== [3/5] MAP — Mapeamento para recursos fisicos ==="
echo "    NGD → NCD mapeado (LUTs, FFs, IOBs do XC3S200)"
"$ISE_BIN/map" -p "$DEVICE" \
    -cm area -ir off -pr off -c 100 \
    -o "${TOP}_map.ncd" "$TOP.ngd" "$TOP.pcf"

echo ""
echo "=== [4/5] PAR — Place and Route ==="
echo "    Posiciona celulas e roteia fios no silicio"
"$ISE_BIN/par" -w -ol high -t 1 \
    "${TOP}_map.ncd" "$TOP.ncd" "$TOP.pcf"

echo ""
echo "=== [5/5] BitGen — Geracao do bitstream ==="
echo "    NCD + UT → .bit (arquivo binario para carregar no FPGA)"
"$ISE_BIN/bitgen" -f "$TOP.ut" "$TOP.ncd"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  BUILD CONCLUIDO — $PROJ_DIR/$TOP.bit"
echo "╚══════════════════════════════════════════════════════════╝"
ls -lh "$PROJ_DIR/$TOP.bit"
