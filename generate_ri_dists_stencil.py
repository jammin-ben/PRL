for i in range(1024):
	for j in range(1024):
		print(f"a[i][j],{i}:{j}")
		print(f"a[i][j-1],{i}:{j-1}")
		print(f"a[i][j+1],{i}:{j+1}")
		print(f"a[i-1][j],{i-1}:{j}")
		print(f"a[i+1][j],{i+1}:{j}")
		print(f"b[i][j],{0:0}")


