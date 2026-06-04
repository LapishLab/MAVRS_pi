#!/usr/bin/python3
import subprocess
from multiprocessing.synchronize import Event
import os
from typing import Optional
from argparse import ArgumentParser
from picamera2 import Picamera2, Preview
from picamera2.encoders import Quality, H264Encoder
from picamera2.outputs import FileOutput
from libcamera import Transform
import yaml
from config import CONFIG_YAML
from utilities import get_filename, get_stop_event
from pathlib import Path

def script_args():
	#Parse recording settings
	parser = ArgumentParser(description='Display and record video.')
	parser.add_argument('--saveDir', type=str,
		help='Path within the Data folder to which data will be saved')
	args = parser.parse_args()
	# Filter out None values and return dict
	return {k: v for k, v in vars(args).items() if v is not None}



def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None):
	with open(CONFIG_YAML, 'r') as f:
		hardware_settings = yaml.full_load(f)

	picam2 = configure_camera(hardware_settings['camera'])
	start_preview(picam2, hardware_settings['display'])
	saveFile = start_recording(picam2=picam2, save_dir=save_dir, quality=hardware_settings['camera']['quality'])

	stop_event = get_stop_event()
	if ready_event is not None:
		ready_event.set()

	# Wait until interrupted, then stop recording
	print('Video started. Waiting for interrupt.')
	stop_event.wait()
	print('closing - recordVideo.py')
	picam2.stop_recording()
	picam2.stop_preview()
	picam2.stop()
	import time
	start = time.time()
	h264_to_mp4(raw_video_path=saveFile, frameRate = picam2.video_configuration.controls.FrameRate)
	elapsed = time.time() - start
	print(f'Video conversion completed in {elapsed:.2f} seconds.')
	print('finished - recordVideo.py')


def start_recording(picam2: Picamera2, save_dir: Optional[str], quality: str):
	picam2.start()
	ext = '.h264' #raw h264 stream from picamera2
	saveFile = get_filename(save_dir=save_dir, subfolder='cam', extension=ext).as_posix() #picamera2 requires string path
	picam2.start_recording(
		output=saveFile,
		pts = saveFile.replace(ext, '.pts'),
		encoder=H264Encoder(),
		quality=Quality[quality])
	print(f'Saving video to {saveFile}')
	return saveFile


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

	#Turn off excessive libcamera info 
	os.environ["LIBCAMERA_LOG_LEVELS"]="3"

	#Need to turn ON/OFF HDR before instantiating picam2
	if camera_settings['sensor_mode'] == "HDR": 
		os.system("v4l2-ctl --set-ctrl wide_dynamic_range=1 -d /dev/v4l-subdev0") #turn on HDR
	else:
		os.system("v4l2-ctl --set-ctrl wide_dynamic_range=0 -d /dev/v4l-subdev0") #turn off HDR

	picam2 = Picamera2()
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
	return picam2

def start_preview(picam2: Picamera2, display_settings: dict):
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


def h264_to_mp4(raw_video_path: str, frameRate: float) -> None:
	output_mp4_path = raw_video_path.replace('.h264', '.mp4')
	
	if not os.path.exists(raw_video_path):
		print(f"Error: Raw video file not found at {raw_video_path}. Cannot convert to MP4.")
		return
	
	print(f"Converting raw H264 to mp4 using pts: {raw_video_path}")
	
	# FFmpeg command structure
	cmd = [
		"ffmpeg", "-y",
		"-r", str(frameRate),
		"-f", "h264",
		"-i", raw_video_path,
		"-c:v", "copy",
		output_mp4_path
	]
	
	try:
		# Run the command and hide unnecessary terminal spam
		subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
		print(f"Success! Perfect variable-framerate video saved to: {output_mp4_path}")
		
		# Optional: Delete the raw recovery files to save space
		os.remove(raw_video_path)
		# os.remove(pts_file_path)
		
	except subprocess.CalledProcessError as e:
		print(f"Muxing failed. FFmpeg Error:\n{e.stderr.decode()}")

if __name__ == "__main__":
	args = script_args()
	main(**args)
	