Disassembler for 8051/8052
==========================

Disassembler written in Python, aiming at producing human-readable
assembly code out of a binary ROM dump. Generated assembly code
can be assembled back to identical binary file with an assembler
like [asem-51].

Usage
-----

First of all, try to figure out the hardware used to run the code you
have and get appropriate MCU file (e.g. from [mcufiles]).
For example, if it's **AT89C2051**, you'll need *89c2051.mcu*.
If you are unsure, you can start from some generic file like *8052.mcu*.

Now let's try
```
disasm51.py --force --include 89c2051.mcu program.bin > program.asm
```
This will disassemble everything (including blocks of data) as code.

If you are not happy with the result, retry without `--force`.
You'll see disssembly of locations reachable from reset interrupt vector
only (and data dumps everywhere else).

Try to figure out what interrupt handlers are used by checking which
interrupts are enabled (look for operations on IE SFR or individual
interrupt flags). Then add entrypoints to the command line:
```
disasm51.py --include 89c2051.mcu --entry RESET --entry TIMER0 --entry EXTI0 --entry EXTI1 --entry SINT program.bin > program.asm
```
In simpler programs this might be enough, but usually there is still
some code reachable only by indirect calls. Check the assembly output
for `JMP @A + DPTR`. If that's the case, you'll need to figure out
the missing entry points and supply it to the disassembler.
Just check the `dptr_XXXX` label refered by the code near indirect
jump. Typically it could be an array of `ACALL` instructions.
For example, if you see an array of such calls starting at 0065h
and ending before 0077h, pass
```
--entry 0x65:0x77
```
(no need to supply each jump separately).
In case the array mixes such jumps with data (like machine states or
recognized characters), e.g. there is a one byte and a jump and so on,
use
```
--entry 0x27C:0x2BE:3
```
where 027Ch is the address of first jump instruction.
If there is no regular pattern, the last resort is to supply each
entry point separately
```
--entry 0x5BF --entry 0x5D5 --entry 0x5DD --entry 0x5E0 --entry 0x5E3 --entry 0x5E6 --entry 0x5E9 --entry 0x5F3 --entry 0x600 --entry 0x603 --entry 0x606 --entry 0x609 --entry 0x60C --entry 0x60F --entry 0x612
```

Another technique you may encounter is a call followed by data.
Such data is misdetected as code by default, since calls are supposed to
return. However, the called procedure may take off return address from
the stack (usually into DPH, DPL) and use it to establish the target
of a following indirect jump.
In such case you need to tell disasm51.py that there is in fact no
return from such call. If you see something like
```asm
	lcall jump_069E
	...
jump_069E:
	...
	pop DPH
	pop DPL
	...
```
just give
```
--no-return-from 0x69E
```
Once you figure out the indirect jumps scheme in the following array,
use `--entry` as before.

However, in case there are just addresses instead of jump instructions,
like in following case:
```asm
	movc A, @A + DPTR
	mov R0, A
	mov A, #01h	;   1
	movc A, @A + DPTR
	mov DPL, A
	mov DPH, R0
	clr A
	jmp @A + DPTR
```
you can use
```
--indirect 0x27C:0x2BE:3
```
what means there are 16-bit long big endian addresses starting at
027Ch, ending before 02BEh, separated by 1 byte of data (in other words,
3 bytes one after another).
Addresses which appear at refered locations will be dumped with **dw**
instead of **db** and, more importantly, added to known entry points.

Polishing
---------
Once you finish separating data from code, you may want to analyze
the code further and assign descriptive names to labels and data and bit
addresses. This can be done with the help of a dedicated include file
using syntax similar to *.mcu* file.

For example, if you supply following file as second `--include`:
```
multiplex_framebuffer	DATA	20h
multiplex_phase		BIT	1
multiplex_disabled	BIT	16

;timer0_cont		LABEL	0024h
;timer0_skip_multiplex	LABEL	0033h
```
disasm51.py will produce:
```asm
	...
	addc A, #0F1h	; 241  -15 'ñ'
	mov TH0, A
	setb TR0
	sjmp timer0_cont


org	SINT
	reti

timer0_cont:
	jb multiplex_disabled, timer0_skip_multiplex
	mov R0, multiplex_framebuffer
	anl P3, #0F9h	; 249   -7 'ù'
	mov P1, @R0
	inc R0
	mov P3, @R0
	cpl multiplex_phase
timer0_skip_multiplex:
	...
```

Note
----
Copyright © 2022 Aleksander Mazur

[asem-51]: http://plit.de/asem-51
[mcufiles]: http://plit.de/asem-51/mcufiles.zip
