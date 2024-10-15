#!/usr/bin/python3
import os
from warnings import warn
from argparse import ArgumentParser
from datetime import datetime

parser = ArgumentParser(description='start an experiment')
parser.add_argument('--session', 
                    help='SessionName'
                    )
args = parser.parse_args()


scriptPath = os.path.dirname(__file__)
hostname = os.uname().nodename
if args.session is None:
        args.session= datetime.now().strftime("%Y%m%d_%H%M%S")

saveDirectory = scriptPath + '/data/' + args.session + '/' + hostname

c = 'python -u pins/recordInput.py --saveDir ' + saveDirectory
print(c)
os.system(c)

c = 'python -u mic/recordAudio.py --saveDir ' + saveDirectory
print(c)
os.system(c)

c = 'python -u cam/recordVideo.py --saveDir ' + saveDirectory
print(c)
os.system(c)