#step 1: implement CARL to get ordering of lease assignments

#TODO: scale down ppuc
#TODO: apply grouping

import math
import argparse
############_CLASSES_######################
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

class Lease():
	def __init__(self,address,ri):
		self.address=address
		self.ri=ri
		self.ri_dual=ri
		self.ppuc=0
		self.dual_prob=0
	def __repr__(self):
		return str(self.address)+','+str(self.ri)+','+str(self.ppuc)
	def set_ppuc(self,ppuc):
		self.ppuc=ppuc
	def set_ppuc_dual(self,ppuc_dual,dual_prob):
		self.ppuc_dual=ppuc_dual
		self.dual_prob=dual_prob
		
	
		
########_HELPER_FUNCTIONS_###############

def convert_to_signed(num):
	if num & 0x8000000:
		return num - 0x100000000
	else: return num

def trim_zeroes(string):
	newstring=""
	for char in string:
		if char != '0':
			newstring+=char
	return newstring

def interpret_hex(string):
	newstring='0x'+string
	return convert_to_signed(int(newstring,16))
	#return int(newstring,16)

def get_avg_lease(distribution,lease):
	#ri hist is the dictionary from a distribuiton object. Key: ri. Value: freq
	ri_hist = distribution.ris
	total=0
	for ri,freq in ri_hist.items():
		if(ri <= lease and ri > 0):
			total+= ri*freq
		else:
			total+=lease*freq
	return total

def check_capacity(distributions,leases):
	total = 0
	for lease_addr,lease in leases.items():
		for addr,hist_obj in distributions.items():
			if(addr==lease_addr):
				ris = hist_obj.ris				
				for ri,freq in ris.items():
					if(ri>lease or ri<0):
						total+=lease*freq
					else:
						total+=ri*freq
	return total

def get_set(n_block_capacity, idx_tag, n_way):
	if(n_way != n_block_capacity):
		return idx_tag & (int(n_block_capacity / n_way) - 1)
	else:
		return 0
########_ALGORITHM_FUNCTIONS_##############
def build_ri_distributions(trace_file):
	distributions={} #Key: address. Value: ri_histogram object
	
	#read file
	with open(trace_file,'r') as f:
		lines = f.readlines()

	for line in lines:
		cells = line.split(',')
		#cells[0]: address (string)
		#cells[1]: ri
		#cells[2]: logical time
		if cells[0] not in distributions:
			#construct new ri_histogram object
			hist = ri_histogram(cells[0])
			#add it to distributions
			distributions[cells[0]] = hist	
		else:
			hist = distributions[cells[0]]

		#increment value of the correct histogram
		hist.add_ri(interpret_hex(cells[1]))
		
	return distributions

def carl(distributions):

	carl_order = []
	addrs = distributions.keys()
	leases={}

	#initialize lease assignments to 0
	for a in addrs:
		leases[a]=0

	while(True):
		opt_ref,opt_lease,delta_ppuc = get_max_ppuc(distributions,leases)
		if(delta_ppuc>0):
			leases[opt_ref]=opt_lease
			l = Lease(opt_ref,opt_lease)
			l.set_ppuc(delta_ppuc)
			carl_order.append(l)
		else:
			break
	print("len(carl_order):")
	print(len(carl_order))

	return carl_order
	
def get_max_ppuc(distributions,current_leases):
	max_value = 0
	opt_lease = None
	opt_ref = None
	for reference,distribution in distributions.items():
		value,lease = get_max_ppuc_single(distribution,current_leases[reference])
		if(value>max_value):
			max_value=value
			opt_lease=lease
			opt_ref=reference
	return opt_ref,opt_lease,max_value

def test_max_ppuc_single(distributions,address):
	lease = 0

	print(distributions[address]) 
	while(True):
		for reference,distribution in distributions.items():
			if(distribution.address==address):
				print("================")
				max_value,newlease = get_max_ppuc_single(distribution,lease)
				lease=newlease
				print(f"newlease: {newlease} Value: {max_value}")
				if(max_value==0):
					break

def get_hit_prob(distribution,lease):
	ris = distribution.ris
	hit_prob = 0 
	for ri,freq in ris.items():
		if(ri<=lease):
			hit_prob += freq
	return hit_prob

def get_max_ppuc_single(distribution,current_lease):
	max_value = -1
	ris=distribution.ris
	lease = None
	
	for ri,freq in ris.items():
		#only look at increasing leases
		if ri > current_lease:
			
			#compare to old lease 
			profit = get_hit_prob(distribution,ri) - get_hit_prob(distribution,current_lease)
			cost   = get_avg_lease(distribution,ri) - get_avg_lease(distribution,current_lease)
			value  = profit / cost
			
			#print(f"\t(Lease,Old_Lease):    ({ri},{current_lease})")
			#print(f"\t(P_new,P_Old):        ({get_hit_prob(distribution,ri)},{get_hit_prob(distribution,current_lease)})")
			#print(f"\t(avg_l_new,avg_l_old):({get_avg_lease(distribution,ri)},{get_avg_lease(distribution,current_lease)})")
			#print(f"\tppuc:                  {value}")
			#print(f"\t__________________")
			#update max value
			if value > max_value:
				max_value = value
				lease = ri
	
	return max_value,lease

def get_binned_hists(trace_file,n_block_capacity,n_way):
	#read file
	binned_ri_distributions = {} #ri dist in each set
	
	#curr_bin = 0
	for i in range(int(n_block_capacity/n_way)):
		binned_ri_distributions[i] = {}
		
	all_keys=[]
	with open(trace_file,'r') as f:
		lines = f.readlines()

	for line in lines:
		cells = line.split(',')
		#cells[0]: ref (string)
		#cells[1]: ri
		#cells[2]: tag
		#cells[3]: logical time
			
		set_idx = get_set(n_block_capacity,interpret_hex(cells[2]),n_way)
		curr_ri_distribution_dict=binned_ri_distributions[set_idx]

	
		#handle ri distribution dict
		if cells[0] not in curr_ri_distribution_dict:
			#construct new ri_histogram object
			hist = ri_histogram(cells[0])
			#add it to curr_ri_distribution_dict
			curr_ri_distribution_dict[cells[0]] = hist	
		else:
			hist = curr_ri_distribution_dict[cells[0]]
		#increment value of the correct histogram
		hist.add_ri(interpret_hex(cells[1]))

		#keep track of all addresses seen
		if(cells[0] not in all_keys):
			all_keys.append(cells[0])
	trace_length=len(lines)
	return binned_ri_distributions,trace_length

#ri_distributions: distribution for each reference
#carl_order: list of Lease objects in order of PPUC
#bin_width: logical time range of each bin
def set_PRL(addrs,binned_ri_distributions,carl_order,consensus,sample_rate,n_block_capacity,n_way,trace_length):
	print(f"TRACE LENGTH: {trace_length}")
	bin_target = trace_length * n_way
	#bin_target = bin_width * cache_size
	num_full_bins = 0
	leases={}
	duals={} #key: Address. Value:(extended lease,probability)
	bin_saturation={}

	#initialize lease assignments to 0
	for a in addrs:
		leases[a]=0

	#initialize bin saturation to 0
	for i in range(int(n_block_capacity/n_way)):

		bin_saturation[i]=0

	#go in order of PPUC	
	for lease_assignment in carl_order:
		addr = lease_assignment.address

		#see if any bins are overful with this assignment, as in CARL with whole program
		num_unsuitable = 0
		impact_dict = {}

		for b in bin_saturation:
			impact = 0
			#frequency=0
			avg_lease=0
			
			if(addr in binned_ri_distributions[b]):
				#frequency = binned_freq_hists[b][addr]
				avg_lease = get_avg_lease(binned_ri_distributions[b][addr],lease_assignment.ri)
				
				#change as of 6/2: Don't double add impact
				old_avg_lease = get_avg_lease(binned_ri_distributions[b][addr],leases[addr])
				
				#impact = avg_lease / sample_rate
				impact = (avg_lease - old_avg_lease)/sample_rate
				impact_dict[b] = impact
			else:
				impact_dict[b] = 0

			if (bin_saturation[b] + impact) > bin_target:
				num_unsuitable +=1

		#if no bins are overful, increse lease
		if(num_unsuitable<consensus):
			leases[addr]=lease_assignment.ri
			#update bin saturation
			print(f"assigning lease {lease_assignment.ri} to address {addr}")
			bin_cache_size_string = "["
			#Increment bin saturation
			for b in bin_saturation:
				if(addr in binned_ri_distributions[b]):
					bin_saturation[b]+=impact_dict[b]
				bin_cache_size_string+=str(bin_saturation[b]/trace_length)[:4]+','
			bin_cache_size_string=bin_cache_size_string[:-1]+']'
			print(f"Average Cache Occupancy Per Bin: {bin_cache_size_string}")
			print(f"Total cost: {bin_saturation[0]}")
		
		
		else:
			bin_ranks={}
			ordered_overflow = {}
			new_bin_saturation=bin_saturation.copy()
			
			print(f"addr: {addr} ri: {lease_assignment.ri}")
			print(f"bin target: {bin_target}")
			num_full_bins=0
			acceptable_ratio=0
			for b,sat in bin_saturation.items():
				if(sat>=bin_target):
					num_full_bins+=1
				new_capacity = sat + impact_dict[b]
				
				if(new_capacity >= bin_target):
					avail_space = bin_target - sat
					
					#only care about bins if the lease shows up in them
					if(impact_dict[b]!=0):
						bin_ranks[b] = avail_space / impact_dict[b]
					ordered_overflow[b]=new_capacity

			#sort capacities
			sorted_capacities = {k:v for k,v in sorted(ordered_overflow.items(), key=lambda item: item[1])}
			sorted_bins = {k:v for k,v in sorted(bin_ranks.items(), key=lambda item: item[1])}
			#for k,v in sorted_capacities.items():
			print(f"num_full_bins: {num_full_bins}")
			print("printing bin ranks sorted:")
						
			for i,b in enumerate(sorted_bins):
				if i == consensus - num_full_bins -  1:
					acceptable_ratio = sorted_bins[b]
					if(acceptable_ratio <0):
						acceptable_ratio=0
					print("\tselecting this^ bin")
			
		#	if(len(sorted_bins) < consensus):
				#we reach this state only when there are several full bins with no instance of this reference, hence the allocation is fine
		#		acceptable_ratio=1			

			print(f"acceptable_ratio: {acceptable_ratio}")

			#change as of 6/1: Only assign dual lease if it is beneficial
			if(acceptable_ratio>0):
				duals[addr]  = (lease_assignment.ri,acceptable_ratio)
				
				#update capacities
				for b in bin_saturation:
					if(addr in binned_ri_distributions[b]):
						bin_saturation[b] += impact_dict[b]*acceptable_ratio
			
				#Print Info
				bin_cache_size_string='['
				for b in bin_saturation:
					bin_cache_size_string+=str(bin_saturation[b]/trace_length)[:4]+','	
				bin_cache_size_string=bin_cache_size_string[:-1]+']'
				print(f"Assigning {addr} dual lease lease {lease_assignment.ri} * {acceptable_ratio}. Bin saturation: {bin_cache_size_string}")
	print(f"Final saturation:")
	for b,sat in bin_saturation.items():
		print(f"\t{b},{sat / trace_length}")
	return leases,duals
		
def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("num_way")	
	parser.add_argument("filename")
	args = parser.parse_args()
	
	cache_size=128
	n_block_capacity=cache_size
	n_way=int(args.num_way)
	num_consensus = 1
	sample_rate = 1/64
	print(f"sample rate: {sample_rate}")
	
	filename = args.filename
	ris = build_ri_distributions(filename)
	num_actual = 0
	#print("ri distributions:")
	#print(ris)
	#for address,distribution in ris.items():
	#	print(f"{address},{distribution}")
	addrs = ris.keys()
	binned_ri_distributions,trace_length = get_binned_hists(filename,n_block_capacity,n_way)
	trace_length/=sample_rate
	#print("printing bin frequencies")
	#for endpoint,d in binned_freqs.items():
#		print(endpoint)
#		print(d)

#	print("printing binned ri distributions:")
#	for endpoint,d in binned_ri_distributions.items():
#		print(endpoint)
#		print(d)

	carl_order = carl(ris)
	print("Printing carl assignment order:")	
	for l in carl_order:
		print(l)
	
	leases,duals = set_PRL(addrs,binned_ri_distributions,carl_order,num_consensus,sample_rate,n_block_capacity,n_way,trace_length)
	print("Dump single leases (last one may be dual)")
	for address,tup in duals.items():
		lease = tup [0]
		percentage = tup [1]
		print(f"{address} {hex(lease)[2:]} percentage {percentage}")
		print(f"{address} {hex(leases[address])[2:]} percentage {1 - percentage}")
		#leases.remove(lease)

	for address,lease in leases.items():
		if(address not in duals):
			print(f"{address} {hex(lease)[2:]}")
	print("Dump dual leases")
	print()
if __name__=="__main__":
	main()
