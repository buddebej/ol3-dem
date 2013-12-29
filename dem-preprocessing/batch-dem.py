#!/usr/bin/python
import subprocess, argparse, os, time, sys, shutil
from tile_border_neighbours import TileBorderComputer
from tile_colorencode import ColorEncoder

class ExecuteCommand():
	def __init__(self,verbose):
		self.durations = []
		self.verbose = verbose
		pass

	def now(self):
		return time.time()

	def printCurrentTime(self,timestamp):
		print (time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()))

	def time(self,n):
		return self.durations[n]

	# calls commandline tools in silent/verbose mode and registers runtime
	def executeCMD(self, c):
		start = self.now()
		self.printCurrentTime(self.now())
		if self.verbose:
			subprocess.call(c, shell=True)
		else:
			with open(os.devnull, 'w') as silent:
				subprocess.call(c, shell=True, stdout=silent)
		self.durations.append("{0:.2f} minutes".format((self.now()-start)/60.0))

	# instanciates python objects and registers runtime
	def executePY(self, p):
		start = self.now()
		self.printCurrentTime(self.now())
		p.start()
		self.durations.append("{0:.2f} minutes".format((self.now()-start)/60.0))



def parseArguments():
	parser = argparse.ArgumentParser(description='Produces a set of tiles of a input dem dataset.')
	parser.add_argument('-i','--input', help='Input dem. Can be *vrt or any other format that can be read by gdal.',required=True)
	parser.add_argument('-o','--output', help='Path for temporary files and tiles.',required=True)
	parser.add_argument('-s','--scheme', help='Tile Scheme of output tiles. Supported are TMS and XYZ (default).',required=False)
	parser.add_argument('-a','--archive', help='Creates archive with tiles (default false).',required=False, action='store_true')	
	parser.add_argument('-tf','--temp', help='Keep temporary files (default false).',required=False, action='store_true')	
	parser.add_argument('-m','--multithread', help='If set, multithreading is deactivated (default true). This functionality is only experimental',required=False,action='store_false')		
	parser.add_argument('-t','--threads', help='Number of threads (8). This functionality is only experimental',required=False)		
	parser.add_argument('-b','--buffer', help='Number of tiles in buffer (40).This functionality is only experimental',required=False)		
	parser.add_argument('-v','--verbose', help='Allow verbose console output.',required=False, action='store_true')	
	parser.add_argument('-n','--dst-nodata', help='Nodata value in tiles (default -500).',required=False)

	return parser.parse_args()

def main():
	args = parseArguments()
	ps = ExecuteCommand(args.verbose) 

	if args.scheme:
		tileScheme = args.scheme
	else:
		tileScheme = 'xyz'

	if args.threads:
		mThreads = args.threads
	else:
		mThreads = 8

	if args.buffer:
		mBuffer = args.buffer
	else:
		mBuffer = 40

	tilesOutput = args.output
	demInput = args.input
	multiThread = args.multithread
	demName = os.path.split(args.input)[1]
	tempPath = os.path.join(tilesOutput,os.path.splitext(demName)[0]+'.'+tileScheme)
	tilesDestination = os.path.join(tilesOutput,'tiles')

	# delete destination folder if already exists
	if os.path.isdir(tilesDestination):
		shutil.rmtree(tilesDestination)

	# clear screen
	os.system('clear')

	print ("Start processing: {demName}".format(demName=demName))
	print('------------------------------------')
	print ("Input Dem: {input}\nWriting tiles to {output}".format(input=args.input, output=tilesDestination))

	print('\n\nCreating tiles (tif).')
	ps.executeCMD("python tiler-tools/gdal_tiler.py --dst-nodata=-500 -p {scheme} --tile-format='tif' --base-resampling='cubic' --overview-resampling='bilinear' {input} -t {output}".format(input=demInput,output=tilesOutput,scheme=tileScheme))

	print('\n\nCompute tile border values based on the neighbouring tiles (tif).')
 	ps.executePY(TileBorderComputer(tileScheme,tempPath,multiThread,mThreads,mBuffer))

	print('\n\nEncode elevation values and create final tiles (png).')
	ps.executePY(ColorEncoder(tempPath+'-with-neighbour-values',multiThread,mThreads,mBuffer))

	# clean up temporary files if flag is set
	if not args.temp:
		print('\n\nCleaning up temporary files.')
		shutil.rmtree(tempPath+'-with-neighbour-values')
		shutil.rmtree(tempPath)

	shutil.move(tempPath+'-with-neighbour-values-colorencoded', tilesDestination)

	# create tar archive of computed tileset
	if args.archive:
		print('\n\nCreating archive of tiles')
		ps.executeCMD("tar -cf {archivePath} {tilefolder}".format(tilefolder=tilesDestination,archivePath=os.path.join(tilesOutput,'tiles.tar')))

	print('')
	print('------------------------------------')
	print('done.')
	print('')
	print "tiler-tools: {total}".format(total=ps.time(0))
	print "tiles-neighbour-borders: {total}".format(total=ps.time(1))
	print "tiles-colorencode: {total}".format(total=ps.time(2))
	if args.archive:
		print "create archive and clean temporary files: {total}".format(total=ps.time(3))
	print('------------------------------------')


if __name__ == '__main__':
    main()   
