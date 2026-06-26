# Placa e Mapeamento de Pinos

## Identificação da Placa

| Campo          | Valor                             |
|----------------|----------------------------------|
| Nome           | Bionexus TX-LED R27              |
| FPGA           | Xilinx Spartan-3 XC3S200-4TQG144 |
| Encapsulamento | TQG144 (144 pinos QFP)           |
| Clock          | 40 MHz (pino P53)                |
| USB            | FT2232H (Dual Channel USB)       |

## Pinos do Projeto

### Clock

| Sinal VHDL | Pino | Frequência |
|------------|------|------------|
| `clk`      | P53  | 40 MHz     |

### LEDs (saída, ativo alto, resistor 560 Ω)

| Sinal VHDL    | Pino | LED | Significado no jogo              |
|---------------|------|-----|----------------------------------|
| `led_reflexo` | P51  | D5  | Acende: hora de reagir           |
| `led_status`  | P50  | D6  | Acende: idle ou resultado OK     |
| `led_erro`    | P47  | D7  | Acende: cedo demais ou timeout   |

### Botão

| Sinal VHDL | Pino | Conector    | Nível ativo | Debounce |
|------------|------|-------------|-------------|----------|
| `btn`      | P56  | J8 BLE_STS  | Alto        | 20 ms    |

### Canal B do FT2232H — FIFO 245 Assíncrono (Bank 6)

> **P29 = GND e P34 = VCCO_6 — NUNCA usar como I/O!**

| Sinal VHDL  | Pino | FT2232H | Função                           |
|-------------|------|---------|----------------------------------|
| `usb_d[0]`  | P31  | BDBUS0  | Bit 0 (LSB)                      |
| `usb_d[1]`  | P30  | BDBUS1  | Bit 1                            |
| `usb_d[2]`  | P27  | BDBUS2  | Bit 2                            |
| `usb_d[3]`  | P28  | BDBUS3  | Bit 3                            |
| `usb_d[4]`  | P32  | BDBUS4  | Bit 4                            |
| `usb_d[5]`  | P33  | BDBUS5  | Bit 5                            |
| `usb_d[6]`  | P36  | BDBUS6  | Bit 6                            |
| `usb_d[7]`  | P35  | BDBUS7  | Bit 7 (MSB)                      |
| `usb_wr`    | P21  | BCBUS3  | WR# — write strobe (ativo baixo) |
| `usb_txe`   | P26  | BCBUS1  | TXE# — TX FIFO nao cheio         |
| —           | P25  | BCBUS0  | RXF# — RX FIFO nao vazio (n/u)  |

### Bank 6 — pinos I/O validos para uso

```
P20  P21  P23  P25  P26  P27  P28  P30  P31  P32  P33  P35  P36
```

## Cadeia JTAG

```
Host ──► TDI ──► [xc3s200, pos 1] ──► [xcf01s, pos 2] ──► TDO ──► Host
```

- FPGA xc3s200:       IDCODE = `0x01414093`, IR = 6 bits
- Platform Flash xcf01s: IDCODE = `0xd5044093`, IR = 8 bits
- Interface: FT2232H Canal A, VID:PID = `0403:70b1`

## Diagrama de Blocos

```
USB ─── FT2232H Canal A ────────────────────► JTAG (gravacao)
        FT2232H Canal B ────────────────────► usb_d[7:0], usb_wr, usb_txe
                                              (FIFO 245 Assíncrono)
                                                   │
                              ┌────────────────────▼──────────────────┐
                              │         FPGA XC3S200                  │
                  CLK 40MHz ──►  Game FSM + BCD + FIFO TX              │
                              │                                        │
                              │  P51 ──► LED D5 (led_reflexo)          │
                              │  P50 ──► LED D6 (led_status)           │
                              │  P47 ──► LED D7 (led_erro)             │
                              │  P56 ◄── BTN (btn)                     │
                              └────────────────────────────────────────┘
```

## Referencias

- Esquematico: `doc/esquematico_R27_FPGA.png`
- Constraints de pinos: `firmware/reflex_game.ucf`
- Comunicacao serial: `doc/02_comunicacao_serial.md`
