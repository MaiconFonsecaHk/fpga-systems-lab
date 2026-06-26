#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# FPGA Systems Lab — Inicializador Linux
# Instala dependencias, configura drivers/udev e abre o painel.
# ──────────────────────────────────────────────────────────────────────────────
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   FPGA Systems Lab — Setup Linux                     ║"
echo "║   Spartan-3 XC3S200-4TQG144                          ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Python ────────────────────────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERRO] Python 3 nao encontrado. Instale com:"
    echo "       sudo dnf install python3   # Fedora"
    echo "       sudo apt install python3   # Ubuntu/Debian"
    exit 1
fi
echo "[OK] Python $(python3 --version)"

# ── pyserial ──────────────────────────────────────────────────────────────────
if ! python3 -c "import serial" &>/dev/null 2>&1; then
    echo "[INFO] Instalando pyserial..."
    pip3 install --user pyserial || pip install --user pyserial
    echo "[OK] pyserial instalado."
else
    echo "[OK] pyserial ja instalado."
fi

# ── OpenOCD ───────────────────────────────────────────────────────────────────
if ! command -v openocd &>/dev/null; then
    echo "[INFO] OpenOCD nao encontrado. Instalando..."
    if command -v apt &>/dev/null; then
        sudo apt install -y openocd
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y openocd
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm openocd
    elif command -v zypper &>/dev/null; then
        sudo zypper install -y openocd
    else
        echo "[ERRO] Nenhum gerenciador de pacotes suportado encontrado."
        echo "       Instale manualmente: https://openocd.org"
        exit 1
    fi
    echo "[OK] OpenOCD instalado."
else
    echo "[OK] OpenOCD $(openocd --version 2>&1 | head -1)"
fi

# ── Drivers FTDI ─────────────────────────────────────────────────────────────
echo "[1/3] Carregando driver ftdi_sio..."
sudo modprobe ftdi_sio 2>/dev/null || echo "       (ja carregado)"

echo "[2/3] Registrando placa (VID:0403 PID:70b1)..."
echo "0403 70b1" | sudo tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id > /dev/null 2>/dev/null || \
    echo "       (ja registrado — normal)"

echo "[3/3] Ajustando permissoes em /dev/ttyUSB*..."
sleep 0.3
PORTS=$(ls /dev/ttyUSB* 2>/dev/null || true)
if [ -n "$PORTS" ]; then
    sudo chmod a+rw $PORTS
    echo "       Portas: $PORTS"
    echo "       → ttyUSB0 = Canal A (JTAG/OpenOCD)"
    echo "       → ttyUSB1 = Canal B (monitor serial)"
else
    echo "       Nenhuma porta USB serial detectada (placa pode nao estar conectada)"
fi

# ── udev permanente ───────────────────────────────────────────────────────────
UDEV_RULE="/etc/udev/rules.d/99-fpga-spartan3.rules"
if [ ! -f "$UDEV_RULE" ]; then
    echo "[udev] Criando regra permanente..."
    sudo tee "$UDEV_RULE" > /dev/null << 'UDEV'
# FPGA Systems Lab — FT2232H (VID:0403 PID:70b1)
SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", MODE="0666"
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", \
    RUN+="/bin/sh -c 'modprobe ftdi_sio; echo 0403 70b1 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'"
ACTION=="add", SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", \
    MODE="0666", SYMLINK+="fpga_serial"
UDEV
    sudo udevadm control --reload-rules
    echo "[udev] Regra criada: $UDEV_RULE"
else
    echo "[udev] Regra ja existe."
fi

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Ambiente pronto. Iniciando painel..."
echo "══════════════════════════════════════════════════════"
echo ""

cd "$SCRIPT_DIR"
python3 fpga_panel.py
