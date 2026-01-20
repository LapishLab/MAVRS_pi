"""Read lines from a serial port (raw bytes) and save each line to a text file as a
binary representation (each byte as an 8-bit string).
"""

from os.path import join, dirname
from os import makedirs
from datetime import datetime
import serial
import time
from serial.tools import list_ports

# port = 'COM15'
# rate = 115200
rate = 250000 # gotta go fast

def main(saveDir):    
    ser = open_serial_port(rate)

    start_time = time.time() # more performant than datetime.now()
    timeString = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    data_file = join(saveDir, f'{timeString}.txt')
    makedirs(dirname(data_file), exist_ok=True)
    print(f"Logging data to {data_file}...")
    with open(data_file, 'w', encoding='utf-8') as f:
        while True:
            line = ser.readline().decode('utf-8').strip()
            elapsed_time = time.time() - start_time
            f.write(f"{elapsed_time:.4f},{line}\n")

def open_serial_port(rate):
    while True:
        try:
            port = find_open_port()
            ser = serial.Serial(port, rate, timeout=None)
            return ser
        except Exception as e:
            print(f"Failed to open serial port {port}: {e}")
            print(f"retrying in 5 seconds...")
            time.sleep(5)


def list_com_ports():
    ports = list_ports.comports()
    if not ports:
        print("No serial/com ports found.")
        return

    print("Available serial ports:")
    for p in ports:
        # p.device is the device name (e.g., COM3)
        # p.description gives a human-readable description
        print(f"- {p.device}: {p.description}")

def find_open_port():
    while True:
        ports = list_ports.comports()
        if ports:
            return ports[0].device
        else:
            print("No serial/com ports found. Trying again in 5 seconds")
            time.sleep(5)
            

if __name__ == "__main__":
    #Parse recording settings
    from argparse import ArgumentParser
    parser = ArgumentParser(description='from serial port')
    parser.add_argument('--saveDir', 
                        help='Path within the Data folder to which data will be saved'
                        )
    args = parser.parse_args()

    main(args.saveDir)