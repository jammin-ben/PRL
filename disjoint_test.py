class SharedRef():
	def __init__(self,p1,p2,d):
		self.p1 = p1
		self.p2=p2
		self.d=d
	def __repr__(self):
		return str(self.p1) +"," + str(self.p2) + '\n\t' + str(self.d)

def interpret_address(address):
	phase = (address & 0xFF000000)>>24
	addr =   address & 0x00FFFFFF
	return phase,addr

def convert_to_signed(num):
	if num & 0x8000000:
		return num - 0x100000000
	else: return num

def interpret_hex(string):
	newstring='0x'+string
	return convert_to_signed(int(newstring,16))
	#return int(newstring,16)



def build_hists(filename):
	
	with open(filename) as f:
		phase_dicts = {} #key = phase(int) value = dict

		lines = f.readlines()
		for line in lines:
			l = line.split(',')
			phase,ref=interpret_address(interpret_hex(l[0]))
			ri = interpret_hex(l[1])
			tag = l[2]
			time = l[3]
			if phase not in phase_dicts:
				phase_dicts[phase] = {} #key = ref , value = dict{}
			p=phase_dicts[phase]
			if ref not in p:
				p[ref] = {} #key =ri, value=freq
			dist = p[ref]
			if ri not in dist:
				dist[ri]= 1
			else:
				dist[ri]+=1
			
	return phase_dicts

def get_union(phase_dicts):
	union = []
	for p in phase_dicts:
		for p2 in phase_dicts:
			if p!=p2:
				for r in phase_dicts[p]:
					if r in phase_dicts[p2]:
						union.append(SharedRef(p,p2,phase_dicts[p][r]))
	print(len(union))
	return union


phase_dicts=build_hists("lease_hardware_sampler/sampling_files/9b_phases/3mm_small_rand.txt")
print("DUMPING PHASE DICTS")
for phase,Dict in phase_dicts.items():
	print(f"Phase {phase}")
	for ref,hist in Dict.items():
		print(f"| Ref {ref}")
		for ri,freq in hist.items():
			print(f"| | ri {ri} freq {freq}")

print("+"*80)
print("COMPUTING SET UNION")
u = get_union(phase_dicts)
for un in u:
	print(un)


