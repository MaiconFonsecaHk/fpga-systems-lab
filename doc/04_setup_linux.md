# Setup Linux

## Requisitos

| Componente | Versao minima | Instalacao                             |
|------------|---------------|----------------------------------------|
| Python     | 3.9           | `sudo dnf install python3` (Fedora)    |
| pyserial   | 3.5           | `pip3 install --user pyserial`         |
| OpenOCD    | 0.11          | `sudo dnf install openocd` (Fedora)    |
| Xilinx ISE | 14.7          | Baixar no site AMD/Xilinx (gratuito)   |

## Primeira Vez (setup completo)

```bash
# 1. Entrar na pasta do toolkit
cd reflex_fpga_kit/toolkit/

# 2. Executar o inicializador (faz tudo automaticamente)
bash iniciar.sh
```

O script `iniciar.sh`:
1. Carrega o driver `ftdi_sio`
2. Registra o VID:PID da placa (`0403:70b1`) no driver
3. Ajusta permissoes em `/dev/ttyUSB*`
4. Cria regra udev permanente em `/etc/udev/rules.d/99-fpga-bionexus.rules`
5. Abre o painel

**Da segunda vez em diante:** basta conectar a placa e rodar `python3 fpga_panel.py`.

## Abrindo o Painel Manualmente

```bash
cd reflex_fpga_kit/toolkit/
python3 fpga_panel.py
```

## Verificar Portas

Apos conectar a placa via USB, dois dispositivos devem aparecer:

```bash
ls /dev/ttyUSB*
# /dev/ttyUSB0  ← Canal A = JTAG (OpenOCD)
# /dev/ttyUSB1  ← Canal B = monitor do jogo
```

Se nao aparecerem, execute `iniciar.sh` ou:
```bash
sudo modprobe ftdi_sio
echo "0403 70b1" | sudo tee /sys/bus/usb-serial/drivers/ftdi_sio/new_id
```

## Permissao para OpenOCD (sem sudo)

A regra udev criada pelo `iniciar.sh` ja cuida disso. Para verificar:

```bash
cat /etc/udev/rules.d/99-fpga-bionexus.rules
```

Se nao existir, crie manualmente:
```bash
sudo tee /etc/udev/rules.d/99-fpga-bionexus.rules << 'EOF'
SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", MODE="0666"
ACTION=="add", SUBSYSTEM=="usb", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", \
    RUN+="/bin/sh -c 'modprobe ftdi_sio; echo 0403 70b1 > /sys/bus/usb-serial/drivers/ftdi_sio/new_id'"
ACTION=="add", SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="70b1", \
    MODE="0666"
EOF
sudo udevadm control --reload-rules
```

## Instalar ISE 14.7

```bash
# Baixar o instalador da AMD/Xilinx
# Arquivo: Xilinx_ISE_DS_Lin_14.7_1015_1.tar
tar xf Xilinx_ISE_DS_Lin_14.7_1015_1.tar
cd Xilinx_ISE_DS_Lin_14.7_1015_1/
sudo ./xsetup   # instala em /opt/Xilinx/14.7/ISE_DS por padrao

# Configurar licenca (obter no site AMD/Xilinx com conta gratuita)
export XILINXD_LICENSE_FILE=~/Downloads/Xilinx.lic
```

## Diagnostico Rapido

```bash
# Verificar USB
lsusb | grep 0403:70b1

# Verificar JTAG (com OpenOCD)
openocd -f toolkit/gravar.cfg -c "init; scan_chain; exit" 2>&1

# Verificar porta serial
python3 -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```
