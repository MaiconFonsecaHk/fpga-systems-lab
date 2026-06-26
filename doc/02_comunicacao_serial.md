# Comunicacao Serial — FT2232H FIFO 245 Assíncrono

## Por que FIFO e nao UART?

O chip FT2232H nesta placa tem o Canal B configurado em modo
**Async FIFO 245**, nao em modo UART serial convencional.

A evidencia esta no esquematico (`R27_FPGA.png`): o Canal B expoe
um barramento de 8 bits (`BDBUS0-7`) mais os sinais de controle
`WR#`, `TXE#` e `RXF#`. Isso e exatamente o protocolo FIFO 245.
Um UART convencional teria apenas `TXD` e `RXD`.

## Protocolo de escrita (FPGA → PC)

```
FPGA                             FT2232H

          ┌─ aguarda TXE# = '0'
          │  (significa: TX FIFO nao esta cheio, pode escrever)
          ▼
Coloca byte em D[7:0]
          │
          ▼
Pulsa WR# = '0' por >= 50 ns
(a 40 MHz: 2 ciclos de clock = 50 ns)
          │
          ▼
Libera WR# = '1'
          │
          └─ repete para o próximo byte
```

## Implementacao VHDL (maquina de estados)

```
FTX_IDLE  ──► uart_trigger='1'? ──► FTX_CHECK
FTX_CHECK ──► usb_txe='0'?      ──► FTX_STROBE   (senao espera)
FTX_STROBE ─► drive WR#='0'     ──► FTX_WAIT
FTX_WAIT  ──► 2 ciclos passaram? ─► FTX_NEXT
FTX_NEXT  ──► mais bytes?        ─► FTX_CHECK / FTX_IDLE
```

## Mensagens enviadas pelo FPGA

Todas as mensagens terminam com `\r\n` (0x0D 0x0A).

| Evento          | Mensagem transmitida   | Bytes | Hex                                      |
|-----------------|------------------------|-------|------------------------------------------|
| Reacao valida   | `RESULT_MS=NNNN\r\n`   | 16    | 52 45 53 55 4C 54 5F 4D 53 3D NN NN NN NN 0D 0A |
| Antes do LED    | `EARLY\r\n`            | 7     | 45 41 52 4C 59 0D 0A                     |
| Sem reacao      | `TIMEOUT\r\n`          | 9     | 54 49 4D 45 4F 55 54 0D 0A               |

Onde `NNNN` sao 4 digitos ASCII do tempo em milissegundos (ex: `0342` = 342 ms).

## Como o PC recebe os dados

O FT2232H aparece no sistema como dois dispositivos seriais:

| Canal | Linux       | Windows | Funcao          |
|-------|-------------|---------|-----------------|
| A     | /dev/ttyUSB0 | COM1   | JTAG (OpenOCD)  |
| B     | /dev/ttyUSB1 | COM2   | Jogo (monitor)  |

O Canal B e lido como porta serial normal. O baudrate configurado
no software e ignorado — o FT2232H tem clock proprio no lado USB.
Use 115200 como valor padrao no monitor serial.

## Presets de pinos FIFO

Se os bytes chegarem mas os caracteres estiverem errados (garbled),
o mapeamento de bits esta incorreto. Tente os presets na ordem:

1. **Padrao (esquematico)** — D0=P31, D1=P30, D2=P27, D3=P28, D4=P32, D5=P33, D6=P36, D7=P35
2. **Sequencial crescente** — D0=P27, D1=P28, D2=P30, D3=P31, D4=P32, D5=P33, D6=P35, D7=P36
3. **Invertido** — D0=P36 (bits na ordem oposta)
4. **Pares L/N alternados** — combinacao de pares diferenciais

Para cada preset: `Configuracao de Pinos` → selecionar preset → `Recompilar + Gravar Flash`.

## Fallback UART Serial

Se o modo FIFO nao funcionar, existe um fallback UART serial 115200 baud 8N1.
Nesse modo o FPGA transmite serialmente por um unico pino.

Desvantagem: o FT2232H Canal B nao e oficialmente em modo UART nessa placa,
entao pode nao funcionar. Tente os pinos P28, P30 ou P27 no modo UART.

Para ativar: `Configuracao de Pinos` → Modo: UART Serial → selecionar pino TX → Recompilar.
