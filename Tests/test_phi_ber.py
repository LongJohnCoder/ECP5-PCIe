from nmigen import *
from nmigen.build import *
from nmigen.lib.cdc import FFSynchronizer
from nmigen_boards import versa_ecp5_5g as FPGA
from nmigen_stdio.serial import AsyncSerial
from ecp5_pcie.utils.utils import UARTDebugger
from ecp5_pcie.ecp5_serdes import LatticeECP5PCIeSERDES
from ecp5_pcie.serdes import Ctrl

# Usage: python test_phi_ber.py run
#        python test_phi_ber.py grab

CAPTURE_DEPTH = 512

class SERDESTestbench(Elaboratable):
    def elaborate(self, platform):
        m = Module()

        m.submodules.serdes = serdes = LatticeECP5PCIeSERDES(2) # Declare SERDES module with 1:2 gearing
        lane = serdes.lane
        m.d.comb += lane.tx_e_idle.eq(0)

        m.domains.rx = ClockDomain()
        m.domains.tx = ClockDomain()
        m.d.comb += [
            ClockSignal("rx").eq(serdes.rx_clk),
            ClockSignal("tx").eq(serdes.tx_clk),
        ]

        # Clock outputs for the RX and TX clock domain
        platform.add_resources([Resource("test", 0, Pins("B19", dir="o"))])
        m.d.comb += platform.request("test", 0).o.eq(ClockSignal("rx"))
        platform.add_resources([Resource("test", 1, Pins("A18", dir="o"))])
        m.d.comb += platform.request("test", 1).o.eq(ClockSignal("tx"))

        # Counters for the LEDs
        refclkcounter = Signal(32)
        m.d.sync += refclkcounter.eq(refclkcounter + 1)
        rxclkcounter = Signal(32)
        m.d.rx += rxclkcounter.eq(rxclkcounter + 1)
        txclkcounter = Signal(32)
        m.d.tx += txclkcounter.eq(txclkcounter + 1)

        old_rx = Signal(8)
        m.d.sync += old_rx.eq(Cat(lane.rx_symbol[0:8]))

        tx_symbol = Signal(9, reset=56)

        timer = Signal(32)

        fftest_a = Signal(32)
        fftest_b = Signal(32)
        fftest_a_last = Signal(32)

        #m.submodules += FFSynchronizer(fftest_a, fftest_b, o_domain="tx")

        with m.FSM():
            #with m.State("Align"):
            #    m.d.rx += fftest_a.eq(~fftest_a)
            #    m.d.rx += timer.eq(timer + 1)
            #    m.d.rx += fftest_a_last.eq(fftest_a)
            #    m.d.tx += fftest_b.eq(fftest_a)
#
            #    with m.If(fftest_b != fftest_a_last):
            #        m.d.rx += timer.eq(0)
            #    
            #    m.d.rx += serdes.slip.eq(rxclkcounter[10])
#
            #    with m.If(timer == 128):
            #        m.next = "BERTest"
#
#
            #    m.next = "BERTest"
            with m.State("Align2"):
                last_rxclkcounter = Signal(32)
                m.d.rx += last_rxclkcounter.eq(rxclkcounter)

                m.d.rx += timer.eq(timer + 1)

                m.d.rx += tx_symbol.eq(Ctrl.STP)

                cond = (Cat(lane.rx_symbol[0:9]) == Ctrl.STP) & (Cat(lane.rx_symbol[9:18]) == Ctrl.COM)

                with m.If(rxclkcounter[8] & ~last_rxclkcounter[8]): #~((Cat(lane.rx_symbol[0:9]) - old_rx == 0) | (Cat(lane.rx_symbol[0:9]) - old_rx == -2)))
                    with m.If(cond):
                        m.d.rx += timer.eq(0)
                        m.next = "BERTest"
                    with m.Else():
                        m.d.rx += serdes.slip.eq(~serdes.slip)
                
                # Invert Lane if too long errored
                m.d.rx += lane.rx_invert.eq(timer[16])
            with m.State("BERTest"):
                m.d.rx += lane.tx_disp.eq(0)
                m.d.rx += lane.tx_set_disp.eq(1)
                m.d.rx += timer.eq(timer + 1)
                m.d.rx += tx_symbol.eq(Cat(timer[0:8], 0))


        
        m.d.rx += lane.rx_invert.eq(1)
        #m.d.rx += tx_symbol.eq(tx_symbol + 1)
        m.d.comb += Cat(serdes.lane.tx_symbol[0:9]).eq(tx_symbol)
        m.d.comb += Cat(serdes.lane.tx_symbol[9:18]).eq(Ctrl.COM)
        uart_pins = platform.request("uart", 0)
        uart = AsyncSerial(divisor = int(100), pins = uart_pins)
        m.submodules += uart
        
        debug = UARTDebugger(uart, 8, CAPTURE_DEPTH, Cat(lane.rx_symbol[0:9], lane.rx_aligned, Signal(6), lane.rx_symbol[9:18], lane.rx_valid[0] | lane.rx_valid[1], Signal(6),
            lane.tx_symbol[0:9], Signal(7), lane.tx_symbol[9:18], Signal(7)), "rx")
        m.submodules += debug

        return m

# -------------------------------------------------------------------------------------------------

import sys
import serial


import os
os.environ["NMIGEN_verbose"] = "Yes"


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        if arg == "run":
            FPGA.VersaECP55GPlatform().build(SERDESTestbench(), do_program=True)

        if arg == "grab":
            port = serial.Serial(port='/dev/ttyUSB1', baudrate=1000000)
            port.write(b"\x00")
            indent = 0
            last_time = 0
            last_realtime = 0

            while True:
                #while True:
                #    if port.read(1) == b'\n': break
                if port.read(1) == b'\n': break

            # Prints a symbol as K and D codes
            def print_symbol(symbol, indent, end=""):
                xa = symbol & 0b11111
                ya = (symbol & 0b11100000) >> 5
                if symbol & 0x1ff == 0x1ee:
                    print("Error\t", end=end)

                # Convert symbol data to a string which represents it
                elif True:
                    if xa == 27 and ya == 7:
                        print("STP\t", end=end)
                        indent = indent + 1
                    elif xa == 23 and ya == 7:
                        print("PAD\t", end=end)
                    elif xa == 29 and ya == 7:
                        print("END\t", end=end)
                        if indent > 0:
                            indent = indent - 1
                    elif xa == 30 and ya == 7:
                        print("EDB\t", end=end)
                        if indent > 0:
                            indent = indent - 1
                    elif xa == 28:
                        if ya == 0:
                            print("SKP\t", end=end)
                        if ya == 1:
                            print("FTS\t", end=end)
                        if ya == 2:
                            print("SDP\t", end=end)
                            indent = indent + 1
                        if ya == 3:
                            print("IDL\t", end=end)
                        if ya == 5:
                            print("COM\t", end=end)
                        if ya == 7:
                            print("EIE\t", end=end)
                    else:
                        print("{}{}{}{}.{} \t{}".format(" " * 0 * indent,
                            "L" if symbol & (1 << 9) else " ",
                            "K" if symbol & (1 << 8) else "D",
                            xa, ya, symbol & 0xFF
                        ), end=end)
                return indent

            # Returns selected bit range from a byte array
            def get_bits(word, offset, count):
                return (word & ((2 ** count - 1) << offset)) >> offset

            # Returns selected byte range from a byte array
            def get_bytes(word, offset, count):
                return (word & ((2 ** (count * 8) - 1) << (offset * 8))) >> (offset * 8)

            old = 0

            # The data is read into a byte array (called word) and then the relevant bits are and'ed out and right shifted.
            for x in range(CAPTURE_DEPTH):
                # ssssssss sa000000 ssssssss sb000000 llllllll SSSSSSSS S0000000 SSSSSSSS S0000000 s = rx_symbol, S = tx_symbol, a = aligned, b = valid, l = ltssm state, d = debug
                chars = port.read(8 * 2 + 1)
                try:
                    data = int(chars, 16)
                except:
                    print("err " + str(chars))
                    data = 0
                print("RX:", end="\t")
                indent = print(hex(data & 0x1FF), end=" \t")
                indent = print(hex((data & 0x1FF0000) >> 16), end=" \t")
                print("TX:", end="\t")
                indent = print(hex((data & 0x1FF00000000) >> 32), end=" \t")
                indent = print(hex((data & 0x1FF000000000000) >> 48), end=" \t")
                indent = print(hex((data & 0x1FF) - old), end="\n")
                old = data & 0x1FF