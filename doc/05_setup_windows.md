# Setup Windows

## Requisitos

| Componente | Versao  | Link / Instalacao                                    |
|------------|---------|------------------------------------------------------|
| Python 3   | 3.9+    | https://python.org/downloads — marcar "Add to PATH"  |
| pyserial   | 3.5+    | `pip install pyserial`                               |
| OpenOCD    | 0.12+   | https://openocd.org ou MSYS2 (ver abaixo)            |
| Driver USB | libusbK | Zadig (ver abaixo)                                   |

## Instalar Python

1. Baixar em https://python.org/downloads
2. Durante a instalacao, marcar **"Add Python to PATH"**
3. Verificar: abrir `cmd` e digitar `python --version`

## Instalar OpenOCD

**Opcao A — Binario pre-compilado:**
1. Baixar em https://openocd.org/pages/getting-openocd.html
2. Extrair para `C:\openocd\`
3. Adicionar `C:\openocd\bin` ao PATH do sistema

**Opcao B — MSYS2 (recomendado para desenvolvedores):**
```bash
pacman -S mingw-w64-x86_64-openocd
```

**Verificar:** `openocd --version` no cmd/PowerShell.

## Instalar Driver USB (Zadig)

O FT2232H precisa do driver `libusbK` no Canal A para o OpenOCD.
O Canal B usa o driver VCP (serial) padrao do Windows.

1. Baixar Zadig em https://zadig.akeo.ie
2. Conectar a placa FPGA via USB
3. Abrir Zadig → Options → **List All Devices**
4. Na lista, selecionar **"Dual RS232-HS (Interface 0)"** (Canal A)
5. Selecionar driver: **libusbK** (ou WinUSB)
6. Clicar **Replace Driver**

> **Nao alterar o Interface 1** (Canal B) — ele deve permanecer com o driver
> serial padrao para aparecer como porta COM no monitor serial.

## Verificar Portas COM

1. Conectar a placa
2. Abrir **Gerenciador de Dispositivos** → Portas (COM e LPT)
3. Devem aparecer duas portas, por exemplo:
   - `USB Serial Port (COM3)` ← Canal A (JTAG)
   - `USB Serial Port (COM4)` ← Canal B (jogo — usar no monitor)

## Abrir o Painel

```cmd
cd reflex_fpga_kit\toolkit\
run.bat
```

Ou diretamente:
```cmd
python fpga_panel.py
```

## Instalar ISE 14.7 no Windows

1. Baixar `Xilinx_ISE_DS_Win_14.7_1015_1.tar` no site AMD/Xilinx
2. Executar o instalador
3. Instalar em `C:\Xilinx\14.7\ISE_DS`
4. Obter licenca gratuita no site da AMD/Xilinx (requer conta)
5. Salvar como `%USERPROFILE%\Downloads\Xilinx.lic`

O `build.sh` e um script Bash — no Windows ele roda via
MSYS2/Git Bash, ou pelo botao **Recompilar** no painel
(que chama `bash build.sh` automaticamente se o Bash estiver no PATH).

## Diagnostico Rapido

```cmd
:: Verificar Python
python --version

:: Verificar pyserial
python -c "import serial; print(serial.__version__)"

:: Verificar OpenOCD
openocd --version

:: Listar portas COM
python -c "from serial.tools import list_ports; print([p.device for p in list_ports.comports()])"
```

## Antivirus / Windows Defender

Alguns antivirus podem bloquear o OpenOCD ou o Python ao tentar
acessar dispositivos USB. Se ocorrer, adicionar excecao para:
- `openocd.exe`
- A pasta `reflex_fpga_kit\toolkit\`
