# Disassembler 8051/8052
#
# Code analyzer
#
# Copyright (c) 2022, 2026 Aleksander Mazur
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import enum
from . import utils
from .instructions import ArgType, Instructions
from .addresses import Addresses


class LabelType(enum.Enum):
    JUMP = 'jump'  # label points to code
    DPTR = 'dptr'  # label points to constant data in program memory
    ADDR = 'addr'  # label points to constant data in program memory - an address


class InstrArgsAnalyzer:
    def __init__(self, rom: bytes, pc: int, pc_rel: int, offset: int):
        self.rom = rom
        self.pc = pc  # points to the opcode (first byte of instruction)
        self.pc_rel = pc_rel  # points to the beginning of next instruction
        self.offset = offset
        # points to the first argument (one byte after opcode)
        self.pc_arg = pc + 1

    def next_arg(self, arg: ArgType) -> tuple[ArgType, int, str] | None:
        if self.pc >= len(self.rom):
            return None

        hint = ''
        val = self.rom[self.pc_arg]
        self.pc_arg += 1  # next byte
        if arg == ArgType.LABEL:
            if self.pc_arg >= len(self.rom):
                return None
            val = ((val << 8) | self.rom[self.pc_arg]) - self.offset
            self.pc_arg += 1  # next byte
        elif arg == ArgType.ADDR:
            val = (self.pc_rel & 0xF800) | val | (
                (self.rom[self.pc] << 3) & 0x700)  # use relevant opcode bits
            arg = ArgType.LABEL
        elif arg == ArgType.REL:
            if val >= 0x80:
                val = val - 0x100
            val = self.pc_rel + val
            if val < 0:
                return None
            arg = ArgType.LABEL
        elif arg == ArgType.IMM:
            hint = utils.binary_hint(val)

        return (arg, val, hint)


class CodeAnalyzer:
    def __init__(self, instructions: Instructions, rom: bytes, addresses: Addresses, offset: int,
                 all_is_code: bool, no_return_from: list[int], indirect: set[int]):
        self.instructions = instructions
        self.rom = rom
        self.addresses = addresses
        self.offset = offset
        self.all_is_code = all_is_code
        # labels
        # key=address, value=type of label
        self.labels: dict[int, LabelType] = {}
        if indirect:
            for address in indirect:
                self.labels[address] = LabelType.ADDR
        # forwarding labels (= just jump to other location)
        self.forwards: dict[int, int] = {}		# key=from, value=to
        # to avoid repeating SFR warnings
        self.SFR_warnings: set[int] = set()
        self.no_return_from: set[int] = set()
        if no_return_from:
            for address in no_return_from:
                self.no_return_from.add(address)

    def __disassemble_instruction(self, pc: int) -> tuple[str, int] | None:
        if pc >= len(self.rom):
            return None

        code = self.rom[pc]
        if code in self.instructions:
            instr = self.instructions[code]
            result = instr.mnemonic
            if instr.args:
                analyzer = InstrArgsAnalyzer(
                    self.rom, pc, pc + instr.length, self.offset)
                args = []
                hints = ''
                for iarg in instr.args:
                    analyzed = analyzer.next_arg(iarg)
                    if not analyzed:
                        return None
                    (arg, val, hint) = analyzed
                    hints = hints + hint

                    if arg == ArgType.BIT and val not in self.addresses[arg.value]:
                        # extract bit number and reduce BIT to DATA
                        suffix = '.%d' % (val & 7)
                        if val >= 0x80:
                            val = val & 0xF8		    # SFR
                        else:
                            val = 0x20 | (val >> 3)     # RAM
                        arg = ArgType.DATA
                    else:
                        suffix = ''

                    if arg == ArgType.DATA and val >= 0x80 and val not in self.SFR_warnings \
                       and val not in self.addresses[arg.value]:
                        print('warning: unknown SFR %s' %
                              utils.int2hex(val), file=sys.stderr)
                        self.SFR_warnings.add(val)

                    if arg == ArgType.LABEL and val == pc:
                        # jump to self - overrides even known labels (still more readable)
                        valstr = '$'
                    elif arg.value in self.addresses and val in self.addresses[arg.value]:
                        valstr = self.addresses[arg.value][val]  # known address
                    else:
                        valstr = utils.int2hex(val)

                    args.append(valstr + suffix)

                if len(args) != len(instr.args):
                    return None

                result = result.format(*args)
                if hints:
                    result = result + '\t; ' + hints

            if instr.jump_out:
                result = result + '\n'
            return ('\t' + result, instr.length)
        else:
            return None

    def maybe_print_org_label(self, pc: int, force_org: bool, just_started: bool) -> bool:
        org = False
        if pc in self.addresses['CODE']:
            print('\norg\t%s' % self.addresses['CODE'][pc])
            org = True
        elif force_org:
            print('\norg\t%s' % utils.int2hex(pc))
            org = True
        elif just_started and pc not in self.addresses['LABEL']:
            print(';org\t%s' % utils.int2hex(pc))
        if pc in self.addresses['LABEL']:
            print('%s:' % self.addresses['LABEL'][pc])
        return org

    def dump_binary_block(self, start: int, end: int, force_org: bool) -> int:
        pc = done_to = start
        while pc < end:
            if pc + 1 < end and pc in self.labels and self.labels[pc] == LabelType.ADDR:
                result = utils.binary_word(
                    (self.rom[pc] << 8) | self.rom[pc + 1], pc)
                length = 2
            else:
                if self.rom[pc] != 0xff:
                    result = utils.binary_byte(self.rom[pc], pc)
                else:
                    result = None
                length = 1
            if result or pc in self.labels:
                if self.maybe_print_org_label(pc, force_org or (pc != done_to), pc == start):
                    force_org = False
            if result:
                print(result)
                done_to = pc + length
            pc += length
        return done_to

    def disassemble_code_block(self, start: int, end: int, force_org: bool) -> int:
        pc = start
        while pc < end:
            if self.maybe_print_org_label(pc, force_org, pc == start):
                force_org = False
            disasm = self.__disassemble_instruction(pc)
            if disasm:
                (result, length) = disasm
            else:
                # cannot disassemble -> dump binary byte
                result = utils.binary_byte(self.rom[pc], pc)
                length = 1
            print(result)
            pc += length
        return pc

    def analyze_jumps(self, start: int, entry_queue: list[int], force: bool = False) -> int:
        jumps: set[int] = set()
        pc = start
        while pc < len(self.rom):
            code = self.rom[pc]
            if code in self.instructions:
                instr = self.instructions[code]
                jump_out = instr.jump_out and not force
                if instr.args:
                    analyzer = InstrArgsAnalyzer(
                        self.rom, pc, pc + instr.length, self.offset)
                    for iarg in instr.args:
                        analyzed = analyzer.next_arg(iarg)
                        if not analyzed:
                            break
                        (arg, val, hint) = analyzed

                        if arg == ArgType.LABEL and val != pc:
                            if instr.no_jump:
                                ltype = LabelType.DPTR
                            else:
                                ltype = LabelType.JUMP
                                if pc == start and instr.jump_out:
                                    self.forwards[pc] = val
                                if val in self.no_return_from:
                                    jump_out = True
                            if val not in self.labels:
                                self.labels[val] = ltype
                                if ltype == LabelType.JUMP:
                                    jumps.add(val)

                pc += instr.length
                if jump_out:
                    break
            else:
                break

        entry_queue += jumps
        return pc

    def give_auto_labels(self) -> None:
        for address, jump in self.labels.items():
            if address not in self.addresses['LABEL']:
                if address in self.forwards:
                    fwd = self.forwards[address]
                    if fwd in self.addresses['LABEL']:
                        label = self.addresses['LABEL'][fwd]
                    else:
                        label = utils.auto_label(jump.value, fwd)
                    label = ('fwd_%04X_' % address) + label
                else:
                    label = utils.auto_label(jump.value, address)
                self.addresses['LABEL'][address] = label
