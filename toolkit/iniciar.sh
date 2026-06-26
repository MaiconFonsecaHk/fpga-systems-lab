#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# FPGA Reflex Game — Inicializador Linux
# Configura drivers, udev e abre o painel.
# Necessário apenas na primeira vez (ou ao conectar em nova máquina).
# ──────────────────────────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   FPGA Reflex Game — Setup Linux                     ║"
echo "║   Placa: Bionexus TX-LED R27 / XC3S200               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Verificar Python
if ! command -v python3 &>/dev/null; then
    echo "[ERRO] Python 3 nao encontrado. Instale com:"
    echo "       sudo dnf install python3   # Fedora"
    echo "       sudo apt install python3   # Ubuntu/Debian"
    exit 1
fi

# Instalar pyserial se necessário
if ! python3 -c "import serial" &>/dev/null 2>&1; then
    echo "[INFO] Instalando pyserial..."
    pip3 install --user pyserial || pip install --user pyserial || true
fi

# 1. Carregar driver FTDI serial
echo "[1/4] Carregando driver ftdi_sio..."
sudo modprobe ftdi_sio 2>/dev/null || echo "       (já carregado ou não necessário)"

# 2. Registrar VID:PID customizado da placa
echo "[2/4] Registrando placa (VID:0403 PID:70b1) no driver serial..."
echo "0403 70b1" | sudo tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id > /dev/null 2>/dev/null || \
    echo "       (já registrado — normal)"

# 3. Permissões nas portas USB
echo "[3/4] Ajustando permissoes em /dev/ttyUSB*..."
sleep 0.3
PORTS=$(ls /dev/ttyUSB* 2>/dev/null || true)
if [ -n "$PORTS" ]; then
    sudo chmod a+rw $PORTS
    echo "       Portas encontradas: $PORTS"
    echo "       → ttyUSB0 = Canal A (JTAG/OpenOCD)"
    echo "       → ttyUSB1 = Canal B (monitor do jogo)"
else
    echo "       Nenhuma porta USB serial (placa pode nao estar conectada)"
fi

# 4. Regra udev permanente (só na primeira vez)
UDEV_RULE="/etc/udev/rules.d/99-fpga-bionexus.rules"
if [ ! -f "$UDEV_RULE" ]; then
    echo "[4/4] Criando regra udev permanente (sera automatico nas proximas vezes)..."
    sudo tee "$UDEV_RULE" > /dev/null << 'UDEV'
# Placa Bionexus ATENA FPGA — FT2232H (VID:0403 PID:70b1)
# Canal A: JTAG via OpenOCD (libusb direto)
# Canal B: interface serial do jogo -> /dev/ttyUSB1

SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", MODE="0666"

ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", \
    RUN+="/bin/sh -c 'modprobe ftdi_sio; echo 0403 70b1 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'"

ACTION=="add", SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", \
    MODE="0666", SYMLINK+="fpga_serial"
UDEV
    sudo udevadm control --reload-rules
    echo "       Regra criada: $UDEV_RULE"
else
    echo "[4/4] Regra udev ja existe em $UDEV_RULE"
fi

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Ambiente pronto. Iniciando painel..."
echo "══════════════════════════════════════════════════════"
echo ""

cd "$SCRIPT_DIR"
python3 fpga_panel.py
