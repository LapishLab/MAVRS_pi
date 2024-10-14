#! /bin/python
import signal, os
from sys import exit
from warnings import warn
from time import sleep
from argparse import ArgumentParser
from gpiozero import Button 
from datetime import datetime
from csv import DictWriter

#Parse recording settings
parser = ArgumentParser(description='Record GPIO pin 16')
parser.add_argument('--duration', 
                    type=int, 
                    help='Recording duration in seconds (default=86400s)',
                    default='86400')
parser.add_argument('--saveDir', 
                    help='Path within the Data folder to which data will be saved'
                    )
args = parser.parse_args()

pins = [16]  # List of GPIO pins to monitor 
csvFields = ['Time', 'Pin', 'Event']

scriptPath = os.path.dirname(__file__)
dataDir = os.path.dirname(scriptPath) + '/data/'
if args.saveDir is None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = os.uname().nodename
        args.saveDir= now + '/' + hostname
saveDirectory=dataDir + args.saveDir

if os.path.exists(saveDirectory):
    warn("directory already exists. Other recordings could already be in "+saveDirectory)
else:
    os.makedirs(saveDirectory)


saveFile = saveDirectory + '/DigitalIn.csv'
print('SavingFile as '+saveFile)

# Create or open the CSV file and write the header 
with open(saveFile, "w", newline='') as csvfile: 
    writer = DictWriter(csvfile, fieldnames=csvFields) 
    writer.writeheader() 

def log_event(pin,event): 
    timeString = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    with open(saveFile, "a", newline='') as csvfile: 
        writer = DictWriter(csvfile, fieldnames=csvFields) 
        writer.writerow({'Time': timeString, 'Pin': pin, 'Event': event}) 

# Set up the GPIO pins and add event detection 
buttons = [Button(pin,bounce_time=0.1) for pin in pins]
for button in buttons: 
    button.when_released = lambda pin=button.pin.number: log_event(pin,'1') 
    button.when_pressed = lambda pin=button.pin.number: log_event(pin,'0') 

def endRecording(sig, frame):
    print('recordInput.py finished')
    exit(0)

signal.signal(signal.SIGINT, endRecording)
signal.signal(signal.SIGTERM, endRecording)

print('waiting for a duration of '+str(args.duration) + ' seconds')
sleep(args.duration)
endRecording(0,None)