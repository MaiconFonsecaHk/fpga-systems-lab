#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPGA Reflex Game — Painel de Gravação e Monitor
Placa: Bionexus TX-LED R27 / Spartan-3 XC3S200-4TQG144
Autor: Projeto acadêmico — Prof. Emiliano Amarante Veiga

Suporta Linux (/dev/ttyUSBx) e Windows (COMx).
Requer Python 3.9+ e pyserial (opcional — apenas para monitor serial).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import platform
import queue
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path
from tkinter import (
    Tk, StringVar, BooleanVar, IntVar, Text, END, DISABLED, NORMAL,
    filedialog, messagebox, Frame, Label
)
from tkinter import ttk

try:
    import serial
    from serial.tools import list_ports
    SERIAL_AVAILABLE = True
except Exception:
    serial = None
    list_ports = None
    SERIAL_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de identificação
# ─────────────────────────────────────────────────────────────────────────────
APP_NAME    = "FPGA Reflex Game"
APP_VERSION = "2.0"
BOARD_NAME  = "Bionexus TX-LED R27 / XC3S200-4TQG144"
FTDI_VID    = "0403"
FTDI_PID    = "70b1"
EXPECTED_FPGA_ID  = "0x01414093"
EXPECTED_FLASH_ID = "0xd5044093"
XCF_DEVICE  = "xcf01s"

IS_WINDOWS = platform.system().lower() == "windows"
IS_LINUX   = platform.system().lower() == "linux"
IS_MAC     = platform.system().lower() == "darwin"

# ─────────────────────────────────────────────────────────────────────────────
# Caminhos padrão do ISE (Linux e Windows)
# ─────────────────────────────────────────────────────────────────────────────
_KIT_DIR     = Path(__file__).resolve().parent
_FIRMWARE    = _KIT_DIR.parent / "firmware"

ISE_BIN_CANDIDATES: list[Path] = [
    Path("/opt/Xilinx/14.7/ISE_DS/ISE/bin/lin64"),
    Path.home() / "Downloads/Xilinx_ISE_DS_Lin_14.7_1015_1/ISE_DS/ISE/bin/lin64",
    Path("C:/Xilinx/14.7/ISE_DS/ISE/bin/nt64"),
    Path("C:/Xilinx/ISE_DS/ISE/bin/nt64"),
]

DEFAULT_VHDL_PATH    = _FIRMWARE / "reflex_game.vhd"
DEFAULT_UCF_PATH     = _FIRMWARE / "reflex_game.ucf"
DEFAULT_BUILD_SCRIPT = _FIRMWARE / ("build.bat" if IS_WINDOWS else "build.sh")

# ─────────────────────────────────────────────────────────────────────────────
# Pinos Bank 6 válidos — P29=GND e P34=VCCO_6 são INVÁLIDOS!
# ─────────────────────────────────────────────────────────────────────────────
BANK6_IO_PINS = [20, 21, 23, 25, 26, 27, 28, 30, 31, 32, 33, 35, 36]

# Presets confirmados pelo esquemático R27_FPGA.png + PAD report ISE
FIFO_PRESETS: dict[str, dict] = {
    "Padrão (esquemático)": {
        "d": [31, 30, 27, 28, 32, 33, 36, 35],
        "wr": 21, "txe": 26,
        "info": "D0=P31(BDBUS0)…D7=P35(BDBUS7), WR#=P21, TXE#=P26. Confirmado pelo esquemático."
    },
    "Sequencial crescente": {
        "d": [27, 28, 30, 31, 32, 33, 35, 36],
        "wr": 21, "txe": 26,
        "info": "D0=P27, D1=P28, D2=P30, D3=P31, D4=P32, D5=P33, D6=P35, D7=P36."
    },
    "Invertido (D0=P36)": {
        "d": [36, 35, 33, 32, 31, 30, 28, 27],
        "wr": 21, "txe": 26,
        "info": "Bits invertidos. Usar se os caracteres chegarem ao contrário."
    },
    "Pares L/N alternados": {
        "d": [27, 28, 31, 30, 32, 33, 35, 36],
        "wr": 21, "txe": 26,
        "info": "L22P=D0, L22N=D1, L21N=D2, L21P=D3, L20P=D4, L20N=D5, L01P=D6, L01N=D7."
    },
    "TXE em P25 (fallback)": {
        "d": [31, 30, 27, 28, 32, 33, 36, 35],
        "wr": 21, "txe": 25,
        "info": "Igual ao padrão mas TXE# no P25 (IO_L23P_6)."
    },
}

UART_PRESETS = {
    "P28": {"tx": 28, "info": "P28 = IO_L22N_6, área de USB_D1"},
    "P30": {"tx": 30, "info": "P30 = IO_L21P_6"},
    "P27": {"tx": 27, "info": "P27 = IO_L22P_6"},
    "P35": {"tx": 35, "info": "P35 = IO_L01P_6/VRN_6"},
}

CONFIG_FILE = _KIT_DIR / "pin_config.json"
LOG_DIR     = _KIT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Cores para o log
# ─────────────────────────────────────────────────────────────────────────────
LOG_COLORS = {
    "OK":   "#1a6b1a",  # verde escuro
    "ERRO": "#9b1c1c",  # vermelho escuro
    "WARN": "#8a5300",  # âmbar
    "CMD":  "#555577",  # azul-cinza
    "DONE": "#0a4a7f",  # azul escuro
    "INFO": "#333333",  # preto suave
    "FIFO": "#003355",  # azul navy
    "RAW":  "#4a0072",  # roxo
}

# ─────────────────────────────────────────────────────────────────────────────
# Geração de VHDL e UCF
# ─────────────────────────────────────────────────────────────────────────────
_VHDL_FIFO_PORTS = """\
        usb_d   : out STD_LOGIC_VECTOR(7 downto 0);
        usb_wr  : out STD_LOGIC;
        usb_txe : in  STD_LOGIC"""

_VHDL_UART_PORTS = """\
        uart_tx : out STD_LOGIC"""

_VHDL_FIFO_SIGNALS = """\
    type t_ftx_state is (FTX_IDLE, FTX_CHECK, FTX_STROBE, FTX_WAIT, FTX_NEXT);
    signal ftx_state    : t_ftx_state := FTX_IDLE;
    signal ftx_byte_idx : integer range 0 to 15 := 0;
    signal ftx_hold     : integer range 0 to 3  := 0;
    signal usb_d_r      : std_logic_vector(7 downto 0) := (others => '0');
    signal usb_wr_r     : std_logic := '1';
"""

_VHDL_UART_SIGNALS = """\
    constant UART_BIT_TICKS : integer := 347;
    type t_utx_state is (TX_IDLE, TX_START, TX_DATA, TX_STOP);
    signal utx_state    : t_utx_state := TX_IDLE;
    signal utx_clk_cnt  : integer range 0 to 346 := 0;
    signal utx_bit_idx  : integer range 0 to 7 := 0;
    signal utx_byte_idx : integer range 0 to 15 := 0;
    signal utx_data     : std_logic_vector(7 downto 0) := (others => '0');
"""

_VHDL_FIFO_PROC = """\
    fifo_proc: process(clk)
    begin
        if rising_edge(clk) then
            case ftx_state is
                when FTX_IDLE =>
                    usb_wr_r <= '1';
                    if uart_trigger = '1' then
                        ftx_byte_idx <= 0;
                        ftx_state    <= FTX_CHECK;
                    end if;
                when FTX_CHECK =>
                    if usb_txe = '0' then
                        usb_d_r   <= uart_msg(ftx_byte_idx);
                        ftx_state <= FTX_STROBE;
                    end if;
                when FTX_STROBE =>
                    usb_wr_r  <= '0';
                    ftx_hold  <= 0;
                    ftx_state <= FTX_WAIT;
                when FTX_WAIT =>
                    if ftx_hold = 1 then
                        usb_wr_r  <= '1';
                        ftx_state <= FTX_NEXT;
                    else
                        ftx_hold <= ftx_hold + 1;
                    end if;
                when FTX_NEXT =>
                    if ftx_byte_idx + 1 >= uart_msg_len then
                        ftx_state <= FTX_IDLE;
                    else
                        ftx_byte_idx <= ftx_byte_idx + 1;
                        ftx_state    <= FTX_CHECK;
                    end if;
            end case;
        end if;
    end process fifo_proc;

    usb_d  <= usb_d_r;
    usb_wr <= usb_wr_r;

end Behavioral;
"""

_VHDL_UART_PROC = """\
    uart_proc: process(clk)
    begin
        if rising_edge(clk) then
            case utx_state is
                when TX_IDLE =>
                    uart_tx <= '1';
                    if uart_trigger = '1' then
                        utx_byte_idx <= 0;
                        utx_data     <= uart_msg(0);
                        utx_clk_cnt  <= 0;
                        utx_state    <= TX_START;
                    end if;
                when TX_START =>
                    uart_tx <= '0';
                    if utx_clk_cnt = UART_BIT_TICKS-1 then
                        utx_clk_cnt <= 0;
                        utx_bit_idx <= 0;
                        utx_state   <= TX_DATA;
                    else
                        utx_clk_cnt <= utx_clk_cnt + 1;
                    end if;
                when TX_DATA =>
                    uart_tx <= utx_data(utx_bit_idx);
                    if utx_clk_cnt = UART_BIT_TICKS-1 then
                        utx_clk_cnt <= 0;
                        if utx_bit_idx = 7 then
                            utx_state <= TX_STOP;
                        else
                            utx_bit_idx <= utx_bit_idx + 1;
                        end if;
                    else
                        utx_clk_cnt <= utx_clk_cnt + 1;
                    end if;
                when TX_STOP =>
                    uart_tx <= '1';
                    if utx_clk_cnt = UART_BIT_TICKS-1 then
                        utx_clk_cnt <= 0;
                        if utx_byte_idx + 1 >= uart_msg_len then
                            utx_state <= TX_IDLE;
                        else
                            utx_byte_idx <= utx_byte_idx + 1;
                            utx_data     <= uart_msg(utx_byte_idx + 1);
                            utx_state    <= TX_START;
                        end if;
                    else
                        utx_clk_cnt <= utx_clk_cnt + 1;
                    end if;
            end case;
        end if;
    end process uart_proc;

end Behavioral;
"""

_VHDL_BODY = """library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;

entity reflex_game is
    Port (
        clk         : in  STD_LOGIC;
        btn         : in  STD_LOGIC;
        led_reflexo : out STD_LOGIC;
        led_status  : out STD_LOGIC;
        led_erro    : out STD_LOGIC;
{comm_ports}
    );
end reflex_game;

architecture Behavioral of reflex_game is

    constant CLK_FREQ_HZ     : integer := 40000000;
    constant TICK_1MS_COUNT  : integer := 40000;
    constant DEBOUNCE_MS     : integer := 20;
    constant RESULT_HOLD_MS  : integer := 3000;
    constant MIN_WAIT_MS     : integer := 1000;
    constant RANDOM_SPAN_MS  : integer := 4096;
    constant MAX_REACTION_MS : integer := 9999;
    constant BTN_ACTIVE_LEVEL: STD_LOGIC := '1';

{comm_signals}
    type t_game_state is (IDLE, WAIT_RELEASE, WAIT_RANDOM, LED_ON,
                          RESULT_OK, EARLY_PRESS, TIMEOUT);
    signal state : t_game_state := IDLE;

    signal ms_divider        : integer range 0 to TICK_1MS_COUNT-1 := 0;
    signal btn_sync_0        : STD_LOGIC := '0';
    signal btn_sync_1        : STD_LOGIC := '0';
    signal btn_debounced     : STD_LOGIC := '0';
    signal debounce_count    : integer range 0 to DEBOUNCE_MS := 0;
    signal lfsr              : unsigned(15 downto 0) := x"ACE1";
    signal delay_target_ms   : integer range MIN_WAIT_MS to MIN_WAIT_MS+RANDOM_SPAN_MS-1 := 2000;
    signal wait_elapsed_ms   : integer range 0 to MIN_WAIT_MS+RANDOM_SPAN_MS := 0;
    signal reaction_time_ms  : integer range 0 to MAX_REACTION_MS := 0;
    signal hold_ms           : integer range 0 to RESULT_HOLD_MS := 0;

    type t_msg is array (0 to 15) of std_logic_vector(7 downto 0);
    signal uart_msg     : t_msg := (others => x"00");
    signal uart_msg_len : integer range 0 to 16 := 0;
    signal uart_trigger : std_logic := '0';

begin

    game_proc: process(clk)
        variable tick_1ms_now  : STD_LOGIC;
        variable btn_sample    : STD_LOGIC;
        variable btn_rise_now  : STD_LOGIC;
        variable lfsr_feedback : STD_LOGIC;
        variable random_value  : integer;
        variable rms           : integer range 0 to 9999;
        variable d3, d2, d1, d0 : integer range 0 to 9;
    begin
        if rising_edge(clk) then
            tick_1ms_now := '0';
            btn_rise_now := '0';
            uart_trigger <= '0';

            if ms_divider = TICK_1MS_COUNT-1 then
                ms_divider <= 0;
                tick_1ms_now := '1';
            else
                ms_divider <= ms_divider + 1;
            end if;

            btn_sync_0 <= btn;
            btn_sync_1 <= btn_sync_0;

            lfsr_feedback := lfsr(15) xor lfsr(13) xor lfsr(12) xor lfsr(10);
            lfsr <= lfsr(14 downto 0) & lfsr_feedback;

            if tick_1ms_now = '1' then

                if BTN_ACTIVE_LEVEL = '1' then
                    btn_sample := btn_sync_1;
                else
                    btn_sample := not btn_sync_1;
                end if;

                if btn_sample = btn_debounced then
                    debounce_count <= 0;
                else
                    if debounce_count = DEBOUNCE_MS-1 then
                        if btn_sample = '1' and btn_debounced = '0' then
                            btn_rise_now := '1';
                        end if;
                        btn_debounced <= btn_sample;
                        debounce_count <= 0;
                    else
                        debounce_count <= debounce_count + 1;
                    end if;
                end if;

                case state is

                    when IDLE =>
                        wait_elapsed_ms  <= 0;
                        reaction_time_ms <= 0;
                        hold_ms          <= 0;
                        if btn_rise_now = '1' then
                            random_value    := to_integer(lfsr(11 downto 0));
                            delay_target_ms <= MIN_WAIT_MS + random_value;
                            state           <= WAIT_RELEASE;
                        end if;

                    when WAIT_RELEASE =>
                        wait_elapsed_ms  <= 0;
                        reaction_time_ms <= 0;
                        if btn_debounced = '0' then
                            state <= WAIT_RANDOM;
                        end if;

                    when WAIT_RANDOM =>
                        if btn_rise_now = '1' then
                            hold_ms <= 0;
                            uart_msg(0) <= x"45"; uart_msg(1) <= x"41";
                            uart_msg(2) <= x"52"; uart_msg(3) <= x"4C";
                            uart_msg(4) <= x"59"; uart_msg(5) <= x"0D";
                            uart_msg(6) <= x"0A";
                            uart_msg_len <= 7;
                            uart_trigger <= '1';
                            state <= EARLY_PRESS;
                        elsif wait_elapsed_ms >= delay_target_ms then
                            reaction_time_ms <= 0;
                            state <= LED_ON;
                        else
                            wait_elapsed_ms <= wait_elapsed_ms + 1;
                        end if;

                    when LED_ON =>
                        if btn_rise_now = '1' then
                            hold_ms <= 0;
                            rms := reaction_time_ms;
                            if    rms >= 9000 then d3 := 9; rms := rms - 9000;
                            elsif rms >= 8000 then d3 := 8; rms := rms - 8000;
                            elsif rms >= 7000 then d3 := 7; rms := rms - 7000;
                            elsif rms >= 6000 then d3 := 6; rms := rms - 6000;
                            elsif rms >= 5000 then d3 := 5; rms := rms - 5000;
                            elsif rms >= 4000 then d3 := 4; rms := rms - 4000;
                            elsif rms >= 3000 then d3 := 3; rms := rms - 3000;
                            elsif rms >= 2000 then d3 := 2; rms := rms - 2000;
                            elsif rms >= 1000 then d3 := 1; rms := rms - 1000;
                            else d3 := 0; end if;
                            if    rms >= 900 then d2 := 9; rms := rms - 900;
                            elsif rms >= 800 then d2 := 8; rms := rms - 800;
                            elsif rms >= 700 then d2 := 7; rms := rms - 700;
                            elsif rms >= 600 then d2 := 6; rms := rms - 600;
                            elsif rms >= 500 then d2 := 5; rms := rms - 500;
                            elsif rms >= 400 then d2 := 4; rms := rms - 400;
                            elsif rms >= 300 then d2 := 3; rms := rms - 300;
                            elsif rms >= 200 then d2 := 2; rms := rms - 200;
                            elsif rms >= 100 then d2 := 1; rms := rms - 100;
                            else d2 := 0; end if;
                            if    rms >= 90 then d1 := 9; rms := rms - 90;
                            elsif rms >= 80 then d1 := 8; rms := rms - 80;
                            elsif rms >= 70 then d1 := 7; rms := rms - 70;
                            elsif rms >= 60 then d1 := 6; rms := rms - 60;
                            elsif rms >= 50 then d1 := 5; rms := rms - 50;
                            elsif rms >= 40 then d1 := 4; rms := rms - 40;
                            elsif rms >= 30 then d1 := 3; rms := rms - 30;
                            elsif rms >= 20 then d1 := 2; rms := rms - 20;
                            elsif rms >= 10 then d1 := 1; rms := rms - 10;
                            else d1 := 0; end if;
                            d0 := rms;
                            uart_msg(0)  <= x"52"; uart_msg(1)  <= x"45";
                            uart_msg(2)  <= x"53"; uart_msg(3)  <= x"55";
                            uart_msg(4)  <= x"4C"; uart_msg(5)  <= x"54";
                            uart_msg(6)  <= x"5F"; uart_msg(7)  <= x"4D";
                            uart_msg(8)  <= x"53"; uart_msg(9)  <= x"3D";
                            uart_msg(10) <= std_logic_vector(to_unsigned(d3 + 48, 8));
                            uart_msg(11) <= std_logic_vector(to_unsigned(d2 + 48, 8));
                            uart_msg(12) <= std_logic_vector(to_unsigned(d1 + 48, 8));
                            uart_msg(13) <= std_logic_vector(to_unsigned(d0 + 48, 8));
                            uart_msg(14) <= x"0D";
                            uart_msg(15) <= x"0A";
                            uart_msg_len <= 16;
                            uart_trigger <= '1';
                            state <= RESULT_OK;
                        elsif reaction_time_ms >= MAX_REACTION_MS then
                            hold_ms <= 0;
                            uart_msg(0) <= x"54"; uart_msg(1) <= x"49";
                            uart_msg(2) <= x"4D"; uart_msg(3) <= x"45";
                            uart_msg(4) <= x"4F"; uart_msg(5) <= x"55";
                            uart_msg(6) <= x"54"; uart_msg(7) <= x"0D";
                            uart_msg(8) <= x"0A";
                            uart_msg_len <= 9;
                            uart_trigger <= '1';
                            state <= TIMEOUT;
                        else
                            reaction_time_ms <= reaction_time_ms + 1;
                        end if;

                    when RESULT_OK | EARLY_PRESS | TIMEOUT =>
                        if hold_ms >= RESULT_HOLD_MS then
                            hold_ms <= 0;
                            state <= IDLE;
                        else
                            hold_ms <= hold_ms + 1;
                        end if;

                end case;
            end if;
        end if;
    end process game_proc;

    led_reflexo <= '1' when state = LED_ON else
                   '1' when state = RESULT_OK and reaction_time_ms >= 250 else '0';
    led_status  <= '1' when state = IDLE else
                   '1' when state = RESULT_OK else '0';
    led_erro    <= '1' when state = EARLY_PRESS else
                   '1' when state = TIMEOUT else
                   '1' when state = RESULT_OK and reaction_time_ms >= 500 else '0';

"""

_UCF_FIXED = """\
NET "clk"         LOC = "P53" | IOSTANDARD = LVCMOS33;
NET "clk"         TNM_NET = "clk";
TIMESPEC "TS_clk" = PERIOD "clk" 25 ns HIGH 50%;

NET "led_reflexo" LOC = "P51" | IOSTANDARD = LVCMOS33;
NET "led_status"  LOC = "P50" | IOSTANDARD = LVCMOS33;
NET "led_erro"    LOC = "P47" | IOSTANDARD = LVCMOS33;

NET "btn"         LOC = "P56" | IOSTANDARD = LVCMOS33 | PULLDOWN;

INST "reaction_time_ms_*" TNM = "TG_rms";
INST "uart_msg_*_*"       TNM = "TG_uart_msg";
TIMESPEC "TS_bcd"         = FROM "TG_rms" TO "TG_uart_msg" TIG;

"""


def generate_vhdl(mode: str) -> str:
    if mode == "fifo":
        return _VHDL_BODY.format(
            comm_ports=_VHDL_FIFO_PORTS,
            comm_signals=_VHDL_FIFO_SIGNALS,
        ) + _VHDL_FIFO_PROC
    else:
        return _VHDL_BODY.format(
            comm_ports=_VHDL_UART_PORTS,
            comm_signals=_VHDL_UART_SIGNALS,
        ) + _VHDL_UART_PROC


def generate_ucf(mode: str, pin_cfg: dict) -> str:
    lines = [
        "# Reflex Game — FPGA Bionexus TX-LED R27 / XC3S200-4TQG144\n",
        _UCF_FIXED,
    ]
    if mode == "fifo":
        lines.append("# FT2232H Canal B — FIFO 245 Assíncrono (Bank 6)\n")
        for i, p in enumerate(pin_cfg["d"]):
            lines.append(f'NET "usb_d<{i}>" LOC = "P{p}" | IOSTANDARD = LVCMOS33;\n')
        lines.append(f'NET "usb_wr"   LOC = "P{pin_cfg["wr"]}" | IOSTANDARD = LVCMOS33;\n')
        lines.append(f'NET "usb_txe"  LOC = "P{pin_cfg["txe"]}" | IOSTANDARD = LVCMOS33 | PULLDOWN;\n')
    else:
        lines.append(f'# UART TX serial 115200 8N1\n')
        lines.append(f'NET "uart_tx" LOC = "P{pin_cfg.get("tx", 28)}" | IOSTANDARD = LVCMOS33;\n')
    return "".join(lines)


def quote_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/")


def timestamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


# ─────────────────────────────────────────────────────────────────────────────
# Painel principal
# ─────────────────────────────────────────────────────────────────────────────
class FPGAPanel:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(f"{APP_NAME}  v{APP_VERSION}")
        self.root.geometry("1200x860")
        self.root.minsize(1020, 680)

        self.queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.current_process: subprocess.Popen | None = None

        # ── variáveis de configuração ──────────────────────────────────────
        self.openocd_path = StringVar(value=shutil.which("openocd") or "openocd")
        self.cfg_path     = StringVar(value=str((_KIT_DIR / "gravar.cfg").resolve()))
        self.bit_path     = StringVar(value=str((_KIT_DIR / "reflex_game.bit").resolve()))
        self.use_sudo     = BooleanVar(value=IS_LINUX)

        self.serial_port   = StringVar(value="COM3" if IS_WINDOWS else "/dev/ttyUSB1")
        self.serial_baud   = StringVar(value="115200")
        self.serial_stop   = threading.Event()
        self.serial_thread: threading.Thread | None = None
        self.serial_obj    = None
        self._rx_byte_count = 0

        self.comm_mode    = StringVar(value="fifo")
        self.vhdl_path    = StringVar(value=str(DEFAULT_VHDL_PATH))
        self.ucf_path     = StringVar(value=str(DEFAULT_UCF_PATH))
        self.build_script = StringVar(value=str(DEFAULT_BUILD_SCRIPT))

        self._d    = [IntVar(value=v) for v in [31, 30, 27, 28, 32, 33, 36, 35]]
        self._wr   = IntVar(value=21)
        self._txe  = IntVar(value=26)
        self._uart_tx = IntVar(value=28)

        # ── status bar vars ────────────────────────────────────────────────
        self._sb_usb    = StringVar(value="USB: —")
        self._sb_jtag   = StringVar(value="JTAG: —")
        self._sb_serial = StringVar(value="Serial: desconectado")
        self._sb_result = StringVar(value="Resultado: —")
        self._sb_clock  = StringVar(value="")

        self._load_pin_config()
        self._apply_style()
        self._build_ui()
        self._poll_queue()
        self._clock_tick()

        self._log("INFO", f"{APP_NAME} v{APP_VERSION} — {BOARD_NAME}")
        self._log("INFO", f"OS: {platform.platform()} / Python {platform.python_version()}")
        self._log("INFO", f"Pasta toolkit: {_KIT_DIR}")
        if not SERIAL_AVAILABLE:
            self._log("WARN", "pyserial não instalado — monitor serial indisponível (pip install pyserial)")

    # ── estilos ───────────────────────────────────────────────────────────────
    def _apply_style(self):
        style = ttk.Style()
        for theme in ("clam", "alt", "default"):
            if theme in style.theme_names():
                style.theme_use(theme)
                break

        bg = "#f0f2f5"
        self.root.configure(bg=bg)

        style.configure("TFrame",      background=bg)
        style.configure("TLabelframe", background=bg)
        style.configure("TLabelframe.Label", background=bg, font=("Arial", 9, "bold"))
        style.configure("TNotebook",   background=bg, tabmargins=[4, 4, 0, 0])
        style.configure("TNotebook.Tab", padding=[12, 6], font=("Arial", 9, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", "#2c5f8a"), ("!selected", "#dde3ea")],
                  foreground=[("selected", "white"),   ("!selected", "#333333")])
        style.configure("TButton",     padding=[10, 5], font=("Arial", 9))
        style.configure("TLabel",      background=bg, font=("Arial", 9))
        style.configure("TCheckbutton", background=bg)
        style.configure("TRadiobutton", background=bg, font=("Arial", 9))
        style.configure("TEntry",      font=("Arial", 9))
        style.configure("TCombobox",   font=("Arial", 9))

        style.configure("Header.TFrame",  background="#1e3a5f")
        style.configure("Header.TLabel",  background="#1e3a5f", foreground="#ffffff", font=("Arial", 11, "bold"))
        style.configure("Header2.TLabel", background="#1e3a5f", foreground="#adc6e8", font=("Arial", 9))
        style.configure("StatusBar.TFrame", background="#2c3e50")
        style.configure("StatusBar.TLabel", background="#2c3e50", foreground="#ecf0f1", font=("Arial", 8))
        style.configure("StatusOK.TLabel",  background="#2c3e50", foreground="#2ecc71", font=("Arial", 8, "bold"))
        style.configure("StatusBAD.TLabel", background="#2c3e50", foreground="#e74c3c", font=("Arial", 8, "bold"))
        style.configure("BigResult.TLabel", font=("Arial", 42, "bold"), background="#f0f2f5")
        style.configure("Action.TButton",  padding=[14, 7], font=("Arial", 9, "bold"))
        style.configure("Rebuild.TButton", padding=[14, 7], font=("Arial", 9, "bold"),
                        foreground="#1e3a5f")
        style.configure("Green.TButton",   padding=[14, 7], font=("Arial", 9, "bold"))
        style.configure("Danger.TButton",  padding=[14, 7], font=("Arial", 9, "bold"))

    # ── UI principal ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # HEADER
        hdr = ttk.Frame(self.root, style="Header.TFrame")
        hdr.pack(fill="x")
        ttk.Label(hdr, text=f"  {APP_NAME}  v{APP_VERSION}",
                  style="Header.TLabel").pack(side="left", padx=8, pady=8)
        ttk.Label(hdr, text=f"  {BOARD_NAME}",
                  style="Header2.TLabel").pack(side="left", padx=4, pady=8)
        _os_label = "Windows" if IS_WINDOWS else ("Linux" if IS_LINUX else "macOS")
        ttk.Label(hdr, text=f"  {_os_label}  |  FT2232H FIFO 245  |  ISE 14.7  |  Python {platform.python_version()}  ",
                  style="Header2.TLabel").pack(side="right", padx=8, pady=8)

        # NOTEBOOK
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        self._tab_prog   = ttk.Frame(nb)
        self._tab_serial = ttk.Frame(nb)
        self._tab_config = ttk.Frame(nb)
        self._tab_help   = ttk.Frame(nb)

        nb.add(self._tab_prog,   text="  Gravacao  ")
        nb.add(self._tab_serial, text="  Monitor do Jogo  ")
        nb.add(self._tab_config, text="  Configuracao de Pinos  ")
        nb.add(self._tab_help,   text="  Guia  ")

        self._build_program_tab(self._tab_prog)
        self._build_serial_tab(self._tab_serial)
        self._build_config_tab(self._tab_config)
        self._build_help_tab(self._tab_help)

        # STATUS BAR
        sb = ttk.Frame(self.root, style="StatusBar.TFrame")
        sb.pack(fill="x", side="bottom")
        ttk.Label(sb, textvariable=self._sb_usb,    style="StatusBar.TLabel").pack(side="left",  padx=12, pady=3)
        ttk.Label(sb, text="|", style="StatusBar.TLabel").pack(side="left", pady=3)
        ttk.Label(sb, textvariable=self._sb_jtag,   style="StatusBar.TLabel").pack(side="left",  padx=12, pady=3)
        ttk.Label(sb, text="|", style="StatusBar.TLabel").pack(side="left", pady=3)
        ttk.Label(sb, textvariable=self._sb_serial, style="StatusBar.TLabel").pack(side="left",  padx=12, pady=3)
        ttk.Label(sb, text="|", style="StatusBar.TLabel").pack(side="left", pady=3)
        ttk.Label(sb, textvariable=self._sb_result, style="StatusOK.TLabel").pack(side="left",   padx=12, pady=3)
        ttk.Label(sb, textvariable=self._sb_clock,  style="StatusBar.TLabel").pack(side="right", padx=12, pady=3)

    def _clock_tick(self):
        self._sb_clock.set(_dt.datetime.now().strftime("%H:%M:%S"))
        self.root.after(1000, self._clock_tick)

    # ── aba Gravação ──────────────────────────────────────────────────────────
    def _build_program_tab(self, parent):
        # Caminhos
        paths = ttk.LabelFrame(parent, text="Caminhos")
        paths.pack(fill="x", padx=10, pady=(10, 4))
        rows = [
            ("OpenOCD:",    self.openocd_path, self._pick_openocd),
            ("Config .cfg:", self.cfg_path,    self._pick_cfg),
            ("Bitstream:",   self.bit_path,    self._pick_bit),
        ]
        for i, (lbl, var, cmd) in enumerate(rows):
            ttk.Label(paths, text=lbl, width=14, anchor="e").grid(row=i, column=0, padx=(8, 4), pady=4, sticky="e")
            ttk.Entry(paths, textvariable=var).grid(row=i, column=1, padx=4, pady=4, sticky="ew")
            ttk.Button(paths, text="...", command=cmd, width=3).grid(row=i, column=2, padx=(4, 8), pady=4)
        paths.columnconfigure(1, weight=1)
        ttk.Checkbutton(paths, text="Usar sudo -n (Linux — necessário se udev não configurado)",
                        variable=self.use_sudo).grid(row=3, column=1, sticky="w", padx=4, pady=4)

        # Botões de ação
        act = ttk.Frame(parent)
        act.pack(fill="x", padx=10, pady=4)
        btns = [
            ("1. Verificar ambiente", self.check_environment),
            ("2. Detectar USB/FTDI",  self.detect_usb),
            ("3. Escanear JTAG",      self.scan_jtag),
            ("4. Gravar na RAM",      self.program_fpga),
            ("5. Gravar na Flash",    self.program_flash),
            ("Parar",                 self.stop_process),
        ]
        for txt, cmd in btns:
            ttk.Button(act, text=txt, command=cmd, style="Action.TButton").pack(side="left", padx=3)

        ttk.Button(act, text="Abrir logs", command=self._open_logs).pack(side="right", padx=3)

        # Banner de status
        self._prog_banner = StringVar(value="")
        self._banner_lbl = ttk.Label(parent, textvariable=self._prog_banner,
                                     font=("Arial", 16, "bold"), anchor="center")
        self._banner_lbl.pack(fill="x", padx=10, pady=(4, 0))

        # Log
        log_lf = ttk.LabelFrame(parent, text="Log")
        log_lf.pack(fill="both", expand=True, padx=10, pady=8)
        self.log_text = self._make_log_widget(log_lf)

        bot = ttk.Frame(parent)
        bot.pack(fill="x", padx=10, pady=(0, 8))
        ttk.Button(bot, text="Salvar log", command=self._save_log).pack(side="left", padx=3)
        ttk.Button(bot, text="Limpar",     command=lambda: self._clear_widget(self.log_text)).pack(side="left", padx=3)

    # ── aba Monitor ───────────────────────────────────────────────────────────
    def _build_serial_tab(self, parent):
        cfg = ttk.LabelFrame(parent, text="Conexao serial")
        cfg.pack(fill="x", padx=10, pady=(10, 4))

        ttk.Label(cfg, text="Porta:").grid(row=0, column=0, sticky="e", padx=(8, 4), pady=5)
        self.port_combo = ttk.Combobox(cfg, textvariable=self.serial_port,
                                       values=self._list_ports(), width=28)
        self.port_combo.grid(row=0, column=1, sticky="w", padx=4, pady=5)
        ttk.Button(cfg, text="Atualizar", command=self._refresh_ports).grid(row=0, column=2, padx=4)

        ttk.Label(cfg, text="Baudrate:").grid(row=1, column=0, sticky="e", padx=(8, 4), pady=5)
        ttk.Entry(cfg, textvariable=self.serial_baud, width=12).grid(row=1, column=1, sticky="w", padx=4)

        btns = ttk.Frame(cfg)
        btns.grid(row=2, column=1, sticky="w", padx=4, pady=5)
        ttk.Button(btns, text="Conectar",    command=self._connect_serial,    style="Green.TButton").pack(side="left", padx=3)
        ttk.Button(btns, text="Desconectar", command=self._disconnect_serial, style="Danger.TButton").pack(side="left", padx=3)
        ttk.Button(btns, text="Limpar log",  command=lambda: self._clear_widget(self.serial_log_text)).pack(side="left", padx=3)

        note = ("Linux: /dev/ttyUSB1 (Canal B FT2232H).  Windows: COMx — verificar Gerenciador de Dispositivos."
                "  Baudrate é ignorado internamente pelo FIFO; use 115200 como padrão.")
        ttk.Label(cfg, text=note, wraplength=900, foreground="#555577").grid(
            row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 6))
        cfg.columnconfigure(1, weight=1)

        # Resultado em destaque
        res_lf = ttk.LabelFrame(parent, text="Ultimo resultado")
        res_lf.pack(fill="x", padx=10, pady=4)
        inner = ttk.Frame(res_lf)
        inner.pack(expand=True, pady=6)
        self._result_label = ttk.Label(inner, text="— ms", style="BigResult.TLabel")
        self._result_label.pack()

        # Log serial
        slog_lf = ttk.LabelFrame(parent, text="Log de bytes recebidos")
        slog_lf.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.serial_log_text = self._make_log_widget(slog_lf, height=12)

    # ── aba Configuração ──────────────────────────────────────────────────────
    def _build_config_tab(self, parent):
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True, padx=10, pady=10)

        # Modo
        mode_lf = ttk.LabelFrame(wrap, text="Modo de comunicacao")
        mode_lf.pack(fill="x", pady=(0, 6))
        ttk.Radiobutton(mode_lf,
            text="FIFO 245 Assincrono — modo nativo FT2232H (8 bits paralelo + WR# + TXE#)",
            variable=self.comm_mode, value="fifo",
            command=self._on_mode_change).pack(anchor="w", padx=10, pady=3)
        ttk.Radiobutton(mode_lf,
            text="UART Serial 115200 8N1 — fallback (1 pino TX)",
            variable=self.comm_mode, value="uart",
            command=self._on_mode_change).pack(anchor="w", padx=10, pady=3)

        # Frame FIFO
        self._fifo_frame = ttk.LabelFrame(wrap, text="Pinos FIFO 245 (Bank 6 — P29=GND e P34=VCCO são invalidos!)")
        self._fifo_frame.pack(fill="x", pady=(0, 6))

        pin_vals = [str(p) for p in BANK6_IO_PINS]
        grid = ttk.Frame(self._fifo_frame)
        grid.pack(fill="x", padx=8, pady=6)

        self._d_combos: list[ttk.Combobox] = []
        labels_d = ["D0 (BDBUS0)", "D1 (BDBUS1)", "D2 (BDBUS2)", "D3 (BDBUS3)",
                    "D4 (BDBUS4)", "D5 (BDBUS5)", "D6 (BDBUS6)", "D7 (BDBUS7)"]
        for i, lbl in enumerate(labels_d):
            r, c = divmod(i, 4)
            ttk.Label(grid, text=f"{lbl}:").grid(row=r*2, column=c*2, sticky="e", padx=(10, 4), pady=3)
            cb = ttk.Combobox(grid, textvariable=self._d[i], values=pin_vals, width=5)
            cb.grid(row=r*2, column=c*2+1, sticky="w", padx=(0, 6), pady=3)
            self._d_combos.append(cb)

        ctrl = ttk.Frame(self._fifo_frame)
        ctrl.pack(fill="x", padx=8, pady=(0, 6))
        ttk.Label(ctrl, text="WR# (write strobe):").pack(side="left", padx=6)
        ttk.Combobox(ctrl, textvariable=self._wr, values=pin_vals, width=5).pack(side="left", padx=4)
        ttk.Label(ctrl, text="  TXE# (TX-FIFO not full):").pack(side="left", padx=6)
        ttk.Combobox(ctrl, textvariable=self._txe, values=pin_vals, width=5).pack(side="left", padx=4)

        preset_lf = ttk.LabelFrame(self._fifo_frame, text="Presets")
        preset_lf.pack(fill="x", padx=8, pady=(0, 8))
        for name in FIFO_PRESETS:
            ttk.Button(preset_lf, text=name,
                       command=lambda n=name: self._apply_fifo_preset(n)).pack(side="left", padx=4, pady=4)
        self._preset_info = StringVar(value="Selecione um preset.")
        ttk.Label(preset_lf, textvariable=self._preset_info,
                  foreground="#0a4a7f", wraplength=950).pack(anchor="w", padx=8, pady=(0, 4))

        # Frame UART
        self._uart_frame = ttk.LabelFrame(wrap, text="Pinos UART (fallback serial)")
        self._uart_frame.pack(fill="x", pady=(0, 6))
        uart_row = ttk.Frame(self._uart_frame)
        uart_row.pack(fill="x", padx=8, pady=8)
        ttk.Label(uart_row, text="uart_tx:").pack(side="left", padx=6)
        ttk.Combobox(uart_row, textvariable=self._uart_tx,
                     values=[str(p) for p in BANK6_IO_PINS + [47, 50, 51, 56, 93]],
                     width=6).pack(side="left", padx=4)
        ttk.Label(uart_row, text="  Presets UART:").pack(side="left", padx=6)
        for name, cfg in UART_PRESETS.items():
            ttk.Button(uart_row, text=name,
                       command=lambda tx=cfg["tx"]: self._uart_tx.set(tx)).pack(side="left", padx=3)

        # Caminhos de build
        build_lf = ttk.LabelFrame(wrap, text="Caminhos do projeto VHDL (para recompilar)")
        build_lf.pack(fill="x", pady=(0, 6))
        for r, (lbl, var, pick) in enumerate([
            ("VHDL (.vhd):", self.vhdl_path,    self._pick_vhdl),
            ("UCF (.ucf):",  self.ucf_path,     self._pick_ucf),
            ("build.bat:" if IS_WINDOWS else "build.sh:", self.build_script, self._pick_build_sh),
        ]):
            ttk.Label(build_lf, text=lbl, anchor="e", width=12).grid(row=r, column=0, padx=(8, 4), pady=4, sticky="e")
            ttk.Entry(build_lf, textvariable=var).grid(row=r, column=1, padx=4, pady=4, sticky="ew")
            ttk.Button(build_lf, text="...", command=pick, width=3).grid(row=r, column=2, padx=(4, 8), pady=4)
        build_lf.columnconfigure(1, weight=1)

        # Botões de ação
        act = ttk.Frame(wrap)
        act.pack(fill="x", pady=6)
        ttk.Button(act, text="Salvar configuracao",
                   command=self._save_and_apply, style="Rebuild.TButton").pack(side="left", padx=4)
        ttk.Button(act, text="Recompilar (XST -> BitGen)",
                   command=self._rebuild, style="Rebuild.TButton").pack(side="left", padx=4)
        ttk.Button(act, text="Recompilar + Gravar Flash",
                   command=self._rebuild_and_flash, style="Action.TButton").pack(side="left", padx=4)
        ttk.Button(act, text="Restaurar padrao",
                   command=self._restore_defaults).pack(side="left", padx=4)

        self._build_status = StringVar(value="Pronto.")
        ttk.Label(wrap, textvariable=self._build_status, foreground="#1e3a5f").pack(anchor="w", pady=(0, 2))

        # Log de build
        blog_lf = ttk.LabelFrame(wrap, text="Log de compilacao ISE")
        blog_lf.pack(fill="both", expand=True, pady=(0, 2))
        self._build_log = Text(blog_lf, wrap="word", height=9,
                               bg="#1a1a2e", fg="#e0e0e0", insertbackground="white",
                               font=("Courier", 9), relief="flat", borderwidth=0)
        sb2 = ttk.Scrollbar(blog_lf, command=self._build_log.yview)
        self._build_log.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self._build_log.pack(fill="both", expand=True, padx=2, pady=2)

        self._on_mode_change()

    # ── aba Guia ──────────────────────────────────────────────────────────────
    def _build_help_tab(self, parent):
        ht = Text(parent, wrap="word", font=("Courier", 9), bg="#fafafa", relief="flat")
        sb = ttk.Scrollbar(parent, command=ht.yview)
        ht.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y", padx=(0, 4), pady=8)
        ht.pack(fill="both", expand=True, padx=(8, 0), pady=8)
        ht.insert("end", textwrap.dedent("""\
            ╔══════════════════════════════════════════════════════════════════════╗
            ║  FPGA Reflex Game — Guia Rápido                                     ║
            ║  Placa: Bionexus TX-LED R27 / Spartan-3 XC3S200-4TQG144            ║
            ╚══════════════════════════════════════════════════════════════════════╝

            ──────────────────────────────────────────────────────────────────────
            FLUXO COMPLETO (primeira vez)
            ──────────────────────────────────────────────────────────────────────
            Linux:
              1. Execute:  bash toolkit/iniciar.sh
                 (instala udev, carrega drivers, abre o painel)
              2. No painel:  Botão 1 → 2 → 3 → 5 (Gravar na Flash)
              3. Aba Monitor → /dev/ttyUSB1 → Conectar → jogue

            Windows:
              1. Instale OpenOCD e adicione ao PATH
              2. Instale ftdi drivers (libusbK via Zadig para Canal A)
              3. Execute: toolkit\run.bat
              4. No painel: Botão 1 → 2 → 3 → 5
              5. Monitor → COM3 (ou verificar Gerenciador de Dispositivos) → jogue

            ──────────────────────────────────────────────────────────────────────
            REGRAS DO JOGO
            ──────────────────────────────────────────────────────────────────────
            1. LED D6 acende → pressione o botão (inicia a rodada)
            2. Aguarde na tela escura (delay aleatório de 1–5 s)
            3. LED D5 acende → pressione o mais rápido possível
            4. Resultado:
               • "RESULT_MS=NNNN" → tempo de reação em ms
               • "EARLY"          → pressionou antes do D5 acender
               • "TIMEOUT"        → não pressionou dentro de 9999 ms

            ──────────────────────────────────────────────────────────────────────
            COMUNICAÇÃO — FT2232H FIFO 245 ASSÍNCRONO
            ──────────────────────────────────────────────────────────────────────
            O chip FT2232H possui 2 canais:
              Canal A (ttyUSB0 / COM1) — JTAG para gravação
              Canal B (ttyUSB1 / COM2) — FIFO 245 para comunicação com o jogo

            O FPGA envia dados via protocolo FIFO 245 paralelo:
              1. Verifica TXE# = '0' (FT2232H pode receber)
              2. Coloca byte nos pinos D[7:0]
              3. Pulsa WR# = '0' por >= 50 ns (2 clocks a 40 MHz)
              4. Repete para cada byte da mensagem

            O PC lê o Canal B como porta serial normal via driver VCP.
            Baudrate é irrelevante — o FT2232H tem clock próprio no lado USB.

            ──────────────────────────────────────────────────────────────────────
            PINOS CONFIRMADOS (esquemático R27_FPGA.png + PAD report ISE)
            ──────────────────────────────────────────────────────────────────────
              FPGA Pino  →  FT2232H    Função
              P31        →  BDBUS0     Data bit 0 (LSB)
              P30        →  BDBUS1     Data bit 1
              P27        →  BDBUS2     Data bit 2
              P28        →  BDBUS3     Data bit 3
              P32        →  BDBUS4     Data bit 4
              P33        →  BDBUS5     Data bit 5
              P36        →  BDBUS6     Data bit 6
              P35        →  BDBUS7     Data bit 7 (MSB)
              P21        →  BCBUS3     WR# (write strobe, ativo baixo)
              P26        →  BCBUS1     TXE# (TX FIFO não cheio, ativo baixo)
              P25        →  BCBUS0     RXF# (RX FIFO não vazio — não usado)

            ATENÇÃO: P29 = GND e P34 = VCCO_6 — nunca usar como I/O!

            ──────────────────────────────────────────────────────────────────────
            PROCESSO DE SÍNTESE — como o .bit é gerado a partir do VHDL
            ──────────────────────────────────────────────────────────────────────
              firmware/reflex_game.vhd  →  [XST]      →  .ngc  (netlist lógico)
              .ngc + reflex_game.ucf    →  [NGDBuild]  →  .ngd  (netlist + pinos)
              .ngd                      →  [MAP]       →  .ncd  (mapeado p/ LUTs)
              .ncd                      →  [PAR]       →  .ncd  (place & route)
              .ncd + reflex_game.ut     →  [BitGen]    →  .bit  (bitstream binário)

              Todos esses passos são executados por build.sh (Linux) / build.bat (Windows) usando ISE 14.7.
              O UCF (.ucf) é o arquivo que define os pinos físicos do FPGA.
              Mudar o UCF e recompilar = testar outro mapeamento de pinos.

            ──────────────────────────────────────────────────────────────────────
            SOLUÇÃO DE PROBLEMAS
            ──────────────────────────────────────────────────────────────────────
            Bytes chegam mas são caracteres errados:
              → Bit order incorreto. Tente outro preset FIFO → Recompilar → Gravar.

            Nenhum byte chega:
              → Verifique /dev/ttyUSB1 (não ttyUSB0 que é JTAG)
              → Confirme que gravou na Flash (não só RAM — RAM perde ao desligar)
              → Execute uma rodada COMPLETA (pressionar 2x conforme regras)

            OpenOCD falha "libusb" ou permissão:
              → Linux: execute iniciar.sh (cria regra udev e dá permissão)
              → Windows: use Zadig para instalar WinUSB/libusbK no Canal A

            MAP/PAR falha com erro de localização (LOC invalid):
              → Um pino inválido foi usado (P29=GND ou P34=VCCO)
              → Abra Configuração de Pinos → selecione apenas pinos da lista
        """))
        ht.configure(state=DISABLED)

    # ── widgets auxiliares ────────────────────────────────────────────────────
    def _make_log_widget(self, parent, height=16):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, padx=4, pady=4)
        w = Text(frame, wrap="word", height=height,
                 bg="#fdfeff", font=("Courier", 9), relief="flat")
        sb = ttk.Scrollbar(frame, command=w.yview)
        w.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        w.pack(fill="both", expand=True)
        for tag, color in LOG_COLORS.items():
            w.tag_configure(tag, foreground=color)
        return w

    # ── log colorido ──────────────────────────────────────────────────────────
    def _log(self, level: str, text: str, widget: Text | None = None):
        w = widget or self.log_text
        ts = _dt.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level:4}] {text}\n"
        w.insert(END, line, level)
        w.see(END)

    def _blog(self, text: str):
        self._build_log.insert(END, text + "\n")
        self._build_log.see(END)

    def _slog(self, text: str, level: str = "INFO"):
        self._log(level, text, self.serial_log_text)

    def _clear_widget(self, w: Text):
        w.delete("1.0", END)

    # ── persistência de pinos ─────────────────────────────────────────────────
    def _load_pin_config(self):
        try:
            if CONFIG_FILE.exists():
                cfg = json.loads(CONFIG_FILE.read_text())
                self.comm_mode.set(cfg.get("mode", "fifo"))
                d = cfg.get("d", [31, 30, 27, 28, 32, 33, 36, 35])
                for i, v in enumerate(d[:8]):
                    self._d[i].set(v)
                self._wr.set(cfg.get("wr", 21))
                self._txe.set(cfg.get("txe", 26))
                self._uart_tx.set(cfg.get("uart_tx", 28))
        except Exception:
            pass

    def _save_pin_config(self):
        try:
            cfg = {
                "mode": self.comm_mode.get(),
                "d":    [v.get() for v in self._d],
                "wr":   self._wr.get(),
                "txe":  self._txe.get(),
                "uart_tx": self._uart_tx.get(),
            }
            CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
        except Exception:
            pass

    def _current_pin_cfg(self) -> dict:
        return {
            "d":   [v.get() for v in self._d],
            "wr":  self._wr.get(),
            "txe": self._txe.get(),
            "tx":  self._uart_tx.get(),
        }

    # ── config tab helpers ────────────────────────────────────────────────────
    def _set_frame_state(self, frame, state: str):
        for w in frame.winfo_children():
            try:
                w.configure(state=state)
            except Exception:
                pass
            self._set_frame_state(w, state)  # recursivo — alcança dropdowns dentro de sub-frames

    def _on_mode_change(self):
        mode = self.comm_mode.get()
        self._set_frame_state(self._fifo_frame, "normal" if mode == "fifo" else "disabled")
        self._set_frame_state(self._uart_frame, "normal" if mode == "uart" else "disabled")

    def _apply_fifo_preset(self, name: str):
        p = FIFO_PRESETS[name]
        for i, v in enumerate(p["d"]):
            self._d[i].set(v)
        self._wr.set(p["wr"])
        self._txe.set(p["txe"])
        self._preset_info.set(f"[{name}]  {p['info']}")

    def _restore_defaults(self):
        self._apply_fifo_preset("Padrão (esquemático)")
        self.comm_mode.set("fifo")
        self._on_mode_change()

    def _save_and_apply(self):
        self._save_pin_config()
        mode = self.comm_mode.get()
        pin_cfg = self._current_pin_cfg()
        try:
            vhdl = generate_vhdl(mode)
            ucf  = generate_ucf(mode, pin_cfg)
            Path(self.vhdl_path.get()).write_text(vhdl, encoding="utf-8")
            Path(self.ucf_path.get()).write_text(ucf,  encoding="utf-8")
            self._blog(f"=== Arquivos gerados ({_dt.datetime.now():%H:%M:%S}) ===")
            self._blog(f"Modo: {mode.upper()}")
            if mode == "fifo":
                for i in range(8):
                    self._blog(f"  D{i} = P{self._d[i].get()}")
                self._blog(f"  WR = P{self._wr.get()}   TXE = P{self._txe.get()}")
            else:
                self._blog(f"  UART TX = P{self._uart_tx.get()}")
            self._build_status.set("VHDL e UCF gerados. Clique Recompilar para gerar o bitstream.")
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))

    def _rebuild(self, on_done=None):
        self._save_and_apply()
        script = Path(self.build_script.get())
        if not script.exists():
            messagebox.showerror("Script de build não encontrado", str(script))
            return
        self._build_status.set("Compilando...")
        self._blog("=" * 60)
        self._blog(f"BUILD INICIADO  {_dt.datetime.now():%Y-%m-%d %H:%M:%S}")

        def worker():
            env = os.environ.copy()
            env["XILINXD_LICENSE_FILE"] = str(
                Path.home() / "Downloads" / "Xilinx.lic"
            )
            try:
                build_cmd = [str(script)] if IS_WINDOWS else ["bash", str(script)]
                proc = subprocess.Popen(
                    build_cmd,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    cwd=str(script.parent), env=env)
                assert proc.stdout
                for line in proc.stdout:
                    self.root.after(0, self._blog, line.rstrip("\n"))
                rc = proc.wait()
            except Exception as exc:
                self.root.after(0, self._blog, f"EXCEÇÃO: {exc}")
                rc = -1

            bit_src = script.parent / "reflex_game.bit"
            bit_dst = _KIT_DIR / "reflex_game.bit"

            def finish():
                if rc == 0 and bit_src.exists():
                    shutil.copy2(str(bit_src), str(bit_dst))
                    self.bit_path.set(str(bit_dst))
                    self._blog(f"✓ Bitstream copiado → {bit_dst}")
                    self._build_status.set(f"Build OK  {_dt.datetime.now():%H:%M:%S}")
                    self._log("OK", "Build concluído — bitstream atualizado.")
                else:
                    self._build_status.set(f"Build FALHOU (rc={rc})")
                    self._log("ERRO", "Build falhou — veja o log de compilação.")
                if on_done:
                    on_done(rc == 0 and bit_src.exists())

            self.root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _rebuild_and_flash(self):
        def after_build(ok):
            if ok:
                self.program_flash()
            else:
                messagebox.showerror("Build falhou", "Veja o log de compilação.")
        self._rebuild(on_done=after_build)

    # ── picks de arquivos ─────────────────────────────────────────────────────
    def _pick_openocd(self):
        p = filedialog.askopenfilename(title="OpenOCD")
        if p: self.openocd_path.set(p)

    def _pick_cfg(self):
        p = filedialog.askopenfilename(filetypes=[("OpenOCD cfg", "*.cfg"), ("Todos", "*")])
        if p: self.cfg_path.set(p)

    def _pick_bit(self):
        p = filedialog.askopenfilename(filetypes=[("Bitstream", "*.bit"), ("Todos", "*")])
        if p: self.bit_path.set(p)

    def _pick_vhdl(self):
        p = filedialog.askopenfilename(filetypes=[("VHDL", "*.vhd"), ("Todos", "*")])
        if p: self.vhdl_path.set(p)

    def _pick_ucf(self):
        p = filedialog.askopenfilename(filetypes=[("UCF", "*.ucf"), ("Todos", "*")])
        if p: self.ucf_path.set(p)

    def _pick_build_sh(self):
        ftypes = [("Batch script", "*.bat"), ("Todos", "*")] if IS_WINDOWS else [("Shell script", "*.sh"), ("Todos", "*")]
        p = filedialog.askopenfilename(filetypes=ftypes)
        if p: self.build_script.set(p)

    # ── execução de comandos ──────────────────────────────────────────────────
    def _openocd_cmd(self) -> list[str]:
        ocd = self.openocd_path.get().strip() or "openocd"
        if (IS_LINUX or IS_MAC) and self.use_sudo.get():
            return ["sudo", "-n", ocd]
        return [ocd]

    def _run(self, title: str, cmd: list[str], log_name: str, on_finish=None):
        if self.current_process:
            messagebox.showwarning("Ocupado", "Já há um processo em execução.")
            return
        self._log("INFO", f"Iniciando: {title}")
        self._log("CMD",  "$ " + " ".join(shlex.quote(x) for x in cmd))

        def worker():
            lp = LOG_DIR / f"{log_name}_{timestamp()}.txt"
            lines: list[str] = []
            rc = -1
            try:
                self.current_process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace",
                    cwd=str(_KIT_DIR))
                assert self.current_process.stdout
                for line in self.current_process.stdout:
                    lines.append(line)
                    self.queue.put(("log", line.rstrip("\n")))
                rc = self.current_process.wait()
            except FileNotFoundError as exc:
                self.queue.put(("error", f"Executável não encontrado: {exc}"))
            except Exception as exc:
                self.queue.put(("error", f"Erro: {exc}"))
            finally:
                header = (
                    f"Acao: {title}\n"
                    f"Data: {_dt.datetime.now().isoformat()}\n"
                    f"Cmd: {' '.join(cmd)}\n"
                    f"RC: {rc}\n"
                    f"{'-'*60}\n"
                )
                lp.write_text(header + "".join(lines), encoding="utf-8")
                self.current_process = None
                self.queue.put(("done", f"Concluído: {title} (rc={rc})"))
                if on_finish:
                    self.queue.put(("callback", (on_finish, rc, "".join(lines))))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "log":
                    lvl = "ERRO" if "error" in str(payload).lower() else "CMD"
                    self._log(lvl, str(payload))
                elif kind == "error":
                    self._log("ERRO", str(payload))
                elif kind == "done":
                    self._log("DONE", str(payload))
                elif kind == "callback":
                    func, rc, out = payload
                    try: func(rc, out)
                    except Exception as exc:
                        self._log("ERRO", f"Callback error: {exc}")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_queue)

    def stop_process(self):
        if self.current_process:
            self.current_process.terminate()
            self._log("WARN", "Processo interrompido pelo usuário.")

    # ── ações de gravação ─────────────────────────────────────────────────────
    def check_environment(self):
        self._log("INFO", "=== Verificação de ambiente ===")
        self._log("INFO", f"OS: {platform.platform()}")
        ocd = self.openocd_path.get().strip()
        which = shutil.which(ocd or "openocd")
        self._log("INFO" if which else "WARN",
                  f"OpenOCD: {which or 'NÃO ENCONTRADO'}")
        for lbl, var in [("cfg", self.cfg_path), ("bit", self.bit_path)]:
            p = Path(var.get())
            self._log("OK" if p.exists() else "ERRO",
                      f"{lbl}: {'OK' if p.exists() else 'NÃO ENCONTRADO'} — {p}")
        self._log("OK" if SERIAL_AVAILABLE else "WARN",
                  f"pyserial: {'instalado' if SERIAL_AVAILABLE else 'ausente'}")
        if which:
            self._run("OpenOCD version", [which, "--version"], "ocd_version")
        else:
            if messagebox.askyesno("OpenOCD não encontrado",
                                   "OpenOCD não está instalado ou não está no PATH.\n\n"
                                   "Deseja instalar automaticamente?"):
                self._install_openocd()
        if not SERIAL_AVAILABLE:
            if messagebox.askyesno("pyserial ausente",
                                   "pyserial não está instalado (necessário para o monitor serial).\n\n"
                                   "Deseja instalar agora via pip?\n"
                                   "O painel precisará ser reiniciado após a instalação."):
                self._install_pyserial()

    def _install_pyserial(self):
        self._log("INFO", "Instalando pyserial via pip...")
        self._run(
            "Instalar pyserial",
            [sys.executable, "-m", "pip", "install", "--user", "pyserial"],
            "install_pyserial",
            on_finish=lambda rc, out: self._log(
                "OK" if rc == 0 else "ERRO",
                "pyserial instalado. Reinicie o painel para ativar o monitor serial." if rc == 0
                else "Falha ao instalar pyserial — tente manualmente: pip install pyserial"
            )
        )

    def _install_openocd(self):
        if IS_WINDOWS:
            self._install_openocd_windows()
        elif IS_LINUX:
            self._install_openocd_linux()
        else:
            self._log("WARN", "Instalação automática não suportada neste OS.")
            self._log("WARN", "Instale manualmente: https://openocd.org")

    def _install_openocd_windows(self):
        if shutil.which("winget"):
            self._log("INFO", "Instalando OpenOCD via winget...")
            self._run("Instalar OpenOCD (winget)",
                      ["winget", "install", "--id=openocd.openocd", "-e", "--silent"],
                      "install_openocd", on_finish=self._after_openocd_install)
        elif shutil.which("choco"):
            self._log("INFO", "Instalando OpenOCD via Chocolatey...")
            self._run("Instalar OpenOCD (choco)",
                      ["choco", "install", "openocd", "-y"],
                      "install_openocd", on_finish=self._after_openocd_install)
        else:
            self._log("WARN", "winget e Chocolatey não encontrados.")
            messagebox.showwarning(
                "Instalação manual necessária",
                "Nem winget nem Chocolatey foram encontrados.\n\n"
                "Instale o OpenOCD manualmente:\n"
                "https://openocd.org/pages/getting-openocd.html\n\n"
                "Ou via MSYS2:\n"
                "pacman -S mingw-w64-x86_64-openocd"
            )

    def _install_openocd_linux(self):
        pkg_managers = [
            ("apt",    ["sudo", "apt",    "install", "-y",           "openocd"]),
            ("dnf",    ["sudo", "dnf",    "install", "-y",           "openocd"]),
            ("pacman", ["sudo", "pacman", "-S",      "--noconfirm",  "openocd"]),
            ("zypper", ["sudo", "zypper", "install", "-y",           "openocd"]),
        ]
        for mgr, cmd in pkg_managers:
            if shutil.which(mgr):
                self._log("INFO", f"Instalando OpenOCD via {mgr}...")
                self._run(f"Instalar OpenOCD ({mgr})", cmd, "install_openocd",
                          on_finish=self._after_openocd_install)
                return
        self._log("WARN", "Nenhum gerenciador de pacotes suportado encontrado.")
        self._log("WARN", "Instale manualmente: sudo <apt|dnf|pacman> install openocd")

    def _after_openocd_install(self, rc, out):
        if rc == 0:
            new_path = shutil.which("openocd")
            if new_path:
                self.openocd_path.set(new_path)
                self._log("OK", f"OpenOCD instalado: {new_path}")
            else:
                self._log("OK", "OpenOCD instalado. Reinicie o painel se o PATH não for atualizado.")
        else:
            self._log("ERRO", "Falha ao instalar OpenOCD — tente instalar manualmente.")

    def detect_usb(self):
        if IS_WINDOWS:
            self._log("INFO", "Windows: verifique o Gerenciador de Dispositivos → Portas (COM e LPT).")
            return
        def parse(rc, out):
            tag = f"{FTDI_VID}:{FTDI_PID}".lower()
            if tag in out.lower():
                self._sb_usb.set(f"USB: FT2232H OK")
                self._log("OK", f"FTDI {FTDI_VID}:{FTDI_PID} encontrado.")
            else:
                self._sb_usb.set("USB: nao encontrado")
                self._log("ERRO", f"FTDI {FTDI_VID}:{FTDI_PID} nao encontrado no lsusb.")
        self._run("Detectar USB", ["lsusb"], "detect_usb", parse)

    def scan_jtag(self):
        cfg = Path(self.cfg_path.get())
        if not cfg.exists():
            self._log("ERRO", f"cfg não encontrado: {cfg}"); return
        cmd = self._openocd_cmd() + ["-f", str(cfg), "-c", "init; scan_chain; exit"]
        def parse(rc, out):
            ol = out.lower()
            if rc == 0 and (EXPECTED_FPGA_ID.lower() in ol or "xc3s200" in ol):
                self._sb_jtag.set("JTAG: FPGA OK")
                self._log("OK", "JTAG: FPGA xc3s200 detectada.")
                if EXPECTED_FLASH_ID.lower() in ol:
                    self._log("OK", "JTAG: Platform Flash xcf01s detectada.")
            else:
                self._sb_jtag.set("JTAG: falha")
                self._log("ERRO", "JTAG falhou — verifique OpenOCD e cabo USB.")
        self._run("Escanear JTAG", cmd, "scan_jtag", parse)

    def program_fpga(self):
        cfg = Path(self.cfg_path.get())
        bit = Path(self.bit_path.get())
        for p, n in [(cfg, "cfg"), (bit, "bit")]:
            if not p.exists():
                self._log("ERRO", f"{n} não encontrado: {p}"); return
        cmd = self._openocd_cmd() + [
            "-f", str(cfg),
            "-c", f'init; pld load 0 "{quote_path(bit)}"; exit',
        ]
        def parse(rc, out):
            ol = out.lower()
            if rc == 0 and "error" not in ol and "failed" not in ol:
                ts = _dt.datetime.now().strftime("%H:%M:%S")
                self._prog_banner.set(f"FPGA GRAVADA NA RAM — {ts}")
                self._banner_lbl.configure(foreground="#1a6b1a")
                self._log("OK", "FPGA gravada na RAM com sucesso.")
                messagebox.showinfo("Gravado", f"FPGA configurada!\nHora: {ts}\nLED D6 deve estar aceso.")
            else:
                self._prog_banner.set("FALHA AO GRAVAR")
                self._banner_lbl.configure(foreground="#9b1c1c")
                self._log("ERRO", "Falha ao gravar FPGA na RAM.")
        self._run("Gravar RAM", cmd, "prog_ram", parse)

    def _find_ise(self, name: str) -> str | None:
        for d in ISE_BIN_CANDIDATES:
            p = d / (name + (".exe" if IS_WINDOWS else ""))
            if p.exists(): return str(p)
        return shutil.which(name)

    def program_flash(self):
        bit = Path(self.bit_path.get())
        if not bit.exists():
            self._log("ERRO", f"Bitstream não encontrado: {bit}"); return
        promgen = self._find_ise("promgen")
        impact  = self._find_ise("impact")
        if not promgen: self._log("ERRO", "promgen (ISE) não encontrado."); return
        if not impact:  self._log("ERRO", "impact (ISE) não encontrado.");  return

        stem     = str(bit.parent / (bit.stem + "_flash"))
        mcs_path = Path(stem + ".mcs")
        svf_path = bit.parent / (bit.stem + "_flash.svf")

        self._log("INFO", "=== Flash 1/3: gerar MCS (promgen) ===")
        self._run(
            "Gerar MCS",
            [promgen, "-w", "-p", "mcs", "-c", "FF", "-x", XCF_DEVICE,
             "-u", "0", str(bit), "-o", stem],
            "gen_mcs",
            on_finish=lambda rc, out: self._flash2(rc, impact, mcs_path, svf_path, bit),
        )

    def _flash2(self, rc, impact, mcs_path, svf_path, bit):
        if rc != 0 or not mcs_path.exists():
            self._log("ERRO", "Falha ao gerar MCS."); return
        self._log("INFO", "=== Flash 2/3: gerar SVF (iMPACT) ===")
        if svf_path.exists(): svf_path.unlink()
        batch = bit.parent / "flash_program.cmd"
        # JTAG chain: TDI → xc3s200 (pos 1) → xcf01s (pos 2) → TDO
        batch.write_text(
            f'setMode -bscan\n'
            f'setCable -port svf -file "{quote_path(svf_path)}"\n'
            f'addDevice -position 1 -part xc3s200\n'
            f'addDevice -position 2 -part {XCF_DEVICE}\n'
            f'assignFile -position 2 -file "{quote_path(mcs_path)}"\n'
            f'program -p 2 -e -v\n'
            f'quit\n',
            encoding="utf-8")
        self._run("Gerar SVF", [impact, "-batch", str(batch)], "gen_svf",
                  on_finish=lambda rc2, out2: self._flash3(rc2, svf_path))

    def _flash3(self, rc, svf_path):
        if rc != 0 or not svf_path.exists() or svf_path.stat().st_size < 1000:
            self._log("ERRO", f"SVF não gerado (rc={rc}, size={svf_path.stat().st_size if svf_path.exists() else 0}).")
            return
        cfg = Path(self.cfg_path.get())
        if not cfg.exists():
            self._log("ERRO", f"cfg não encontrado: {cfg}"); return
        self._log("INFO", "=== Flash 3/3: programar via OpenOCD SVF (1–3 min) ===")
        self._log("WARN", "Não desconecte o cabo USB durante a gravação!")
        cmd = self._openocd_cmd() + [
            "-f", str(cfg),
            "-c", f'init; svf "{quote_path(svf_path)}" progress; exit',
        ]
        def parse(rc2, out):
            ol = out.lower()
            if rc2 == 0 and "error" not in ol and "failed" not in ol:
                ts = _dt.datetime.now().strftime("%H:%M:%S")
                self._prog_banner.set(f"FLASH GRAVADA COM SUCESSO — {ts}")
                self._banner_lbl.configure(foreground="#1a6b1a")
                self._log("OK", "Flash gravada com sucesso.")
                messagebox.showinfo("Flash gravada",
                                    f"Firmware na Flash!\nHora: {ts}\n"
                                    "Firmware carrega automaticamente ao ligar a placa.")
            else:
                self._prog_banner.set("FALHA NA GRAVACAO DA FLASH")
                self._banner_lbl.configure(foreground="#9b1c1c")
                self._log("ERRO", "Falha ao gravar Flash.")
        self._run("Gravar Flash", cmd, "prog_flash", parse)

    # ── serial monitor ────────────────────────────────────────────────────────
    def _list_ports(self) -> list[str]:
        if not SERIAL_AVAILABLE: return []
        all_ports = [p.device for p in list_ports.comports()]
        if IS_WINDOWS:
            return sorted(all_ports)
        usb  = sorted([p for p in all_ports if "USB" in p])
        rest = [p for p in all_ports if "USB" not in p]
        return usb + rest

    def _refresh_ports(self):
        ports = self._list_ports()
        self.port_combo["values"] = ports
        if not self.serial_port.get() and ports:
            pref = next((p for p in ports if "ttyUSB1" in p or "COM2" in p), ports[0])
            self.serial_port.set(pref)
        self._slog(f"Portas disponíveis: {ports or 'nenhuma'}")

    def _connect_serial(self):
        if not SERIAL_AVAILABLE:
            messagebox.showerror("pyserial ausente", "pip install pyserial"); return
        if self.serial_thread and self.serial_thread.is_alive():
            self._slog("Já conectado."); return
        port = self.serial_port.get().strip()
        if not port:
            messagebox.showwarning("Porta ausente", "Selecione uma porta serial."); return
        if "USB0" in port or "COM1" in port:
            self._slog("AVISO: ttyUSB0/COM1 provavelmente é o Canal A (JTAG). Use ttyUSB1/COM2.", "WARN")
        try:
            baud = int(self.serial_baud.get())
        except ValueError:
            messagebox.showerror("Baudrate inválido", "Use um número inteiro."); return

        self.serial_stop.clear()
        self._rx_byte_count = 0

        def reader():
            try:
                self.serial_obj = serial.Serial(port, baudrate=baud, timeout=0.2)
                self._sb_serial.set(f"Serial: {port}")
                self.root.after(0, self._slog,
                                f"Conectado em {port} @ {baud}. Jogue uma rodada para ver o resultado.")
                buf = b""
                while not self.serial_stop.is_set():
                    data = self.serial_obj.read(256)
                    if data:
                        self._rx_byte_count += len(data)
                        hex_s = data.hex(" ").upper()
                        try: txt = data.decode("ascii", errors="replace")
                        except Exception: txt = "?"
                        self.root.after(0, self._slog,
                                        f"RAW [{len(data)}B] {hex_s}  |  {repr(txt)}", "RAW")
                        buf += data
                        while b"\n" in buf:
                            raw, buf = buf.split(b"\n", 1)
                            line = raw.decode("utf-8", errors="replace").strip()
                            if line:
                                self.root.after(0, self._handle_line, line)
                    else:
                        time.sleep(0.05)
            except Exception as exc:
                self.root.after(0, self._slog, f"Erro serial: {exc}", "ERRO")
                self._sb_serial.set("Serial: erro")
            finally:
                try:
                    if self.serial_obj: self.serial_obj.close()
                except Exception: pass
                self.serial_obj = None
                self._sb_serial.set("Serial: desconectado")
                self.root.after(0, self._slog,
                                f"Desconectado. Total recebido: {self._rx_byte_count} bytes.")

        self.serial_thread = threading.Thread(target=reader, daemon=True)
        self.serial_thread.start()

    def _disconnect_serial(self):
        self.serial_stop.set()

    def _handle_line(self, line: str):
        upper = line.strip().upper()
        if upper == "EARLY":
            self._result_label.configure(text="CEDO!", foreground="#e74c3c")
            self._sb_result.set("Resultado: CEDO!")
            self._slog(f"EVENTO: botão pressionado antes do LED (EARLY)", "WARN")
            return
        if upper == "TIMEOUT":
            self._result_label.configure(text="TIMEOUT", foreground="#e67e22")
            self._sb_result.set("Resultado: TIMEOUT")
            self._slog(f"EVENTO: tempo esgotado (TIMEOUT)", "WARN")
            return
        m = re.search(r"RESULT_MS\s*=\s*(\d{1,5})", line, re.IGNORECASE)
        if not m:
            m = re.search(r"(\d{3,5})\s*ms?", line, re.IGNORECASE)
        if m:
            ms = int(m.group(1))
            color = "#1a6b1a" if ms < 300 else "#2980b9" if ms < 600 else "#e67e22"
            self._result_label.configure(text=f"{ms} ms", foreground=color)
            self._sb_result.set(f"Resultado: {ms} ms")
            self._slog(f"RESULTADO: {ms} ms  ←  '{line}'", "OK")
            return
        self._slog(f"LINHA: {line}")

    # ── misc ──────────────────────────────────────────────────────────────────
    def _save_log(self):
        p = LOG_DIR / f"log_{timestamp()}.txt"
        p.write_text(self.log_text.get("1.0", END), encoding="utf-8")
        self._log("INFO", f"Log salvo: {p}")

    def _open_logs(self):
        try:
            if IS_WINDOWS:
                os.startfile(str(LOG_DIR))
            else:
                subprocess.Popen(["xdg-open", str(LOG_DIR)])
        except Exception as exc:
            self._log("ERRO", f"Não foi possível abrir logs: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
def main():
    root = Tk()
    FPGAPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
