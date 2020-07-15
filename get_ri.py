class ri_histogram():
	def __init__(self,address):
		self.address=address
		self.ris = {}

	def __repr__(self):
		ret = "\n"
		for ri,freq in self.ris.items():
			ret += "\t["+str(ri)+","+str(freq)+"]\n"
		return ret

	def add_ri(self,ri):
		if ri in self.ris:
			self.ris[ri]+=1
		else:
			self.ris[ri]=1
	def get_num_bins(self):
		return len(self.ris)

def build_ri_distributions(trace_file):
	distributions={} #Key: address. Value: ri_histogram object

	#read file
	with open(trace_file,'r') as f:
		lines = f.readlines()

	for line in lines:
		cells = line.split(',')
		#cells[0]: address (string)
		#cells[1]: ri
		if cells[0] not in distributions:
			#construct new ri_histogram object
			hist = ri_histogram(cells[0])
			#add it to distributions
			distributions[cells[0]] = hist	
		else:
			hist = distributions[cells[0]]

		#increment value of the correct histogram
		hist.add_ri(cells[1])
		
	return distributions

ds=build_ri_distributions("stencil_trace.txt")
for d in ds:
	print(ds[d])

