# OpenOCD e o Processo de Gravação

---

## O que é o OpenOCD

**OpenOCD** (Open On-Chip Debugger) é um programa open-source que permite
ao seu PC se comunicar com chips via **JTAG** — o protocolo padrão da
indústria para programar, depurar e testar circuitos integrados.

Sem o OpenOCD não há como enviar o bitstream para o FPGA ou gravar
o firmware na Flash, porque o PC não fala JTAG nativamente.

---

## O problema: PC não fala JTAG

O seu PC tem USB. O FPGA tem JTAG (4 fios). Eles não são compatíveis diretamente.

A placa resolve isso com o chip **FT2232H**, que faz a conversão:

```
PC
│
USB ──────────────────► FT2232H
                        │
                        ├── Canal A: USB → JTAG ──► FPGA + Flash (gravação)
                        │
                        └── Canal B: USB → FIFO ──► FPGA (comunicação do jogo)
```

O OpenOCD controla o FT2232H via **libusb** (acesso direto ao USB)
para gerar os sinais JTAG corretos.

---

## O que é JTAG

JTAG (Joint Test Action Group, IEEE 1149.1) é um protocolo de 4 fios
criado em 1990 para testar placas de circuito impresso e programar chips.

### Os 4 fios

| Sinal | Direção      | Função                                          |
|-------|--------------|-------------------------------------------------|
| TCK   | PC → Chip    | Clock — sincroniza toda a comunicação           |
| TDI   | PC → Chip    | Test Data In — dados entram no chip             |
| TDO   | Chip → PC    | Test Data Out — dados saem do chip              |
| TMS   | PC → Chip    | Test Mode Select — controla a máquina de estados|

### Como funciona

O JTAG usa uma **máquina de estados** de 16 estados controlada pelo TMS.
Para enviar dados ao chip, o OpenOCD:

1. Navega pela máquina de estados via TMS
2. Serializa os dados bit a bit em TDI, sincronizado pelo TCK
3. Lê a resposta bit a bit em TDO

Parece simples, mas a sequência exata de bits para programar um FPGA
Xilinx é complexa — é por isso que o OpenOCD e o arquivo `.svf` existem.

### Cadeia JTAG desta placa

Os chips são ligados em série — TDO de um vai para TDI do próximo:

```
PC
│
TDI ──────────────────► FPGA xc3s200 ──► Platform Flash xcf01s ──► TDO ──► PC
                        (posição 1)       (posição 2)
                        IR = 6 bits       IR = 8 bits
                        ID = 0x01414093   ID = 0xd5044093
```

O OpenOCD precisa saber quantos chips há na cadeia, o tamanho do
registrador de instrução (IR) de cada um e o ID esperado —
tudo isso está no `gravar.cfg`.

---

## O arquivo gravar.cfg explicado linha a linha

```tcl
adapter driver ftdi
```
Usar o driver FTDI do OpenOCD. Esse driver sabe falar com chips FT2232H/FT232H
via libusb, gerando os sinais TCK/TDI/TDO/TMS nos pinos corretos.

```tcl
ftdi vid_pid 0x0403 0x70b1
```
Identificar a placa pelo VID:PID USB. O `0x0403` é o vendor ID da FTDI.
O `0x70b1` é o product ID específico desta placa Bionexus.
Sem isso o OpenOCD não sabe qual dispositivo USB abrir.

```tcl
ftdi layout_init 0x0008 0x000b
```
Configura quais pinos do FT2232H Canal A são saída (TDI, TCK, TMS)
e qual é entrada (TDO). Esses valores são determinados pelo hardware da placa.

```tcl
transport select jtag
```
Usar o protocolo JTAG (em vez de SWD, que é para ARM).

```tcl
adapter speed 3000
```
Velocidade do clock JTAG: 3 MHz. Mais rápido pode causar erros em
cabos longos ou em layouts de PCB ruins.

```tcl
jtag newtap xc3s200 tap -irlen 6 -expected-id 0x01414093
```
Declarar o FPGA na cadeia JTAG:
- Nome: `xc3s200`
- Registrador de instrução: 6 bits (específico do XC3S200)
- ID esperado: `0x01414093` — o OpenOCD vai verificar isso ao conectar

```tcl
jtag newtap platform_flash tap -irlen 8 -expected-id 0xd5044093
```
Declarar a Platform Flash xcf01s na cadeia JTAG:
- Registrador de instrução: 8 bits
- ID esperado: `0xd5044093`

```tcl
pld device virtex2 xc3s200.tap
```
Registrar o FPGA como um dispositivo programável usando o driver `virtex2`.
O Spartan-3 é compatível com esse driver (mesma geração de ferramentas Xilinx).
Isso habilita o comando `pld load 0 "arquivo.bit"` no OpenOCD.

---

## Como o OpenOCD grava o bitstream na RAM do FPGA

Quando você clica **"Gravar na RAM"** no painel, ele executa:

```bash
openocd -f gravar.cfg -c "init; pld load 0 reflex_game.bit; exit"
```

O que acontece internamente:

```
1. OpenOCD abre a conexão USB com o FT2232H
2. Verifica os IDs JTAG (0x01414093 para o FPGA)
3. Envia a instrução JPROGRAM para o FPGA (coloca em modo de configuração)
4. Transfere os 128 KB do .bit via TDI, bit a bit, sincronizado pelo TCK
5. Envia a instrução JSTART para iniciar a execução
6. O FPGA carrega a configuração da sua SRAM interna e começa a rodar
```

**Limitação:** a SRAM do FPGA é volátil — ao desligar a energia, o FPGA
perde a configuração. Por isso existe a gravação na Flash.

---

## Como o OpenOCD grava na Flash (processo de 3 etapas)

A Platform Flash xcf01s não aceita ser programada diretamente pelo
OpenOCD com um arquivo .bit. O processo é mais complexo:

### Etapa 1 — promgen (ISE): gerar o arquivo MCS

```bash
promgen -w -p mcs -c FF -x xcf01s -u 0 reflex_game.bit -o reflex_game_flash
```

O `promgen` converte o `.bit` em formato **MCS** (Intel HEX), que é o
formato que a Platform Flash xcf01s entende. O parâmetro `-x xcf01s`
especifica o tipo de memória Flash de destino.

Saída: `reflex_game_flash.mcs`

### Etapa 2 — iMPACT (ISE): gerar o arquivo SVF

```bash
impact -batch flash_program.cmd
```

O arquivo `flash_program.cmd` contém:
```
setMode -bscan
setCable -port svf -file "reflex_game_flash.svf"
addDevice -position 1 -part xc3s200        ← FPGA na pos. 1
addDevice -position 2 -part xcf01s         ← Flash na pos. 2
assignFile -position 2 -file "reflex_game_flash.mcs"
program -p 2 -e -v                         ← programar posição 2 (Flash)
quit
```

O iMPACT gera um arquivo **SVF** (Serial Vector Format) — um script
de texto que descreve cada operação JTAG necessária para gravar a Flash,
incluindo apagamento, programação e verificação.

O SVF é independente de hardware — qualquer ferramenta que entenda
JTAG pode executá-lo. Por isso o OpenOCD consegue usá-lo.

### Etapa 3 — OpenOCD: executar o SVF

```bash
openocd -f gravar.cfg -c "init; svf reflex_game_flash.svf progress; exit"
```

O OpenOCD lê o arquivo SVF e executa cada vetor JTAG descrito nele,
gravando o firmware na Flash. Leva 1 a 3 minutos.

**Resultado:** ao ligar a placa, o FPGA lê automaticamente a Platform Flash
e carrega o bitstream sem precisar de computador.

---

## Por que dois chips na cadeia JTAG?

O FPGA (xc3s200) não tem memória Flash interna. Ao desligar, perde tudo.
A Platform Flash (xcf01s) é uma memória não-volátil dedicada — ao ligar,
ela transmite o bitstream via JTAG interno para o FPGA.

```
Ligar a placa:
  xcf01s lê seu conteúdo → envia para xc3s200 via JTAG interno → FPGA configura
  (automático, sem PC, sem USB)

Gravar nova versão:
  PC → USB → FT2232H → JTAG → xcf01s (nova versão gravada)
  → na próxima ligada, FPGA carrega a nova versão
```

---

## Resumo do fluxo completo

```
PC
│
│ python fpga_panel.py
│
├─► "Gravar na RAM"
│     openocd ... "pld load 0 reflex_game.bit"
│     Dura: ~3 segundos
│     Persiste: até desligar
│
└─► "Gravar na Flash"
      │
      ├─ [1] promgen → reflex_game_flash.mcs   (ISE)
      ├─ [2] impact  → reflex_game_flash.svf   (ISE)
      └─ [3] openocd → "svf reflex_game_flash.svf"
             Dura: ~2 minutos
             Persiste: permanente (carrega ao ligar)
```

---

## Resolução de problemas comuns

### "Error: libusb_open() failed with LIBUSB_ERROR_ACCESS"

**Linux:** permissão negada no dispositivo USB.
```bash
bash toolkit/iniciar.sh    # configura udev
# ou:
sudo openocd -f gravar.cfg ...
```

### "Error: JTAG scan chain interrogation failed"

- Cabo USB mal conectado
- Placa sem energia
- Driver errado no Windows (precisa do libusbK via Zadig no Canal A)
- Velocidade muito alta: tentar `adapter speed 1000` no gravar.cfg

### "Error: Could not find device matching 0403:70b1"

- Placa não conectada ou não reconhecida pelo sistema
- Linux: rodar `iniciar.sh` para registrar o VID:PID no driver ftdi_sio
- Windows: verificar Gerenciador de Dispositivos

### "svf: ... FAIL"

O SVF gerado pelo iMPACT está incorreto ou a Flash está com problema.
Tentar gravar na RAM primeiro para confirmar que o JTAG funciona.
Se RAM funcionar mas Flash falhar, verificar se o iMPACT tem licença ativa.
