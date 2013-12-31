import sys, os, argparse, fnmatch, time
from osgeo import gdal
from osgeo import osr
import numpy as np
from multiprocessing import Process, Queue
from math import ceil


class TileBorderCore:

    def __init__(self,tilescheme, nodata):
        self.tileScheme = tilescheme
        self.noData = float(nodata)
        pass

    def process(self, in_fn, in_zxy, out_fn):

        # supress creation of aux.xml metadata-files.
        gdal.SetConfigOption("GDAL_PAM_ENABLED","NO")
        self.openInputDataset(in_fn)
        self.createOutputDataset(self.getTileNeighbours(in_zxy,self.tileScheme))
        self.exportToTif(self.out_ds, out_fn)

        self.in_ds = None
        self.out_ds = None

    def openInputDataset(self, in_fn):
        self.in_ds = gdal.Open(in_fn, gdal.GA_Update)

        # if file not exists exit
        if self.in_ds is None: 
            return -1

        # read band 1 and blocksize from input image
        self.in_band_1 = self.in_ds.GetRasterBand(1)
        self.in_band_1.SetNoDataValue(self.noData)

    
    def getTileNeighbours(self, in_zxy, tilescheme):
        root=in_zxy[0] # contains z
        x=int(in_zxy[1])
        y=int(in_zxy[2])
        #   Neighbours
        #   NW  N  NE 
        #   W   X  E
        #   SW  S  SE 

	if tilescheme == 'tms':
		NW = [root,x-1,y+1,255,255,1,1] # [path to tile (root,x,y), offsett x, offset y, nbr  of pixel in x and y direction]
		N = [root,x,y+1,0,255,256,1]
		NE = [root,x+1,y+1,0,255,1,1]
		E = [root,x+1,y,0,0,1,256]
		SE = [root,x+1,y-1,0,0,1,1]
		S = [root,x,y-1,0,0,256,1]
		SW = [root,x-1,y-1,255,0,1,1]
		W = [root,x-1,y,255,0,1,256] 
	else:
		NW = [root,x-1,y-1,255,255,1,1]
		N = [root,x,y-1,0,255,256,1]
		NE = [root,x+1,y-1,0,255,1,1]
		E = [root,x+1,y,0,0,1,256]
		SE = [root,x+1,y+1,0,0,1,1]
		S = [root,x,y+1,0,0,256,1]
		SW = [root,x-1,y+1,255,0,1,1]
		W = [root,x-1,y,255,0,1,256] 
		
        neighbourValues = [] 
        for n in [N,S,E,W,NW,NE,SE,SW]:
            neighbourValues.append(self.getNeighbourValues(n))
        return neighbourValues


    def getNeighbourValues(self,in_neighbour):
        in_n_fn = os.path.join(in_neighbour[0],str(in_neighbour[1]))+'/'+str(in_neighbour[2])+'.tif'
       
        # if file not exists exit
        if not os.path.isfile(in_n_fn):
            return -1

        in_n_ds = gdal.Open(in_n_fn, gdal.GA_ReadOnly)
        
        # if file is empty or corrupt
        if in_n_ds is None: 
            return -1

        # read band 1 from input image
        in_n_ds_band_1 = in_n_ds.GetRasterBand(1)

        # read relevant columns or rows of neighbour tile as specified in getTileNeighbours
        data = in_n_ds_band_1.ReadAsArray(in_neighbour[3], in_neighbour[4], in_neighbour[5], in_neighbour[6])

        return data

    def getToKnowTheNeighbours(self,corners,input_grid_copy,neighbourValues):

        if( not corners):
            # list has to be flattened to fit into stempel_data column
            def flatten(*args):
                for x in args:
                    if hasattr(x, '__iter__'):
                        for y in flatten(*x):
                            yield y
                    else:
                        yield x
          
            # store original values of corners
            self.nwCorner = input_grid_copy[0,0]
            self.neCorner = input_grid_copy[0,255]
            self.seCorner = input_grid_copy[255,255]
            self.swCorner = input_grid_copy[255,0]     

            # numpy matrix: [row index, column index], : = all values

            # N
            input_grid_copy[0,:] = neighbourValues[0] 
            # S
            input_grid_copy[255,:] = neighbourValues[1]
            # E
            input_grid_copy[:,255] = list(flatten(neighbourValues[2])) # list has to be flattened to fit into stempel_data column
            # W
            input_grid_copy[:,0] = list(flatten(neighbourValues[3])) # list has to be flattened to fit into stempel_data column

        else:

            # values in the corners of a tile have actually to be averaged with the help of every adjacent pixel
            # if a neighbour exists overwrite corner with new mean value

            if(neighbourValues[4] != -1):
               # NW
                input_grid_copy[0,0] = (neighbourValues[4][0][0] + neighbourValues[0][0][0] +  neighbourValues[3][0][0] + self.nwCorner) / 4.0
            if(neighbourValues[5] != -1):      
              # NE
                input_grid_copy[0,255] = (neighbourValues[5][0][0] + neighbourValues[0][0][255] +  neighbourValues[2][0][0] + self.neCorner) / 4.0
            if(neighbourValues[6] != -1):
              # SE
                input_grid_copy[255,255] = (neighbourValues[6][0][0] + neighbourValues[1][0][255] +  neighbourValues[2][255][0] + self.seCorner) / 4.0
            if(neighbourValues[7] != -1):
              # SW
                input_grid_copy[255,0] = (neighbourValues[7][0][0] + neighbourValues[1][0][0] +  neighbourValues[3][255][0] + self.swCorner) / 4.0            


    def createOutputDataset(self,in_neighbourValues):
        format = "MEM"  
        driver = gdal.GetDriverByName( format ) 

        # create output image as temporary MEM Buffer with same size as input
        self.out_ds = driver.Create('', self.in_ds.RasterXSize, self.in_ds.RasterYSize, 1, gdal.GDT_Float32)

        # set Band Type (grey scale) and no data value
        self.out_ds.GetRasterBand(1).SetColorInterpretation(gdal.GCI_PaletteIndex)
        self.out_ds.GetRasterBand(1).SetNoDataValue(self.in_band_1.GetNoDataValue())

        # create matrix of input grid
        input_grid = self.in_band_1.ReadAsArray(0, 0, self.in_ds.RasterXSize, self.in_ds.RasterYSize)

        # create masks to modify input grid               
        input_grid_copy = self.in_band_1.ReadAsArray(0, 0, self.in_ds.RasterXSize, self.in_ds.RasterYSize) # copy needed because in_data is pointer
        
        # copy values of borders and compute mean
        self.getToKnowTheNeighbours(False,input_grid_copy,in_neighbourValues) 

        # computing mean of original raster grid and stempel_border_data for averaged border values
        input_grid=np.divide(np.add(input_grid,input_grid_copy),2.0)

        # unfortunately this method has to be called a second time here because of a floating point issue (see getToKnowTheNeighbours())
        self.getToKnowTheNeighbours(True,input_grid,in_neighbourValues) 

        # save to output dataset
        self.out_ds.GetRasterBand(1).WriteArray(input_grid)
                    

    def exportToTif(self, ds, out_fn):
        format = "GTiff"  
        driver = gdal.GetDriverByName( format )  
        export_ds = driver.CreateCopy(out_fn, ds)

        export_ds = None

class TileBorderComputer:
    def __init__(self,tileScheme,rootPath,noData,multiThread,mThreads,mBuffer):
        self.tileScheme = tileScheme
        self.rootPath = rootPath
        self.noData = noData
        self.multiThread = multiThread
        self.mThreads = mThreads
        self.mBuffer = mBuffer
        pass

    def start(self):
        pattern = '*.tif'
        start = time.time();

        if self.multiThread:
            tileBuffer = []
            tileCluster = []
            tileQueue = Queue()
            j=0
            # parameters for multithreading
            maxThreads=int(self.mThreads)
            bufferSize=int(self.mBuffer)
            # create instance of core class
            _TileBorderCore=TileBorderCore(self.tileScheme,self.noData)

        # walk directory
        for root, dirs, files in os.walk(self.rootPath):
            for filename in fnmatch.filter(files, pattern):
                inputFile = os.path.join(root, filename)
                y = os.path.splitext(filename)[0]
                fzx =os.path.split(root)
                x = fzx[1]
                fz = os.path.split(fzx[0])
                z = fz[1]
                zxy = [fzx[0],x,y]
                f = fz[0] + "-with-neighbour-values"
                if not os.path.isdir(f):
                    os.mkdir(f)
                if not os.path.isdir(os.path.join(f,z)):
                    os.mkdir(os.path.join(f,z))
                if not os.path.isdir(os.path.join(f,z,x)):
                    os.mkdir(os.path.join(f,z,x))
                outputFile = os.path.join(f, z, x, y + '.tif')

                if self.multiThread: 
                    # start computing with multiple threads (is much faster!)
                    # write file to cluster 
                    tileCluster.append([inputFile, zxy, outputFile])  

                    # if cluster has reached maximum size
                    if len(tileCluster) == bufferSize:    
                        # copy cluster to buffer
                        tileBuffer.append(tileCluster)
                        # clear cluster 
                        tileCluster=[]
                        # put recenc cluster into multiprocess queue
                        tileQueue.put(tileBuffer[j])  
                        j+=1
                else:
                    # start computing for each single file (takes forever!)
                    TileBorderCore(self.tileScheme,self.noData).process(inputFile, zxy, outputFile)

        if self.multiThread:
                # should be done in a nicer way
                # this adds the last remaining tiles, of the dir walk
                # when cluster maximum size is not reached anymore during the last loop
                tileBuffer.append(tileCluster)
                tileQueue.put(tileBuffer[j])  

                print str(j*bufferSize+len(tileCluster))+' tiles to process.'
                                
                def callThread(queue):
                    # read tile stack from queue
                    if not queue.empty():
                        tileProcessQueue=queue.get()
                        for tile in tileProcessQueue:
                            # start computing
                            _TileBorderCore.process(*tile)

                def drawProgressBar(percent, barLen = 50):
                    sys.stdout.write("\r")
                    progress = ""
                    for i in range(barLen):
                        if i < int(barLen * percent):
                            progress += "="
                        else:
                            progress += " "
                    sys.stdout.write("[ %s ] %.2f%%" % (progress, percent * 100))
                    sys.stdout.flush()
                
                # this loop starts multiple threads (maxThreads) to process one cluster per thread
                # it runs as often as numberOfPools = (number of clusters / maxThreads)
                numberOfPools=int(ceil((len(tileBuffer))/maxThreads))+1
                for n in range(numberOfPools):
                    drawProgressBar(float(n+1)/float(numberOfPools))

                    # multiple threads are defined (callThread gets called)
                    processes=[(Process(target=callThread,args=(tileQueue,))) for m in range(maxThreads)]

                    # all processes get started
                    for p in processes:
                        p.start()
                    # loop waits until they are all finished
                    for p in processes:
                        p.join() 
                sys.stdout.write("\n\n")

        #print time.time()-start

def extant_folder(x):
    """
    'Type' for argparse - checks if outputfolder exists, yes: return true (means to use existing output!!! UPDATE MODE) no: create folder + return false.
    """
    if not os.path.isdir(x):
        raise argparse.ArgumentError("{0} does not exist".format(x))
    return x

def parseArguments():
    parser = argparse.ArgumentParser(description='Tiles get to know their neighbours.')
    parser.add_argument( "tilefolder", type=extant_folder, nargs='+',help="Tile Map Service Folder ", metavar="TMS FOLDER")    
    parser.add_argument( "tilescheme", type=str, default='xyz', help="Set tile scheme [tms or xyz]", metavar="TILE SCHEME")    
    parser.add_argument('-m','--multithread', help='If set, multithreading is deactivated (default true).',required=False, action='store_true')    
    parser.add_argument('-t','--threads', help='Number of threads (4). This functionality is only experimental',required=False)      
    parser.add_argument('-b','--buffer', help='Number of tiles in buffer (300).This functionality is only experimental',required=False)     
    parser.add_argument('-n','--dstnodata', help='Nodata value in tiles (default -500).',required=False)
    return parser.parse_args()

def main():

    args = parseArguments()
    tileScheme = args.tilescheme
    multiThread =  args.multithread
    rootPath = args.tilefolder[0]
    noData = args.dstnodata

    mThreads = args.threads and args.threads or 8
    mBuffer = args.buffer and args.buffer or 40
    noData = args.dstnodata and args.dstnodata or -500

    print "Compute tile border values with help of their neighbours."
    print "Input: {input}".format(input=args.tilefolder)
    print "Tilescheme: {tileScheme}".format(tileScheme=tileScheme)

    TileBorderComputer(tileScheme,rootPath,noData,multiThread,mThreads,mBuffer).start()

if __name__ == '__main__':
    main()   
