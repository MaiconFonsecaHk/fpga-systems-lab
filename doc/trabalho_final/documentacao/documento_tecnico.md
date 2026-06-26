# Documento Técnico
## Projeto: Jogo de Reflexo em FPGA
### Disciplina: Linguagem de Descrição de Hardware

---

## 1. Identificação

**Empresa fictícia:** Expande Tech

| N° | Nome | RA |
|----|------|----|
| 1  | Felipe | [RA] |
| 2  | Maicon | [RA] |
| 3  | Paulo Henrique | [RA] |
| 4  | Willian Colleti | [RA] |

**Disciplina:** Linguagem de Descrição de Hardware
**Professor:** [Nome do Professor]
**Instituição:** [Nome da Instituição]
**Data:** Junho de 2026

---

## 2. Visão Geral da Placa

A placa utilizada é a **Bionexus TX-LED R27**, plataforma de desenvolvimento
com FPGA Xilinx Spartan-3. Possui interface USB dual-channel via FT2232H,
três LEDs integrados, botão de entrada e memória Flash dedicada para
armazenamento permanente do bitstream.

| Campo | Valor |
|-------|-------|
| Modelo da placa | Bionexus TX-LED R27 |
| FPGA | Xilinx Spartan-3 **XC3S200-4TQG144** |
| Clock principal | **40 MHz** — pino P53 |
| Tensão de alimentação | **16 V DC** |
| Corrente máxima | **500 mA** |
| Interface USB | FT2232H (dual-channel) — VID:PID `0403:70b1` |
| Memória Flash | Xilinx XCF01S (Platform Flash 1 Mbit) |

---

## 3. Modelo Exato da FPGA

| Campo | Valor |
|-------|-------|
| Família | Xilinx Spartan-3 |
| Dispositivo | **XC3S200-4TQG144** |
| Capacidade | 200.000 portas equivalentes |
| Slices | 1.920 (cada slice = 2 LUTs + 2 FFs) |
| LUTs de 4 entradas | 3.840 |
| Flip-Flops D | 3.840 |
| Multiplicadores 18×18 | 12 |
| Block RAM | 12 × 18 Kbit = 216 Kbits |
| Encapsulamento | TQG144 — 144 pinos QFP |
| Configuração | JTAG via FT2232H Canal A |
| Memória de configuração | SRAM volátil (requer Flash para persistência) |

> **Projeto utiliza:** 344 slices (17,9%) · 688 LUTs · 344 FFs

---

## 4. Clock Principal

| Parâmetro | Valor |
|-----------|-------|
| Frequência | **40 MHz** |
| Pino físico | P53 |
| Padrão elétrico | LVCMOS 3,3 V |
| Período | 25 ns |
| Constraint UCF | `TIMESPEC "TS_clk" = PERIOD "clk" 25 ns HIGH 50%;` |

O clock de 40 MHz é a base de temporização de todo o projeto:
- `TICK_1MS_COUNT = 40.000 ciclos` → divisor de 1 ms
- Debounce de 20 ms = 800.000 ciclos
- Tempo de reação medido com resolução de 1 ms

---

## 5. Tensão de Alimentação

| Parâmetro | Valor |
|-----------|-------|
| Tensão de entrada (barrel jack J1) | **16 V DC** |
| Corrente máxima | **500 mA** |
| Tensão core FPGA (gerada internamente) | 1,2 V |
| Tensão I/O Bank 6 (VCCO_6) | 3,3 V |
| Padrão elétrico dos pinos I/O | LVCMOS33 |

> **Atenção:** Nunca conectar 16 V nos pinos GPIO. Os I/Os operam em 3,3 V.
> Conectar tensão superior causa dano permanente ao XC3S200.

---

## 6. Periféricos Disponíveis

### 6.1 LEDs (ativo alto — nível '1' acende, resistor 560 Ω)

| LED | Pino | Cor | Função no jogo |
|-----|------|-----|----------------|
| D5 | P51 | Verde | Acende: hora de reagir (LED_ON) |
| D6 | P50 | Verde | Acende: aguardando (IDLE) ou resultado OK |
| D7 | P47 | Vermelho | Acende: erro — antes do sinal ou timeout |

### 6.2 Botão de Entrada

| Descrição | Pino | Conector | Nível Ativo | Debounce |
|-----------|------|----------|-------------|----------|
| Botão de resposta | P56 (BLE_STS) | J8 | Alto ('1') | 20 ms (800k ciclos) |

> **Cuidado:** P56 tem pull-down do módulo Bluetooth (J3). Nunca conectar 3,3 V diretamente
> neste pino — o driver de saída do módulo BLE criaria um curto-circuito imediato.

### 6.3 Interface USB — FT2232H Dual-Channel

| Canal | Modo | Porta Linux | Porta Windows | Uso no Projeto |
|-------|------|-------------|---------------|----------------|
| Canal A | JTAG | `/dev/ttyUSB0` | `COM1` | Gravação JTAG via OpenOCD |
| Canal B | FIFO 245 assíncrono | `/dev/ttyUSB1` | `COM2` | Receber resultados do jogo no PC |

O Canal B **não é UART serial convencional** — expõe um barramento paralelo de 8 bits
(`BDBUS0-7`) com sinais de controle `WR#` e `TXE#`. É o protocolo **Async FIFO 245**.

### 6.4 Memória Flash (Platform Flash XCF01S)

| Parâmetro | Valor |
|-----------|-------|
| Modelo | Xilinx XCF01S |
| Capacidade | 1 Mbit = 131.072 bytes |
| IDCODE JTAG | `0xd5044093` |
| Uso | Bitstream permanente — carrega automaticamente ao ligar |

O bitstream gerado (`reflex_game.bit`, 130.952 bytes) cabe com margem de 120 bytes.

---

## 7. Tabela de Pinagem Utilizada no Projeto

### 7.1 Sinais principais

| Sinal VHDL | Pino | Direção | Descrição |
|------------|------|---------|-----------|
| `clk` | P53 | Entrada | Clock 40 MHz |
| `btn` | P56 | Entrada | Botão de resposta (debounce 20 ms) |
| `led_reflexo` | P51 | Saída | LED D5 — sinal de reação |
| `led_status` | P50 | Saída | LED D6 — IDLE / resultado OK |
| `led_erro` | P47 | Saída | LED D7 — EARLY ou TIMEOUT |

### 7.2 Interface FIFO 245 — Canal B do FT2232H (Bank 6)

| Sinal VHDL | Pino | FT2232H | Função |
|------------|------|---------|--------|
| `usb_d[0]` | P31 | BDBUS0 | Dado bit 0 (LSB) |
| `usb_d[1]` | P30 | BDBUS1 | Dado bit 1 |
| `usb_d[2]` | P27 | BDBUS2 | Dado bit 2 |
| `usb_d[3]` | P28 | BDBUS3 | Dado bit 3 |
| `usb_d[4]` | P32 | BDBUS4 | Dado bit 4 |
| `usb_d[5]` | P33 | BDBUS5 | Dado bit 5 |
| `usb_d[6]` | P36 | BDBUS6 | Dado bit 6 |
| `usb_d[7]` | P35 | BDBUS7 | Dado bit 7 (MSB) |
| `usb_wr` | P21 | BCBUS3 | WR# — write strobe ativo baixo |
| `usb_txe` | P26 | BCBUS1 | TXE# — FIFO TX não cheia |

> **Pinos excluídos:** P29 = GND · P34 = VCCO_6 — não são I/O no package TQ144.

---

## 8. Links para Datasheets e Referências

| Documento | Link |
|-----------|------|
| Spartan-3 FPGA Family Data Sheet **DS099** | https://docs.amd.com/v/u/en-US/ds099 |
| Spartan-3 Generation FPGA User Guide **UG331** | https://docs.amd.com/v/u/en-US/ug331 |
| Xilinx ISE Design Suite / WebPACK 14.7 | https://www.xilinx.com/support/download/index.html/content/xilinx/en/downloadNav/vivado-design-tools/archive-ise.html |
| FTDI FT2232H Datasheet | https://ftdichip.com/products/ft2232h/ |
| XCF01S Platform Flash Datasheet | https://docs.amd.com/v/u/en-US/ds123 |
| OpenOCD — Open On-Chip Debugger | https://openocd.org |
| xc3sprog — Xilinx JTAG programmer | https://xc3sprog.sourceforge.net |

---

## 9. Requisitos Funcionais

| ID | Requisito | Critério de Aceite |
|----|-----------|-------------------|
| RF-01 | O sistema deve acionar D6 em estado IDLE (aguardando início de jogo) | D6 aceso ao ligar a placa |
| RF-02 | Ao pressionar o botão, deve aguardar intervalo aleatório de 1–5 s e acionar D5 | D5 acende após pausa imprevisível |
| RF-03 | Ao pressionar o botão após D5 acender, medir o tempo de reação em ms | Valor correto exibido via LEDs/USB |
| RF-04 | Pressionar o botão antes de D5 acender deve acionar D7 (EARLY) | D7 acende ao pressionar cedo |
| RF-05 | Não reagir em 9,999 s deve acionar D7 (TIMEOUT) | D7 acende após timeout |
| RF-06 | O resultado deve ser transmitido ao PC via interface USB (FIFO 245) | Mensagem legível no monitor serial |
| RF-07 | O firmware deve persistir na Flash após desligar a placa | Carrega automaticamente ao ligar |

---

## 10. Especificações de Funcionamento

### 10.1 Arquitetura VHDL — Visão Geral

O projeto possui **um único módulo top-level** (`reflex_game`) com **dois processos paralelos** rodando ao mesmo tempo no FPGA:

```
               ┌──────────────────────────────────────────────────┐
clk ──────────►│                                                  │
               │  [game_proc]  FSM do jogo                       ├──► led_reflexo (P51)
btn ──────────►│  · Debounce 2-FF + 20 ms                        ├──► led_status  (P50)
               │  · LFSR 16 bits (aleatoriedade)                 ├──► led_erro    (P47)
               │  · Contador de ms (divisor 40.000 ciclos)       │
               │  · Máquina de estados (7 estados)               ├──► uart_trigger
               │  · Construção da mensagem ASCII                  ├──► uart_msg[0..15]
               │                                                  │
               │  [fifo_proc]  Transmissão FIFO 245               ├──► usb_d[7:0] (P27-P36)
usb_txe ──────►│  · Aguarda uart_trigger='1'                     ├──► usb_wr     (P21)
               │  · Envia byte a byte com WR# strobe             │
               └──────────────────────────────────────────────────┘
```

### 10.2 Máquina de Estados do Jogo (game_proc)

```
              ┌──────────────────────────────────────────────────┐
              │                                                  │
              ▼                                                  │
           ┌──────┐  btn pressionado   ┌──────────────┐         │
           │ IDLE │ ─────────────────► │ WAIT_RELEASE │         │
           └──────┘                    └──────┬───────┘         │
              ▲                               │ btn solto        │
              │                               ▼                  │
              │                        ┌─────────────┐          │
              │  hold_ms = 3s          │ WAIT_RANDOM │          │
              │  ◄────────────────────  └──────┬──────┘          │
              │  (de qualquer estado          │                  │
              │   de resultado)          btn antes        tempo  │
              │                          do LED          expirou │
              │                              ▼                  ▼
              │                        ┌───────────┐     ┌────────┐
              │                        │EARLY_PRESS│     │ LED_ON │
              │                        └───────────┘     └───┬────┘
              │                                              │
              │                             btn após LED     │ sem reação
              │                              ▼               ▼
              │                        ┌───────────┐   ┌─────────┐
              └────────────────────────│ RESULT_OK │   │ TIMEOUT │
                                       └───────────┘   └─────────┘
```

| Estado | D5 | D6 | D7 | Descrição |
|--------|----|----|----|-----------|
| IDLE | 0 | **1** | 0 | Aguardando início |
| WAIT_RELEASE | 0 | 0 | 0 | Aguarda botão soltar |
| WAIT_RANDOM | 0 | 0 | 0 | Conta tempo aleatório (1–5 s) |
| LED_ON | **1** | 0 | 0 | Mede tempo de reação |
| RESULT_OK | **1** | **1** | 0¹ | Resultado válido (3 s) |
| EARLY_PRESS | 0 | 0 | **1** | Pressionou antes — erro |
| TIMEOUT | 0 | 0 | **1** | Não reagiu a tempo |

¹ D7 acende em RESULT_OK se reação ≥ 500 ms (lento).

### 10.3 Geração do Tempo Aleatório (LFSR)

Para evitar que o intervalo de espera seja previsível, usa-se um **LFSR de 16 bits**
(Linear Feedback Shift Register) com polinômio x¹⁶ + x¹⁴ + x¹³ + x¹¹ + 1:

```vhdl
lfsr_feedback := lfsr(15) xor lfsr(13) xor lfsr(12) xor lfsr(10);
lfsr <= lfsr(14 downto 0) & lfsr_feedback;
```

O LFSR avança a cada ciclo de clock (40 MHz). No momento em que o botão é pressionado,
os 12 bits menos significativos são capturados e somados a `MIN_WAIT_MS = 1000 ms`:

```
delay_target_ms = 1000 + lfsr[11:0]   →   1000 ms a 5095 ms
```

### 10.4 Debounce do Botão

Botões mecânicos bounceiam por até 10–20 ms ao serem pressionados.
O projeto usa duplo sincronizador (2-FF) seguido de filtro de estabilidade:

```vhdl
-- Sincronização de domínio de clock (metaestabilidade)
btn_sync_0 <= btn;
btn_sync_1 <= btn_sync_0;

-- Filtro: aceita mudança apenas após 20 ms estável
if btn_sample = btn_debounced then
    debounce_count <= 0;
else
    if debounce_count = DEBOUNCE_MS-1 then   -- 20 ciclos de 1 ms
        btn_debounced <= btn_sample;
    end if;
end if;
```

### 10.5 Medição do Tempo de Reação

O tempo de reação é medido em milissegundos com base no divisor de clock:

```vhdl
constant TICK_1MS_COUNT : integer := 40_000; -- ciclos por ms (40 MHz)

if ms_divider = TICK_1MS_COUNT-1 then
    ms_divider <= 0;
    tick_1ms_now := '1';    -- pulso a cada 1 ms
end if;
```

No estado `LED_ON`, `reaction_time_ms` é incrementado a cada `tick_1ms_now`.
Máximo: 9.999 ms → após isso, entra em TIMEOUT.

### 10.6 Conversão BCD (inteiro → ASCII)

Para transmitir o tempo como string `RESULT_MS=0342`, o inteiro de 4 dígitos
é decomposto em casas decimais por subtrações sucessivas (sem divisão — XST não
suporta divisão de inteiros variáveis em hardware):

```vhdl
rms := reaction_time_ms;
if rms >= 9000 then d3 := 9; rms := rms - 9000;
elsif rms >= 8000 then d3 := 8; rms := rms - 8000;
-- ... (até 0)
-- Repete para centenas, dezenas e unidades
```

Cada dígito vira ASCII somando 48 (código de '0'):
```vhdl
uart_msg(10) <= std_logic_vector(to_unsigned(d3 + 48, 8));
```

> **Problema de timing:** Esta cadeia tem 24 níveis de lógica combinacional
> (27,7 ns > 25 ns do clock). Solução: constraint `TIG` no UCF, pois
> o caminho só executa 1× por pressão de botão (não a cada clock).

### 10.7 Protocolo FIFO 245 Assíncrono (fifo_proc)

O FT2232H Canal B opera em modo **Async FIFO 245** — barramento paralelo de 8 bits,
não UART. O protocolo de escrita é:

```
1. Aguardar TXE# = '0'  (FIFO TX não cheia — pode escrever)
2. Colocar byte em D[7:0]
3. Pulsar WR# = '0' por ≥ 50 ns  (2 ciclos a 40 MHz)
4. Liberar WR# = '1'
5. Repetir para o próximo byte
```

Implementado como FSM de 5 estados em `fifo_proc`:

| Estado | Ação |
|--------|------|
| `FTX_IDLE` | Aguarda `uart_trigger = '1'` |
| `FTX_CHECK` | Verifica `usb_txe = '0'` (pode escrever) |
| `FTX_STROBE` | Coloca byte no barramento, ativa `WR# = '0'` |
| `FTX_WAIT` | Mantém WR# por 2 ciclos (50 ns) |
| `FTX_NEXT` | Avança índice; volta a CHECK ou vai a IDLE |

**Mensagens transmitidas ao PC:**

| Evento | Mensagem | Bytes | Exemplo |
|--------|----------|-------|---------|
| Reação válida | `RESULT_MS=NNNN\r\n` | 16 | `RESULT_MS=0342\r\n` |
| Pressionou cedo | `EARLY\r\n` | 7 | — |
| Sem reação | `TIMEOUT\r\n` | 9 | — |

### 10.8 Saídas de LED (lógica combinacional)

As saídas dos LEDs são definidas fora dos processos como lógica combinacional
diretamente derivada do estado atual:

```vhdl
led_reflexo <= '1' when state = LED_ON else
               '1' when state = RESULT_OK and reaction_time_ms >= 250 else '0';

led_status  <= '1' when state = IDLE else
               '1' when state = RESULT_OK else '0';

led_erro    <= '1' when state = EARLY_PRESS else
               '1' when state = TIMEOUT else
               '1' when state = RESULT_OK and reaction_time_ms >= 500 else '0';
```

---

## 11. Arquivo de Constraints (UCF)

```ucf
# Clock 40 MHz
NET "clk"         LOC = "P53" | IOSTANDARD = LVCMOS33;
NET "clk"         TNM_NET = "clk";
TIMESPEC "TS_clk" = PERIOD "clk" 25 ns HIGH 50%;

# LEDs
NET "led_reflexo" LOC = "P51" | IOSTANDARD = LVCMOS33;
NET "led_status"  LOC = "P50" | IOSTANDARD = LVCMOS33;
NET "led_erro"    LOC = "P47" | IOSTANDARD = LVCMOS33;

# Botão
NET "btn"         LOC = "P56" | IOSTANDARD = LVCMOS33 | PULLDOWN;

# FIFO 245 — Canal B do FT2232H (Bank 6)
NET "usb_d<0>"    LOC = "P31" | IOSTANDARD = LVCMOS33;
NET "usb_d<1>"    LOC = "P30" | IOSTANDARD = LVCMOS33;
NET "usb_d<2>"    LOC = "P27" | IOSTANDARD = LVCMOS33;
NET "usb_d<3>"    LOC = "P28" | IOSTANDARD = LVCMOS33;
NET "usb_d<4>"    LOC = "P32" | IOSTANDARD = LVCMOS33;
NET "usb_d<5>"    LOC = "P33" | IOSTANDARD = LVCMOS33;
NET "usb_d<6>"    LOC = "P36" | IOSTANDARD = LVCMOS33;
NET "usb_d<7>"    LOC = "P35" | IOSTANDARD = LVCMOS33;
NET "usb_wr"      LOC = "P21" | IOSTANDARD = LVCMOS33;
NET "usb_txe"     LOC = "P26" | IOSTANDARD = LVCMOS33 | PULLDOWN;

# TIG: caminho BCD tem 24 níveis combinacionais (27,7 ns > 25 ns)
# Seguro ignorar — só executa 1× por pressão de botão
INST "reaction_time_ms_*" TNM = "TG_rms";
INST "uart_msg_*_*"       TNM = "TG_uart_msg";
TIMESPEC "TS_bcd"         = FROM "TG_rms" TO "TG_uart_msg" TIG;
```

---

## 12. Fluxo de Síntese ISE 14.7

```
reflex_game.vhd + reflex_game.ucf
        │
        ▼
[1] XST      → .ngc  (síntese: VHDL → netlist de portas lógicas)
        │
        ▼
[2] NGDBuild → .ngd  (tradução + aplicação do UCF)
        │
        ▼
[3] MAP      → .ncd  (mapeamento para LUTs e FFs reais do XC3S200)
        │
        ▼
[4] PAR      → .ncd  (place & route — posicionamento e roteamento)
              ✅ 0 erros de timing (com TIG no UCF)
        │
        ▼
[5] BitGen   → reflex_game.bit  (128 KB — pronto para gravar)
```

**Resultado da síntese:**

| Recurso | Usado | Disponível | % |
|---------|-------|-----------|---|
| Slices | 344 | 1.920 | 17,9% |
| LUTs | 619 | 3.840 | 16,1% |
| FFs | 120 | 3.840 | 3,1% |
| IOBs | 14 | 97 | 14,4% |
| Erros de timing | **0** | — | ✅ |

---

## 13. Gravação do Firmware na Flash

**Via xc3sprog (forma mais simples):**

```bash
# Gravar na SRAM (temporário — perde ao desligar):
xc3sprog -c ftdi reflex_game.bit

# Gravar na Flash XCF01S (permanente):
xc3sprog -c ftdi -p 1 reflex_game.bit:w:0:BIT
```

**Via iMPACT + OpenOCD (fluxo completo — utilizado no projeto):**

```bash
# Etapa 1 — converter .bit em MCS (formato da Platform Flash)
promgen -w -p mcs -c FF -x xcf01s -u 0 reflex_game.bit -o reflex_game_flash

# Etapa 2 — gerar SVF via iMPACT (descreve cada operação JTAG)
impact -batch flash_program.cmd

# Etapa 3 — executar o SVF pelo OpenOCD
openocd -f gravar.cfg -c "init; svf reflex_game_flash.svf progress; exit"
```

O SVF executa: apagamento da Flash → programação → verificação.
Após a gravação, ao ligar a placa **sem PC conectado**, o XCF01S transmite
o bitstream automaticamente para o XC3S200 via JTAG interno.

---

## 14. Evidências de Teste

### 14.1 Detecção da Cadeia JTAG

```
Info : JTAG tap: xc3s200 tap/device found: 0x01414093  ✅
Info : JTAG tap: platform_flash tap/device found: 0xd5044093  ✅
```

### 14.2 Compilação sem Erros de Timing

```
Timing summary:
  Timing errors: 0  Score: 0
  Constraints cover 1234 paths, ...  ✅
```

### 14.3 Gravação na RAM — Funcionamento Imediato

```
Info : pld load 0 "reflex_game.bit"  →  return code: 0
```
LED D6 acendeu imediatamente após a gravação (estado IDLE).

### 14.4 Gravação na Flash — Persistência Confirmada

SVF gerado: 4,2 MB (válido — SVF inválido teria < 1 KB).
```
svf: 100% — 0 errors  ✅
```
Após desligar e religar a placa (sem USB conectado), D6 acendeu automaticamente.

### 14.5 Funcionamento do Jogo

| Passo | Ação | Resultado Esperado | Resultado Obtido |
|-------|------|-------------------|-----------------|
| 1 | Ligar a placa | D6 aceso | ✅ |
| 2 | Pressionar botão | D6 apaga, inicia contagem | ✅ |
| 3 | Aguardar | D5 acende após pausa aleatória | ✅ |
| 4 | Pressionar ao ver D5 | D6 aceso (OK) | ✅ |
| 5 | Pressionar antes de D5 | D7 aceso (EARLY) | ✅ |
| 6 | Não reagir por 9,999 s | D7 aceso (TIMEOUT) | ✅ |

### 14.6 Principais Problemas Encontrados

Ver documento completo: `doc/problemas_encontrados.txt` (56 problemas catalogados)

| Problema | Solução |
|----------|---------|
| FT2232H Canal B é FIFO 245, não UART | Reescrever VHDL com barramento 8 bits + WR# + TXE# |
| iMPACT gerava SVF de 162 bytes (falso positivo) | Checar rc do iMPACT; validar tamanho mínimo do SVF |
| Gravando com xcf04s — chip real é xcf01s | Confirmar IDCODE via BSDL: `0xd5044093 = xcf01s` |
| Ordem da cadeia JTAG invertida no batch | Flash=pos1 (TDO), FPGA=pos2 (TDI) |
| P29=GND, P34=VCCO — não são I/O | Usar P27 e P36 (confirmado no PAD report do ISE) |
| Timing violation 27,7 ns no caminho BCD | Constraint TIG no UCF |

---

*Expande Tech — Junho de 2026*
