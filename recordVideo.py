#!/usr/bin/python3
from multiprocessing.synchronize import Event
import signal, os
import threading
from pathlib import Path
from typing import Optional
from argparse import ArgumentParser
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import Quality
from picamera2.outputs import FfmpegOutput
from picamera2 import Preview
from libcamera import Transform
import yaml
from config import default_data_path, CONFIG_YAML

picam2 = None # set in configure_camera()


def script_args():
    #Parse recording settings
    parser = ArgumentParser(description='Display and record video.')
    parser.add_argument('--saveDir', type=str,
        help='Path within the Data folder to which data will be saved')
    args = parser.parse_args()
    # Filter out None values and return dict
    return {k: v for k, v in vars(args).items() if v is not None}

def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None):
    if save_dir is None:
        save_dir = default_data_path()
    else:
        save_dir = Path(save_dir)
    save_dir = save_dir /  'cam'
    save_dir.mkdir(parents=True, exist_ok=True)

    #Turn off excessive libcamera info 
    os.environ["LIBCAMERA_LOG_LEVELS"]="3"

    hardware_settings = load_hardware_settings()
    configure_camera(hardware_settings['camera'])
    start_preview(hardware_settings['display'])

    # Set up save file
    now = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output = FfmpegOutput(
        output_filename= str(save_dir / f'{now}.mp4'),
        pts = str(save_dir / f'{now}.pts')
        )
    picam2.start_and_record_video(
        output = output,
        quality = Quality[hardware_settings['camera']['quality']]
        )

    # Define a signal handler to cleanly exit on interrupt
    stop_event = threading.Event()
    stop_func = lambda sig, frame: stop_event.set()
    stop_signals = [signal.SIGINT, signal.SIGTERM]
    [signal.signal(sig, stop_func) for sig in stop_signals]

    # Wait until interrupted, then stop recording
    print('Video started. Waiting for interrupt.')
    if ready_event is not None:
        ready_event.set()
    stop_event.wait()
    print('closing - recordVideo.py')
    picam2.stop_recording()
    print('finished - recordVideo.py')

def load_hardware_settings():
    with open(CONFIG_YAML, 'r') as f:
            default_settings = yaml.full_load(f)
    return default_settings

def configure_camera(camera_settings):
    match camera_settings['sensor_mode']: 
        case 'low_res':
            sensor_mode_index = 0
        case 'medium_res':
            sensor_mode_index = 1
        case 'high_res':
            sensor_mode_index = 2
        case _: # Default to HDR
            camera_settings['sensor_mode'] = 'HDR'
            sensor_mode_index = 0

    if camera_settings['sensor_mode'] == "HDR": #Need to turn ON/OFF HDR before instantiating picam2
        os.system("v4l2-ctl --set-ctrl wide_dynamic_range=1 -d /dev/v4l-subdev0") #turn on HDR
    else:
        os.system("v4l2-ctl --set-ctrl wide_dynamic_range=0 -d /dev/v4l-subdev0") #turn off HDR

    global picam2
    picam2 = Picamera2() #Need to turn ON/OFF HDR before instantiating picam2
    sensor_mode = picam2.sensor_modes[sensor_mode_index]
    
    max_H264_res = (1920,1080)
    if sensor_mode['size'][0] > max_H264_res[0]:
        main_size = (1280,720)
    else:
        main_size = sensor_mode['size']
    config = picam2.create_video_configuration(
        sensor={
            'output_size': sensor_mode['size'],
            'bit_depth': sensor_mode['bit_depth']
        },
        main={'size': main_size}
    )
    picam2.align_configuration(config) #set optimal image size for main stream
    picam2.configure(config)

def start_preview(display_settings):
    if display_settings['enable']:
        print('Starting preview window')
        os.environ["DISPLAY"] = ':0' 
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

if __name__ == "__main__":
    args = script_args()
    main(**args)