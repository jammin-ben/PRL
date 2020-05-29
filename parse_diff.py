import argparse
parser = argparse.ArgumentParser()
parser.add_argument("f1")
parser.add_argument("f2")
args=parser.parse_args()


def parse_file(filename):
	ls={}
	with open (filename,'r') as f:
		parsing=False
		for line in f.readlines():
			lins=line.split()
#			print(lins)
			if(len(lins)>0):
				if(lins[0]=="Dump"):
					parsing=not parsing
					
				if(parsing):
					ls[lins[0]]=lins[1]
	return ls	
ls1=parse_file(args.f1)
ls2=parse_file(args.f2)

print(f"Address  | {args.f1} | {args.f2}")
for addr,lease in ls1.items():
	if (addr not in ls2):
		print(f"{addr} | {lease} | NA")
	elif(ls2[addr] != ls1[addr]):
		print(f"{addr} | {lease} | {ls2[addr]} ")

for addr,lease in ls2.items():
	
	if(addr not in ls1):
		
		print(f"{addr} | NA    | {lease} ")
