import ctypes, os
libc = ctypes.CDLL(None)
for _ in range(10):
    p = libc.malloc(1024)
    libc.free(p)
