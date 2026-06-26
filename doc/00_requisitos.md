# Requisitos Completos do Projeto

Este documento lista tudo que você precisa para usar o kit,
separando o que é obrigatório do que é opcional.

---

## Resumo rápido

| Componente      | Para que serve                    | Obrigatório para...             |
|-----------------|-----------------------------------|---------------------------------|
| Python 3.9+     | Rodar o painel (fpga_panel.py)    | Tudo                            |
| pyserial        | Monitor serial (aba Monitor)      | Ver resultados do jogo          |
| OpenOCD 0.11+   | Gravar o bitstream na placa       | Gravação                        |
| libusbK/libusb  | Driver USB para OpenOCD           | Gravação (Linux já tem embutido)|
| Xilinx ISE 14.7 | Recompilar .vhd/.ucf → .bit      | Só se mudar o código/pinos      |
| Licença ISE     | Ativar o ISE (gratuita)           | Só se recompilar                |
| Git             | Versionamento                     | Opcional                        |

O kit já inclui o `reflex_game.bit` pré-compilado.
Se você só quiser gravar e jogar, não precisa do ISE.

---

## Python 3.9+

### O que é

Linguagem de programação que roda o painel gráfico (`fpga_panel.py`).
O painel usa apenas bibliotecas da stdlib (tkinter, subprocess, threading)
exceto pelo pyserial para o monitor serial.

### Verificar se já está instalado

```bash
python3 --version      # Linux/Mac
python --version       # Windows
```

### Instalar

**Fedora / RHEL:**
```bash
sudo dnf install python3
```

**Ubuntu / Debian:**
```bash
sudo apt install python3 python3-pip
```

**Windows:**
Baixar em https://python.org/downloads  
Marcar **"Add Python to PATH"** durante a instalação.

---

## pyserial

### O que é

Biblioteca Python que permite abrir portas seriais (`/dev/ttyUSB1`, `COM4`, etc.)
e ler os bytes que chegam. Usada pela aba **Monitor do Jogo** para receber
as mensagens `RESULT_MS=NNNN` enviadas pelo FPGA.

Sem o pyserial o painel abre normalmente, mas a aba de monitor fica desabilitada.

### Instalar

```bash
pip3 install pyserial        # Linux/Mac
pip install pyserial         # Windows
```

Ou via arquivo de requisitos:
```bash
pip3 install -r toolkit/requirements.txt
```

### Verificar

```bash
python3 -c "import serial; print(serial.__version__)"
```

---

## OpenOCD

### O que é (explicação completa em doc/06_openocd_e_gravacao.md)

Open On-Chip Debugger. Programa open-source que traduz comandos do PC
para o protocolo JTAG que o FPGA entende. Sem ele não é possível gravar
o bitstream na placa.

### Versão necessária

0.11 ou superior (0.12 recomendado).

### Verificar

```bash
openocd --version
```

### Instalar

**Fedora:**
```bash
sudo dnf install openocd
```

**Ubuntu / Debian:**
```bash
sudo apt install openocd
```

**Arch Linux:**
```bash
sudo pacman -S openocd
```

**Windows — opção A (binário):**
Baixar em https://openocd.org/pages/getting-openocd.html  
Extrair para `C:\openocd\` e adicionar `C:\openocd\bin` ao PATH.

**Windows — opção B (MSYS2):**
```bash
pacman -S mingw-w64-x86_64-openocd
```

**Mac:**
```bash
brew install open-ocd
```

---

## Driver USB (libusb / libusbK)

### Por que é necessário

O OpenOCD acessa o FT2232H diretamente via USB (sem passar pelo driver serial
do sistema). Para isso precisa de um driver de acesso direto a dispositivos USB.

### Linux

Já incluído no kernel como `libusb`. Nenhuma instalação necessária.
Basta configurar a permissão udev (feito pelo `iniciar.sh`):

```bash
bash toolkit/iniciar.sh
```

### Windows

O Windows usa por padrão o driver VCP (serial) para o FT2232H.
O OpenOCD precisa do **libusbK** no **Canal A** (JTAG).

**Instalar via Zadig:**
1. Baixar Zadig em https://zadig.akeo.ie
2. Conectar a placa
3. Zadig → Options → **List All Devices**
4. Selecionar **"Dual RS232-HS (Interface 0)"** — este é o Canal A (JTAG)
5. Driver: **libusbK**
6. Clicar **Replace Driver**

> **Não alterar o Interface 1** (Canal B) — ele deve permanecer
> com o driver serial para aparecer como porta COM.

### Verificar (Linux)

```bash
lsusb | grep "0403:70b1"
# Se aparecer: placa detectada, driver ok
```

### Verificar (Windows)

Gerenciador de Dispositivos → Controladores de barramento USB  
Deve aparecer: "Dual RS232-HS" com ícone de dispositivo USB (não serial).

---

## Xilinx ISE 14.7

### O que é

Suite de ferramentas da AMD/Xilinx para síntese e implementação de FPGAs.
Necessário **apenas se você precisar recompilar** o firmware
(mudar o VHDL ou os pinos).

Se você só quer gravar o bitstream já compilado, **não precisa do ISE**.

### Ferramentas usadas pelo build.sh

| Binário    | Função                                        |
|------------|-----------------------------------------------|
| `xst`      | Sintetizador: VHDL → netlist lógico (.ngc)    |
| `ngdbuild` | Tradução + aplicação do UCF → .ngd            |
| `map`      | Mapeia para LUTs/FFs reais do XC3S200 → .ncd |
| `par`      | Place & Route: posiciona e roteia → .ncd      |
| `bitgen`   | Gera o bitstream binário → .bit               |
| `promgen`  | Gera arquivo .mcs para a Platform Flash       |
| `impact`   | Gera arquivo .svf para programação da Flash   |

### Obter o ISE 14.7

1. Criar conta gratuita em https://www.xilinx.com (agora AMD)
2. Baixar **ISE Design Suite 14.7** — arquivo `Xilinx_ISE_DS_Lin_14.7_1015_1.tar` (Linux) ou `...Win...` (Windows)
3. Tamanho: ~6 GB

### Instalar no Linux

```bash
tar xf Xilinx_ISE_DS_Lin_14.7_1015_1.tar
cd Xilinx_ISE_DS_Lin_14.7_1015_1/
sudo ./xsetup
# Escolher: ISE WebPACK (gratuito)
# Destino padrão: /opt/Xilinx/14.7/ISE_DS
```

### Instalar no Windows

Executar o instalador, instalar em `C:\Xilinx\14.7\ISE_DS`.

### Licença (gratuita para Spartan-3)

1. Acessar https://www.xilinx.com/getlicense
2. Fazer login
3. Solicitar: **ISE WebPACK License** (gratuita, sem prazo)
4. Baixar o arquivo `Xilinx.lic`
5. Salvar em `~/Downloads/Xilinx.lic` (Linux) ou `%USERPROFILE%\Downloads\Xilinx.lic` (Windows)

O `build.sh` já aponta para esse caminho:
```bash
export XILINXD_LICENSE_FILE=~/Downloads/Xilinx.lic
```

### Verificar instalação

```bash
/opt/Xilinx/14.7/ISE_DS/ISE/bin/lin64/xst --help 2>&1 | head -3
```

---

## Resumo: o que instalar dependendo do objetivo

### Quero só gravar o bitstream já compilado e jogar

```
Python 3.9+
pyserial
OpenOCD
libusbK (Windows) / udev configurado (Linux)
```

### Quero recompilar (mudar pinos ou código VHDL)

```
Tudo acima +
Xilinx ISE 14.7
Licença ISE (gratuita)
```

### Quero só ver o código / documentação

```
Nada (arquivos de texto puro)
```
