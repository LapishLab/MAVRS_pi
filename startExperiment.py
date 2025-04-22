#!/usr/bin/python3
import os
from warnings import warn
from argparse import ArgumentParser
from datetime import datetime
from subprocess import Popen

parser = ArgumentParser(description='start an experiment')
parser.add_argument('--session', 
                    help='SessionName'
                    )
args = parser.parse_args()


scriptPath = os.path.dirname(__file__)
hostname = os.uname().nodename
if args.session is None:
        args.session= datetime.now().strftime("%Y%m%d_%H%M%S")

saveDirectory = args.session + '/' + hostname

Popen(['python', '-u', scriptPath+'/pins/recordInput.py', '--saveDir', saveDirectory + '/gpio'])
Popen(['python', '-u', scriptPath+'/mic/recordAudio.py', '--saveDir', saveDirectory + '/mic'])
Popen(['python', '-u', scriptPath+'/cam/recordVideo.py', '--saveDir', saveDirectory + '/cam'])