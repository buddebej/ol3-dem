#!/usr/bin/python
import subprocess, argparse, os, time, sys, shutil
from tile_border_neighbours import TileBorderComputer
from tile_colorencode import ColorEncoder

class ExecuteCommand():
	def __init__(self,verbose):
		self.durations = {}
		self.verbose = verbose
		pass

	def now(self):
		return time.time()

	def printCurrentTime(self,timestamp):
		print (time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime()))

	def time(self,n):
		return self.durations[n]

	# calls commandline tools in silent/verbose mode and registers runtime
	def executeCMD(self, index, msg, c):
		start = self.now()
		print("\n{app}: {output}".format(app=index,output=msg))
		self.printCurrentTime(self.now())
		if self.verbose:
			subprocess.call(c, shell=True)
		else:
			with open(os.devnull, 'w') as silent:
				subprocess.call(c, shell=True, stdout=silent)
		self.durations[index]=("{0:.2f} minutes".format((self.now()-start)/60.0))

	# instanciates python objects and registers runtime
	def executePY(self, index, msg, p):
		start = self.now()
		print("\n{app}: {output}".format(app=index,output=msg))
		self.printCurrentTime(self.now())
		p.start()
		self.durations[index]=("{0:.2f} minutes".format((self.now()-start)/60.0))

def parseArguments():
	parser = argparse.ArgumentParser(description='Produces a tileset of a input dem dataset. The resulting tiles can i.e. be read by webgl applications')
	group = parser.add_mutually_exclusive_group(required=True)
	group.add_argument('-i','--deminput', help='Set input raw dem. Can be *vrt or any other format that can be read by gdal.')
	group.add_argument('-x','--tileinput', help='Set input tileset (tif). Can be tileset created previously by tiler-tools. \nTile computing is not done to save cpu time.')
	parser.add_argument('-o','--output', help='Output path for temporary files and tiles.',required=True)
	parser.add_argument('-n','--dstnodata', help='Nodata value in destination tileset (default -500).',required=False)
	parser.add_argument('-s','--scheme', help='Tile Scheme of output tiles. Supported are TMS and XYZ (default).',required=False)
	parser.add_argument('-m','--multithread', help='If set, multithreading is enabled (default false). \nThis functionality is only experimental.\n You can play with the -t and -b flag.',required=False,action='store_true')		
	parser.add_argument('-t','--threads', help='Number of threads (4). Experimental!',required=False)		
	parser.add_argument('-b','--buffer', help='Number of tiles in buffer (20). Experimental',required=False)	
	parser.add_argument('-a','--archive', help='Creates tar archive of tileset (default false).',required=False, action='store_true')	
	parser.add_argument('-tf','--temp', help='Keep temporary files (default false).',required=False, action='store_true')	
	parser.add_argument('-v','--verbose', help='Allow verbose console output (default false).',required=False, action='store_true')	

	return parser.parse_args()

def main():
	args = parseArguments()
	ps = ExecuteCommand(args.verbose) 

	# parameter = if x use x else use default value
	tileScheme = args.scheme and args.scheme or 'xyz'
	multiThread = args.multithread
	mThreads = args.threads and args.threads or 4
	mBuffer = args.buffer and args.buffer or 20
	inputData = args.tileinput and args.tileinput or args.deminput
	noData = args.dstnodata and args.dstnodata or -500

	# set working directories
	tilesOutput = args.output
	tilesDestination = os.path.join(tilesOutput,'tiles')
	demName = os.path.split(inputData)[1]

	if args.tileinput:
			tilesRaw = inputData
	else:
			tilesRaw = os.path.join(tilesOutput,os.path.splitext(demName)[0]+'.'+tileScheme)


	tilesWithNeighbours = tilesRaw+'-with-neighbour-values'
	tilesColorEncoded = tilesRaw+'-with-neighbour-values-colorencoded'

	# delete destination folder if already exists
	if os.path.isdir(tilesDestination):
		shutil.rmtree(tilesDestination)

	# clear screen
	os.system('clear')
	
	print ("Start processing: {demName}".format(demName=demName))	
	if multiThread:
		print ("\nMultithreading enabled. Using {nt} parallel threads. BufferSize is {bf} tiles.\nPlease note that this is an experimental functionality.\n".format(nt=mThreads,bf=mBuffer))
	print ("Input Dem: {input}\nWriting tiles to {output}\nNoData Value is {nodata}.".format(input=inputData, output=tilesDestination, nodata=noData))
	print('\n------------------------------------')

	if not args.tileinput:
		ps.executeCMD("tiler-tools","Creating tiles (tif).","python tiler-tools/gdal_tiler.py --dst-nodata={nodata} -p {scheme} --tile-format='tif' --base-resampling='cubic' --overview-resampling='bilinear' {input} -t {output}".format(input=inputData,output=tilesOutput,nodata=noData,scheme=tileScheme))

 	ps.executePY("tile_border_neighbours","Compute tile border values based on the neighbouring tiles (tif)",TileBorderComputer(tileScheme,tilesRaw,noData,multiThread,mThreads,mBuffer))
	ps.executePY("tile_colorencode","Encode elevation values and create final tiles (png)",ColorEncoder(tilesWithNeighbours,noData,multiThread,mThreads,mBuffer))

	# clean up temporary files if flag is set
	if not args.temp and not args.tileinput:
		print('\nCleaning up temporary files.')
		shutil.rmtree(tilesWithNeighbours)
		shutil.rmtree(tilesRaw)

	# rename output dir
	shutil.move(tilesColorEncoded, tilesDestination)

	# create tar archive of computed tileset
	if args.archive:
		ps.executeCMD("tar-archive","Creating archive of tiles","tar -cf {archivePath} {tilefolder}".format(tilefolder=tilesDestination,archivePath=os.path.join(tilesOutput,'tiles.tar')))

	print('\n------------------------------------\ndone.\n')
	for t in ps.durations:
		print t+': '+ps.durations[t]

if __name__ == '__main__':
    main()   
