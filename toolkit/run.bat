@echo off
:: ──────────────────────────────────────────────────────────────────────────────
:: FPGA Systems Lab — Launcher Windows
:: Instala dependencias automaticamente e abre o painel.
:: Requisito unico: Python 3.9+ com "Add Python to PATH" marcado na instalacao.
:: ──────────────────────────────────────────────────────────────────────────────
title FPGA Systems Lab

echo.
echo  FPGA Systems Lab — Spartan-3 XC3S200-4TQG144
echo  ================================================
echo.

:: ── Python ───────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python nao encontrado no PATH.
    echo         Baixe em: https://python.org/downloads
    echo         Marque "Add Python to PATH" durante a instalacao.
    pause
    exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" >nul 2>&1
if errorlevel 1 (
    echo  [ERRO] Python 3.9+ necessario.
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo         Versao encontrada: %%v
    pause
    exit /b 1
)
echo  [OK] Python encontrado.

:: ── pyserial ─────────────────────────────────────────────────────────────────
python -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Instalando pyserial...
    pip install --user pyserial
    if errorlevel 1 (
        echo  [AVISO] Falha ao instalar pyserial. Monitor serial indisponivel.
        echo          Para instalar manualmente: pip install pyserial
    )
    echo  [OK] pyserial instalado.
) else (
    echo  [OK] pyserial ja instalado.
)

:: ── OpenOCD ──────────────────────────────────────────────────────────────────
openocd --version >nul 2>&1
if not errorlevel 1 (
    echo  [OK] OpenOCD encontrado.
    goto :openocd_ok
)

echo  [INFO] OpenOCD nao encontrado. Tentando instalar automaticamente...

:: Tentar winget
winget --version >nul 2>&1
if not errorlevel 1 (
    echo  [INFO] Instalando OpenOCD via winget...
    winget install --id=openocd.openocd -e --silent
    if not errorlevel 1 (
        echo  [OK] OpenOCD instalado via winget.
        goto :openocd_ok
    )
)

:: Tentar Chocolatey
choco --version >nul 2>&1
if not errorlevel 1 (
    echo  [INFO] Instalando OpenOCD via Chocolatey...
    choco install openocd -y
    if not errorlevel 1 (
        echo  [OK] OpenOCD instalado via Chocolatey.
        goto :openocd_ok
    )
)

echo  [AVISO] Nao foi possivel instalar OpenOCD automaticamente.
echo          Instale manualmente e reinicie:
echo            - https://openocd.org/pages/getting-openocd.html
echo            - MSYS2: pacman -S mingw-w64-x86_64-openocd
echo            - Zadig (driver libusbK): https://zadig.akeo.ie
echo.
echo  O painel abrira, mas gravacao JTAG nao estara disponivel.
echo.

:openocd_ok

:: ── Painel ───────────────────────────────────────────────────────────────────
cd /d "%~dp0"
echo  [INFO] Iniciando painel...
echo.
python fpga_panel.py

if errorlevel 1 (
    echo.
    echo  [ERRO] O painel encerrou com erro.
    pause
)
