# Disassembler 8051/8052
#
# Dictionary of opcodes and instructions
#
# Copyright (c) 2022 Aleksander Mazur
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

import enum
from typing import Iterator
from . import utils


class ArgType(enum.Enum):
    IMM = 'IMM'
    DATA = 'DATA'
    BIT = 'BIT'
    LABEL = 'LABEL'
    REL = 'REL'
    ADDR = 'ADDR'


class Instruction:
    def __init__(self, code: int, length: int, mnemonic: str, args: list[ArgType] | None = None,
                 jump_out: bool = False, no_jump: bool = False):
        self.code = code
        self.length = length
        self.mnemonic = mnemonic
        self.args = args
        self.jump_out = jump_out
        self.no_jump = no_jump

    def __str__(self) -> str:
        if self.args:
            mnemonic = self.mnemonic.format(*self.args)
        else:
            mnemonic = self.mnemonic
        return '%02X (%d) %s' % (self.code, self.length, mnemonic)


class Instructions:
    def __init__(self) -> None:
        self.instructions: dict[int, Instruction] = {}

        for (msb, mnemonic) in {
                0x00: 'inc',
                0x10: 'dec',
                0x20: 'add A,',
                0x30: 'addc A,',
                0x40: 'orl A,',
                0x50: 'anl A,',
                0x60: 'xrl A,',
                0x90: 'subb A,',
                0xC0: 'xch A,',
                0xD0: ('xchd A,', '', False),
                0xE0: 'mov A,',
                0xF0: ('mov', ', A', True),
        }.items():
            if type(mnemonic) is tuple:
                prefix, suffix, direct = mnemonic
            else:
                prefix = mnemonic
                suffix = ''
                direct = True
            for reg in range(0, 1+1):
                self.__add(Instruction(msb | (reg + 6), 1,
                           '%s @R%d%s' % (prefix, reg, suffix)))
            if direct:
                for reg in range(0, 7+1):
                    self.__add(Instruction(msb | (reg + 8), 1,
                               '%s R%d%s' % (prefix, reg, suffix)))

        for reg in range(0, 7+1):
            self.__add(Instruction(0x78 | reg, 2,
                       'mov R%d, #{0}' % reg, [ArgType.IMM]))
            self.__add(Instruction(0x88 | reg, 2,
                       'mov {0}, R%d' % reg, [ArgType.DATA]))
            self.__add(Instruction(0xA8 | reg, 2,
                       'mov R%d, {0}' % reg, [ArgType.DATA]))
            self.__add(Instruction(0xB8 | reg, 3, 'cjne R%d, #{0}, {1}' % reg, [
                       ArgType.IMM, ArgType.REL]))
            self.__add(Instruction(0xD8 | reg, 2,
                       'djnz R%d, {0}' % reg, [ArgType.REL]))

        for addr in range(0, 8):
            self.__add(Instruction(0x01 | (addr << 5), 2,
                       'ajmp {0}', [ArgType.ADDR], jump_out=True))
            self.__add(Instruction(0x11 | (addr << 5),
                       2, 'acall {0}', [ArgType.ADDR]))

        self.__add(Instruction(0x00, 1, 'nop'))
        self.__add(Instruction(0x02, 3, 'ljmp {0}', [
                   ArgType.LABEL], jump_out=True))
        self.__add(Instruction(0x03, 1, 'rr A'))
        self.__add(Instruction(0x04, 1, 'inc A'))
        self.__add(Instruction(0x05, 2, 'inc {0}', [ArgType.DATA]))
        self.__add(Instruction(0x10, 3, 'jbc {0}, {1}', [
                   ArgType.BIT, ArgType.REL]))
        self.__add(Instruction(0x12, 3, 'lcall {0}', [ArgType.LABEL]))
        self.__add(Instruction(0x13, 1, 'rrc A'))
        self.__add(Instruction(0x14, 1, 'dec A'))
        self.__add(Instruction(0x15, 2, 'dec {0}', [ArgType.DATA]))
        self.__add(Instruction(0x20, 3, 'jb {0}, {1}', [
                   ArgType.BIT, ArgType.REL]))
        self.__add(Instruction(0x22, 1, 'ret', jump_out=True))
        self.__add(Instruction(0x23, 1, 'rl A'))
        self.__add(Instruction(0x24, 2, 'add A, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x25, 2, 'add A, {0}', [ArgType.DATA]))
        self.__add(Instruction(0x30, 3, 'jnb {0}, {1}', [
                   ArgType.BIT, ArgType.REL]))
        self.__add(Instruction(0x32, 1, 'reti', jump_out=True))
        self.__add(Instruction(0x33, 1, 'rlc A'))
        self.__add(Instruction(0x34, 2, 'addc A, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x35, 2, 'addc A, {0}', [ArgType.DATA]))
        self.__add(Instruction(0x40, 2, 'jc {0}', [ArgType.REL]))
        self.__add(Instruction(0x42, 2, 'orl {0}, A', [ArgType.DATA]))
        self.__add(Instruction(0x43, 3, 'orl {0}, #{1}', [
                   ArgType.DATA, ArgType.IMM]))
        self.__add(Instruction(0x44, 2, 'orl A, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x45, 2, 'orl A, {0}', [ArgType.DATA]))
        self.__add(Instruction(0x50, 2, 'jnc {0}', [ArgType.REL]))
        self.__add(Instruction(0x52, 2, 'anl {0}, A', [ArgType.DATA]))
        self.__add(Instruction(0x53, 3, 'anl {0}, #{1}', [
                   ArgType.DATA, ArgType.IMM]))
        self.__add(Instruction(0x54, 2, 'anl A, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x55, 2, 'anl A, {0}', [ArgType.DATA]))
        self.__add(Instruction(0x60, 2, 'jz {0}', [ArgType.REL]))
        self.__add(Instruction(0x62, 2, 'xrl {0}, A', [ArgType.DATA]))
        self.__add(Instruction(0x63, 3, 'xrl {0}, #{1}', [
                   ArgType.DATA, ArgType.IMM]))
        self.__add(Instruction(0x64, 2, 'xrl A, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x65, 2, 'xrl A, {0}', [ArgType.DATA]))
        self.__add(Instruction(0x70, 2, 'jnz {0}', [ArgType.REL]))
        self.__add(Instruction(0x72, 2, 'orl C, {0}', [ArgType.BIT]))
        self.__add(Instruction(0x73, 1, 'jmp @A + DPTR', jump_out=True))
        self.__add(Instruction(0x74, 2, 'mov A, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x75, 3, 'mov {0}, #{1}', [
                   ArgType.DATA, ArgType.IMM]))
        self.__add(Instruction(0x76, 2, 'mov @R0, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x77, 2, 'mov @R1, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x80, 2, 'sjmp {0}', [
                   ArgType.REL], jump_out=True))
        self.__add(Instruction(0x82, 2, 'anl C, {0}', [ArgType.BIT]))
        self.__add(Instruction(0x83, 1, 'movc A, @A + PC'))
        self.__add(Instruction(0x84, 1, 'div AB'))
        self.__add(Instruction(0x85, 3, 'mov {1}, {0}', [
                   ArgType.DATA, ArgType.DATA]))
        self.__add(Instruction(0x86, 2, 'mov {0}, @R0', [ArgType.DATA]))
        self.__add(Instruction(0x87, 2, 'mov {0}, @R1', [ArgType.DATA]))
        self.__add(Instruction(0x90, 3, 'mov DPTR, #{0}', [
                   ArgType.LABEL], no_jump=True))
        self.__add(Instruction(0x92, 2, 'mov {0}, C', [ArgType.BIT]))
        self.__add(Instruction(0x93, 1, 'movc A, @A + DPTR'))
        self.__add(Instruction(0x94, 2, 'subb A, #{0}', [ArgType.IMM]))
        self.__add(Instruction(0x95, 2, 'subb A, {0}', [ArgType.DATA]))
        self.__add(Instruction(0xA0, 2, 'orl C, /{0}', [ArgType.BIT]))
        self.__add(Instruction(0xA2, 2, 'mov C, {0}', [ArgType.BIT]))
        self.__add(Instruction(0xA3, 1, 'inc DPTR'))
        self.__add(Instruction(0xA4, 1, 'mul AB'))
        self.__add(Instruction(0xA5, 1, 'dec DPTR'))
        self.__add(Instruction(0xA6, 2, 'mov @R0, {0}', [ArgType.DATA]))
        self.__add(Instruction(0xA7, 2, 'mov @R1, {0}', [ArgType.DATA]))
        self.__add(Instruction(0xB0, 2, 'anl C, /{0}', [ArgType.BIT]))
        self.__add(Instruction(0xB2, 2, 'cpl {0}', [ArgType.BIT]))
        self.__add(Instruction(0xB3, 1, 'cpl C'))
        self.__add(Instruction(0xB4, 3, 'cjne A, #{0}, {1}', [
                   ArgType.IMM, ArgType.REL]))
        self.__add(Instruction(0xB5, 3, 'cjne A, {0}, {1}', [
                   ArgType.DATA, ArgType.REL]))
        self.__add(Instruction(
            0xB6, 3, 'cjne @R0, #{0}, {1}', [ArgType.IMM, ArgType.REL]))
        self.__add(Instruction(
            0xB7, 3, 'cjne @R1, #{0}, {1}', [ArgType.IMM, ArgType.REL]))
        self.__add(Instruction(0xC0, 2, 'push {0}', [ArgType.DATA]))
        self.__add(Instruction(0xC2, 2, 'clr {0}', [ArgType.BIT]))
        self.__add(Instruction(0xC3, 1, 'clr C'))
        self.__add(Instruction(0xC4, 1, 'swap A'))
        self.__add(Instruction(0xC5, 2, 'xch A, {0}', [ArgType.DATA]))
        self.__add(Instruction(0xD0, 2, 'pop {0}', [ArgType.DATA]))
        self.__add(Instruction(0xD2, 2, 'setb {0}', [ArgType.BIT]))
        self.__add(Instruction(0xD3, 1, 'setb C'))
        self.__add(Instruction(0xD4, 1, 'da A'))
        self.__add(Instruction(0xD5, 3, 'djnz {0}, {1}', [
                   ArgType.DATA, ArgType.REL]))
        self.__add(Instruction(0xE0, 1, 'movx A, @DPTR'))
        self.__add(Instruction(0xE2, 1, 'movx A, @R0'))
        self.__add(Instruction(0xE3, 1, 'movx A, @R1'))
        self.__add(Instruction(0xE4, 1, 'clr A'))
        self.__add(Instruction(0xE5, 2, 'mov A, {0}', [ArgType.DATA]))
        self.__add(Instruction(0xF0, 1, 'movx @DPTR, A'))
        self.__add(Instruction(0xF2, 1, 'movx @R0, A'))
        self.__add(Instruction(0xF3, 1, 'movx @R1, A'))
        self.__add(Instruction(0xF4, 1, 'cpl A'))
        self.__add(Instruction(0xF5, 2, 'mov {0}, A', [ArgType.DATA]))

        for code in range(0, 0x100):
            assert code in self.instructions, 'missing instruction for opcode %s' % utils.int2hex(
                code)

    def __add(self, instruction: Instruction) -> None:
        assert instruction.code not in self.instructions, 'duplicate opcode %s' % str(
            instruction)
        self.instructions[instruction.code] = instruction

    def __str__(self) -> str:
        result = ''
        for code in range(0, 0x100):
            result = result + '\n' + str(self.instructions[code])
        return result[1:]

    def __getitem__(self, code: int) -> Instruction:
        return self.instructions[code]

    def __iter__(self) -> Iterator[int]:
        return iter(self.instructions)
