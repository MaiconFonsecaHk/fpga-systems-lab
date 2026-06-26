# Sintetizando o Firmware — Como o .bit e Gerado

## Visao Geral

O arquivo `reflex_game.bit` e o **bitstream binario** que configura
o FPGA. Ele nao e um executavel — e uma sequencia de bits que
programa as LUTs, flip-flops e conexoes internas do XC3S200.

O bitstream e gerado a partir do codigo VHDL pelo ISE 14.7 em 5 passos.

## Fluxo de Sintese

```
reflex_game.vhd          (codigo VHDL — logica do jogo)
reflex_game.xst          (opcoes do sintetizador XST)
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│  [1] XST — Xilinx Synthesis Technology                  │
│  Converte VHDL em netlist de portas logicas              │
│  Saida: reflex_game.ngc                                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼ + reflex_game.ucf (pinos!)
┌─────────────────────────────────────────────────────────┐
│  [2] NGDBuild — Native Generic Database Build           │
│  Traduz o netlist e aplica os constraints de pinos      │
│  Saida: reflex_game.ngd                                  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  [3] MAP — Technology Mapping                           │
│  Mapeia as portas logicas para LUTs e FFs reais do FPGA │
│  Saida: reflex_game_map.ncd + reflex_game.pcf           │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  [4] PAR — Place and Route                              │
│  Posiciona cada celula no chip e roteia os fios         │
│  Saida: reflex_game.ncd (colocado e roteado)            │
│  Verifica timing: deve passar com 0 erros               │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼ + reflex_game.ut (opcoes BitGen)
┌─────────────────────────────────────────────────────────┐
│  [5] BitGen — Bitstream Generation                      │
│  Converte o design roteado em bitstream binario         │
│  Saida: reflex_game.bit (pronto para gravar no FPGA)    │
└─────────────────────────────────────────────────────────┘
```

## O Papel do UCF

O arquivo `reflex_game.ucf` (User Constraints File) e o elo entre
o VHDL e o hardware fisico. Ele diz ao ISE:

- Qual pino fisico do chip corresponde a cada porta VHDL
- O padrao eletrico do pino (LVCMOS33 = 3,3 V)
- Restricoes de timing (period do clock, TIG para paths lentos)

**Exemplo de linha UCF:**
```ucf
NET "usb_d<0>" LOC = "P31" | IOSTANDARD = LVCMOS33;
```
Isso significa: o sinal `usb_d[0]` do VHDL deve sair pelo pino fisico P31
com nivel logico LVCMOS 3,3 V.

**Se voce mudar o UCF e recompilar**, o mesmo codigo VHDL
gera um bitstream diferente com outro mapeamento de pinos.
E exatamente isso que o painel faz ao trocar presets de pinos.

## Constraint TIG (Timing Ignore)

O caminho BCD (conversao de `reaction_time_ms` para digitos ASCII)
tem 24 niveis de logica combinacional — demora 27,7 ns, mas o clock
e 25 ns (40 MHz). Isso seria um erro de timing.

A solucao e uma constraint TIG no UCF:
```ucf
INST "reaction_time_ms_*" TNM = "TG_rms";
INST "uart_msg_*_*"       TNM = "TG_uart_msg";
TIMESPEC "TS_bcd" = FROM "TG_rms" TO "TG_uart_msg" TIG;
```

`TIG` (Timing Ignore) diz ao PAR para ignorar esse caminho especifico.
E seguro porque esse caminho roda apenas uma vez por pressao de botao
(nao no mesmo ciclo do clock).

## Arquivos de Entrada

| Arquivo              | Papel                                           |
|----------------------|-------------------------------------------------|
| `reflex_game.vhd`    | Codigo VHDL — logica do jogo + FIFO TX          |
| `reflex_game.ucf`    | Constraints de pinos e timing                   |
| `reflex_game.xst`    | Opcoes do XST (dispositivo alvo, otimizacao)    |
| `reflex_game.prj`    | Lista de arquivos VHDL para o XST               |
| `reflex_game.ut`     | Opcoes do BitGen (startup clock, pinos nao usados) |

## Executar a Sintese

```bash
cd firmware/
bash build.sh
```

Ou pelo painel: aba **Configuracao de Pinos** → botao **Recompilar**.

O bitstream gerado (`firmware/reflex_game.bit`) e copiado
automaticamente para `toolkit/reflex_game.bit`.

## Requisitos

- Xilinx ISE 14.7 instalado em `/opt/Xilinx/14.7/ISE_DS` (Linux)
  ou `C:\Xilinx\14.7\ISE_DS` (Windows)
- Licenca ISE em `~/Downloads/Xilinx.lic`
  (ou definir `export XILINXD_LICENSE_FILE=/caminho/licenca.lic`)

O ISE 14.7 pode ser obtido gratuitamente no site da AMD/Xilinx
para dispositivos da familia Spartan-3.
