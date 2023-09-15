import os
import argparse
from hashlib import sha256
import random
import string
import sys
import struct

def proof_of_work_okay(chall, solution, hardness):
    h = sha256(chall.encode('ASCII') + struct.pack('<Q', solution)).hexdigest()
    return int(h, 16) < 2**256 / hardness

def solve_proof_of_work(task):
    hardness, task = task.split('_')
    hardness = int(hardness)

    ''' You can use this to solve the proof of work. '''
    print('Creating proof of work for {} (hardness {})'.format(task, hardness))
    i = 0
    while True:
        if i % 1000000 == 0: print('Progress: %d' % i)
        if proof_of_work_okay(task, i, hardness):
            return i
        i += 1

if __name__ == '__main__':
    
    if len(sys.argv) > 1:
        challenge = sys.argv[1]
    else:
        sys.stdout.write('Challenge? ')
        sys.stdout.flush()
        challenge = input()
    print('Solution: {}'.format(solve_proof_of_work(challenge)))