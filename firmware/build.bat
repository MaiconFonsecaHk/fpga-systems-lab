@echo off
:: ──────────────────────────────────────────────────────────────────────────────
:: FPGA Systems Lab — Script de Sintese Completa (ISE 14.7) — Windows
:: Spartan-3 XC3S200-4TQG144
::
:: Equivalente Windows do build.sh
:: Requer ISE 14.7 instalado em C:\Xilinx\14.7\ISE_DS
::
:: Fluxo de sintese:
::   [1] XST      : reflex_game.vhd  ->  .ngc  (sintese logica)
::   [2] NGDBuild  : .ngc + .ucf     ->  .ngd  (netlist + constraints)
::   [3] MAP       : .ngd             ->  _map.ncd  (mapeado para LUTs/FFs)
::   [4] PAR       : _map.ncd         ->  .ncd  (place & route)
::   [5] BitGen    : .ncd + .ut       ->  .bit  (bitstream binario)
:: ──────────────────────────────────────────────────────────────────────────────
setlocal enabledelayedexpansion

set "PROJ_DIR=%~dp0"
set "DEVICE=xc3s200-4-tq144"
set "TOP=reflex_game"

:: Localizar ISE 14.7
set "ISE_DS="
for %%D in (
    "C:\Xilinx\14.7\ISE_DS"
    "C:\Xilinx\ISE_DS"
) do (
    if exist "%%~D\ISE\bin\nt64\xst.exe" (
        set "ISE_DS=%%~D"
        goto :found_ise
    )
)

echo ERRO: ISE 14.7 nao encontrado.
echo       Instale em C:\Xilinx\14.7\ISE_DS ou ajuste a variavel ISE_DS neste script.
exit /b 1

:found_ise
set "ISE_BIN=%ISE_DS%\ISE\bin\nt64"
echo ISE encontrado: %ISE_DS%

:: Configurar ambiente ISE
if exist "%ISE_DS%\settings64.bat" (
    call "%ISE_DS%\settings64.bat"
)

:: Licenca ISE
if not defined XILINXD_LICENSE_FILE (
    set "XILINXD_LICENSE_FILE=%USERPROFILE%\Downloads\Xilinx.lic"
)
echo Licenca: %XILINXD_LICENSE_FILE%

cd /d "%PROJ_DIR%"

echo === Limpando artefatos intermediarios anteriores ===
for %%E in (ngc ngd ncd pcf bgn bld mrp pad par syr drc lso map ngm ngr ptwx twr twx unroutes xdl xpi xrpt xwbt) do (
    if exist "%TOP%.%%E" del /q "%TOP%.%%E"
)
if exist "%TOP%_map.ncd" del /q "%TOP%_map.ncd"
if exist "%TOP%_map.pcf" del /q "%TOP%_map.pcf"
if exist "xst\work"      del /q "xst\work\*.*" 2>nul

if not exist xst\projnav.tmp mkdir xst\projnav.tmp
if not exist xst\work        mkdir xst\work
if not exist _ngo            mkdir _ngo
if not exist _xmsgs          mkdir _xmsgs

echo.
echo === [1/5] XST -- Sintese logica ===
echo     VHDL -^> NGC (netlist de portas logicas)
"%ISE_BIN%\xst.exe" -ifn "%TOP%.xst" -ofn "%TOP%.syr"
if errorlevel 1 ( echo ERRO no XST & exit /b 1 )

echo.
echo === [2/5] NGDBuild -- Traducao + UCF ===
echo     NGC + UCF -^> NGD (aplica constraints de pinos)
"%ISE_BIN%\ngdbuild.exe" -dd _ngo -nt timestamp -uc "%TOP%.ucf" -p "%DEVICE%" "%TOP%.ngc" "%TOP%.ngd"
if errorlevel 1 ( echo ERRO no NGDBuild & exit /b 1 )

echo.
echo === [3/5] MAP -- Mapeamento para recursos fisicos ===
echo     NGD -^> NCD mapeado (LUTs, FFs, IOBs do XC3S200)
"%ISE_BIN%\map.exe" -p "%DEVICE%" -cm area -ir off -pr off -c 100 -o "%TOP%_map.ncd" "%TOP%.ngd" "%TOP%.pcf"
if errorlevel 1 ( echo ERRO no MAP & exit /b 1 )

echo.
echo === [4/5] PAR -- Place and Route ===
echo     Posiciona celulas e roteia fios no silicio
"%ISE_BIN%\par.exe" -w -ol high -t 1 "%TOP%_map.ncd" "%TOP%.ncd" "%TOP%.pcf"
if errorlevel 1 ( echo ERRO no PAR & exit /b 1 )

echo.
echo === [5/5] BitGen -- Geracao do bitstream ===
echo     NCD + UT -^> .bit (arquivo binario para carregar no FPGA)
"%ISE_BIN%\bitgen.exe" -f "%TOP%.ut" "%TOP%.ncd"
if errorlevel 1 ( echo ERRO no BitGen & exit /b 1 )

echo.
echo ============================================================
echo   BUILD CONCLUIDO: %PROJ_DIR%%TOP%.bit
echo ============================================================
dir "%PROJ_DIR%%TOP%.bit"
