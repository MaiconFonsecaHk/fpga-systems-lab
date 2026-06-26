# Resumo do Projeto — fpga-systems-lab

## 1. Identificação do projeto

- **Nome do projeto:** fpga-systems-lab
- **Tipo de projeto:** Toolkit de gravação de firmware FPGA + firmware VHDL de aplicação
- **Objetivo aparente:** Facilitar a gravação e o flash de firmware no chip FPGA Xilinx Spartan-3 XC3S200, com interface gráfica multiplataforma para programação via JTAG e monitoramento serial
- **Plataforma(s) alvo:** Windows 10/11 e Linux (Fedora, Ubuntu/Debian, Arch, openSUSE)
- **Estado atual observado:** Repositório Git com ao menos um commit; código funcional em produção (logs de execução datados de 2026-06-26 presentes)
- **Linguagem principal:** Python 3 (toolkit), VHDL (firmware)
- **Framework principal:** Nenhum framework externo — tkinter (stdlib Python) para a GUI
- **Gerenciador de pacotes/build:** pip (Python); ISE 14.7 (síntese VHDL); winget/choco (Windows auto-install); apt/dnf/pacman/zypper (Linux auto-install)
- **Ambiente de execução:** Python 3.9+ no host; Xilinx ISE 14.7 para recompilação do firmware (opcional); OpenOCD para programação JTAG

---

## 2. Descrição geral

O projeto consiste em dois componentes principais:

**Toolkit (PC):** Uma interface gráfica (`fpga_panel.py`) que permite ao usuário verificar o ambiente, detectar a placa via USB, escanear a cadeia JTAG, gravar o bitstream na RAM volátil do FPGA, gravar permanentemente na Platform Flash, monitorar a porta serial e reconfigurar o mapeamento de pinos sem editar arquivos manualmente. Launchers (`run.bat` para Windows, `iniciar.sh` para Linux) instalam todas as dependências automaticamente antes de abrir o painel.

**Firmware (FPGA):** Um jogo de reflexo implementado em VHDL para o Xilinx Spartan-3 XC3S200. A lógica principal é uma FSM de 7 estados que controla LEDs, debounça botão, gera delay aleatório via LFSR de 16 bits e transmite os resultados (`RESULT_MS=NNNN`, `EARLY`, `TIMEOUT`) via FT2232H Canal B em modo FIFO 245 Assíncrono (8 bits paralelo).

A placa alvo é a Bionexus TX-LED R27 com chip FT2232H para USB: Canal A faz JTAG (gravação), Canal B faz FIFO 245 (comunicação do jogo).

---

## 3. Stack técnica identificada

### Linguagem
- Python 3.9+ (toolkit/painel)
- VHDL (IEEE 1076 — firmware FPGA)
- Bash (launcher Linux, build script Linux)
- Batch/CMD (launcher Windows, build script Windows)
- Tcl (arquivo de configuração OpenOCD — `gravar.cfg`)

### Framework
- Nenhum framework externo

### UI
- tkinter + ttk (stdlib Python 3) — GUI cross-platform
- Notebook com 4 abas: Gravação, Monitor do Jogo, Configuração de Pinos, Guia

### Estado/gerenciamento de estado
- Variáveis tkinter (`StringVar`, `BooleanVar`, `IntVar`) para campos do formulário
- `queue.Queue` para comunicação thread→UI (producer-consumer)
- `threading.Thread` (daemon) para processos e monitor serial em background
- `threading.Event` para controle de parada do monitor serial

### Persistência/banco de dados
- `toolkit/pin_config.json` — configuração de pinos salva localmente (gitignored)
- `toolkit/logs/` — logs de execução com timestamp (gitignored exceto `.gitkeep`)

### Navegação/rotas
- Não identificado (aplicação desktop com abas, sem roteamento)

### Rede/APIs
- Não identificado (sem conexões de rede)

### Autenticação
- Não identificado

### Internacionalização
- Não identificado (interface em português; sem sistema i18n)

### Testes
- Não identificado (nenhum arquivo de teste encontrado)

### Build/release
- **Firmware Linux:** `firmware/build.sh` chama ISE 14.7 `lin64` binaries (XST → NGDBuild → MAP → PAR → BitGen)
- **Firmware Windows:** `firmware/build.bat` chama ISE 14.7 `nt64` binaries (mesmo fluxo)
- **Bitstream pré-compilado:** `toolkit/reflex_game.bit` incluído no repositório

### Outras dependências relevantes
- `pyserial >= 3.5` (opcional — monitor serial)
- `OpenOCD >= 0.11` (obrigatório para gravação JTAG)
- `libusbK` via Zadig (Windows — driver USB para OpenOCD no Canal A)
- `libusb` via kernel (Linux — embutido)
- `Xilinx ISE 14.7` + licença WebPACK (opcional — apenas para recompilar firmware)
- `promgen` e `iMPACT` (parte do ISE — usados para gravação na Flash)

---

## 4. Estrutura de pastas

### /doc
Documentação do projeto em Markdown.

Arquivos/subpastas principais:
- `00_requisitos.md` — lista completa de dependências e instruções de instalação
- `01_placa_e_pinos.md` — pinout do FPGA, Bank 6, cadeia JTAG
- `02_comunicacao_serial.md` — protocolo FIFO 245, mensagens enviadas
- `03_sintetizando_o_firmware.md` — fluxo de síntese XST → BitGen
- `04_setup_linux.md` — configuração Linux (drivers, udev)
- `05_setup_windows.md` — configuração Windows (Zadig, drivers)
- `06_openocd_e_gravacao.md` — explicação do OpenOCD, JTAG e processo de gravação
- `esquematico_R27_FPGA.png` — esquemático da placa Bionexus TX-LED R27

### /firmware
Código-fonte VHDL e scripts de síntese.

Arquivos/subpastas principais:
- `reflex_game.vhd` — código VHDL principal (309 linhas)
- `reflex_game.ucf` — constraints de pinos (User Constraints File)
- `reflex_game.xst` — opções do sintetizador XST
- `reflex_game.prj` — lista de arquivos VHDL para o XST
- `reflex_game.ut` — opções do BitGen
- `build.sh` — script de síntese Linux (chama binários `lin64`)
- `build.bat` — script de síntese Windows (chama binários `nt64`)

### /toolkit
Aplicação Python de gravação e monitoramento.

Arquivos/subpastas principais:
- `fpga_panel.py` — painel GUI principal (1616 linhas, classe `FPGAPanel`)
- `gravar.cfg` — configuração OpenOCD para o FT2232H e cadeia JTAG
- `reflex_game.bit` — bitstream pré-compilado (para gravação sem ISE)
- `requirements.txt` — dependências Python (`pyserial >= 3.5`)
- `run.bat` — launcher Windows (instala dependências + abre painel)
- `iniciar.sh` — launcher Linux (instala dependências, configura udev + abre painel)
- `logs/` — diretório de logs de execução (gitignored; `.gitkeep` commitado)
- `__pycache__/` — cache Python (gitignored)

---

## 5. Arquivos principais

### toolkit/fpga_panel.py
- **Função:** Aplicação GUI principal; ponto de entrada via `main()` → `FPGAPanel(root)`
- **Observações factuais:** 1616 linhas; Python 3.9+; janela 1200×860 px mínima 1020×680; 4 abas (Gravação, Monitor, Configuração de Pinos, Guia); status bar com relógio em tempo real; todos os processos externos executam em threads daemon com comunicação via `queue.Queue`; detecta OS em tempo de execução (`IS_WINDOWS`, `IS_LINUX`, `IS_MAC`); mostra OS no header do painel; version `2.0`

### toolkit/gravar.cfg
- **Função:** Configuração OpenOCD para a placa Bionexus TX-LED R27
- **Observações factuais:** Driver `ftdi`; VID:PID `0x0403:0x70b1`; layout_init `0x0008 0x000b`; transporte JTAG; velocidade 3 MHz; declara dois TAPs: `xc3s200` (IR=6, ID=0x01414093) e `platform_flash` (IR=8, ID=0xd5044093); registra FPGA com driver `virtex2`

### toolkit/reflex_game.bit
- **Função:** Bitstream pré-compilado para gravação imediata sem ISE
- **Observações factuais:** Arquivo binário; incluído no repositório; pode ser substituído por recompilação via painel

### toolkit/run.bat
- **Função:** Launcher Windows — verifica Python, instala pyserial, instala OpenOCD, abre painel
- **Observações factuais:** Tenta OpenOCD via winget, depois choco, depois exibe aviso manual; continua mesmo se OpenOCD não for instalado (painel abre sem função JTAG)

### toolkit/iniciar.sh
- **Função:** Launcher Linux — verifica Python, instala pyserial, instala OpenOCD, carrega driver FTDI, configura udev, abre painel
- **Observações factuais:** Detecta apt/dnf/pacman/zypper; cria regra udev `/etc/udev/rules.d/99-fpga-spartan3.rules` se não existir; usa `set -e`; registra VID:PID no `ftdi_sio`; ajusta permissões em `/dev/ttyUSB*`

### firmware/reflex_game.vhd
- **Função:** Código VHDL da lógica do FPGA (jogo de reflexo + comunicação USB)
- **Observações factuais:** 309 linhas; `architecture Behavioral`; dois processos concorrentes: `game_proc` (FSM + debounce + LFSR + montagem de mensagem) e `fifo_proc` (FSM de TX FIFO); clock 40 MHz; BCD via subtração encadeada (compatível XST); três saídas LED combinacionais

### firmware/reflex_game.ucf
- **Função:** Mapeamento de pinos físicos do FPGA (User Constraints File)
- **Observações factuais:** Define clock P53 (40 MHz, TIMESPEC 25 ns), LEDs P51/P50/P47, botão P56 (PULLDOWN), barramento FIFO D[0-7] em P31/P30/P27/P28/P32/P33/P36/P35, WR# P21, TXE# P26; inclui TIG para caminho BCD

### firmware/build.sh
- **Função:** Script de síntese completa Linux (VHDL → .bit)
- **Observações factuais:** 5 passos: XST → NGDBuild → MAP → PAR → BitGen; detecta ISE em `/opt/Xilinx/14.7/ISE_DS` ou path alternativo; usa `set -e`; parâmetro device `xc3s200-4-tq144`

### firmware/build.bat
- **Função:** Script de síntese completa Windows (equivalente ao build.sh)
- **Observações factuais:** Mesmo fluxo 5 passos; detecta ISE em `C:\Xilinx\14.7\ISE_DS` ou `C:\Xilinx\ISE_DS`; chama `settings64.bat`; usa binários `nt64`; sai com `exit /b 1` em qualquer erro

### README.md
- **Função:** Documentação principal do projeto; quick start, estrutura, regras do jogo, comunicação serial, pinos, dependências
- **Observações factuais:** 166 linhas; menciona contexto acadêmico (Prof. Emiliano Amarante Veiga, disciplina de Sistemas Digitais / Arquitetura de Computadores)

---

## 6. Arquitetura observada

O padrão arquitetural não foi identificado de forma explícita; a organização observada é:

**Toolkit (Python):** Aplicação monolítica em arquivo único (`fpga_panel.py`). Uma classe principal `FPGAPanel` centraliza toda a lógica: UI (tkinter/ttk), execução de subprocessos (OpenOCD, lsusb, pip, promgen, iMPACT), monitor serial em thread separada e geração programática de VHDL/UCF. Funções livres fora da classe tratam geração de código (`generate_vhdl`, `generate_ucf`) e utilitários (`quote_path`, `timestamp`).

**Firmware (VHDL):** Arquitetura Behavioral com dois processos síncronos paralelos no mesmo clock de 40 MHz: `game_proc` (lógica do jogo, controle de LEDs, LFSR, montagem de buffer de mensagem) e `fifo_proc` (transmissão byte a byte pelo FIFO 245). Comunicação entre processos via sinais internos (`uart_trigger`, `uart_msg`, `uart_msg_len`).

**Launchers:** Scripts independentes (Bash/Batch) que atuam como bootstrappers — verificam e instalam dependências antes de delegar a execução ao `fpga_panel.py`.

---

## 7. Módulos e funcionalidades existentes

### Aba Gravação (tab_prog)
- **Caminho(s):** `toolkit/fpga_panel.py` → `_build_program_tab()`
- **O que faz:** Campo de caminhos configuráveis (OpenOCD, .cfg, .bit); botões para 5 ações sequenciais: verificar ambiente, detectar USB/FTDI, escanear JTAG, gravar na RAM, gravar na Flash; banner de status em tempo real; log colorido; salvar/limpar log; abrir pasta de logs
- **Dependências externas:** OpenOCD, lsusb (Linux), promgen/iMPACT (ISE, para Flash)

### Aba Monitor do Jogo (tab_serial)
- **Caminho(s):** `toolkit/fpga_panel.py` → `_build_serial_tab()`
- **O que faz:** Conecta a uma porta serial (COM/ttyUSB); exibe bytes brutos em hex e ASCII; parseia linhas `RESULT_MS=NNNN`, `EARLY`, `TIMEOUT`; mostra resultado em destaque (fonte 42pt, cor por tempo: verde <300ms, azul <600ms, laranja ≥600ms); atualiza status bar
- **Dependências externas:** pyserial (opcional — aba fica desabilitada sem ele)

### Aba Configuração de Pinos (tab_config)
- **Caminho(s):** `toolkit/fpga_panel.py` → `_build_config_tab()`
- **O que faz:** Alterna entre modo FIFO 245 e UART 115200; configura 8 pinos de dados + WR# + TXE# (ou uart_tx); aplica presets de mapeamento; gera VHDL e UCF correspondentes; executa recompilação (build.sh/build.bat); encadeia recompilação + gravação na Flash; persiste configuração em `pin_config.json`
- **Dados utilizados:** Constantes `FIFO_PRESETS`, `UART_PRESETS`, `BANK6_IO_PINS`

### Aba Guia (tab_help)
- **Caminho(s):** `toolkit/fpga_panel.py` → `_build_help_tab()`
- **O que faz:** Texto estático (read-only) com fluxo de uso, regras do jogo, detalhes do protocolo FIFO 245, tabela de pinos e solução de problemas

### Auto-instalação (check_environment / launchers)
- **Caminho(s):** `fpga_panel.py` → `check_environment()`, `_install_pyserial()`, `_install_openocd()`, `_install_openocd_windows()`, `_install_openocd_linux()`, `_after_openocd_install()`; `toolkit/run.bat`; `toolkit/iniciar.sh`
- **O que faz:** Detecta ausência de OpenOCD e pyserial; oferece instalação automática via diálogo (no painel) ou executa silenciosamente (nos launchers); tenta winget → choco (Windows) ou apt → dnf → pacman → zypper (Linux)

### Gravação na Flash (program_flash)
- **Caminho(s):** `fpga_panel.py` → `program_flash()`, `_flash2()`, `_flash3()`
- **O que faz:** Pipeline de 3 etapas: (1) promgen gera .mcs a partir do .bit; (2) iMPACT gera .svf a partir do .mcs via arquivo de batch; (3) OpenOCD executa o .svf via `svf ... progress`

---

## 8. Fluxos principais identificados

### Gravação na RAM (volátil)
- **Objetivo:** Carregar bitstream no FPGA para teste imediato (não persiste após desligar)
- **Entrada:** Arquivo `.bit` selecionado no painel; OpenOCD e `.cfg` configurados
- **Processamento:** `openocd -f gravar.cfg -c "init; pld load 0 <bit>; exit"`
- **Saída/resultado:** FPGA configurado, LED D6 acende; duração ~3 segundos
- **Arquivos envolvidos:** `toolkit/gravar.cfg`, `toolkit/reflex_game.bit`, `toolkit/fpga_panel.py`

### Gravação na Flash (permanente)
- **Objetivo:** Gravar firmware na Platform Flash xcf01s para carregamento automático ao ligar
- **Entrada:** Arquivo `.bit`, promgen, iMPACT (ISE), OpenOCD, `.cfg`
- **Processamento:** promgen → .mcs; iMPACT (batch) → .svf; OpenOCD → executa .svf
- **Saída/resultado:** Firmware persistente na Flash; FPGA carrega automaticamente ao ligar; duração ~2 min
- **Arquivos envolvidos:** `toolkit/fpga_panel.py`, `toolkit/gravar.cfg`, arquivos `.mcs`/`.svf` gerados em `toolkit/`

### Recompilação de firmware
- **Objetivo:** Gerar novo `.bit` a partir de VHDL/UCF modificados (novo mapeamento de pinos ou nova lógica)
- **Entrada:** `reflex_game.vhd` e `reflex_game.ucf` (gerados ou editados), ISE 14.7 instalado
- **Processamento:** `build.sh` (Linux) ou `build.bat` (Windows): XST → NGDBuild → MAP → PAR → BitGen
- **Saída/resultado:** `firmware/reflex_game.bit`; painel copia para `toolkit/reflex_game.bit`
- **Arquivos envolvidos:** `firmware/reflex_game.vhd`, `firmware/reflex_game.ucf`, `firmware/reflex_game.xst`, `firmware/reflex_game.prj`, `firmware/reflex_game.ut`, `firmware/build.sh` ou `firmware/build.bat`

### Monitor serial (jogo)
- **Objetivo:** Receber e exibir resultados do jogo enviados pelo FPGA
- **Entrada:** Porta serial selecionada (ttyUSB1 / COM par)
- **Processamento:** Thread lê bytes brutos; parseia linhas `RESULT_MS=NNNN`, `EARLY`, `TIMEOUT` via regex
- **Saída/resultado:** Resultado exibido em destaque (42pt); log de bytes raw hex+ASCII; status bar atualizado
- **Arquivos envolvidos:** `toolkit/fpga_panel.py` → `_connect_serial()`, `_handle_line()`
- **Dependências externas:** pyserial

### Setup automático (launchers)
- **Objetivo:** Preparar ambiente completo sem intervenção manual do usuário
- **Entrada:** Execução do launcher (`run.bat` ou `iniciar.sh`)
- **Processamento:** Verifica Python → instala pyserial via pip → instala OpenOCD → [Linux: carrega ftdi_sio, registra VID:PID, ajusta permissões, cria regra udev] → abre painel
- **Saída/resultado:** Painel aberto com ambiente configurado
- **Arquivos envolvidos:** `toolkit/run.bat`, `toolkit/iniciar.sh`

---

## 9. Modelos de dados

### Configuração de pinos (pin_config.json)
- **Caminho:** `toolkit/pin_config.json` (gerado em runtime, gitignored)
- **Campos principais:**
  ```json
  {
    "mode": "fifo",
    "d": [31, 30, 27, 28, 32, 33, 36, 35],
    "wr": 21,
    "txe": 26,
    "uart_tx": 28
  }
  ```
- **Finalidade:** Persistir configuração de pinos entre execuções do painel
- **Persistência:** JSON no filesystem local

### Presets FIFO (FIFO_PRESETS)
- **Caminho:** `toolkit/fpga_panel.py` (constante em memória)
- **Campos:** `d` (lista 8 inteiros), `wr` (inteiro), `txe` (inteiro), `info` (string descritiva)
- **Presets definidos:** "Padrão (esquemático)", "Sequencial crescente", "Invertido (D0=P36)", "Pares L/N alternados", "TXE em P25 (fallback)"

### Buffer de mensagem VHDL (uart_msg)
- **Caminho:** `firmware/reflex_game.vhd`
- **Estrutura:** Array de 16 bytes (`t_msg`); `uart_msg_len` indica quantos bytes transmitir
- **Mensagens geradas:**
  - `EARLY\r\n` — 7 bytes (0x45 0x41 0x52 0x4C 0x59 0x0D 0x0A)
  - `RESULT_MS=NNNN\r\n` — 16 bytes (fixo)
  - `TIMEOUT\r\n` — 9 bytes

---

## 10. Persistência e armazenamento

- **Configuração de pinos:** `toolkit/pin_config.json` — JSON local, lido ao iniciar o painel, escrito ao salvar configuração; gitignored
- **Logs de execução:** `toolkit/logs/<acao>_<timestamp>.txt` — texto plano; gerado por cada operação (`ocd_version`, `detect_usb`, `scan_jtag`, `prog_ram`, `prog_flash`, `gen_mcs`, `gen_svf`, `install_openocd`, `install_pyserial`); gitignored (`.gitkeep` no dir)
- **Bitstream:** `toolkit/reflex_game.bit` — arquivo binário compilado; versionado no repositório; substituído pelo painel após recompilação
- **Regra udev (Linux):** `/etc/udev/rules.d/99-fpga-spartan3.rules` — criada pelo `iniciar.sh` se não existir; persistente no sistema operacional fora do repositório

---

## 11. Integrações externas

### OpenOCD
- **Finalidade:** Programação via JTAG (RAM e Flash)
- **Arquivos relacionados:** `toolkit/gravar.cfg`, `toolkit/fpga_panel.py`
- **Dados enviados:** Arquivo `.bit` (via `pld load`), arquivo `.svf` (via `svf`)
- **Dados recebidos:** Logs de texto com status da operação e IDs JTAG
- **Permissões:** Linux: requer udev configurado ou `sudo`; Windows: requer driver libusbK via Zadig no Canal A

### Xilinx ISE 14.7 (xst, ngdbuild, map, par, bitgen, promgen, impact)
- **Finalidade:** Síntese VHDL → bitstream; geração de MCS e SVF para gravação na Flash
- **Arquivos relacionados:** `firmware/build.sh`, `firmware/build.bat`, `toolkit/fpga_panel.py` (`program_flash`, `_find_ise`)
- **Dados enviados:** Arquivos `.vhd`, `.ucf`, `.xst`, `.prj`, `.ut`, `.bit`, `.mcs`
- **Dados recebidos:** `.ngc`, `.ngd`, `.ncd`, `.bit`, `.mcs`, `.svf`
- **Permissões:** Requer licença WebPACK (gratuita) em `~/Downloads/Xilinx.lic` (Linux) ou `%USERPROFILE%\Downloads\Xilinx.lic` (Windows)

### FT2232H (hardware)
- **Finalidade:** Ponte USB↔JTAG (Canal A) e USB↔FIFO245 (Canal B)
- **Arquivos relacionados:** `toolkit/gravar.cfg`, `firmware/reflex_game.vhd`, `toolkit/iniciar.sh`
- **VID:PID:** 0x0403:0x70b1
- **Canal A:** JTAG via OpenOCD; requer libusbK (Windows) ou libusb (Linux)
- **Canal B:** FIFO 245 lido como porta serial pelo driver VCP; aparece como `/dev/ttyUSB1` (Linux) ou `COM par` (Windows)

### winget / Chocolatey (Windows auto-install)
- **Finalidade:** Instalação automática do OpenOCD
- **Arquivos relacionados:** `toolkit/run.bat`, `toolkit/fpga_panel.py`
- **Comando winget:** `winget install --id=openocd.openocd -e --silent`
- **Comando choco:** `choco install openocd -y`

### apt / dnf / pacman / zypper (Linux auto-install)
- **Finalidade:** Instalação automática do OpenOCD
- **Arquivos relacionados:** `toolkit/iniciar.sh`, `toolkit/fpga_panel.py`
- **Permissões:** Requer `sudo`

### pip (Python)
- **Finalidade:** Instalação automática do pyserial
- **Arquivos relacionados:** `toolkit/run.bat`, `toolkit/iniciar.sh`, `toolkit/fpga_panel.py`
- **Comando:** `pip install --user pyserial` / `pip3 install --user pyserial`

---

## 12. Internacionalização e textos

Não identificado sistema de i18n. Toda a interface e documentação estão em português brasileiro. Textos definidos diretamente como strings literais no código (`fpga_panel.py`) e nos arquivos de documentação (`doc/*.md`).

---

## 13. Configuração de build e execução

### Abrir o painel (uso normal)

**Windows:**
```
toolkit\run.bat
```
Instala dependências e abre o painel. Requisito único: Python 3.9+ no PATH.

**Linux:**
```bash
bash toolkit/iniciar.sh
```
Instala dependências, configura udev e abre o painel.

**Direto (sem launcher):**
```bash
cd toolkit/
python3 fpga_panel.py     # Linux
python fpga_panel.py      # Windows
```

### Instalar dependências Python manualmente
```bash
pip3 install -r toolkit/requirements.txt    # Linux
pip install -r toolkit/requirements.txt     # Windows
```

### Compilar firmware

**Linux:**
```bash
cd firmware/
bash build.sh
```
Requer: ISE 14.7 em `/opt/Xilinx/14.7/ISE_DS` (ou `$XILINX_DIR`); licença em `~/Downloads/Xilinx.lic`

**Windows:**
```cmd
cd firmware\
build.bat
```
Requer: ISE 14.7 em `C:\Xilinx\14.7\ISE_DS` ou `C:\Xilinx\ISE_DS`; licença em `%USERPROFILE%\Downloads\Xilinx.lic`

### Variáveis de ambiente relevantes
- `XILINX_DIR` (Linux) — path do ISE (padrão: `/opt/Xilinx/14.7/ISE_DS`)
- `XILINXD_LICENSE_FILE` — path da licença ISE (padrão: `~/Downloads/Xilinx.lic` Linux / `%USERPROFILE%\Downloads\Xilinx.lic` Windows)

### Gitignore
- Artefatos de build ISE (`*.ngc`, `*.ngd`, `*.ncd`, `*.bit` intermediários, etc.)
- Artefatos de gravação Flash (`*_flash.*`, `flash_program.cmd`)
- Cache Python (`__pycache__/`, `*.pyc`)
- Logs em runtime (`toolkit/logs/*`)
- Configuração de pinos (`toolkit/pin_config.json`)
- Licença ISE (`*.lic`)

---

## 14. Testes existentes

Não identificado nenhum arquivo de teste automatizado. Nenhuma pasta `test/`, `tests/`, ou `spec/` encontrada. Nenhum uso de `unittest`, `pytest` ou framework de testes identificado no código.

---

## 15. Documentação existente

### README.md
- Caminho: `f:\Projetos\fpga-systems-lab\README.md`
- Assunto: Visão geral, quick start, estrutura de pastas, regras do jogo, comunicação serial, pinos confirmados, dependências
- Finalidade aparente: Ponto de entrada da documentação

### doc/00_requisitos.md
- Caminho: `f:\Projetos\fpga-systems-lab\doc\00_requisitos.md`
- Assunto: Lista completa de dependências (Python, pyserial, OpenOCD, libusbK/libusb, ISE, licença)
- Finalidade aparente: Referência de instalação para novos usuários

### doc/01_placa_e_pinos.md
- Caminho: `f:\Projetos\fpga-systems-lab\doc\01_placa_e_pinos.md`
- Assunto: Pinout físico da Bionexus TX-LED R27, Bank 6, cadeia JTAG
- Finalidade aparente: Referência de hardware

### doc/02_comunicacao_serial.md
- Caminho: `f:\Projetos\fpga-systems-lab\doc\02_comunicacao_serial.md`
- Assunto: Protocolo FIFO 245, mensagens enviadas, mapeamento de porta por OS
- Finalidade aparente: Referência de protocolo de comunicação

### doc/03_sintetizando_o_firmware.md
- Caminho: `f:\Projetos\fpga-systems-lab\doc\03_sintetizando_o_firmware.md`
- Assunto: Fluxo ISE completo (XST → NGDBuild → MAP → PAR → BitGen)
- Finalidade aparente: Guia de recompilação

### doc/04_setup_linux.md
- Caminho: `f:\Projetos\fpga-systems-lab\doc\04_setup_linux.md`
- Assunto: Instalação de dependências e drivers no Linux
- Finalidade aparente: Guia de configuração para Linux

### doc/05_setup_windows.md
- Caminho: `f:\Projetos\fpga-systems-lab\doc\05_setup_windows.md`
- Assunto: Instalação de dependências e drivers no Windows (inclui Zadig)
- Finalidade aparente: Guia de configuração para Windows

### doc/06_openocd_e_gravacao.md
- Caminho: `f:\Projetos\fpga-systems-lab\doc\06_openocd_e_gravacao.md`
- Assunto: Explicação detalhada do OpenOCD, JTAG, cadeia JTAG desta placa, processo de gravação RAM e Flash, conteúdo do gravar.cfg linha a linha, troubleshooting
- Finalidade aparente: Documentação técnica aprofundada da gravação

### doc/esquematico_R27_FPGA.png
- Caminho: `f:\Projetos\fpga-systems-lab\doc\esquematico_R27_FPGA.png`
- Assunto: Esquemático da placa Bionexus TX-LED R27
- Finalidade aparente: Referência visual para conferência de pinos

---

## 16. Estado atual do projeto

- O repositório possui ao menos um commit (estrutura `.git` presente com objetos de pack)
- Existem logs de execução datados de 2026-06-26 em `toolkit/logs/`, indicando uso recente
- O arquivo `toolkit/__pycache__/fpga_panel.cpython-314.pyc` indica execução com Python 3.14 (inferência)
- O painel possui 4 abas funcionais: Gravação, Monitor do Jogo, Configuração de Pinos, Guia
- Ambas as plataformas (Windows e Linux) possuem launchers com auto-instalação de dependências
- O bitstream pré-compilado `toolkit/reflex_game.bit` está disponível para uso imediato
- A documentação cobre: requisitos, hardware, protocolo, síntese, setup Linux, setup Windows e gravação
- O modo de comunicação FIFO 245 está ativo como padrão; modo UART disponível como fallback configurável
- Não há testes automatizados
- O contexto acadêmico é mencionado no README (Prof. Emiliano Amarante Veiga, disciplina de Sistemas Digitais / Arquitetura de Computadores)

---

## 17. Informações não identificadas

- **Item não identificado:** Conteúdo exato de `doc/01_placa_e_pinos.md`, `doc/02_comunicacao_serial.md`, `doc/03_sintetizando_o_firmware.md`, `doc/04_setup_linux.md`, `doc/05_setup_windows.md`
  - **Onde foi procurado:** Glob do diretório `doc/`; arquivos identificados mas não lidos individualmente
  - **Observação:** Títulos e assuntos são inferíveis pelos nomes dos arquivos e referências cruzadas no README e `doc/00_requisitos.md`

- **Item não identificado:** Conteúdo exato de `doc/esquematico_R27_FPGA.png`
  - **Onde foi procurado:** Arquivo listado no Glob
  - **Observação:** Arquivo de imagem não lido; referenciado em múltiplos arquivos de doc como fonte de verdade para mapeamento de pinos

- **Item não identificado:** Histórico completo de commits (mensagens, datas, autores)
  - **Onde foi procurado:** Objetos `.git` identificados mas não inspecionados
  - **Observação:** `git log` não executado

- **Item não identificado:** Conteúdo atual de `toolkit/reflex_game.bit`
  - **Onde foi procurado:** Arquivo binário listado no Glob
  - **Observação:** Arquivo binário; não lido

---

## 18. Glossário do projeto

- **Termo:** Bitstream / `.bit`
  - **Significado aparente:** Arquivo binário gerado pelo ISE que contém a configuração completa do FPGA; é carregado na SRAM interna do chip via JTAG
  - **Onde aparece:** `toolkit/reflex_game.bit`, `firmware/build.sh`, `firmware/build.bat`, `doc/06_openocd_e_gravacao.md`

- **Termo:** FIFO 245 / FIFO 245 Assíncrono
  - **Significado aparente:** Modo de operação do FT2232H Canal B que transmite dados em paralelo (8 bits) com sinais de handshake WR# e TXE#; não é UART
  - **Onde aparece:** `firmware/reflex_game.vhd`, `firmware/reflex_game.ucf`, `toolkit/fpga_panel.py`, `doc/02_comunicacao_serial.md`

- **Termo:** FT2232H
  - **Significado aparente:** Chip FTDI de dois canais USB; Canal A conectado ao JTAG do FPGA; Canal B conectado ao barramento de dados para comunicação com o jogo
  - **Onde aparece:** `toolkit/gravar.cfg`, `firmware/reflex_game.vhd`, `doc/06_openocd_e_gravacao.md`

- **Termo:** Platform Flash / xcf01s
  - **Significado aparente:** Memória Flash externa não-volátil (Xilinx xcf01s) que armazena o bitstream permanentemente; ao ligar a placa, transmite o bitstream para o FPGA via JTAG interno automaticamente
  - **Onde aparece:** `toolkit/gravar.cfg`, `toolkit/fpga_panel.py`, `doc/06_openocd_e_gravacao.md`

- **Termo:** UCF / User Constraints File
  - **Significado aparente:** Arquivo de texto que mapeia portas VHDL lógicas a pinos físicos do FPGA; também define restrições de timing
  - **Onde aparece:** `firmware/reflex_game.ucf`, `firmware/build.sh`, `firmware/build.bat`, `toolkit/fpga_panel.py`

- **Termo:** LFSR
  - **Significado aparente:** Linear Feedback Shift Register; registrador de 16 bits com polinômio x^16+x^14+x^13+x^11+1 e seed 0xACE1 usado para gerar delay aleatório no jogo
  - **Onde aparece:** `firmware/reflex_game.vhd`

- **Termo:** SVF / Serial Vector Format
  - **Significado aparente:** Arquivo de texto que descreve operações JTAG necessárias para gravar a Platform Flash; gerado pelo iMPACT (ISE) e executado pelo OpenOCD
  - **Onde aparece:** `doc/06_openocd_e_gravacao.md`, `toolkit/fpga_panel.py`

- **Termo:** MCS / Intel HEX
  - **Significado aparente:** Formato de arquivo intermediário gerado pelo promgen (ISE) a partir do `.bit`; compatível com a Platform Flash xcf01s
  - **Onde aparece:** `doc/06_openocd_e_gravacao.md`, `toolkit/fpga_panel.py`

- **Termo:** Bank 6
  - **Significado aparente:** Banco de I/O físico do Spartan-3 XC3S200 onde os pinos do FT2232H Canal B estão conectados; P29=GND e P34=VCCO_6 são pinos especiais inválidos para I/O
  - **Onde aparece:** `firmware/reflex_game.ucf`, `toolkit/fpga_panel.py`

- **Termo:** ISE / ISE 14.7
  - **Significado aparente:** Xilinx ISE Design Suite versão 14.7; suite de ferramentas de síntese para FPGAs Xilinx legados (inclui XST, NGDBuild, MAP, PAR, BitGen, promgen, iMPACT)
  - **Onde aparece:** `firmware/build.sh`, `firmware/build.bat`, `toolkit/fpga_panel.py`, `doc/00_requisitos.md`

- **Termo:** Bionexus TX-LED R27
  - **Significado aparente:** Modelo da placa de desenvolvimento FPGA usada no projeto; contém Spartan-3 XC3S200-4TQG144 + FT2232H + LEDs + botão
  - **Onde aparece:** `toolkit/fpga_panel.py`, `firmware/reflex_game.vhd`, `README.md`

- **Termo:** TIG (Timing Ignore)
  - **Significado aparente:** Diretiva UCF que instrui o ISE a ignorar análise de timing em um caminho específico; usado no caminho BCD (reaction_time_ms → uart_msg) para evitar falsos erros
  - **Onde aparece:** `firmware/reflex_game.ucf`

---

## 19. Resumo para continuidade

**O que o projeto é:** Toolkit de gravação FPGA para a placa Bionexus TX-LED R27 (Spartan-3 XC3S200-4TQG144). Inclui uma interface gráfica Python/tkinter cross-platform para programar o FPGA via JTAG/OpenOCD, monitorar comunicação serial e reconfigurar pinos com recompilação automática via ISE 14.7. O firmware de aplicação é um jogo de reflexo em VHDL.

**Stack principal:**
- Python 3.9+ / tkinter (interface)
- VHDL / Xilinx ISE 14.7 (firmware)
- OpenOCD >= 0.11 (gravação JTAG)
- pyserial >= 3.5 (monitor serial, opcional)
- FT2232H: Canal A = JTAG, Canal B = FIFO 245

**Módulos principais:**
- `toolkit/fpga_panel.py` — toda a lógica da interface e operações (1616 linhas, classe `FPGAPanel`)
- `toolkit/gravar.cfg` — configuração OpenOCD (VID:PID, TAPs, velocidade JTAG)
- `firmware/reflex_game.vhd` — FSM do jogo + FSM de TX FIFO
- `firmware/reflex_game.ucf` — mapeamento de pinos (fonte de verdade dos pinos físicos)
- `firmware/build.sh` / `firmware/build.bat` — síntese completa Linux/Windows
- `toolkit/run.bat` / `toolkit/iniciar.sh` — launchers com auto-instalação

**Onde começar a leitura:**
1. `README.md` — visão geral e quick start
2. `toolkit/fpga_panel.py` — início da classe `FPGAPanel.__init__()` (linha 544)
3. `firmware/reflex_game.vhd` — entity + arquitetura (linha 1)
4. `toolkit/gravar.cfg` — configuração JTAG
5. `doc/06_openocd_e_gravacao.md` — entender o fluxo de gravação

**Arquivos mais importantes:**
- `toolkit/fpga_panel.py`
- `toolkit/gravar.cfg`
- `firmware/reflex_game.vhd`
- `firmware/reflex_game.ucf`
- `firmware/build.sh` / `firmware/build.bat`

**Comandos identificados:**
```bash
# Abrir painel (Linux)
bash toolkit/iniciar.sh

# Abrir painel (Windows)
toolkit\run.bat

# Compilar firmware (Linux)
cd firmware && bash build.sh

# Compilar firmware (Windows)
cd firmware && build.bat

# Instalar pyserial
pip3 install -r toolkit/requirements.txt
```

**Documentação relevante:**
- `doc/00_requisitos.md` — o que instalar e como
- `doc/06_openocd_e_gravacao.md` — como funciona a gravação JTAG
- `doc/01_placa_e_pinos.md` — hardware e pinos
