# Disassembler 8051/8052
#
# Symbols and associated addresses
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

import sys
import re
from typing import TextIO, Iterator
from . import utils


class Addresses:
    pat = re.compile(
        r';?(?P<label>[a-zA-Z0-9_]+)\s+(?P<scope>[A-Z]+)\s+(?P<addr>[0-9A-F]+)(?P<hex>h|H)?')

    def __init__(self) -> None:
        self.addr: dict[str, dict[int, str]] = {}
        # offsets in code segment used for emitting ORG statements
        self.addr['CODE'] = {}
        self.addr['DATA'] = {}  # symbols in data segment (direct addressing)
        self.addr['BIT'] = {}  # symbols in bit segment
        # symbols in code segment used for emitting labels
        self.addr['LABEL'] = {}

    def __str__(self) -> str:
        s = ''
        for k, v in self.addr.items():
            s += ('\n%s: ' % k) + str(v)
        return s[1:]

    def include(self, f: TextIO) -> dict[str, int]:
        starts = {}
        for line in f.readlines():
            line = line[:-1]
            m = Addresses.pat.match(line)
            if m:
                label = m.group('label')
                scope = m.group('scope').upper()
                base = m.group('hex')
                if base:
                    base = 16
                else:
                    base = 10
                addr = int(m.group('addr'), base)
                if scope in self.addr:
                    if addr in self.addr[scope]:
                        print('warning: overriding %s %s from %s to %s' % (
                            scope, utils.int2hex(addr), self.addr[scope][addr], label), file=sys.stderr)
                    self.addr[scope][addr] = label
                if scope == 'CODE':
                    starts[label] = addr
            elif len(line) > 0 and line[0] != ';':
                print('warning: unrecognized definition: %s' %
                      line, file=sys.stderr)
        return starts

    def __getitem__(self, scope: str) -> dict[int, str]:
        return self.addr[scope]

    def __iter__(self) -> Iterator[str]:
        return iter(self.addr)
