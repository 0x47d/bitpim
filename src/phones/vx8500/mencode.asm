;### BITPIM
;###
;### Copyright (C) 2007 Joe Pham <djpham@bitpim.org>
;###
;### This program is free software; you can redistribute it and/or modify
;### it under the terms of the BitPim license as detailed in the LICENSE file.
;###
;### $Id$
; Filename: encode.asm
; Assemble options needed for ML: /c /Cx /coff

.386
.MODEL flat, C

.CODE

calldll  PROC long_in:DWORD, buf: PTR, dll_addr:PTR
		mov		ebx,dll_addr
		add		ebx,5150
		push	long_in
		mov		ecx,buf
		call	ebx
		ret
calldll  ENDP


END
