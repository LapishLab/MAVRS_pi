#!/usr/bin/python3
import signal, os
from sys import exit
#from warnings import warn
from time import sleep
from argparse import ArgumentParser
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from picamera2 import Preview
from libcamera import Transform


os.system("v4l2-ctl --set-ctrl wide_dynamic_range=1 -d /dev/v4l-subdev0") #turn on HDR
#os.system("v4l2-ctl --set-ctrl wide_dynamic_range=0 -d /dev/v4l-subdev0") #turn off HDR
os.environ["DISPLAY"] = ':0' 



#Turn off Info and warning logging
Picamera2.set_logging(Picamera2.ERROR)
os.environ["LIBCAMERA_LOG_LEVELS"]="3"

#Parse recording settings
parser = ArgumentParser(description='Display and record video.')
parser.add_argument('--duration', 
                    type=int, 
                    help='Recording duration in seconds (default=86400s)',
                    default='86400')
parser.add_argument('--noSave', 
                    action='store_true',
                    help='No file is saved. Screen still displays the video')
parser.add_argument('--saveDir', 
                    help='Path within the Data folder to which data will be saved'
                    )
parser.add_argument('--sensorMode', 
                    help='Mode number of the camera sensor',
                    type=int,
                    default='0'
                    )
parser.add_argument('--bitrate', 
                    help='Bitrate of video (compression level)',
                    type=int,
                    default='10000000'
                    )

args = parser.parse_args()

#Start PiCamera2
picam2 = Picamera2()

#Configure camera
print('configuring camera')
mode = picam2.sensor_modes[args.sensorMode]
config = picam2.create_video_configuration(
    sensor={
        'output_size': mode['size'],
        'bit_depth': mode['bit_depth']
    }
)
picam2.configure(config)

#Start preview window
print('Starting preview window')
picam2.start_preview(
    Preview.QTGL, 
    width=800, 
    height=480, 
    x=0, 
    y=0,
    transform=Transform(
        hflip=1,
        vflip=1
    )
)
picam2.title_fields = [
    "ExposureTime",
    "FrameDuration",
    "Lux"
    ]

# Set up encoder
if not args.noSave:
    print('Setting up H264 encoder')
    encoder = H264Encoder(
        bitrate=args.bitrate,
        framerate=mode['fps']
        )
    scriptPath = os.path.dirname(__file__)
    dataDir = os.path.dirname(scriptPath) + '/data/'
    if args.saveDir is None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = os.uname().nodename
        args.saveDir= now + '/' + hostname
    saveDirectory=dataDir + args.saveDir

    if not os.path.exists(saveDirectory):
        os.makedirs(saveDirectory)

    now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    saveFile = saveDirectory + '/' + now
    
    
    output = FfmpegOutput(
        output_filename=saveFile+'.mp4',
        pts=saveFile+'.pts'
        )
    picam2.start_encoder(
        encoder=encoder,
        output=output
        )
picam2.start()

#Record for specified duration
def endRecording(sig, frame):
    picam2.stop()
    if not args.noSave:
        picam2.stop_encoder()
    print('recordVideo.py finished')
    exit(0)

signal.signal(signal.SIGINT, endRecording)
signal.signal(signal.SIGTERM, endRecording)
print('waiting for a duration of '+str(args.duration) + ' seconds')
sleep(args.duration)
endRecording(0,None)