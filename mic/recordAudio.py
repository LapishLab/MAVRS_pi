#!/usr/bin/python3
import os
#from warnings import warn
from argparse import ArgumentParser
from datetime import datetime

#Parse recording settings
parser = ArgumentParser(description='Record audio.')
parser.add_argument('--autoSaveInterval', '-a', 
                    help='Length of each audiofile in minutes (default 5)',
                    default='5')
parser.add_argument('--sampleRate', '-r', 
                    help='Sample rate (default 250,000 Hz)',
                    default='250000')
parser.add_argument('--saveDir', 
                    help='Path within the Data folder to which data will be saved'
                    )
parser.add_argument('--heterodyne', '-z', 
                    help='Heterodyne frequency for audio output (default 20,000 Hz)'
                    )

args = parser.parse_args()

scriptPath = os.path.dirname(__file__)
dataDir = os.path.dirname(scriptPath) + '/data/'
if args.saveDir is None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = os.uname().nodename
        args.saveDir= now + '/' + hostname
saveDirectory=dataDir + args.saveDir


if not os.path.exists(saveDirectory):
    os.makedirs(saveDirectory)
print('SavingFile in '+saveDirectory)

c= 'AudioMoth-Live ' + args.sampleRate
c=c + ' autosave ' + args.autoSaveInterval + ' ' + saveDirectory

if args.heterodyne is not None:
    c=c + ' heterodyne ' + args.heterodyne
    warn('Heterodyne might cause sporadic camera disconnect problems')
    

print('starting audio recording')
os.system(c)
print('recordAudio.sh finished')
