#!/usr/bin/python3
from __future__ import annotations

from multiprocessing import Process, get_context
from multiprocessing.synchronize import Event
from multiprocessing.queues import Queue
from queue import Full
import os
from typing import Optional
from argparse import ArgumentParser
from picamera2 import Picamera2, Preview
from picamera2.encoders import Quality, H264Encoder
from picamera2.outputs import FfmpegOutput, Output
from libcamera import Transform, controls
from utilities import get_filename, get_stop_event, get_settings
from videoStream import serve_video


class StreamOutput(Output):
	"""Offer encoded frames to the stream without waiting for a client."""

	def __init__(self, frames: Queue[tuple[bytes, bool]], client_connected: Event) -> None:
		super().__init__()
		self.frames = frames
		self.client_connected = client_connected
		self.dropped_frames = 0
		self.failed = False

	def outputframe(self, frame: bytes, keyframe: bool = True, timestamp: int | None = None,
			packet: object | None = None, audio: bool = False) -> None:
		if self.recording and not self.failed:
			try:
				if not self.client_connected.is_set():
					return
				self.frames.put_nowait((frame, keyframe))
			except Full:
				self.dropped_frames += 1  # A slow viewer loses frames; the MP4 never waits.
			except Exception:
				self.failed = True  # A streaming error must not reach Picamera2's encoder.


class StreamSession:
	def __init__(self, stream_settings: dict) -> None:
		frames = None
		try:
			context = get_context('spawn')
			queue_size = stream_settings.get('queue_size', 16)
			if not isinstance(queue_size, int) or queue_size < 1:
				raise ValueError('streaming.queue_size must be a positive integer')
			frames = context.Queue(maxsize=queue_size)
			frames.cancel_join_thread()  # Never wait for disposable stream frames at exit.
			client_connected = context.Event()
			stream_stop = context.Event()
			stream_process = context.Process(
				target=serve_video,
				args=(frames, client_connected, stream_stop, stream_settings.get('port', 9000)),
				daemon=True,
			)
			output = StreamOutput(frames, client_connected)
			stream_process.start()
		except Exception:
			if frames is not None:
				frames.close()
			raise

		self.output = output
		self.process = stream_process
		self.frames = frames
		self.client_connected = client_connected
		self.stop_event = stream_stop

	def stop(self) -> None:
		if self.output.failed:
			print('Video stream disabled after a queue error')
		if self.output.dropped_frames:
			print(f'Video stream dropped {self.output.dropped_frames} encoded frames')
		self.client_connected.clear()
		self.stop_event.set()
		self.process.join(timeout=2)
		if self.process.is_alive():
			self.process.terminate()
			self.process.join()
		self.frames.close()


def script_args() -> dict[str, str]:
	#Parse recording settings
	parser = ArgumentParser(description='Display and record video.')
	parser.add_argument('--saveDir', type=str,
		help='Path within the Data folder to which data will be saved')
	args = parser.parse_args()
	# Filter out None values and return dict
	return {k: v for k, v in vars(args).items() if v is not None}



def main(save_dir: Optional[str] = None, ready_event: Optional[Event] = None) -> None:
	stop_event = get_stop_event()
	hardware_settings = get_settings()
	camera_settings = hardware_settings['camera']
	stream: StreamSession | None = None
	stream_settings = hardware_settings.get('streaming', {})
	if stream_settings.get('enable', False):
		try:
			stream = StreamSession(stream_settings)
		except Exception as exc:
			print(f'Video stream unavailable: {exc}')

	picam2 = configure_camera(camera_settings)
	start_preview(picam2, hardware_settings['display'])
	start_recording(
		picam2=picam2,
		save_dir=save_dir,
		quality=camera_settings['quality'],
		frame_rate=camera_settings['frame_rate'],
		stream_output=stream.output if stream is not None else None,
	)

	if ready_event is not None:
		ready_event.set()

	# Wait until interrupted, then stop recording
	print('Video started. Waiting for interrupt.')
	stop_event.wait()
	print('closing - recordVideo.py')
	picam2.stop_recording()
	if stream is not None:
		stream.stop()
	picam2.stop_preview()
	picam2.stop()
	print('finished - recordVideo.py')


def start_recording(picam2: Picamera2, save_dir: Optional[str], quality: str, frame_rate: float = 30,
		stream_output: Optional[StreamOutput] = None) -> str:
	picam2.start()
	ext = '.mp4'
	saveFile = get_filename(save_dir=save_dir, subfolder='cam', extension=ext).as_posix() #picamera2 requires string path
	
	output = FfmpegOutput(
		output_filename=saveFile,
		pts=saveFile.replace(ext, '.pts')
		)

	picam2.start_recording(
		output=[output, stream_output] if stream_output is not None else output,
		encoder=H264Encoder(framerate=int(round(frame_rate)), repeat=True),
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
	camera_controls = {'FrameRate': frame_rate}
	autofocus = camera_settings.get('autofocus')
	lens_position = camera_settings.get('lens_position')
	if autofocus is not None and not isinstance(autofocus, bool):
		raise ValueError('camera autofocus must be true or false')
	if lens_position is not None:
		if isinstance(lens_position, bool) or not isinstance(lens_position, (int, float)) or lens_position < 0:
			raise ValueError('camera lens_position must be a non-negative number')
		if autofocus is True:
			raise ValueError('camera lens_position can only be set when autofocus is false')
		camera_controls['AfMode'] = controls.AfModeEnum.Manual
		camera_controls['LensPosition'] = float(lens_position)
	elif autofocus is not None:
		camera_controls['AfMode'] = (
			controls.AfModeEnum.Continuous if autofocus else controls.AfModeEnum.Manual
		)

	config = picam2.create_video_configuration(
		sensor={
			'output_size': sensor_mode['size'],
			'bit_depth': sensor_mode['bit_depth']
		},
		main={'size': main_size, 'format': 'YUV420'},
		raw=None,
		controls=camera_controls
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
