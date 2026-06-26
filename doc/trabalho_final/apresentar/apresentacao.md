# Apresentação — Jogo de Reflexo em FPGA
## Linguagem de Descrição de Hardware
### Nexus Sistemas Embarcados

> **14 slides · ~15 minutos** (~1 min por slide, exceto problemas ~2 min)
> Cada `---` marca um novo slide. Importar no Google Slides ou PowerPoint.

---

## SLIDE 1 — Capa
**⏱ 1 min**

# Jogo de Reflexo em FPGA
## Spartan-3 XC3S200 · Bionexus TX-LED R27

**Expande Tech**

| Integrante | RA |
|------------|----|
| Felipe | [RA] |
| Maicon | [RA] |
| Paulo Henrique | [RA] |
| Willian Colleti | [RA] |

*Linguagem de Descrição de Hardware — Junho 2026*

---

## SLIDE 2 — Desafio Recebido
**⏱ 1 min**

### O que foi pedido

> Implementar um projeto digital completo em VHDL para a placa FPGA fornecida,
> com gravação permanente via USB e comunicação de resultados ao PC.

**Hardware fornecido pelo professor:**
- Placa Bionexus TX-LED R27
- Alimentação 16 V DC / 500 mA
- Gravação via USB (xc3sprog / OpenOCD)

**O que desenvolvemos:**

| Entregável | Descrição |
|------------|-----------|
| VHDL base | Pisca LED 1 Hz (exemplo de contador) |
| **Projeto principal** | **Jogo de Reflexo — mede tempo de reação em ms** |
| Comunicação | Resultado enviado ao PC via FIFO USB |
| Firmware permanente | Gravado na Platform Flash XCF01S |

---

## SLIDE 3 — A Placa: Bionexus TX-LED R27
**⏱ 1 min**

```
┌──────────────────────────────────────────────────────┐
│  Bionexus TX-LED R27                                 │
│                                                      │
│  ┌──────────┐   Canal A (JTAG) ──────► XC3S200       │
│  │ FT2232H  │                          XCF01S        │
│  │ Dual USB │   Canal B (FIFO) ──────► D[7:0]+WR#+   │
│  └──────────┘                          TXE# (Bank 6) │
│                                                      │
│  Clock: 40 MHz (P53)                                 │
│  LEDs:  D5(P51) · D6(P50) · D7(P47)                 │
│  Botão: P56 (BLE_STS)                               │
│  Flash: XCF01S — 1 Mbit                             │
└──────────────────────────────────────────────────────┘
```

| Campo | Valor |
|-------|-------|
| FPGA | Xilinx **XC3S200-4TQG144** |
| Clock | **40 MHz** |
| Alimentação | **16 V DC / 500 mA** |
| USB | FT2232H dual-channel `0403:70b1` |

---

## SLIDE 4 — Requisitos do Jogo
**⏱ 1 min**

### O que o jogo deve fazer

```
  LIGA A PLACA
       │
       ▼
  D6 acende  ←──── IDLE: aguardando jogador
       │
  [Jogador pressiona botão]
       │
       ▼
  Espera aleatória: 1 a 5 segundos
  (jogador não sabe quando vai acender)
       │
       ▼
  D5 ACENDE  ←──── hora de reagir!
       │
  [Jogador pressiona o mais rápido possível]
       │
       ▼
  Resultado enviado ao PC: RESULT_MS=0342
  LEDs indicam: OK / EARLY / TIMEOUT
```

**Resolução de medição: 1 ms**
**Máximo: 9.999 ms (≈ 10 segundos)**

---

## SLIDE 5 — Pinagem Utilizada
**⏱ 1 min**

### Sinais do Jogo

| Sinal VHDL | Pino | Periférico |
|------------|------|-----------|
| `clk` | **P53** | Clock 40 MHz |
| `btn` | **P56** | Botão de resposta |
| `led_reflexo` | **P51** | D5 — hora de reagir |
| `led_status` | **P50** | D6 — IDLE / OK |
| `led_erro` | **P47** | D7 — EARLY / TIMEOUT |
| `usb_d[0..7]` | **P31/P30/P27/P28/P32/P33/P36/P35** | Dado FIFO |
| `usb_wr` | **P21** | WR# write strobe |
| `usb_txe` | **P26** | TXE# FIFO não cheia |

> ⚠ **Descoberta importante:** P29 = GND · P34 = VCCO_6
> Estes não são pinos I/O — atribuí-los no UCF causa rejeição no MAP/PAR.

---

## SLIDE 6 — Arquitetura VHDL: Dois Processos Paralelos
**⏱ 1 min**

### A lógica paralela do FPGA

```vhdl
entity reflex_game is Port (
    clk, btn, usb_txe : in  STD_LOGIC;
    led_reflexo, led_status, led_erro : out STD_LOGIC;
    usb_d : out STD_LOGIC_VECTOR(7 downto 0);
    usb_wr : out STD_LOGIC
);
```

```
FPGA — execução simultânea real (não sequencial!)
┌─────────────────────────────────────────────────┐
│                                                 │
│  game_proc  ─── FSM + debounce + LFSR + BCD ──► LEDs
│                                             ──► uart_trigger
│                                                 │
│  fifo_proc  ─── FIFO 245 TX ────────────────── ► usb_d + usb_wr
│                                                 │
└─────────────────────────────────────────────────┘
```

**Em software** você não consegue fazer isso: um processador executa
uma instrução por vez. No FPGA, os dois processos rodam **ao mesmo tempo**.

---

## SLIDE 7 — Máquina de Estados do Jogo (FSM)
**⏱ 1 min**

### 7 estados · transições por eventos de ms

```
         btn press
IDLE ─────────────► WAIT_RELEASE
 ▲                       │ btn solto
 │                       ▼
 │              ┌──── WAIT_RANDOM ────┐
 │          btn │   (1 a 5 segundos)  │ tempo expirou
 │         cedo │                     ▼
 │              ▼                  LED_ON
 │        EARLY_PRESS                 │ btn pressionado
 │        (D7 acende)                 ▼
 │                              RESULT_OK
 │                              (D5+D6 acendem)
 │                                    │
 │                              TIMEOUT (D7)
 │                                    │
 └────────────────────── após 3 s ────┘
```

**Cada tick = 1 ms** · Gerado dividindo 40.000 ciclos do clock de 40 MHz

---

## SLIDE 8 — Aleatoriedade com LFSR
**⏱ 1 min**

### Por que o intervalo de espera é imprevisível

Um **LFSR de 16 bits** (Linear Feedback Shift Register) avança
40 milhões de vezes por segundo. No momento exato do clique,
seus 12 bits menos significativos definem o atraso:

```vhdl
-- Polinômio: x¹⁶ + x¹⁴ + x¹³ + x¹¹ + 1
lfsr_feedback := lfsr(15) xor lfsr(13) xor lfsr(12) xor lfsr(10);
lfsr <= lfsr(14 downto 0) & lfsr_feedback;

-- Ao pressionar o botão:
delay_target_ms <= 1000 + to_integer(lfsr(11 downto 0));
--                         ↑ entre 0 e 4095 ms
--              Total: 1000 ms a 5095 ms
```

**Por que não usar um simples contador?**
Um contador sempre daria o mesmo intervalo → jogador memorizaria o padrão.
O LFSR produz sequências pseudoaleatórias com período de 65.535 valores.

---

## SLIDE 9 — Comunicação com o PC: FIFO 245
**⏱ 1 min**

### Por que não UART?

O FT2232H Canal B desta placa expõe **barramento paralelo de 8 bits** no esquemático
(BDBUS0-7 + WR# + TXE#). Isso é **Async FIFO 245** — não UART serial.

```
FPGA                FT2232H              PC
  │                    │                  │
  ├── D[7:0] = byte ──►│                  │
  ├── WR# = '0' ───────► (pulso ≥ 50 ns) │
  ├── WR# = '1' ───────►│                 │
  │◄── TXE# = '0' ──────│ (pode escrever) │
  │                    ├── USB ──────────►│ /dev/ttyUSB1
```

**Mensagem enviada para cada partida:**
```
RESULT_MS=0342\r\n    ← 342 ms de tempo de reação
EARLY\r\n             ← pressionou antes do LED
TIMEOUT\r\n           ← não reagiu
```

**Erro cometido:** tentar usar 1 pino `uart_tx` num barramento de 8 bits
→ zero bytes chegavam. Protocolo todo errado.

---

## SLIDE 10 — Conversão BCD e Timing Violation
**⏱ 1 min**

### Transformar número em texto ASCII no FPGA

Para enviar `"0342"`, o FPGA precisa converter o inteiro 342 em 4 dígitos ASCII.
Divisão não é suportada pelo XST → usamos subtrações sucessivas:

```vhdl
rms := reaction_time_ms;
if rms >= 9000 then d3 := 9; rms := rms - 9000;
elsif rms >= 8000 then d3 := 8; rms := rms - 8000;
-- ... até 0
-- Repete para centenas, dezenas, unidades
uart_msg(10) <= to_unsigned(d3 + 48, 8); -- ASCII '0' = 48
```

**Problema:** 24 níveis de lógica combinacional → 27,7 ns > 25 ns (clock 40 MHz)

**Solução — constraint TIG no UCF:**
```ucf
INST "reaction_time_ms_*" TNM = "TG_rms";
INST "uart_msg_*_*"       TNM = "TG_uart_msg";
TIMESPEC "TS_bcd" = FROM "TG_rms" TO "TG_uart_msg" TIG;
```
TIG = Timing Ignore. **Seguro** porque esse caminho executa apenas 1× por clique,
nunca em dois clocks consecutivos.

---

## SLIDE 11 — Fluxo de Síntese ISE 14.7
**⏱ 1 min**

### Do código ao chip

```
reflex_game.vhd  +  reflex_game.ucf
         │
    [1] XST ──────────► .ngc   VHDL → portas lógicas
         │
    [2] NGDBuild ─────► .ngd   aplica constraints de pinos
         │
    [3] MAP ──────────► .ncd   mapeia para LUTs e FFs do XC3S200
         │
    [4] PAR ──────────► .ncd   place & route + verificação de timing
         │               ✅ 0 erros de timing
    [5] BitGen ───────► reflex_game.bit  (128 KB)
```

**Resultado:**

| Recurso | Uso | % |
|---------|-----|---|
| Slices | 344 / 1.920 | 17,9% |
| IOBs | 14 / 97 | 14,4% |
| Erros de timing | **0** | ✅ |

---

## SLIDE 12 — Gravação do Firmware
**⏱ 1 min**

### SRAM (temporário) vs Flash (permanente)

**Via xc3sprog — linha de comando direta:**
```bash
# SRAM — temporário (perde ao desligar):
xc3sprog -c ftdi reflex_game.bit

# Flash — permanente (carrega ao ligar):
xc3sprog -c ftdi -p 1 reflex_game.bit:w:0:BIT
```

**Via iMPACT + OpenOCD — fluxo completo utilizado:**
```
promgen → .mcs    (converte .bit para formato da Platform Flash)
iMPACT  → .svf    (gera script JTAG: apagar + programar + verificar)
OpenOCD → executa  (reproduz cada vetor JTAG na placa)
```

**Após a gravação na Flash:**
```
Desligar USB → desligar placa → religar placa (sem PC)
→ XCF01S envia bitstream para XC3S200 automaticamente
→ D6 acende: jogo pronto!
```

---

## SLIDE 13 — Problemas Encontrados e Soluções
**⏱ 2 min**

### Os mais impactantes (total: 56 catalogados)

| # | Problema | Como descobrimos | Solução |
|---|----------|-----------------|---------|
| P40 | Canal B é FIFO 245, não UART | Zero bytes chegando em qualquer pino testado | Reescrever VHDL com 8 bits + WR# + TXE# |
| P44 | SVF do iMPACT com 162 bytes — falso positivo na gravação | Flash não carregava após power cycle | Verificar rc do iMPACT + tamanho mínimo do SVF |
| P45 | Gravando com xcf04s — chip real é xcf01s | IDCODE mismatch na cadeia JTAG | Cruzar IDCODE `0xd5044093` com BSDL do ISE |
| P46 | Cadeia JTAG invertida — FPGA e Flash trocados | TDO sempre zero na leitura | Flash=pos1 (lado TDO), FPGA=pos2 (lado TDI) |
| P42/P43 | P29=GND, P34=VCCO não são I/O | PAR rejeitou os pinos | Usar P27 e P36 (validar no PAD report) |
| P43 | Timing violation 27,7 ns no caminho BCD | PAR reportou 16 erros de timing | Constraint TIG no UCF |

> **Maior aprendizado:** leia o esquemático e o BSDL antes de escrever o UCF.
> Horas de debug causadas por suposições que pareciam óbvias.

---

## SLIDE 14 — Conclusão e Aprendizados
**⏱ 1 min**

### Resultado final

✅ Jogo de reflexo funcional gravado **permanentemente** na Platform Flash XCF01S
✅ Firmware carrega automaticamente ao ligar — sem PC, sem cabo
✅ 3 LEDs · botão · comunicação USB FIFO · tempo de reação em ms
✅ 0 erros de timing · 344 slices (17,9% do FPGA)

### O que aprendemos

**Sobre VHDL:**
- Código VHDL descreve hardware paralelo — dois processos rodam simultaneamente
- FSMs são a estrutura central do design digital síncrono
- O UCF é tão crítico quanto o VHDL — pino errado = sem saída de sinal

**Sobre ferramentas:**
- ISE 14.7 · OpenOCD · xc3sprog · iMPACT: cada um tem papel específico
- Gravação volátil (SRAM) e permanente (Flash) têm fluxos completamente diferentes

**Sobre processo:**
- Ler datasheet e esquemático **antes** de codificar economiza horas de debug
- Verificar IDCODE dos chips na cadeia JTAG antes de gerar SVF

---

*Nexus Sistemas Embarcados — Junho de 2026*
*Repositório: `f:/Projetos/fpga-systems-lab/`*
