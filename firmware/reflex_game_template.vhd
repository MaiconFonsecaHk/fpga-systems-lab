library IEEE;
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

{comm_proc}
