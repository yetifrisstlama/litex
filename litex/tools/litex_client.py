#!/usr/bin/env python3

#
# This file is part of LiteX.
#
# Copyright (c) 2015-2020 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2016 Tim 'mithro' Ansell <mithro@mithis.com>
# SPDX-License-Identifier: BSD-2-Clause

import os
import argparse
import socket

from litex.tools.remote.etherbone import EtherbonePacket, EtherboneRecord
from litex.tools.remote.etherbone import EtherboneReads, EtherboneWrites
from litex.tools.remote.etherbone import EtherboneIPC
from litex.tools.remote.csr_builder import CSRBuilder

# Remote Client ------------------------------------------------------------------------------------

class RemoteClient(EtherboneIPC, CSRBuilder):
    def __init__(self, host="localhost", port=1234, base_address=0, csr_csv=None, csr_data_width=None, debug=False):
        # If csr_csv set to None and local csr.csv file exists, use it.
        if csr_csv is None and os.path.exists("csr.csv"):
            csr_csv = "csr.csv"
        # If valid csr_csv file found, build the CSRs.
        if csr_csv is not None:
            CSRBuilder.__init__(self, self, csr_csv, csr_data_width)
        # Else if csr_data_width set to None, force to csr_data_width 32-bit.
        elif csr_data_width is None:
            csr_data_width = 32
        self.host         = host
        self.port         = port
        self.base_address = base_address
        self.debug        = debug

    def open(self):
        if hasattr(self, "socket"):
            return
        self.socket = socket.create_connection((self.host, self.port), 5.0)
        self.socket.settimeout(5.0)

    def close(self):
        if not hasattr(self, "socket"):
            return
        self.socket.close()
        del self.socket

    def read(self, addr, length=None, burst="incr"):
        """
        addr = start address in [bytes], should be 32 bit aligned
        length = number of 32 bit words to read. Maximum is 255.
        """
        length_int = 1 if length is None else length
        # prepare packet
        record = EtherboneRecord()
        incr = (burst == "incr")
        record.reads = EtherboneReads(addrs=[self.base_address + addr + 4*incr*j for j in range(length_int)])
        record.rcount = len(record.reads)

        # send packet
        packet = EtherbonePacket()
        packet.records = [record]
        packet.encode()
        self.send_packet(self.socket, packet[:])

        # receive response
        packet = EtherbonePacket(self.receive_packet(self.socket))
        packet.decode()
        datas = packet.records.pop().writes.get_datas()
        if self.debug:
            for i, data in enumerate(datas):
                print("read {:08x} @ {:08x}".format(data, self.base_address + addr + 4*i))
        return datas[0] if length is None else datas

    def big_read(self, addr, length, chunk_size=255):
        """
        read data of arbitrary length in chunks
        addr = start address in [bytes], should be 32 bit aligned
        length = number of 32 bit words to read
        chunk_size = how many words to read in one Etherbone transaction
        """
        dats = []
        while length > 0:
            temp = self.read(addr, min(chunk_size, length))
            dats.append(temp)
            addr += len(temp) * 4
            length -= len(temp)
        # return hstack(dats)
        return [i for dat in dats for i in dat]

    def write(self, addr, datas):
        datas = datas if isinstance(datas, list) else [datas]
        record = EtherboneRecord()
        record.writes = EtherboneWrites(base_addr=self.base_address + addr, datas=[d for d in datas])
        record.wcount = len(record.writes)

        packet = EtherbonePacket()
        packet.records = [record]
        packet.encode()
        self.send_packet(self.socket, packet)

        if self.debug:
            for i, data in enumerate(datas):
                print("write {:08x} @ {:08x}".format(data, self.base_address + addr + 4*i))

# Utils --------------------------------------------------------------------------------------------

def dump_identifier(port):
    wb = RemoteClient(port=port)
    wb.open()

    fpga_identifier = ""

    for i in range(256):
        c = chr(wb.read(wb.bases.identifier_mem + 4*i) & 0xff)
        fpga_identifier += c
        if c == "\0":
            break

    print(fpga_identifier)

    wb.close()

def dump_registers(port):
    wb = RemoteClient(port=port)
    wb.open()

    for name, register in wb.regs.__dict__.items():
        print("0x{:08x} : 0x{:08x} {}".format(register.addr, register.read(), name))

    wb.close()

# Run ----------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX Client utility")
    parser.add_argument("--port",  default="1234",      help="Host bind port")
    parser.add_argument("--ident", action="store_true", help="Dump FPGA identifier")
    parser.add_argument("--regs",  action="store_true", help="Dump FPGA registers")
    args = parser.parse_args()

    port = int(args.port, 0)

    if args.ident:
        dump_identifier(port=port)

    if args.regs:
        dump_registers(port=port)

if __name__ == "__main__":
    main()
