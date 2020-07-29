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
			
########_ALGORITHM_FUNCTIONS_##############
def build_ri_distributions(trace_file):
	distributions={} #Key: address. Value: ri_histogram object

	#read file
	with open(trace_file,'r') as f:
		lines = f.readlines()

	for line in lines:
		cells = line.split(',')
		#cells[0]: phase + address (string)
		#cells[1]: ri
		#cells[2]: tag
		#cells[3]: logical time
		if cells[0] not in distributions:
			#construct new ri_histogram object
			hist = ri_histogram(cells[0])
			#add it to distributions
			distributions[cells[0]] = hist	
		else:
			hist = distributions[cells[0]]

		#increment value of the correct histogram
		hist.add_ri(interpret_hex(cells[1]))
		
	last_address = int(lines[-1].split(",")[3])
	return distributions,last_address

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

def get_binned_hists(trace_file,bin_endpts):
	#read file
	bins={}
	binned_ri_distributions = {}
	curr_bin = 0
	bin_idx = 0
	
	bin_width = bin_endpts[1]-bin_endpts[0]

	curr_bin_dict={}
	curr_ri_distribution_dict={}

	bins[curr_bin]=curr_bin_dict
	binned_ri_distributions[curr_bin]=curr_ri_distribution_dict	

	all_keys=[]
	with open(trace_file,'r') as f:
		lines = f.readlines()

	for line in lines:
		cells = line.split(',')
		#cells[0]: address (string)
		#cells[1]: ri
		#cells[2]: tag
		#cells[3]: logical time
		
		if(int(cells[3])>curr_bin+bin_width):
			curr_bin_dict={}
			curr_ri_distribution_dict={}

			curr_bin+=bin_width
			bins[curr_bin]=curr_bin_dict
			binned_ri_distributions[curr_bin]=curr_ri_distribution_dict	
			bin_idx +=1 
			bin_width = bin_endpts[bin_idx+1]-bin_endpts[bin_idx]
			
		#handle frequency dict
		if cells[0] not in curr_bin_dict:
			curr_bin_dict[cells[0]]=1
		else:
			curr_bin_dict[cells[0]]+=1

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

	#append zeroes for addresses not in bins
	for b in bins:
		for k in all_keys:
			if k not in bins[b]:
				bins[b][k]=0
	return bins,binned_ri_distributions

#ri_distributions: distribution for each reference
#binned_freq_hists: histograms of frequency of accesses per program phase
#cache_size: number of cache blocks in fully assoc cache
#carl_order: list of Lease objects in order of PPUC
#bin_width: logical time range of each bin
def phased_CARL(addrs,binned_ri_distributions,binned_freq_hists,cache_size,carl_order,bin_endpts,consensus,sample_rate):
	#bin_idx = 0
	#bin_width = bin_endpts[bin_idx+1]-bin_endpts[bin_idx]
	#bin_target = bin_width * cache_size
	bin_targets = {}
	bin_width={}
	for i,b in enumerate(bin_endpts[:-1]):
		bin_targets[b] = (bin_endpts[i+1]-bin_endpts[i] )*cache_size
		bin_width[b] = (bin_endpts[i+1]-bin_endpts[i])

	bin_endpoints = binned_freq_hists.keys()
	num_full_bins = 0
	leases={}
	duals={} #key: Address. Value:(extended lease,probability)
	bin_saturation={}

	#initialize lease assignments to 0
	for a in addrs:
		leases[a]=0

	#initialize bin saturation to 0
	for b in bin_endpoints:
		bin_saturation[b]=0

	#go in order of PPUC	
	#print(f"bin_width: {bin_width}")
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

			if (bin_saturation[b] + impact) > bin_targets[b]:
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
				bin_cache_size_string+=str(bin_saturation[b]/bin_width[b])[:4]+','
			bin_cache_size_string=bin_cache_size_string[:-1]+']'
			print(f"Average Cache Occupancy Per Bin: {bin_cache_size_string}")
			print(f"Total cost: {bin_saturation[0]}")
		
		
		else:
			bin_ranks={}
			ordered_overflow = {}
			new_bin_saturation=bin_saturation.copy()
			
			print(f"addr: {addr} ri: {lease_assignment.ri}")
			print(f"bin targets: {bin_targets}")
			num_full_bins=0
			acceptable_ratio=0
			for b,sat in bin_saturation.items():
				if(sat>=bin_targets[b]):
					num_full_bins+=1
				new_capacity = sat + impact_dict[b]
				
				if(new_capacity >= bin_targets[b]):
					avail_space = bin_targets[b] - sat
					
					#only care about bins if the lease shows up in them
					if(impact_dict[b]!=0):
						bin_ranks[b] = avail_space / impact_dict[b]
					ordered_overflow[b]=new_capacity
					print(f"\tbin: {b} current capacity: {sat/bin_width[b]}  avg impact: {impact_dict[b]/bin_width[b]}")

			#sort capacities
			sorted_capacities = {k:v for k,v in sorted(ordered_overflow.items(), key=lambda item: item[1])}
			sorted_bins = {k:v for k,v in sorted(bin_ranks.items(), key=lambda item: item[1])}
			#for k,v in sorted_capacities.items():
			print(f"num_full_bins: {num_full_bins}")
			print("printing bin ranks sorted:")
						
			for i,b in enumerate(sorted_bins):
				print(f"\tbin: {b/bin_width[b]} rank: {sorted_bins[b]}")
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
					bin_cache_size_string+=str(bin_saturation[b]/bin_width[b])[:4]+','	
				bin_cache_size_string=bin_cache_size_string[:-1]+']'
				print(f"Assigning {addr} dual lease lease {lease_assignment.ri} * {acceptable_ratio}. Bin saturation: {bin_cache_size_string}")
	print(f"Final saturation:")
	for b,sat in bin_saturation.items():
		print(f"\t{b/bin_width[b]},{sat}")
	return leases,duals
		
def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("num_bins")	
	parser.add_argument("filename")
	args = parser.parse_args()
	
	cache_size=128
	num_bins=int(args.num_bins)
	
	num_consensus = 1
	sample_rate = 1/256
	print(f"sample rate: {sample_rate}")
	
	filename = args.filename
	ris,last_address = build_ri_distributions(filename)
	num_actual = 0
	#print("ri distributions:")
	#print(ris)
	for address,distribution in ris.items():
		print(f"{address},{distribution}")
	addrs = ris.keys()
	#bin_width = math.ceil(last_address/num_bins)
	bin_endpts=[0,1210000,2422524, 5200000, 8061438, 8061438 + (last_address - 8061438)/2 ,last_address]
	binned_freqs,binned_ri_distributions = get_binned_hists(filename,bin_endpts)
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
	
	leases,duals = phased_CARL(addrs,binned_ri_distributions,binned_freqs,cache_size,carl_order,bin_endpts,num_consensus,sample_rate)
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
