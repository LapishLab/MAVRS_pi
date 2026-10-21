#!/usr/bin/python3
from multiprocessing.synchronize import Event
import os
from typing import Optional
from argparse import ArgumentParser
from picamera2 import Picamera2, Preview
from picamera2.encoders import Quality, H264Encoder
from picamera2.outputs import PyavOutput
from libcamera import Transform
from utilities import get_filename, get_stop_event, get_settings

def script_args() -> dict[str, str]:
	#Parse recording settings
	parser = ArgumentParser(description='Display and record video.')
	parser.add_argument('--saveDir', type=str,
		help='Path within the Data folder to which data will be saved')
	args = parser.parse_args()
	# Filter out None values and return dict
	return {k: v for k, v in vars(args).items() if v is not None}



def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None) -> None:
	hardware_settings = get_settings()
	camera_settings = hardware_settings['camera']

	picam2 = configure_camera(camera_settings)
	start_preview(picam2, hardware_settings['display'])
	start_recording(
		picam2=picam2,
		save_dir=save_dir,
		quality=camera_settings['quality'],
		frame_rate=camera_settings['frame_rate']
	)

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
	print('finished - recordVideo.py')


def start_recording(picam2: Picamera2, save_dir: Optional[str], quality: str, frame_rate: float = 30) -> str:
	picam2.start()
	ext = '.mp4'
	saveFile = get_filename(save_dir=save_dir, subfolder='cam', extension=ext).as_posix() #picamera2 requires string path
	
	output = PyavOutput(
		output_name=saveFile,
		pts = saveFile.replace(ext, '.pts')
		)
	
	picam2.start_recording(
		output=output,
		encoder=H264Encoder(framerate=int(round(frame_rate))),
		quality=Quality[quality])
	print(f'Saving video to {saveFile}')
	return saveFile


def configure_camera(camera_settings: dict) -> Picamera2:
	sensor_mode_name = camera_settings['sensor_mode']

	#Turn off excessive libcamera info 
	os.environ["LIBCAMERA_LOG_LEVELS"]="3"

	#Need to turn ON/OFF HDR before instantiating picam2
	if sensor_mode_name == "HDR":
		os.system("v4l2-ctl --set-ctrl wide_dynamic_range=1 -d /dev/v4l-subdev0") #turn on HDR
	else:
		os.system("v4l2-ctl --set-ctrl wide_dynamic_range=0 -d /dev/v4l-subdev0") #turn off HDR

	picam2 = Picamera2()
	sensor_modes = sorted(picam2.sensor_modes, key=lambda mode: mode['size'][0] * mode['size'][1])
	match sensor_mode_name:
		case 'low_res' | 'HDR':
			sensor_mode = sensor_modes[0]
		case 'medium_res':
			sensor_mode = sensor_modes[1]
		case 'high_res':
			sensor_mode = sensor_modes[2]
		case _:
			raise ValueError(f'Unknown camera sensor mode: {sensor_mode_name}')

	requested_frame_rate = camera_settings.get('frame_rate')
	if requested_frame_rate is None:
		frame_rate = sensor_mode['fps']
	elif requested_frame_rate > sensor_mode['fps']:
		print(
			f'Requested {requested_frame_rate} FPS, but {sensor_mode_name} supports at most '
			f'{sensor_mode["fps"]:.2f} FPS. Using the supported maximum.'
		)
		frame_rate = sensor_mode['fps']
	else:
		frame_rate = requested_frame_rate
	camera_settings['frame_rate'] = frame_rate

	requested_resolution = camera_settings.get('resolution')
	if requested_resolution is None:
		if sensor_mode['size'][0] > 1920 or sensor_mode['size'][1] > 1080:
			main_size = (1280,720)
		else:
			main_size = sensor_mode['size']
	else:
		if (
			not isinstance(requested_resolution, (list, tuple))
			or len(requested_resolution) != 2
			or not all(isinstance(value, int) and value > 0 for value in requested_resolution)
		):
			raise ValueError('camera resolution must be [width, height] using positive integers')
		max_output_size = (
			min(sensor_mode['size'][0], 1920),
			min(sensor_mode['size'][1], 1080)
		)
		main_size = (
			min(requested_resolution[0], max_output_size[0]),
			min(requested_resolution[1], max_output_size[1])
		)
		if main_size != tuple(requested_resolution):
			print(
				f'Requested resolution {tuple(requested_resolution)}, but {sensor_mode_name} supports '
				f'at most {max_output_size} for H.264. Using the supported maximum.'
			)
		camera_settings['resolution'] = main_size
	config = picam2.create_video_configuration(
		sensor={
			'output_size': sensor_mode['size'],
			'bit_depth': sensor_mode['bit_depth']
		},
		main={'size': main_size, 'format': 'YUV420'},
		raw=None,
		controls={'FrameRate': frame_rate}
	)
	picam2.align_configuration(config) #set optimal image size for main stream
	picam2.configure(config)
	return picam2

def start_preview(picam2: Picamera2, display_settings: dict) -> None:
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
