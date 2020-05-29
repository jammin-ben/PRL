import ctypes

num=0xffffffff
print(num)
print(ctypes.c_long(num).value)
def convert_to_signed(num):
	if num & 0x8000000:
		return num - 0x100000000
	else: return num

print(convert_to_signed(num))
		
