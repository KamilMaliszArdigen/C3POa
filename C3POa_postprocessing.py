#!/usr/bin/env python3
# Roger Volden and Chris Vollmers
# Last updated: 29 Mar 2018

import sys
import os
import argparse
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input_fasta_file', type=str)
parser.add_argument('-o', '--output_path', type=str)
parser.add_argument('-a', '--adapter_file', type=str)

args = parser.parse_args()
output_path = args.output_path + '/'
input_file = args.input_fasta_file
adapter_file = args.adapter_file

blat = 'blat'

def read_fasta(inFile):
    '''Reads in FASTA files, returns a dict of header:sequence'''
    readDict = {}
    tempSeqs, headers, sequences = [], [], []
    for line in open(inFile):
        line = line.rstrip()
        if not line:
            continue
        if line.startswith('>'):
            headers.append(line.split()[0][1:])
        # covers the case where the file ends while reading sequences
        if line.startswith('>'):
            sequences.append(''.join(tempSeqs).upper())
            tempSeqs = []
        else:
            tempSeqs.append(line)
    sequences.append(''.join(tempSeqs).upper())
    sequences = sequences[1:]
    for i in range(len(headers)):
        readDict[headers[i]] = sequences[i]
    return readDict

def reverse_complement(sequence):
    '''Returns the reverse complement of a sequence'''
    bases = {'A':'T', 'C':'G', 'G':'C', 'T':'A', 'N':'N', '-':'-'}
    return ''.join([bases[x] for x in list(sequence)])[::-1]

def run_blat(path, infile, adapter_fasta):
    os.system('%s -noHead -stepSize=1 -tileSize=6 -t=DNA q=DNA -minScore=15 \
              -minIdentity=10 -minMatch=1 -oneOff=1 \
              %s %s %s/Adapter_to_consensus_alignment.psl' \
              %(blat,adapter_fasta,infile,path))

def parse_blat(path, infile):
    adapter_dict = {}
    length = 0
    for line in open(infile):
        length += 1

    iterator = 0
    infile1 = open(infile, 'r')
    while iterator < length:
        line = infile1.readline()
        sequence = infile1.readline()
        name = line[1:].strip()
        adapter_dict[name] = {}
        adapter_dict[name]['+'] = []
        adapter_dict[name]['-'] = []
        adapter_dict[name]['+'].append(('-', 1, 0))
        adapter_dict[name]['-'].append(('-', 1, len(sequence)))
        iterator += 2

    for line in open(path + '/Adapter_to_consensus_alignment.psl'):
        a = line.strip().split('\t')
        read_name, adapter, strand = a[9], a[13], a[8]
        if int(a[5]) < 50 and float(a[0]) > 10:
            if strand == '+':
                  start = int(a[11]) - int(a[15])
                  end = int(a[12]) + int(a[14]) - int(a[16])
                  position = end
            if strand == '-':
                  start = int(a[11]) - int(a[14]) - int(a[16])
                  end = int(a[12]) + int(a[15])
                  position = start
            adapter_dict[read_name][strand].append((adapter,
                                                    float(a[0]),
                                                    position))
    return adapter_dict

def write_fasta_file(path, adapter_dict, reads):
    out = open(path + 'R2C2_full_length_consensus_reads.fasta', 'w')

    for name, sequence in reads.items():
      qual = float(name.split('_')[1])
      if qual >= 9:
        adapter_plus = sorted(adapter_dict[name]['+'],
                              key=lambda x: x[2], reverse=False)
        adapter_minus = sorted(adapter_dict[name]['-'],
                               key=lambda x: x[2], reverse=False)
        plus_list_name, plus_list_position = [], []
        minus_list_name, minus_list_position = [], []
        for adapter in adapter_plus:
            if adapter[0] != '-':
                plus_list_name.append(adapter[0])
                plus_list_position.append(adapter[2])
        for adapter in adapter_minus:
            if adapter[0] != '-':
                minus_list_name.append(adapter[0])
                minus_list_position.append(adapter[2])

        if len(plus_list_name) == 1 and len(minus_list_name) == 1:
            if plus_list_position[0] < minus_list_position[0]:
                seq = sequence[plus_list_position[0]:minus_list_position[0]]
                ada = sequence[plus_list_position[0]-40:minus_list_position[0]+40]
                name += '_' + str(len(seq))
                if '5Prime_adapter' in plus_list_name[0] \
                   and '3Prime_adapter' in minus_list_name[0]:
                    out.write('>%s\n%s\n' %(name, ada))
                elif '3Prime_adapter' in plus_list_name[0] \
                     and '5Prime_adapter' in minus_list_name[0]:
                    out.write('>%s\n%s\n' %(name, reverse_complement(ada)))


def main():
    reads = read_fasta(input_file)
    run_blat(output_path, input_file, adapter_file)
    adapter_dict = parse_blat(output_path, input_file)
    write_fasta_file(output_path, adapter_dict, reads)

if __name__ == '__main__':
    main()