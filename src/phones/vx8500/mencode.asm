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
