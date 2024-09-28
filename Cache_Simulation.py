import argparse
import sys
import math
import random

# create the parser for the arguments
parser = argparse.ArgumentParser(description='Takes in trace file(s) as well as information about the cache.')

# create the arguments we will be parsing
parser.add_argument('-f',type=argparse.FileType('r'),action='append', help='-f <trace file name> [name of the text file with the trace]',required=True)
parser.add_argument('-s',type=int,help='-s <cache size in KB> [1KB to 8MB]')
parser.add_argument('-b',type=int,help='-b <block size> [4 bytes to 64 bytes]')
parser.add_argument('-a',type=int,help='-a <associativity> [1,2,4,8,16]')
parser.add_argument('-r',type=str,help='-r <replacement policy> [RR or RND]')

args = parser.parse_args()

# create a list of the files
files= args.f

# Cache size error checking
if args.s >= 1 and args.s <= 8192:
    pass
else:
    print(f'Cache size: {args.s}')
    print('ERROR cache size must be between 1KB and 8MB expressed as KB')
    exit(1)

# Block size error checking
if args.b < 4 or args.b > 64:
    print('ERROR: block size must be between 4 and 64 bytes')
    exit(1)

# associativity error checking
if args.a > 0 and args.a < 17 and (args.a & (args.a-1)) ==0:
    pass
else:
    print('ERROR associativity must be [1,2,4,8,16]')
    exit(1)

# replacement policy error checking
if args.r.lower() == 'rr' or args.r.lower() == 'rnd':
    pass
else:
    print('Error replacement policy must be either RR or RND')
    exit(1)

#------------- Cache Input Params -------------
# print out the header for the output
print('Cache Simulator\n')

# print out the trace file(s)
for input in sys.argv[1:]:
    if input.endswith(".trc"):
        print(f'Trace File: {input} ')
print('\n***** Cache Input Parameters *****\n')

# print out the infomation given in the command line argument

# information for cache size
if isinstance(args.s,int):
    print(f'Cache Size:\t\t\t{args.s} KB')

# information for Block size
if isinstance(args.b,int):
    print(f'Block Size:\t\t\t{args.b} bytes')

# information for the associativity
if isinstance(args.a,int):
    print(f'Associativity:\t\t\t{args.a}')

# information for the replacement policy
if isinstance(args.r,str):
    if(args.r.lower() == "rnd"):
        print(f'Replacement Policy:\t\tRandom')
    else:
        print('Replacement Policy:\t\tRound Robin')

#--------------- Cache Calculated Values ---------------
#print header for Cache Calculated values
print('\n\n***** Cache Calculated Values *****\n')

# calculate the values for the cache
blocks = args.s * math.pow(2,10)/args.b
index_bits = int(math.log2(args.s * math.pow(2,10)/(args.b * args.a)))
tag_bits = (32 - math.log2(args.b) - index_bits)
offset_bits = int(math.log2(args.b))
num_rows = int(math.pow(2, index_bits))
overhead = ((tag_bits + 1) * (blocks/8))
imp_mem = (args.s * math.pow(2,10) + overhead)/math.pow(2,10)
cost=(imp_mem * .09)
print('Total # Blocks:\t\t\t%d' % (blocks))
print('Tag Size:\t\t\t%d bits' % tag_bits)
print('Index Size:\t\t\t%d bits' % (index_bits))
print('Total # Rows:\t\t\t%d' % (num_rows))
print('Overhead Size:\t\t\t%d bytes' % (overhead))
print('Implementation Memory Size:\t%.02lf KB (%d bytes)' % (imp_mem, args.s * math.pow(2,10) + overhead))
print('Cost:\t\t\t\t$%.02lf @ ($0.09 / KB)' % cost)

#---------Trace file parsing-------------
i_len   = 0 # instruction length
i_addr  = 0 # instruction addr
dst_m   = 0 # dst write
src_m   = 0 # src read

# Create lists and arrays to be used for cache simulation
cache = [['-1' for x in range(args.a)] for y in range(num_rows)]
rr_order = [0 for x in range(num_rows)]
rnd_list = []
address_list = []
hit_rate = 0.0 
cycle_cnt = 0
instruction_cnt =0
num_accesses = 0
cache_hits = 0
blk_cnt=0
cache_misses = 0
compulsory_misses = 0
conflict_misses = 0
unused_blocks=blocks
overflow = 0
# capacity_misses = 0  # not implemented

for f in files:
    line = '\n'
    while line:
        line = f.readline()
        if line == '':
            break

        # get the length of the instruction
        i_len = int(line[5:7])

        # get the address of the instruction
        i_addr = int(line[10:18], 16)

        # increment the cycle and instruction counters
        cycle_cnt +=2
        instruction_cnt +=1

        address_list.append(i_addr)

        # read the dst_m, src_m from the file
        line = f.readline()

        dst_m = int(line[6:14], 16)
        if dst_m != 0:
            #print(f'0x{dst_m:08x}: (04)')
            cycle_cnt += 1
            address_list.append(dst_m)
            

        src_m = int(line[33:41], 16)
        if src_m != 0:
            #print(f'0x{src_m:08x}: (04)')
            cycle_cnt += 1
            address_list.append(src_m)

        # list of addresses is iterated through
        for i in range (len(address_list)):
            length = i_len if i == 0 else 4
            address = address_list[i]

            # while loop reads 1 byte at a time until it reaches 0
            while length > 0:
                # Address is broken up into index, offset, and tag values
                index = (address >> offset_bits) & int(math.pow(2,index_bits) - 1)
                offset = address & (args.b-1)
                tag = address >> (offset_bits + index_bits)
                #print(f'Address: 0x{address:08x} - Offset: 0x{offset:x} - Index: 0x{index:x} - Tag: 0x{tag:x}') # Print line used for testing address separation. Can comment out

                for block in range(args.a):
                    # if an empty block is found, the tag populates the block and the loop is exited (Compulsory miss)
                    if cache[index][block] == '-1':
                        cache[index][block] = '%x' % tag
                        compulsory_misses += 1
                        cache_misses += 1
                        unused_blocks -= 1
                        break

                   # if a block with a matching tag is found, the loop is exited (Cache hit)
                    if cache[index][block] == '%x' % tag:
                        cache_hits += 1
                        break

                    if block == (args.a - 1):
                        # Branch taken if round robin block replacement is being used
                        # if all blocks in the row are populated with different tags, then a block is chosen for replacement using round robin (Conflict miss)
                        if args.r.lower() == 'rr':
                            # if the round robin value goes beyond the number of available blocks in the row, then the counter is reset back to 0
                            if(rr_order[index] >= args.a):
                                rr_order[index] = 0
                            cache[index][rr_order[index]] = '%x' % tag
                            rr_order[index] += 1
                            conflict_misses +=1
                            cache_misses += 1
                        # Branch taken if random block replacement is being used
                        # if each block is populated, one is chosen at random to be replaced using the entire range of blocks (Conflict miss)
                        elif args.r.lower() == 'rnd':
                            random.seed()
                            cache[index][random.randint(0, args.a - 1)] = '%x' % tag
                            conflict_misses += 1
                            cache_misses += 1

                # once cache is checked for the byte read, the number of bytes is decremented by 1 and the address is incremented by 1
                length -= 1
                address += 1
                num_accesses += 1 

        # read the blank line
        f.readline()
        address_list.clear()


# Print statements used to visualize the cache, intentionally commented out
# for i in range(num_rows):
#    print('Row #', i, end=' ')
#    for j in range(args.a):
#        print('[',cache[i][j],']', end='')
#    print()

# final calculations for simulation results
cycle_cnt += cache_hits
cycle_cnt += (cache_misses * (4 * math.ceil(args.b/4)))
hit_rate = ((cache_hits * 100) / num_accesses)
cpi= (cycle_cnt/instruction_cnt)
unused_kb = ((unused_blocks * (args.b + (tag_bits + 1)/8)) / 1024)
waste = (.09 * unused_kb)

print('\n\n***** CACHE SIMULATION RESULTS *****\n')
print('Total Cache Accesses:\t%d' % num_accesses)
print('Cache Hits:\t\t%d' % cache_hits)
print('Cache Misses:\t\t%d' % cache_misses)
print('--- Compulsory Misses:\t%d' % compulsory_misses)
print('--- Conflict Misses:\t%d' % conflict_misses)


print('\n***** ***** CACHE HIT & MISS RATE ***** *****\n')
print('Hit Rate:\t\t%.04f%%' % hit_rate)
print('Miss Rate:\t\t%.04f%%' % float(100 - hit_rate))
print('CPI\t\t\t%0.2f Cycles/Instruction' % cpi)
print('Unused Cache Space:\t%.02f KB / %.02f KB = %02.02f%% Waste: $%.02f' % (unused_kb, imp_mem, (unused_kb/imp_mem)*100, waste))
print('Unused Cache Blocks:\t%d / %d' % (unused_blocks,blocks))
