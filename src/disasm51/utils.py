# Disassembler 8051/8052
#
# Utility functions
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

def int2hex(x):
    s = '%02Xh' % x
    if not s[0].isdigit():
        s = '0' + s
    return s


def binary_hint(byte):
    s = '%3d' % byte
    if byte >= 0x80:
        s = s + (' %4d' % (byte - 0x100))
    c = chr(byte)
    if c.isprintable():
        s = s + (" '%s'" % c)
    return s


def binary_byte(byte, pc):
    return '\tdb %s\t; [%04Xh] %s' % (int2hex(byte), pc, binary_hint(byte))


def binary_word(word, pc):
    return '\tdw %s\t; [%04Xh]' % (int2hex(word), pc)


def auto_label(prefix, address):
    return '%s_%04X' % (prefix, address)
