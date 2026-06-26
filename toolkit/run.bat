@echo off
:: ──────────────────────────────────────────────────────────────────────────
:: FPGA Reflex Game — Launcher Windows
:: Pré-requisitos:
::   1. Python 3.9+ no PATH  (https://python.org/downloads)
::   2. OpenOCD no PATH      (https://openocd.org ou MSYS2: pacman -S openocd)
::   3. Zadig com libusbK no Canal A do FT2232H (https://zadig.akeo.ie)
:: ──────────────────────────────────────────────────────────────────────────

title FPGA Reflex Game

echo.
echo  FPGA Reflex Game - Bionexus TX-LED R27
echo  ========================================
echo.

:: Verificar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado no PATH.
    echo         Baixe em: https://python.org/downloads
    echo         Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)

:: Instalar pyserial se necessario
python -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Instalando pyserial...
    pip install pyserial
)

:: Verificar OpenOCD
openocd --version >nul 2>&1
if errorlevel 1 (
    echo  [AVISO] OpenOCD nao encontrado no PATH.
    echo          Baixe em: https://openocd.org/pages/getting-openocd.html
    echo          Ou via MSYS2: pacman -S mingw-w64-x86_64-openocd
    echo.
    echo  Continuando sem OpenOCD - so o monitor serial estara disponivel.
    echo.
)

:: Iniciar painel
cd /d "%~dp0"
echo  Iniciando painel...
echo.
python fpga_panel.py

if errorlevel 1 (
    echo.
    echo  [ERRO] O painel encerrou com erro.
    pause
)
