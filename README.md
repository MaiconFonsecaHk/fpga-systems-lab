# FPGA Reflex Game

Jogo de reflexo em FPGA com monitor serial USB.  
Plataforma: **Bionexus TX-LED R27 / Xilinx Spartan-3 XC3S200-4TQG144**

---

## Inicio Rapido

### Linux

```bash
cd toolkit/
bash iniciar.sh          # configura drivers udev + abre o painel
```

### Windows

```cmd
cd toolkit\
run.bat                  # verifica dependencias + abre o painel
```

No painel:

1. **Verificar ambiente** — confirma Python, OpenOCD e arquivos
2. **Detectar USB/FTDI** — confirma que a placa esta conectada
3. **Escanear JTAG** — verifica a cadeia JTAG (FPGA + Flash)
4. **Gravar na Flash** — grava o firmware permanente (persiste apos desligar)
5. Aba **Monitor do Jogo** → selecionar porta → **Conectar**
6. Jogar (ver Regras do Jogo abaixo)

---

## Estrutura do Repositorio

```
fpga-systems-lab/
├── README.md                        <- este arquivo
├── .gitignore
│
├── doc/
│   ├── 00_requisitos.md             <- O QUE INSTALAR (Python, OpenOCD, ISE, drivers)
│   ├── 01_placa_e_pinos.md          <- pinos FPGA, Bank 6, cadeia JTAG
│   ├── 02_comunicacao_serial.md     <- protocolo FIFO 245, mensagens enviadas
│   ├── 03_sintetizando_o_firmware.md <- como o .bit e gerado (XST→BitGen)
│   ├── 04_setup_linux.md            <- instalacao e drivers no Linux
│   ├── 05_setup_windows.md          <- instalacao e drivers no Windows
│   ├── 06_openocd_e_gravacao.md     <- O QUE E O OPENOCD, JTAG, gravar.cfg, SVF
│   └── esquematico_R27_FPGA.png     <- esquematico da placa
│
├── firmware/                        <- codigo-fonte VHDL
│   ├── reflex_game.vhd              <- logica principal (EDITAR AQUI)
│   ├── reflex_game.ucf              <- mapeamento de pinos (EDITAR AQUI)
│   ├── reflex_game.xst              <- opcoes do sintetizador XST
│   ├── reflex_game.prj              <- lista de arquivos VHDL
│   ├── reflex_game.ut               <- opcoes do BitGen
│   ├── build.sh                     <- script de sintese (Linux)
│   └── build.bat                    <- script de sintese (Windows)
│
└── toolkit/                         <- aplicacao de gravacao e monitor
    ├── fpga_panel.py                <- interface grafica principal
    ├── gravar.cfg                   <- configuracao OpenOCD
    ├── reflex_game.bit              <- bitstream pre-compilado
    ├── requirements.txt             <- dependencias Python
    ├── iniciar.sh                   <- launcher Linux (setup + painel)
    ├── run.bat                      <- launcher Windows
    └── logs/                        <- logs gerados automaticamente
```

---

## Regras do Jogo

1. **LED D6 acende** → pressione o botao para iniciar a rodada
2. **Espere** na tela escura (delay aleatorio de 1 a 5 segundos)
3. **LED D5 acende** → pressione o botao o mais rapido possivel
4. Resultado (aparece no monitor serial e nos LEDs):
   - `RESULT_MS=NNNN` — tempo de reacao em milissegundos
   - `EARLY` — pressionou antes do LED D5 acender
   - `TIMEOUT` — nao pressionou dentro de 9999 ms

---

## Comunicacao Serial

O FPGA envia dados via **FT2232H Canal B** em modo **FIFO 245 Assíncrono**
(protocolo paralelo de 8 bits, nao UART serial convencional).

O PC le os dados como porta serial normal:

| Sistema | Porta JTAG    | Porta do Jogo |
|---------|---------------|---------------|
| Linux   | /dev/ttyUSB0  | /dev/ttyUSB1  |
| Windows | COM3 (exemplo)| COM4 (exemplo)|

Baudrate: 115200 (o FT2232H ignora o baudrate no modo FIFO — qualquer valor funciona).

---

## Modificando os Pinos (Recompilacao)

Se precisar testar um mapeamento diferente de pinos:

1. Abrir painel → aba **Configuracao de Pinos**
2. Selecionar um **preset** ou ajustar os pinos manualmente
3. Clicar **Recompilar + Gravar Flash**

O painel gera automaticamente o novo `.vhd` e `.ucf`, executa o
`build.bat` (Windows) ou `build.sh` (Linux) e grava o novo bitstream na placa.

Requer ISE 14.7 instalado. Ver `doc/03_sintetizando_o_firmware.md`.

---

## Pinos Confirmados (esquematico R27_FPGA.png)

| Sinal       | Pino FPGA | FT2232H |
|-------------|-----------|---------|
| usb_d[0]    | P31       | BDBUS0  |
| usb_d[1]    | P30       | BDBUS1  |
| usb_d[2]    | P27       | BDBUS2  |
| usb_d[3]    | P28       | BDBUS3  |
| usb_d[4]    | P32       | BDBUS4  |
| usb_d[5]    | P33       | BDBUS5  |
| usb_d[6]    | P36       | BDBUS6  |
| usb_d[7]    | P35       | BDBUS7  |
| usb_wr (WR#)| P21       | BCBUS3  |
| usb_txe(TXE#)| P26      | BCBUS1  |
| led_reflexo | P51       | —       |
| led_status  | P50       | —       |
| led_erro    | P47       | —       |
| btn         | P56       | —       |
| clk (40MHz) | P53       | —       |

> **P29 = GND e P34 = VCCO_6 — nunca usar como I/O!**

---

## Dependencias

```
Python 3.9+            (obrigatorio — roda o painel)
pyserial >= 3.5        (opcional — monitor serial)
OpenOCD >= 0.11        (obrigatorio — gravacao na placa)
libusbK / libusb       (obrigatorio — driver USB para o OpenOCD)
Xilinx ISE 14.7        (apenas se recompilar o firmware)
Licenca ISE (gratuita) (apenas se recompilar o firmware)
```

Ver `doc/00_requisitos.md` para instrucoes de instalacao completas.
Ver `doc/06_openocd_e_gravacao.md` para entender o que e o OpenOCD e como funciona.

---

## Projeto Academico

Prof. Emiliano Amarante Veiga  
Disciplina de Sistemas Digitais / Arquitetura de Computadores
