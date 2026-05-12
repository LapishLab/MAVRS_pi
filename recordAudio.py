#!/usr/bin/python3
import os
from pathlib import Path
from argparse import ArgumentParser
from config import default_data_path

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

if args.saveDir is None:
    saveDir = default_data_path() / 'mic'
else:
    saveDir = Path(args.saveDir)
saveDir.mkdir(parents=True, exist_ok=True)
print('SavingFile in ' + str(saveDir))

c= 'AudioMoth-Live ' + args.sampleRate
c=c + ' autosave ' + args.autoSaveInterval + ' ' + str(saveDir)

if args.heterodyne is not None:
    c=c + ' heterodyne ' + args.heterodyne
    print('Heterodyne might cause sporadic camera disconnect problems')
    

print('starting audio recording')
os.system(c)
print('recordAudio.sh finished')
