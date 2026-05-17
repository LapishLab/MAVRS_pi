import time
from pathlib import Path
from argparse import ArgumentParser

#Parse recording settings
parser = ArgumentParser(description='Test script')
parser.add_argument(
	'--saveDir', 
	help='Path within the Data folder to which data will be saved'
)
parser.add_argument(
	'--fname',
	help='Filename to save data to (without extension)'
)
args = parser.parse_args()

saveDir = Path(args.saveDir)
saveDir.mkdir(parents=True, exist_ok=True)
saveFile = saveDir / f'{args.fname}.txt'
print('SavingFile as ' + str(saveFile))

i = 0
while True:
	print(f'Writing {i}')
	with open(saveFile, "a", newline='') as f: 
		f.write(str(i))
	i+=1
	time.sleep(1)