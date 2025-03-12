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
import yaml

def main():
    #Turn off Info and warning logging
    Picamera2.set_logging(Picamera2.ERROR)
    os.environ["LIBCAMERA_LOG_LEVELS"]="3"

    experiment_options = parse_arguments()
    hardware_settings = load_hardware_settings()
    (picam2, sensor_mode) = configure_camera(hardware_settings['camera'])
    if hardware_settings['display']['enable']:
        configure_preview(picam2, hardware_settings['display'])
    if not experiment_options.noSave:
        saveFile = parse_save_file(experiment_options.saveDir)
        start_recording(picam2, hardware_settings['camera']['bitrate'], saveFile)
    picam2.start()

    #Record for specified duration
    def endRecording(sig, frame):
        picam2.stop()
        if not experiment_options.noSave:
            picam2.stop_encoder()
        print('recordVideo.py finished')
        exit(0)

    signal.signal(signal.SIGINT, endRecording)
    signal.signal(signal.SIGTERM, endRecording)
    print('waiting for a duration of '+str(experiment_options.duration) + ' seconds')
    sleep(experiment_options.duration)
    endRecording(0,None)

def parse_arguments():
    #Parse recording settings
    parser = ArgumentParser(description='Display and record video.')
    parser.add_argument('--duration', 
                        type=int, 
                        help='Recording duration in seconds (default=86400s)',
                        default='30')
    parser.add_argument('--noSave', 
                        action='store_true',
                        help='No file is saved. Screen still displays the video')
    parser.add_argument('--saveDir', 
                        help='Path within the Data folder to which data will be saved'
                        )
    return parser.parse_args()

def load_hardware_settings():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    default_yaml = script_dir + "/default_settings.yaml"
    with open(default_yaml, 'r') as f:
            default_settings = yaml.full_load(f)
    return default_settings

def configure_camera(camera_settings):
    if camera_settings['sensor_mode'] == 0:
        os.system("v4l2-ctl --set-ctrl wide_dynamic_range=1 -d /dev/v4l-subdev0") #turn on HDR
        sensor_ind = 0
    else:
        os.system("v4l2-ctl --set-ctrl wide_dynamic_range=0 -d /dev/v4l-subdev0") #turn off HDR
        sensor_ind = camera_settings['sensor_mode']-1

    picam2 = Picamera2()

    sensor_mode = picam2.sensor_modes[sensor_ind]
    config = picam2.create_video_configuration(
        sensor={
            'output_size': sensor_mode['size'],
            'bit_depth': sensor_mode['bit_depth']
        }
    )
    picam2.configure(config)
    return (picam2, sensor_mode)

def configure_preview(picam2, display_settings):
    os.environ["DISPLAY"] = ':0' 

    print('Starting preview window')
    picam2.start_preview(
        Preview.QTGL, 
        width=display_settings['size_x'], 
        height=display_settings['size_y'], 
        x=0, 
        y=0,
        transform=Transform(
            hflip=display_settings['horizontal_flip'],
            vflip=display_settings['vertical_flip']
        )
    )
    picam2.title_fields = display_settings['title_fields']

def parse_save_file(saveDir):
    scriptPath = os.path.dirname(__file__)
    dataDir = os.path.dirname(scriptPath) + '/data/'
    if saveDir is None:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = os.uname().nodename
        saveDir= now + '/' + hostname
    saveDirectory=dataDir + saveDir

    if not os.path.exists(saveDirectory):
        os.makedirs(saveDirectory)

    now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    saveFile = saveDirectory + '/' + now
    return saveFile

def start_recording(picam2, bitrate, saveFile):
    print('Setting up H264 encoder')
    encoder = H264Encoder(
        bitrate=bitrate#,
        #framerate=sensor_mode['fps']
    )
    output = FfmpegOutput(
        output_filename=saveFile+'.mp4',
        pts=saveFile+'.pts'
    )
    picam2.start_encoder(
        encoder=encoder,
        output=output
    )









if __name__ == "__main__":
    main()