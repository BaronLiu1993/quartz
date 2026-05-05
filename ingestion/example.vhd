library ieee;
use ieee.std_logic_1164.all;

entity counter is
    port (
        clk   : in  std_logic;
        reset : in  std_logic;
        q     : out std_logic
    );
end entity counter;

architecture rtl of counter is
    signal count_reg : std_logic := '0';
begin
    process (clk, reset)
    begin
        if reset = '1' then
            count_reg <= '0';
        elsif rising_edge(clk) then
            count_reg <= not count_reg;
        end if;
    end process;

    q <= count_reg;
end architecture rtl;
