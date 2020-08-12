#step 1: implement CARL to get ordering of lease assignments

#TODO: scale down ppuc
#TODO: apply grouping

import math
import argparse
############_CLASSES_######################
#class ri_histogram():
#	def __init__(self,address):
#		self.address=address
#		self.ris = {}

#	def __repr__(self):
#		ret = "\n"
#		for ri,freq in self.ris.items():
#			ret += "\t["+str(ri)+","+str(freq)+"]\n"
#		return ret

#	def add_ri(self,ri):
#		if ri in self.ris:
#			self.ris[ri]+=1
#		else:
#			self.ris[ri]=1
#	def get_num_bins(self):
#		return len(self.ris)

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
def interpret_address(address):
	phase = (address & 0xFF000000)>>24
	addr =   address & 0x00FFFFFF
	return phase,addr


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
	total=0
	for ri,freq in distribution.items():
		if(ri <= lease and ri > 0):
			total+= ri*freq
		else:
			total+=lease*freq
	return total

def check_capacity(distributions,leases):
	total = 0
	for lease_addr,lease in leases.items():
		for addr,ris in distributions.items():
			if(addr==lease_addr):	
				for ri,freq in ris.items():
					if(ri>lease or ri<0):
						total+=lease*freq
					else:
						total+=ri*freq
	return total
			
########_ALGORITHM_FUNCTIONS_##############
def build_hists(filename):	
	with open(filename) as f:
		lines = f.readlines()
	global_hists = {} #{ref_addr : {ri : freq}}
	phase_dicts = {} #{phase(int): {ref_addr: {ri: freq}}}
	phase_populations = {}#{phase: num_accesses}
	for line in lines:
		l = line.split(',')
		phase,ref=interpret_address(interpret_hex(l[0]))
		ri = interpret_hex(l[1])
		tag = l[2]
		time = l[3]
		#Handle phase dicts
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

		#handle global hists
		if ref not in global_hists:
			global_hists[ref]={}
		dist = global_hists[ref]
		if ri not in dist:
			dist[ri]=1
		else:
			dist[ri]+=1

		if phase not in phase_populations:
			phase_populations[phase]=1
		else:
			phase_populations[phase]+=1

	return phase_dicts,global_hists,phase_populations

"""def build_ri_distributions(trace_file):
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
"""
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

def get_hit_prob(ris,lease):
	hit_prob = 0 
	for ri,freq in ris.items():
		if(ri<=lease):
			hit_prob += freq
	return hit_prob

def get_max_ppuc_single(distribution,current_lease):
	max_value = -1
	lease = None
	
	for ri,freq in distribution.items():
		#only look at increasing leases
		if ri > current_lease:
			
			#compare to old lease 
			profit = get_hit_prob(distribution,ri) - get_hit_prob(distribution,current_lease)
			cost   = get_avg_lease(distribution,ri) - get_avg_lease(distribution,current_lease)
			value  = profit / cost
			
			if value > max_value:
				max_value = value
				lease = ri
	
	return max_value,lease

"""def get_binned_hists(trace_file,bin_endpts):
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
"""
#ri_distributions: distribution for each reference
#binned_freq_hists: histograms of frequency of accesses per program phase
#cache_size: number of cache blocks in fully assoc cache
#carl_order: list of Lease objects in order of PPUC
#bin_width: logical time range of each bin
def PRL(addrs,binned_ri_distributions,phase_populations,cache_size,carl_order,consensus,sample_rate):
	phase_targets = {} #total allocation in each phase
	phase_saturation = {}

	print("DUMP PHASE POPULATIONS")
	for p in phase_populations:
		phase_populations[p] /= sample_rate
		phase_targets[p]    = phase_populations[p]*cache_size
		phase_saturation[p] = 0
		print(f"Phase {p}: NumAccesses={phase_populations[p]}")

	#num_full_bins = 0
	leases={}
	duals={} #key: Address. Value:(extended lease,probability)

	#initialize lease assignments to 0
	for a in addrs:
		leases[a]=0

	#go in order of PPUC	
	for lease_assignment in carl_order:
		addr = lease_assignment.address

		#see if any bins are overful with this assignment, as in CARL with whole program
		num_unsuitable = 0
		impact_dict = {}
		for p in phase_saturation:
			impact = 0
			avg_lease=0
			
			if(addr in binned_ri_distributions[p]):
				avg_lease = get_avg_lease(binned_ri_distributions[p][addr],lease_assignment.ri)
				old_avg_lease = get_avg_lease(binned_ri_distributions[p][addr],leases[addr])

				impact = (avg_lease - old_avg_lease)/sample_rate
				impact_dict[p] = impact
			else:
				impact_dict[p] = 0

			if (phase_saturation[p] + impact) > phase_targets[p]:
				num_unsuitable +=1

		#if no bins are overful, increse lease
		if(num_unsuitable<consensus):
			leases[addr]=lease_assignment.ri

			#update bin saturation
			avg_cache_size_string = "["
			#Increment bin saturation
			for p in phase_saturation:
				if(addr in binned_ri_distributions[p]):
					phase_saturation[p]+=impact_dict[p]
				avg_cache_size_string+="{:.2f}".format(phase_saturation[p]/phase_populations[p])+','
			avg_cache_size_string=avg_cache_size_string[:-1]+']'

			print(f"Assigning lease {lease_assignment.ri} to ref {addr}. Avg cache size: {avg_cache_size_string}")

		#Dual Lease Handling
		else:
			bin_ranks={}
			
			#num_full_bins=0
			acceptable_ratio=0
			for p,sat in phase_saturation.items():
				#if(sat>=phase_targets[p]):
				#	num_full_bins+=1
				new_capacity = sat + impact_dict[p]
				
				#if this assignment would overfill this phase
				if(new_capacity >= phase_targets[p]):
					avail_space = phase_targets[p] - sat
					
					#only care about bins if the lease shows up in them
					if(impact_dict[p]!=0):
						bin_ranks[p] = avail_space / impact_dict[p]

					#7/30 MAY NEED TO MULTIPLY BY CACHE SIZE
					print(f"\tphase: {p} avg cache size: {sat/phase_populations[p]}  avg cache impact: {impact_dict[p]/phase_populations[p]}")

			#sort capacities
			sorted_bins = {k:v for k,v in sorted(bin_ranks.items(), key=lambda item: item[1])}
			#print("printing bin ranks sorted:")
			for i,b in enumerate(sorted_bins):
				print(f"\tphase: {b} rank: {sorted_bins[b]}")
				
				#if i == num_overflowing - num_full_bins -  1:
				if i == 0:
					acceptable_ratio = sorted_bins[b]
					if(acceptable_ratio <0):
						acceptable_ratio=0
					print("\tselecting this^ bin")
			print(f"acceptable_ratio: {acceptable_ratio}")

			#Only assign dual lease if it is beneficial
			if(acceptable_ratio>0):
				duals[addr]  = (lease_assignment.ri,acceptable_ratio)
				
				#update capacities
				for p in phase_saturation:
					if(addr in binned_ri_distributions[p]):
						phase_saturation[p] += impact_dict[p]*acceptable_ratio
			
				#Print Info
				phase_cache_size_string='['
				for p in phase_saturation:
					phase_cache_size_string+=str(phase_saturation[p]/phase_populations[p])[:4]+','	
				phase_cache_size_string=phase_cache_size_string[:-1]+']'

				print(f"Assigning {addr} dual lease lease {lease_assignment.ri} * {acceptable_ratio}. Phase saturation: {phase_cache_size_string}")


	return leases,duals
		
def main():
	parser = argparse.ArgumentParser()
	parser.add_argument("num_bins")	
	parser.add_argument("filename")
	args = parser.parse_args()
	
	cache_size=128
	#num_bins=int(args.num_bins)
	
	num_consensus = 1
	sample_rate = 1/256
	print(f"sample rate: {sample_rate}")
	
	filename = args.filename
	
	#ris,last_address = build_ri_distributions(filename)
	phase_dicts,global_hists,phase_populations = build_hists(filename)
	
	#for address,distribution in ris.items():
	#	print(f"{address},{distribution}")
	print(f"DUMP RI HISTOGRAMS")
	for phase,dist in phase_dicts.items():
		print(f"phase {phase}")
		for ref,hist in dist.items():
			print(f"| ref {ref}")
			for ri,freq in hist.items():
				print(f"| | ri {ri} freq {freq}")

	addrs = global_hists.keys()
	#bin_endpts=[0,1210000,2422524, 5200000, 8061438, 8061438 + (last_address - 8061438)/2 ,last_address]
	#binned_freqs,binned_ri_distributions = get_binned_hists(filename,bin_endpts)

	carl_order = carl(global_hists)
	print("DUMP GLOBAL CARL ORDER <Ref,RI,delata_PPUC>")	
	for l in carl_order:
		print(l)
	
	leases,duals = PRL(addrs,phase_dicts,phase_populations,cache_size,carl_order,num_consensus,sample_rate)
	print("DUMP LEASES")
	#for address,tup in duals.items():
	#	lease = tup [0]
	#	percentage = tup [1]
	#	print(f"{address} {hex(lease)[2:]} percentage {percentage}")
	#	print(f"{address} {hex(leases[address])[2:]} percentage {1 - percentage}")
		#leases.remove(lease)

	for address,lease in leases.items():
		if(address in duals):
			print(f"0, {address}, {hex(lease)[2:]}, {hex(duals[address][0])[2:]}, {1 - duals[address][1]} ")
		else:
			print(f"0, {address}, {hex(lease)[2:]}, 0, 1 ")

	print("Dump dual leases")
	print()
if __name__=="__main__":
	main()
