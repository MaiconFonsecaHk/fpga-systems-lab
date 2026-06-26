# Roteiro da Apresentação
## Jogo de Reflexo em FPGA — Expande Tech
### Linguagem de Descrição de Hardware · Junho 2026

---

> **Duração total:** ~15 minutos
> **Distribuição:**
> - **Felipe** → Slides 1, 2, 3, 4 · empresa + contexto + placa + solução (~4 min)
> - **Paulo Henrique** → Slides 5, 6, 7, 8 · pinagem + arquitetura VHDL + FSM + LFSR (~4 min)
> - **Maicon** → Slides 9, 10, 11, 12, 14 · FIFO + BCD + síntese + gravação flash + testes (~5 min)
> - **William** → Slide 13 · problemas encontrados e soluções (~2 min)
> - **Felipe** → Slide 15 · conclusão (~1 min)

---

---

# PARTE 1 — FELIPE

---

## SLIDE 1 · Capa
**Quem fala:** Felipe
**Tempo:** ~30 segundos

### O que este slide é
A capa da apresentação com o nome do projeto, empresa fictícia e equipe.

### O que dizer
> "Boa tarde a todos. Somos a **Expande Tech** e vamos apresentar nosso projeto final da disciplina de Linguagem de Descrição de Hardware. O projeto é um **Jogo de Reflexo implementado em FPGA**, rodando na placa **Bionexus TX-LED R27** com um chip **Spartan-3 da Xilinx**. Nossa equipe é composta por Felipe, Maicon, Paulo Henrique e Willian Colleti."

---

## SLIDE 2 · Desafio Recebido
**Quem fala:** Felipe
**Tempo:** ~1 minuto

### O que este slide é
Explica o que o professor pediu e o que a equipe entregou.

### O que este slide contém
- **Caixa azul (esquerda):** A proposta do professor — implementar um projeto digital em VHDL com gravação permanente via USB e envio de resultados ao PC.
- **Lista de entregáveis:** O que fizemos: código VHDL base (pisca LED), projeto principal (jogo de reflexo), documento técnico e estes slides.
- **Tabela direita:** Especificações do hardware que o professor forneceu.

### O que dizer
> "O desafio proposto pelo professor foi implementar um projeto digital completo em VHDL para a placa FPGA que nos foi fornecida. O hardware é a placa **Bionexus TX-LED R27**, alimentada com **16 volts DC**, com no máximo **500 mA**. A placa usa um chip USB chamado **FT2232H** que permite tanto gravar o firmware quanto comunicar o resultado do jogo com o PC — tudo pela mesma entrada USB."

> "Os entregáveis eram: um código VHDL de exemplo simples, que é o pisca LED, e um projeto principal. Nosso projeto principal é o **Jogo de Reflexo**: o jogador aperta um botão, espera um LED acender em momento aleatório, e aperta o botão de novo o mais rápido possível. O sistema mede e envia o tempo de reação em milissegundos ao computador."

---

## SLIDE 3 · A Placa: Bionexus TX-LED R27
**Quem fala:** Felipe
**Tempo:** ~1 minuto

### O que este slide é
Apresenta a placa física que usamos com diagrama de blocos e tabela de especificações.

### O que o diagrama mostra
```
[PC com USB]
     ↓
[FT2232H — chip conversor USB]
     ├── Canal A → JTAG → grava o firmware no FPGA e na Flash
     └── Canal B → FIFO → comunica o resultado do jogo ao PC
                              ↓
                         [XC3S200 — o FPGA]
                              ├── P51 → LED D5 (sinal de reação)
                              ├── P50 → LED D6 (idle / ok)
                              ├── P47 → LED D7 (erro)
                              └── P56 ← botão do jogador
                              ↕
                         [XCF01S — memória Flash]
                         guarda o firmware permanentemente
```

### O que dizer
> "Esta é a placa que usamos. O coração dela é o **FPGA XC3S200**, que é o chip que programamos em VHDL. Ele tem 200 mil portas lógicas equivalentes, mas no nosso projeto usamos apenas 17% disso."

> "A placa tem um chip chamado **FT2232H** que faz a ponte entre o USB do PC e o FPGA. Ele tem dois canais: um para gravar o código no chip via protocolo JTAG, e outro para o FPGA mandar os resultados do jogo de volta ao PC."

> "Também há uma **memória Flash XCF01S** de 1 megabit. Quando gravamos o firmware nela, o FPGA carrega o jogo automaticamente toda vez que a placa é ligada — sem precisar de computador."

---

## SLIDE 4 · Requisitos do Jogo
**Quem fala:** Felipe
**Tempo:** ~1 minuto

### O que este slide é
Explica como o jogo funciona e lista os requisitos que o sistema atende.

### O que o fluxo visual mostra
Seis caixas em sequência mostrando uma partida completa:
1. **Ligar a placa** → D6 aceso (aguardando)
2. **Pressionar botão** → inicia o jogo
3. **Espera aleatória 1–5 s** → jogador não sabe quando vai acender
4. **D5 ACENDE** → hora de reagir!
5. **Botão pressionado** → mede o tempo em ms
6. **Resultado no PC** → `RESULT_MS=0342` aparece no monitor serial

### O que a tabela mostra
Os 7 requisitos funcionais que o sistema implementa (D6 idle, D5 aleatório, medição em ms, EARLY, TIMEOUT, comunicação USB, Flash permanente).

### O que dizer
> "O jogo funciona assim: quando a placa liga, o LED D6 fica aceso indicando que está pronto. O jogador pressiona o botão e o sistema começa a contar um tempo aleatório — entre 1 e 5 segundos. Em um momento imprevisível, o LED D5 acende. O jogador deve pressionar o botão o mais rápido possível."

> "Se apertar antes do D5 acender, o LED D7 acende em vermelho — isso é o estado EARLY, ou seja, foi cedo demais. Se não reagir em 10 segundos, também é D7 — TIMEOUT. Quando a reação é válida, o sistema manda ao PC uma mensagem como `RESULT_MS=0342`, que significa 342 milissegundos de tempo de reação."

> "Agora o Paulo Henrique vai explicar como isso foi implementado em VHDL."

---

---

# PARTE 2 — PAULO HENRIQUE

---

## SLIDE 5 · Pinagem Utilizada
**Quem fala:** Paulo Henrique
**Tempo:** ~1 minuto

### O que este slide é
O mapeamento de cada sinal do código VHDL para um pino físico da placa.

### O que é um pino de FPGA
Um FPGA tem centenas de pinos físicos numerados (P47, P50, P51...). Cada um pode ser configurado como entrada ou saída. O arquivo UCF (User Constraints File) diz ao ISE qual pino do chip corresponde a qual variável do código VHDL.

### Tabelas do slide
**Sinais do jogo:**
| Sinal no VHDL | Pino | Função |
|---|---|---|
| `clk` | P53 | Clock de 40 MHz — o coração do sistema |
| `btn` | P56 | Botão do jogador |
| `led_reflexo` | P51 | LED D5 — hora de reagir |
| `led_status` | P50 | LED D6 — idle / ok |
| `led_erro` | P47 | LED D7 — erro |

**Interface FIFO (comunicação USB):**
Os pinos P27, P28, P30, P31, P32, P33, P35, P36 formam um barramento de 8 bits. P21 é o sinal de escrita (WR#) e P26 é o sinal que diz se pode escrever (TXE#).

### Armadilha que descobrimos (caixa vermelha)
**P29 = GND** (terra) e **P34 = VCCO_6** (alimentação) — estes não são pinos de I/O. Tentamos usá-los como pinos do barramento FIFO e o ISE rejeitou na hora de fazer o roteamento. Descobrimos olhando o "PAD report" gerado pelo ISE.

### O que dizer
> "Antes de escrever qualquer linha de VHDL, precisamos saber quais pinos físicos da placa estão conectados a cada coisa. No arquivo **UCF** — que é o arquivo de constraints — dizemos ao ISE coisas como: 'o sinal `btn` do meu código deve entrar pelo pino P56 com tensão de 3,3 volts'."

> "O clock principal é o P53 — 40 megahertz. Os três LEDs são P51, P50 e P47. O botão é P56."

> "Para a comunicação com o PC, usamos 10 pinos do **Bank 6**: 8 para dados em paralelo, 1 para o sinal de escrita e 1 para verificar se pode escrever. Uma coisa que descobrimos na prática: os pinos **P29 e P34 não são pinos de I/O** — são pinos de terra e alimentação. Tentamos usá-los e o ISE deu erro. A solução foi usar P27 e P36 no lugar deles."

---

## SLIDE 6 · Arquitetura VHDL: Dois Processos Paralelos
**Quem fala:** Paulo Henrique
**Tempo:** ~1 minuto

### O que este slide é — explicação detalhada

Este é um dos slides mais importantes. Ele mostra **como o código VHDL está organizado internamente**.

#### A diferença fundamental entre VHDL e programação normal
Em um programa normal (Python, C, Java), as instruções executam **uma de cada vez**, em sequência:
```
instrução 1 → instrução 2 → instrução 3 → ...
```

Em VHDL, você está **descrevendo hardware**. O FPGA coloca circuitos físicos no chip. Dois circuitos diferentes funcionam **ao mesmo tempo, em paralelo**, assim como dois motores num carro funcionam juntos.

#### O que o slide mostra
**Caixa azul clara — `entity reflex_game`:** É o módulo principal, com os pinos de entrada e saída listados.

**Caixa azul escura dentro — `game_proc`:** É o primeiro processo (circuito). Ele cuida de:
- **FSM do jogo (7 estados):** A máquina de estados — o "cérebro" do jogo, controla quando o LED acende, quando conta o tempo, etc.
- **Debounce + sincronizador 2-FF:** Filtra o ruído elétrico do botão mecânico
- **LFSR 16 bits:** Gera os intervalos aleatórios de espera
- **Divisor de ms + conversão BCD:** Conta o tempo em milissegundos e converte para texto

**Caixa verde dentro — `fifo_proc`:** É o segundo processo (outro circuito). Ele cuida de:
- **FIFO TX 245 (5 estados):** Controla o envio de bytes ao PC pelo barramento paralelo
- Aguarda o sinal `uart_trigger='1'` do game_proc para começar a enviar
- Envia byte a byte com o pulso elétrico correto no WR#

**Direita — Entradas e Saídas:** Mostra os pinos de entrada (clk, btn, usb_txe) e saída (os LEDs e o barramento FIFO).

**Caixa laranja — "Paralelismo real no FPGA":** Destaca que `game_proc` e `fifo_proc` **executam ao mesmo tempo**. Enquanto o game_proc está contando o tempo de reação, o fifo_proc pode estar enviando o resultado anterior ao PC. Em software, você teria que fazer isso com threads. No FPGA, é hardware paralelo — não tem custo extra.

### O que dizer
> "Nosso código VHDL tem um único módulo chamado `reflex_game`, que tem dois circuitos internos — chamamos de processos — rodando **em paralelo ao mesmo tempo**."

> "O primeiro, o `game_proc`, é o cérebro do jogo. Ele controla os LEDs, lê o botão, conta o tempo de reação e monta a mensagem de resultado para enviar ao PC."

> "O segundo, o `fifo_proc`, é o circuito de comunicação. Ele pega a mensagem pronta do `game_proc` e envia byte a byte para o PC pelo barramento USB."

> "A diferença fundamental para programação é que **os dois funcionam ao mesmo tempo**. O `game_proc` pode estar medindo uma nova reação enquanto o `fifo_proc` ainda está mandando o resultado da jogada anterior. Em VHDL, isso é natural — em software você precisaria de threads."

---

## SLIDE 7 · Máquina de Estados do Jogo (FSM)
**Quem fala:** Paulo Henrique
**Tempo:** ~1 minuto

### O que este slide é
O diagrama de estados do jogo — a lógica central do `game_proc`.

### O que é uma FSM (Finite State Machine)
Uma FSM é como um mapa de situações. O sistema sempre está em **um** estado por vez. Quando algo acontece (um botão é pressionado, um tempo expira), ele passa para outro estado. É a forma padrão de descrever comportamento sequencial em hardware digital.

### Os 7 estados e o que cada um faz
| Estado | Situação | LEDs |
|--------|----------|------|
| `IDLE` | Aguardando o jogador pressionar o botão | D6 aceso |
| `WAIT_RELEASE` | Botão ainda pressionado — aguarda soltar | Apagados |
| `WAIT_RANDOM` | Contando o tempo aleatório | Apagados |
| `LED_ON` | D5 aceso — contando o tempo de reação | D5 aceso |
| `RESULT_OK` | Jogador reagiu a tempo — mostra resultado 3 s | D5 + D6 |
| `EARLY_PRESS` | Pressionou antes do LED — erro | D7 aceso |
| `TIMEOUT` | Não reagiu em 9,999 s — timeout | D7 aceso |

### Como ler o diagrama
- Setas com texto = o que provoca a transição
- Depois de `RESULT_OK`, `EARLY_PRESS` ou `TIMEOUT`: espera 3 segundos e volta ao `IDLE`
- De `WAIT_RANDOM`: se o botão for pressionado antes do tempo → `EARLY_PRESS`; se o tempo expirar → `LED_ON`

### O que dizer
> "Esta é a máquina de estados do jogo — a FSM. O sistema sempre está em um dos 7 estados. Cada estado determina o que os LEDs mostram e o que o sistema aceita como evento."

> "Começa em **IDLE** com D6 aceso. Quando o jogador pressiona o botão, vai para **WAIT_RELEASE** — esperando soltar — e depois para **WAIT_RANDOM**, onde conta um tempo aleatório de 1 a 5 segundos."

> "Quando esse tempo acaba, entra em **LED_ON** e D5 acende. Se o jogador pressionar agora, vai para **RESULT_OK** e o sistema manda o tempo ao PC. Se pressionar antes — **EARLY_PRESS**, D7. Se não pressionar em 9,999 segundos — **TIMEOUT**, também D7."

> "Depois de 3 segundos em qualquer estado de resultado, volta ao início: **IDLE**."

---

## SLIDE 8 · Aleatoriedade: LFSR de 16 Bits
**Quem fala:** Paulo Henrique
**Tempo:** ~1 minuto

### O que este slide é
Explica como o sistema gera o intervalo aleatório de espera.

### Por que precisamos de aleatoriedade
Se o tempo de espera fosse sempre o mesmo (ex: 2 segundos), o jogador memorizaria em 2 rodadas e poderia antecipar o LED. O jogo perderia o sentido.

### O que é um LFSR (Linear Feedback Shift Register)
É um registrador de deslocamento com realimentação. Imagine 16 flip-flops em fila. A cada ciclo de clock (40 milhões de vezes por segundo), um novo bit entra no início e todos os outros se deslocam. O novo bit é calculado fazendo XOR de alguns bits específicos — chamados de "taps". O resultado é uma sequência de 65.535 valores diferentes antes de se repetir.

**Vantagem:** É implementado em hardware simples (flip-flops + portas XOR). Custo zero de lógica extra — o LFSR avança sozinho todo ciclo de clock mesmo quando não está sendo usado.

### Como o intervalo é gerado
No momento exato em que o botão é pressionado, capturamos os 12 bits menos significativos do LFSR. Como o LFSR avançou 40 milhões de vezes desde o último clique, esse valor é essencialmente imprevisível. Somamos com 1000:

```
delay = 1000 ms + lfsr[11:0]   →   1000 ms até 5095 ms
```

### Os quadradinhos no slide
Os 16 quadradinhos mostram os bits do LFSR. Os em **azul escuro** são os taps — os bits 15, 13, 12 e 10 (contando do MSB). São esses que fazem o XOR para gerar o próximo bit.

### O que dizer
> "Para o intervalo ser imprevisível, usamos um **LFSR de 16 bits** — um Linear Feedback Shift Register. Em vez de um número aleatório verdadeiro, ele gera uma sequência pseudoaleatória com **65.535 valores diferentes** antes de repetir."

> "Ele avança automaticamente 40 milhões de vezes por segundo, o tempo todo, mesmo quando o jogo está esperando. Quando o jogador aperta o botão, capturamos 12 bits do LFSR naquele instante exato. Como ele avançou bilhões de vezes desde o último clique, o valor é imprevisível."

> "Somamos esse valor com 1000 milissegundos, o que nos dá um intervalo entre **1 segundo e 5 segundos**. Agora o Maicon vai explicar como o sistema comunica o resultado ao PC e como gravamos o firmware."

---

---

# PARTE 3 — MAICON

---

## SLIDE 9 · Comunicação com o PC: FIFO 245 Assíncrono
**Quem fala:** Maicon
**Tempo:** ~1 minuto

### O que este slide é
Explica como o FPGA envia o tempo de reação ao PC através do USB.

### O erro que cometemos — e o que descobrimos
A nossa primeira suposição foi que o Canal B do FT2232H funcionaria como uma **porta UART serial** — um fio TX e um RX, como um Arduino. Tentamos usar o pino P28, P30, P29 e até P93 como `uart_tx`. Zero bytes chegavam ao PC.

Depois de ler o esquemático da placa com cuidado, descobrimos que o Canal B **não é UART**. Ele expõe um **barramento paralelo de 8 bits** — 8 fios de dados ao mesmo tempo — com dois sinais de controle: `WR#` (write strobe) e `TXE#` (TX FIFO not full). Isso é o protocolo **Async FIFO 245**.

### Como funciona o FIFO 245 (protocolo)
1. O FPGA verifica se `TXE#` está em '0' (significa: "FIFO não está cheia, pode escrever")
2. Coloca o byte nos 8 fios de dados (D0–D7)
3. Pulsa o sinal `WR#` para nível baixo ('0') por pelo menos **50 nanosegundos** (2 ciclos do clock de 40 MHz)
4. Solta o `WR#` de volta para '1'
5. Repete para o próximo byte

### A FSM `fifo_proc` — 5 estados
```
FTX_IDLE   → aguarda uart_trigger='1' (game_proc pede envio)
FTX_CHECK  → verifica TXE#='0' (pode escrever?)
FTX_STROBE → coloca byte no barramento, ativa WR#='0'
FTX_WAIT   → mantém WR# baixo por 2 ciclos (50 ns)
FTX_NEXT   → avança para próximo byte ou encerra
```

### Mensagens enviadas ao PC
- Reação válida: `RESULT_MS=0342\r\n` (16 bytes)
- Antes do LED: `EARLY\r\n` (7 bytes)
- Sem reação: `TIMEOUT\r\n` (9 bytes)

### O que dizer

> "Bom, vou explicar um pouco de como o FPGA envia o tempo de reação ao PC através da USB. Basicamente a nossa primeira suposição foi que o Canal B do FT2232H funcionaria como uma UART serial qualquer, tipo um Arduino ou um ESP — aí tentamos usar o pino 28, 30, 29 e até o 93 como `uart_tx`, só que vinham zero bytes pro PC."

> "Aí resolvi dar uma lida na esquemática da placa e descobri que o Canal B não é UART. Ele expõe um barramento paralelo de 8 bits — que são 8 fios de dados ao mesmo tempo — com dois sinais de controle: o Write Strobe e o TX FIFO Not Full, o `WR#` e o `TXE#`. Pesquisando um pouco, descobri que isso é o protocolo **Async FIFO 245**."

> "Como funciona? Basicamente o FPGA verifica se o TXE tá em zero, o que significa que a TX FIFO não tá cheia e dá pra escrever. Aí coloca o byte nos 8 fios de dados D0 a D7, pulsa o WR pra nível baixo por pelo menos 50 nanosegundos — que seriam 2 ciclos do clock de 40 MHz — aí solta o WR de volta pra nível alto e repete pro próximo byte."

> "Então basicamente é: verificar se posso escrever, colocar o byte nos 8 fios, pulsar o WR e avançar pro próximo byte. Implementei isso com uma máquina de estados de 5 estados no processo `fifo_proc`: o `FTX_IDLE` que aguarda o trigger, o `FTX_CHECK` que verifica se pode escrever pelo TXE, o `FTX_STROBE` que coloca o byte no barramento e ativa o WR, o `FTX_WAIT` que mantém o WR baixo por 2 ciclos, e o `FTX_NEXT` que avança pro próximo byte ou encerra caso seja o byte final."

> "E as mensagens que chegam ao PC são texto ASCII: antes do LED chega `EARLY` com 7 bytes, sem reação chega `TIMEOUT` com 9 bytes, e quando a reação é válida chega `RESULT_MS=0342` com 16 bytes."

---

## SLIDE 10 · Conversão BCD e Timing Violation
**Quem fala:** Maicon
**Tempo:** ~1 minuto

### O que este slide é
Explica um problema técnico específico: como converter o número 342 em texto `"0342"` dentro do FPGA — e o problema de timing que isso causou.

### Por que não usar divisão
Em VHDL para o XST da Xilinx, divisão de inteiros por variáveis não é suportada em hardware. `342 / 100 = 3` parece simples, mas implementar um divisor de hardware é caro (muitas LUTs). A solução usada é **subtrações sucessivas** — equivalente ao que seu cérebro faz ao decompor 342 manualmente.

### O processo BCD
```
342 >= 300? Sim → d2 = 3, resto = 42
42  >= 40?  Sim → d1 = 4, resto = 2
2   >= 2?   Sim → d0 = 2, resto = 0
d3 = 0 (milhares)

Converte para ASCII somando 48 ('0' = 48 em ASCII):
d3+48 = '0', d2+48 = '3', d1+48 = '4', d0+48 = '2'
Resultado: string "0342"
```

O código tem 10 ramos `if/elsif` para cada casa decimal — somando 4 casas = 40 comparações = **24 andares de lógica combinacional**.

### O timing violation
O clock tem período de **25 ns** (40 MHz). O ISE mediu que esse caminho combinacional demora **27,7 ns** — ou seja, o resultado de `reaction_time_ms` → `uart_msg` não fica estável a tempo para o próximo ciclo do clock. O PAR reportou **16 timing errors**.

### A solução: TIG (Timing Ignore)
O comando `TIG` no UCF diz ao ISE: "ignore este caminho específico". É seguro neste caso porque:
- O caminho só executa **uma vez por pressão de botão** — nunca em ciclos consecutivos
- O valor de `reaction_time_ms` já está estabilizado quando o botão é pressionado
- Não há risco de metaestabilidade

```ucf
INST "reaction_time_ms_*" TNM = "TG_rms";
INST "uart_msg_*_*"       TNM = "TG_uart_msg";
TIMESPEC "TS_bcd" = FROM "TG_rms" TO "TG_uart_msg" TIG;
```

### O que dizer

> "Agora falando de como o FPGA converte o número 342 em texto, e o problema de timing que isso causou..."

> "Em VHDL pro XST da Xilinx, divisão de inteiros por variáveis não é suportada em hardware. Então implementar um divisor de hardware é caro quando se fala de processamento. A solução que usei foi subtrações sucessivas — tipo: quanto de 1000 cabe em 342? Zero. E de 100? Três vezes. E de 10? Quatro vezes. Resto 2. Logo, 0342."

> "O problema é que o código tem 10 ramos if-else pra cada casa decimal, e são 4 casas — isso gera **24 andares de lógica combinacional**. Imagina um prédio de 24 andares: o sinal entra no térreo e precisa percorrer todos os andares antes de sair com o resultado. Cada andar é uma camada de portas lógicas e cada uma tem um pequeno atraso físico de propagação. Com 24 andares, o ISE mediu que esse caminho demora **27,7 nanossegundos**. Mas o período do clock é de **25 nanossegundos** — o resultado não fica pronto a tempo pro próximo pulso. O PAR reportou 16 timing errors."

> "A solução foi uma constraint **TIG** no arquivo UCF — Timing Ignore. Basicamente digo pro ISE: 'ignora esse caminho específico'. É seguro porque essa conversão só executa uma vez por clique, nunca em dois ciclos de clock seguidos — então o resultado já tá estabilizado quando o FIFO vai buscar."

---

## SLIDE 11 · Fluxo de Síntese ISE 14.7
**Quem fala:** Maicon
**Tempo:** ~1 minuto

### O que este slide é
Explica o processo de transformar o código VHDL num arquivo binário que vai para o chip.

### O que cada ferramenta faz
| Passo | Ferramenta | O que faz |
|-------|-----------|-----------|
| 1 | **XST** | Lê o VHDL e cria uma lista de portas lógicas (E, OU, NOT, flip-flop). É como traduzir português para lógica booleana. |
| 2 | **NGDBuild** | Pega essa lista e aplica o UCF — liga cada sinal ao pino físico correto. |
| 3 | **MAP** | Converte as portas lógicas abstratas para os blocos reais do XC3S200 (LUTs e flip-flops). |
| 4 | **PAR** | Place and Route — **posiciona** cada bloco dentro do chip e **roteia** os fios. Verifica se os sinais chegam no tempo certo (timing analysis). |
| 5 | **BitGen** | Pega o design finalizado e gera o arquivo `.bit` — 128 KB de configuração binária do FPGA. |

### Resultado da síntese do nosso projeto
- **344 slices** de 1.920 disponíveis → 17,9%
- **0 erros de timing** (depois do TIG no UCF)
- O arquivo `reflex_game.bit` tem 130.952 bytes

### O que dizer
> "Para transformar o código VHDL num arquivo que vai para o chip, passamos por **5 etapas no ISE 14.7**."

> "Primeiro o **XST** traduz o VHDL para portas lógicas. Depois o **NGDBuild** aplica o arquivo UCF, ligando os sinais aos pinos físicos. O **MAP** converte essas portas para os blocos reais do FPGA — as LUTs e flip-flops. O **PAR** então posiciona cada bloco fisicamente dentro do chip e roteia os fios, verificando se tudo respeita o timing."

> "Por último o **BitGen** gera o arquivo `.bit` — o bitstream. É esse arquivo binário de 128 KB que configura o FPGA. No final tivemos **0 erros de timing** e usamos apenas 17,9% do chip."

---

## SLIDE 12 · Gravação do Firmware
**Quem fala:** Maicon
**Tempo:** ~1 minuto

### O que este slide é
Explica as duas formas de colocar o firmware no hardware — temporária e permanente.

### Gravação na SRAM (temporário)
O FPGA tem uma SRAM interna que guarda a configuração enquanto tem energia. Ao desligar, perde tudo.

**Via xc3sprog:**
```bash
xc3sprog -c ftdi reflex_game.bit
```
Resultado: ~3 segundos. O LED D6 acende imediatamente.

**Via OpenOCD:**
```bash
openocd -f gravar.cfg -c "init; pld load 0 reflex_game.bit; exit"
```

Usamos isso durante o desenvolvimento para testar rapidamente sem ter que esperar a gravação da Flash.

### Gravação na Flash XCF01S (permanente)
A Platform Flash é uma memória não-volátil separada. Quando a placa liga, ela transmite automaticamente o bitstream para o FPGA via JTAG interno — sem PC, sem cabo USB.

**Via xc3sprog (mais simples):**
```bash
xc3sprog -c ftdi -p 1 reflex_game.bit:w:0:BIT
```

**Via iMPACT + OpenOCD (3 etapas — o que utilizamos):**
1. `promgen` → converte `.bit` para `.mcs` (formato que a Flash XCF01S entende)
2. `iMPACT` → gera um arquivo `.svf` (script que descreve cada operação JTAG necessária: apagar, programar, verificar)
3. `OpenOCD` → executa o `.svf` na placa (~2 minutos)

### A cadeia JTAG
```
TDI → [xc3s200 pos1] → [xcf01s pos2] → TDO
```
O FPGA fica no lado TDI (posição 1 para o iMPACT) e a Flash no lado TDO (posição 2). Trocamos essas posições no começo e o TDO ficava sempre zero.

### O que dizer
> "Depois de gerar o arquivo `.bit`, precisamos colocar o firmware no hardware. Temos duas opções."

> "A primeira é gravar na **SRAM** do FPGA — é temporário, rápido, 3 segundos. Ótimo para testar durante o desenvolvimento. Mas ao desligar a placa, perde."

> "A segunda é gravar na **Platform Flash XCF01S** — permanente. Quando a placa liga, a Flash transmite automaticamente o firmware para o FPGA, sem precisar de computador ou cabo."

> "Usamos o **xc3sprog** que é a ferramenta mais simples: uma linha de comando e está feito. Também testamos o fluxo completo com o iMPACT do ISE mais o OpenOCD — são 3 etapas: gerar o MCS com promgen, gerar o SVF com iMPACT, e executar o SVF com OpenOCD."

---

## TOOLKIT · A Aplicação de Gravação e Monitor
**Quem fala:** Maicon
**Tempo:** ~1 minuto *(se o professor perguntar ou se houver espaço)*

### O que é o toolkit

O toolkit é a ferramenta que a gente usou para **gravar o firmware na placa e monitorar o jogo** — sem precisar abrir o ISE ou digitar comandos no terminal. Ele vive na pasta `toolkit/` do projeto.

### Como funciona por dentro

São quatro peças que trabalham juntas:

**`run.bat` / `iniciar.sh` — a porta de entrada**
São os arquivos que você clica para abrir o programa. Eles fazem apenas uma coisa: preparam o ambiente (no Linux, instalam os drivers USB e configuram permissões; no Windows, verificam se o OpenOCD está instalado) e depois chamam `python fpga_panel.py`. Depois disso, saem de cena. São bootstrappers — só iniciam, não fazem mais nada.

**`fpga_panel.py` — a aplicação inteira**
Aqui é onde tudo acontece. O Python faz os dois papéis:
- **Interface gráfica** → feita com tkinter (a biblioteca de janelas do Python). São as abas, botões, área de log que aparece na tela.
- **Orquestrador** → quando você clica em "Gravar na Flash", o Python monta o comando do OpenOCD e chama `subprocess.Popen()`. Isso abre o OpenOCD como um processo separado. O Python lê a saída do OpenOCD em uma **thread em segundo plano** e vai jogando as linhas na tela em tempo real, sem travar a interface.
- **Monitor serial** → abre a porta USB com pyserial e lê as mensagens `RESULT_MS=`, `EARLY`, `TIMEOUT` do jogo conforme chegam.

**`build.bat` / `build.sh` — scripts de síntese**
São chamados pelo Python (via subprocess) quando você clica em "Recompilar". Eles executam a cadeia completa do ISE: XST → NGDBuild → MAP → PAR → BitGen. O Python apenas exibe a saída na tela conforme vai chegando.

**`gravar.cfg` — configuração do OpenOCD**
Não é código executável. É um arquivo de texto que diz ao OpenOCD qual adaptador usar (FTDI) e como é a cadeia JTAG da placa. O Python passa ele como argumento: `openocd -f gravar.cfg`.

### Diagrama resumido

```
run.bat / iniciar.sh
        ↓ prepara sistema e chama Python
  fpga_panel.py
        │
        ├── subprocess.Popen("openocd -f gravar.cfg ...")  → grava bitstream na placa
        ├── subprocess.Popen("build.bat / build.sh")       → recompila VHDL → .bit
        └── serial.Serial("COM4 / ttyUSB1")                → lê resultados do jogo
```

### O que dizer

> "Bom, pra quem ainda não me conhece eu sou o Maicon, e vou estar apresentando o sisteminha que eu fiz utilizando scripts padrão bat e bash, e Python como back e front."

> "A estrutura é essa: o `run.bat` no Windows e o `iniciar.sh` no Linux são só a porta de entrada — eles configuram o ambiente, instalam o que falta, e chamam o Python. Depois disso saem de cena, o trabalho real é tudo no `fpga_panel.py`."

> "O Python faz os dois papéis ao mesmo tempo. O front é a interface gráfica feita com tkinter — as janelas, abas e botões que você vê. O back é o orquestrador: quando você clica em Gravar na Flash, o Python monta o comando do OpenOCD e dispara ele como um processo separado. Lê a saída em uma thread em segundo plano e vai jogando na tela em tempo real, sem travar a interface."

> "Os scripts `build.bat` e `build.sh` são chamados pelo Python quando você quer recompilar o firmware — eles rodam a cadeia inteira do ISE. E o `gravar.cfg` é um arquivo de configuração que o OpenOCD precisa pra saber como falar com a placa — o Python só passa ele como argumento."

> "Então no fundo é isso: Python no centro controlando tudo, e os processos externos — OpenOCD, ISE, porta serial — sendo orquestrados por ele."

---

## SLIDE 14 · Testes e Evidências
**Quem fala:** Maicon
**Tempo:** ~30 segundos

### O que este slide é
Os resultados dos testes realizados na bancada — o que funcionou e o que ficou pendente.

### O que testar significava no nosso caso
Não tinha simulação disponível no computador — testamos direto na placa física. Cada teste envolvia: gravar o firmware → ligar a placa → apertar o botão → observar os LEDs → comparar com o esperado.

### Resultado dos testes
✅ **Tudo o que testamos com a placa física funcionou:**
- Detecção JTAG (IDs corretos)
- Compilação sem erros de timing
- Gravação na RAM e na Flash
- Todos os estados do jogo (IDLE, D5 aleatório, EARLY, TIMEOUT)
- Persistência após power cycle

⏳ **O que ficou pendente:**
- Receber os bytes no monitor serial (`/dev/ttyUSB1`) — a porta aparecia no sistema, mas o professor levou a placa antes de conseguirmos validar os dados chegando. O firmware foi gravado e o código FIFO compilou sem erros — só não confirmamos com a placa na mão.

### O que dizer
> "Testamos o sistema diretamente na placa física. Todos os comportamentos dos LEDs funcionaram corretamente — IDLE, sinal aleatório, EARLY e TIMEOUT. A gravação permanente na Flash foi confirmada: desligamos a placa, desconectamos o USB e religamos — o D6 acendeu automaticamente."

> "O único ponto que ficou pendente foi confirmar a chegada dos dados no monitor serial, porque o professor levou a placa para casa antes de conseguirmos testar isso. O firmware estava gravado e compilou sem erros — não tivemos tempo de verificar os bytes chegando."

> "Agora o William vai falar sobre os problemas que encontramos no caminho."

---

---

# PARTE 4 — WILLIAM

---

## SLIDE 13 · Problemas Encontrados e Soluções
**Quem fala:** William
**Tempo:** ~2 minutos

### O que este slide é
Os 6 problemas mais críticos dos 56 catalogados durante o projeto. Cada problema tem uma causa real e uma solução concreta.

### Os 6 problemas — explicação detalhada

---

**P40 — FT2232H Canal B é FIFO 245, não UART**

Passamos várias horas tentando pinos diferentes como `uart_tx` (P28, P30, P29, P93). Zero bytes chegavam. O erro foi assumir que o Canal B funcionaria como UART — como um Arduino — sem verificar o esquemático. Quando finalmente lemos o esquemático, vimos que o Canal B tem 8 fios de dados + WR# + TXE# = protocolo FIFO 245 paralelo. Reescrevemos todo o código VHDL de comunicação.

**Lição:** Leia o esquemático antes de qualquer suposição sobre o hardware.

---

**P44 — SVF do iMPACT com 162 bytes → Flash "gravada" mas vazia**

O painel mostrava "FLASH GRAVADA COM SUCESSO" mas o firmware nunca carregava ao ligar. Quando analisamos o SVF gerado pelo iMPACT, ele tinha apenas 162 bytes — quase vazio. Um SVF completo tem mais de 1 MB. A causa: o batch do iMPACT tinha `addDevice -position 2` sem especificar qual chip (`-part xcf01s`). O iMPACT gerava um SVF só com cabeçalho. O código do painel não verificava o tamanho do arquivo gerado.

**Lição:** Sempre validar o tamanho do arquivo gerado antes de usá-lo.

---

**P45 — xcf04s em vez de xcf01s**

Estávamos usando o device errado — `xcf04s` (4 megabits) quando a Flash real é `xcf01s` (1 megabit). O IDCODE da Flash é `0xd5044093`. Cruzamos esse número com os arquivos BSDL do ISE e encontramos que `xcf01s` espera `0x05044093` com máscara — bate. O `xcf04s` espera `0x05046093` — não bate. Além disso, o bitstream do projeto tem 130.952 bytes e a xcf01s tem 131.072 bytes — cabe com apenas 120 bytes de folga.

**Lição:** Nunca assuma o modelo do chip. Confirme pelo IDCODE.

---

**P46 — Cadeia JTAG invertida no batch iMPACT**

O iMPACT numera os dispositivos pela ordem TDO→TDI (o lado da saída para o lado da entrada). Na placa, a ordem física é TDI→FPGA→Flash→TDO. Isso significa que a Flash está no lado TDO = **posição 1 no iMPACT**, e o FPGA está no lado TDI = **posição 2 no iMPACT**. Colocamos invertido no início (Flash=pos2, FPGA=pos1). O SVF gerado tentava programar o FPGA com o arquivo de Flash — o TDO ficava sempre zero.

**Lição:** Posição no iMPACT = ordem TDO→TDI, não TDI→TDO.

---

**P42 — P29=GND e P34=VCCO_6 não são pinos I/O**

Ao escolher pinos para o barramento FIFO no Bank 6, assumimos que qualquer número de pino na faixa certa seria I/O. P29 é pino de GND (terra) e P34 é VCCO_6 (alimentação do Bank 6). O ISE rejeitou o roteamento ao tentar usar esses pinos. Corrigimos para P27 e P36.

**Lição:** Verifique o PAD report do ISE antes de escolher pinos.

---

**P43 — Timing violation no caminho BCD**

A conversão de `reaction_time_ms` para texto ASCII tem 24 andares de lógica combinacional — demora 27,7 ns. O clock é 25 ns. O PAR detectou 16 violações de timing. Solução: constraint TIG no UCF para ignorar esse caminho específico. Seguro porque esse caminho só executa uma vez por clique, não a cada ciclo de clock.

**Lição:** Caminhos combinacionais longos precisam de TIG quando são logicamente seguros de ignorar.

---

### O que dizer
> "Tivemos 56 problemas catalogados. Vou falar dos 6 mais críticos."

> "O maior foi descobrir que o **Canal B do FT2232H não é UART** — é FIFO paralelo de 8 bits. Perdemos horas tentando pinos errados. Só resolvemos quando lemos o esquemático."

> "O segundo foi o **SVF falso do iMPACT** — o arquivo tinha 162 bytes quando deveria ter mais de 1 megabyte. A Flash parecia gravada mas estava vazia. Faltava especificar o chip no batch do iMPACT."

> "Depois tínhamos o **device errado** — xcf04s em vez de xcf01s. Descobrimos comparando o IDCODE da Flash com os arquivos BSDL do ISE."

> "A **cadeia JTAG invertida** fazia o SVF tentar programar o chip errado — corrigimos a ordem TDO→TDI no batch."

> "Os pinos **P29 e P34 não são I/O** — são terra e alimentação. O ISE rejeitou quando tentamos usá-los."

> "Por fim, a **violation de timing no BCD** — 27,7 ns num clock de 25 ns. Resolvemos com uma constraint TIG no UCF."

> "A lição geral: leia o esquemático e o datasheet **antes** de escrever o código. Economiza muitas horas."

---

---

# PARTE 5 — FELIPE (VOLTA)

---

## SLIDE 15 · Conclusão e Aprendizados
**Quem fala:** Felipe
**Tempo:** ~1 minuto

### O que este slide é
Resumo do que foi entregue e o que a equipe aprendeu com o projeto.

### O resultado final
- ✅ Jogo de reflexo funcional
- ✅ Firmware gravado permanentemente na Flash XCF01S
- ✅ Carrega sozinho ao ligar a placa — sem PC, sem USB
- ✅ 3 LEDs, botão, comunicação USB FIFO
- ✅ Tempo de reação medido com resolução de 1 ms
- ✅ 344 slices (17,9% do FPGA), 0 erros de timing

### O que dizer
> "Para fechar: entregamos um jogo de reflexo completamente funcional em FPGA. O firmware está gravado permanentemente na Flash — ligar a placa já inicia o jogo, sem precisar de computador."

> "Aprendemos que VHDL é fundamentalmente diferente de programação: você descreve hardware paralelo, não instruções sequenciais. A FSM é a estrutura central de qualquer projeto digital síncrono."

> "A maior lição prática foi: **leia o esquemático e o datasheet antes de escrever uma linha de código**. Quase todos os nossos 56 problemas vieram de suposições não verificadas sobre o hardware."

> "Obrigado."

---

---

# RESUMO — QUEM FALA O QUÊ

| Slide | Título | Apresentador | Tempo |
|-------|--------|--------------|-------|
| 1 | Capa | **Felipe** | 30 s |
| 2 | Desafio Recebido | **Felipe** | 1 min |
| 3 | A Placa: Bionexus TX-LED R27 | **Felipe** | 1 min |
| 4 | Requisitos do Jogo | **Felipe** | 1 min |
| 5 | Pinagem Utilizada | **Paulo Henrique** | 1 min |
| 6 | Arquitetura VHDL: Dois Processos | **Paulo Henrique** | 1 min |
| 7 | Máquina de Estados (FSM) | **Paulo Henrique** | 1 min |
| 8 | Aleatoriedade: LFSR 16 bits | **Paulo Henrique** | 1 min |
| 9 | Comunicação: FIFO 245 | **Maicon** | 1 min |
| 10 | Conversão BCD e Timing | **Maicon** | 1 min |
| 11 | Fluxo de Síntese ISE 14.7 | **Maicon** | 1 min |
| 12 | Gravação do Firmware (Flash) | **Maicon** | 1 min |
| 13 | Problemas Encontrados | **William** | 2 min |
| 14 | Testes e Evidências | **Maicon** | 30 s |
| 15 | Conclusão e Aprendizados | **Felipe** | 1 min |
| **Total** | | | **~15 min** |

---

# DICAS PARA A APRESENTAÇÃO

- **Não leia os slides.** Os slides são visuais de apoio. Use as falas deste roteiro com suas próprias palavras.
- **Cada apresentador deve estudar os slides dos outros** para entender o contexto completo — as perguntas do professor podem cair em qualquer parte.
- **Transição entre apresentadores:** A última frase de cada parte já passa a palavra para o próximo (ex: PH termina dizendo "Agora o Maicon vai explicar...").
- **Slide 6 — Arquitetura VHDL:** Este é o slide mais difícil de explicar. PH deve praticar a explicação de paralelismo — a ideia de que dois processos rodam ao mesmo tempo no hardware. Use a analogia: "em software você faria com threads; aqui é hardware de verdade rodando junto".
- **Se perguntarem sobre a comunicação serial não testada (slide 14):** Sejam honestos — o firmware estava gravado e o código compilou sem erros, mas não conseguimos confirmar os bytes chegando ao monitor porque a placa foi levada antes de terminar os testes.

---

*Expande Tech — Junho de 2026*
