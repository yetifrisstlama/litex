# This file is Copyright (c) 2019 Michael Betz <michibetz@gmail.com>
# License: BSD

import math
from sys import argv
from migen import *
from litex.soc.interconnect.csr import *


# I2C Master ------------------------------------------------------------------
class I2CMaster(Module, AutoCSR):
    """2-wire I2C Master

    Provides a simple and minimal hardware I2C Master
    """
    pads_layout = [("scl", 1), ("sda", 1), ("sda_i", 1)]

    def __init__(self, pads, sys_clk_freq, i2c_clk_freq=400e3):
        if pads is None:
            pads = Record(self.pads_layout, reset=1)
        self.pads = pads

        self.start = Signal()
        self.done = Signal()
        self.mode = Signal(2)  # 0 = send byte, 1 = send start, 2 = send stop

        # # #

        bits = Signal(4)
        tx_word = Signal(9, reset=(0x83 << 1) | 1)
        rx_word = Signal(9)

        # Clock generation ----------------------------------------------------
        clk_divide = math.ceil(sys_clk_freq / i2c_clk_freq)
        clk_divider = Signal(max=clk_divide)
        clk_rise = Signal()
        clk_fall = Signal()
        self.sync += [
            If(clk_fall,
                clk_divider.eq(0)
            ).Else(
                clk_divider.eq(clk_divider + 1)
            )
        ]
        self.comb += [
            clk_rise.eq(clk_divider == (clk_divide // 2 - 1)),
            clk_fall.eq(clk_divider == (clk_divide - 1))
        ]

        # Control FSM ---------------------------------------------------------
        self.submodules.fsm = fsm = FSM(reset_state="IDLE")
        fsm.act("IDLE",
            self.done.eq(1),
            If(self.start & (self.mode == 2),
                NextValue(self.pads.sda, 0),
                NextState("XFER_STOP")
            ),
            If(self.start & (self.mode == 1),
                NextValue(self.pads.sda, 0),
                NextState("XFER_START")
            ),
            If(self.start & (self.mode == 0),
                NextState("XFER")
            )
        )
        fsm.act("XFER_START",
            If(clk_fall,
                NextValue(self.pads.scl, 0),
                NextValue(self.start, 0),
                NextState("IDLE")
            )
        )
        fsm.act("XFER_STOP",
            If(clk_rise,
                NextValue(self.pads.sda, 1),
                NextValue(self.start, 0),
                NextState("IDLE")
            )
        )
        fsm.act("XFER",
            If(clk_fall,
                NextValue(tx_word, Cat(0, tx_word[:-1])),
                NextValue(self.pads.sda, tx_word[-1]),
                NextValue(self.pads.scl, 0),
            ),
            If(clk_rise,
                NextValue(bits, bits + 1),
                NextValue(self.pads.scl, 1),
                If(bits == 9,
                    NextState("IDLE"),
                    NextValue(bits, 0),
                    NextValue(self.start, 0)
                ).Else(
                    NextValue(rx_word, Cat(self.pads.sda, rx_word[:-1]))
                )
            )
        )


    # def add_csr(self):
    #     self._control  = CSRStorage(fields=[
    #         CSRField("start",  size=1, offset=0, pulse=True),
    #         CSRField("length", size=8, offset=8)])
    #     self._status   = CSRStatus(fields=[
    #         CSRField("done", size=1, offset=0)])
    #     self._mosi     = CSRStorage(self.data_width)
    #     self._miso     = CSRStatus(self.data_width)
    #     self._cs       = CSRStorage(len(self.cs), reset=1)
    #     self._loopback = CSRStorage()

    #     self.comb += [
    #         self.start.eq(self._control.fields.start),
    #         self.length.eq(self._control.fields.length),
    #         self.mosi.eq(self._mosi.storage),
    #         self.cs.eq(self._cs.storage),
    #         self.loopback.eq(self._loopback.storage),

    #         self._status.fields.done.eq(self.done),
    #         self._miso.status.eq(self.miso),
    #     ]


def i2c_tb(dut):
    for i in range(10):
        yield
    # Send START
    yield dut.mode.eq(1)
    yield dut.start.eq(1)
    yield
    yield
    while (yield dut.done) == 0:
        yield
    # Send TX_WORD
    yield dut.mode.eq(0)
    yield dut.start.eq(1)
    yield
    yield
    while (yield dut.done) == 0:
        yield
    # Send STOP
    yield dut.mode.eq(2)
    yield dut.start.eq(1)
    yield
    yield
    while (yield dut.done) == 0:
        yield



if __name__ == "__main__":
    tName = argv[0].replace('.py', '')
    dut = I2CMaster(None, 1.6e6)
    tb = i2c_tb(dut)
    run_simulation(dut, tb, vcd_name=tName + '.vcd')
