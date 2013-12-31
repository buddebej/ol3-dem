import sys, os, argparse, fnmatch, time
from osgeo import gdal
from osgeo import osr
import numpy as np
from multiprocessing import Process,Queue
from math import ceil

class EncoderCore:

    def __init__(self,noData):
        self.noData = float(noData)
        pass

    def process(self, in_fn, out_fn):

       # supress creation of aux.xml metadata-files.
       gdal.SetConfigOption("GDAL_PAM_ENABLED","NO")
       self.openInputDataset(in_fn)
       self.createOutputDataset()
       self.exportToPng(self.out_ds, out_fn)

       self.in_ds = None
       self.out_ds = None

    def openInputDataset(self, in_fn):
        self.in_ds = gdal.Open(in_fn, gdal.GA_Update)
        if self.in_ds is None:
            return -1

        self.in_band_1 = self.in_ds.GetRasterBand(1)
        self.in_band_1.SetNoDataValue(self.noData)

        blockSizes = self.in_band_1.GetBlockSize()

        self.in_xBlockSize = blockSizes[0]
        self.in_yBlockSize = blockSizes[1]

        self.in_min = self.in_band_1.GetMinimum()
        self.in_max = self.in_band_1.GetMaximum()
        
        if self.in_max == None or self.in_min == None:
            stats = self.in_band_1.GetStatistics(0, 1)
            self.in_min = stats[0]
            self.in_max = stats[1]

    def createOutputDataset(self):
        format = "MEM"  
        driver = gdal.GetDriverByName( format ) 

        self.out_ds = driver.Create('', self.in_ds.RasterXSize, self.in_ds.RasterYSize, 4)

        self.out_ds.GetRasterBand(1).SetColorInterpretation(gdal.GCI_RedBand)
        self.out_ds.GetRasterBand(2).SetColorInterpretation(gdal.GCI_GreenBand)
        self.out_ds.GetRasterBand(3).SetColorInterpretation(gdal.GCI_BlueBand)
        self.out_ds.GetRasterBand(4).SetColorInterpretation(gdal.GCI_AlphaBand)

        self.out_ds.GetRasterBand(1).SetNoDataValue(self.in_band_1.GetNoDataValue())
        self.out_ds.GetRasterBand(2).SetNoDataValue(self.in_band_1.GetNoDataValue())
        self.out_ds.GetRasterBand(3).SetNoDataValue(self.in_band_1.GetNoDataValue())
        self.out_ds.GetRasterBand(4).SetNoDataValue(self.in_band_1.GetNoDataValue())

        for i in range(0, self.in_ds.RasterYSize, self.in_yBlockSize):  
            if i + self.in_yBlockSize < self.in_ds.RasterYSize:  
                rows = self.in_yBlockSize 
            else:  
                rows = self.in_ds.RasterYSize - i  
            for j in range(0, self.in_ds.RasterXSize, self.in_xBlockSize):  
                if j + self.in_xBlockSize < self.in_ds.RasterXSize:  
                    cols = self.in_xBlockSize  
                else:  
                    cols = self.in_ds.RasterXSize - j
                
                data = self.in_band_1.ReadAsArray(j, i, cols, rows)

                o = np.empty((rows, cols), np.uint8)
                o.fill(255)
                self.out_ds.GetRasterBand(4).WriteArray(o, j, i)

                z = np.zeros((rows, cols), np.uint8)
                
                if self.in_band_1.DataType == 1: # GDT_Byte
                    self.out_ds.GetRasterBand(1).WriteArray(np.bitwise_and(data, 0xff), j, i)
                    self.out_ds.GetRasterBand(2).WriteArray(z, j, i)
                    self.out_ds.GetRasterBand(3).WriteArray(z, j, i)
                
                elif self.in_band_1.DataType == 2: # GDT_UInt16
                    self.out_ds.GetRasterBand(1).WriteArray(np.bitwise_and(data, 0xff), j, i)
                    self.out_ds.GetRasterBand(2).WriteArray(np.bitwise_and(np.right_shift(data, 8), 0xff), j, i)
                    self.out_ds.GetRasterBand(3).WriteArray(z, j, i)

                elif self.in_band_1.DataType == 3: # GDT_Int16
                    data = np.add(data, 11000)
                    self.out_ds.GetRasterBand(1).WriteArray(np.bitwise_and(data, 0xff), j, i)
                    self.out_ds.GetRasterBand(2).WriteArray(np.bitwise_and(np.right_shift(data, 8), 0xff), j, i)
                    self.out_ds.GetRasterBand(3).WriteArray(z, j, i)

                elif self.in_band_1.DataType == 4: # GDT_UInt32
                    self.out_ds.GetRasterBand(1).WriteArray(np.bitwise_and(data, 0xff), j, i)
                    self.out_ds.GetRasterBand(2).WriteArray(np.bitwise_and(np.right_shift(data, 8), 0xff), j, i)
                    self.out_ds.GetRasterBand(3).WriteArray(np.bitwise_and(np.right_shift(data, 16), 0xff), j, i)

                elif self.in_band_1.DataType == 5: # GDT_Int32
                    self.out_ds.GetRasterBand(1).WriteArray(np.bitwise_and(data, 0xff), j, i)
                    self.out_ds.GetRasterBand(2).WriteArray(np.bitwise_and(np.right_shift(data, 8), 0xff), j, i)
                    self.out_ds.GetRasterBand(3).WriteArray(np.bitwise_and(np.right_shift(data, 16), 0xff), j, i)

                elif self.in_band_1.DataType == 6: # GDT_Float32
                    data = np.around(data,decimals=1)
                    data = np.multiply(data,10)
                    data = np.add(data, 11000, dtype="int32")
                    self.out_ds.GetRasterBand(1).WriteArray(np.bitwise_and(data, 0xff), j, i)
                    self.out_ds.GetRasterBand(2).WriteArray(np.bitwise_and(np.right_shift(data, 8), 0xff), j, i)
                    self.out_ds.GetRasterBand(3).WriteArray(z, j, i)
                else:
                    print "ERROR: DataType ({0}) is not valid!".format(self.in_band_1.DataType)
                    

    def exportToPng(self, ds, out_fn):
        format = "PNG"  
        driver = gdal.GetDriverByName( format )  
        export_ds = driver.CreateCopy(out_fn, ds)
        export_ds = None

class ColorEncoder:
    def __init__(self,rootPath,noData,multiThread,mThreads,mBuffer):
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
            _EncoderCore=EncoderCore(self.noData)

        # walk directory
        for root, dirs, files in os.walk(self.rootPath):
            for filename in fnmatch.filter(files, pattern):
                inputFile = os.path.join(root, filename)
                y = os.path.splitext(filename)[0]
                fzx =os.path.split(root)
                x = fzx[1]
                fz = os.path.split(fzx[0])
                z = fz[1]
                f = fz[0] + "-colorencoded"
                if not os.path.isdir(f):
                    os.mkdir(f)
                if not os.path.isdir(os.path.join(f,z)):
                    os.mkdir(os.path.join(f,z))
                if not os.path.isdir(os.path.join(f,z,x)):
                    os.mkdir(os.path.join(f,z,x))
                outputFile = os.path.join(f, z, x, y + '.png')

                if self.multiThread: 
                    # start computing with multiple threads (is much faster!)
                    # write file to cluster 
                    tileCluster.append([inputFile, outputFile])  

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
                    EncoderCore(self.noData).process(inputFile, outputFile)

        if self.multiThread:
                # should be done in a nicer way
                # this adds the last remaining tiles, of the dir walk
                # when cluster maximum size is not reached anymore during the last loop
                tileBuffer.append(tileCluster)
                tileQueue.put(tileBuffer[j])  
                print str(j*bufferSize+len(tileCluster))+' tiles to process.'
         
                def callThread(queue):
                    if not queue.empty():
                        # read tile stack from queue
                        tileProcessQueue=queue.get()
                        for tile in tileProcessQueue:
                            # start computing
                            _EncoderCore.process(*tile)

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
    parser = argparse.ArgumentParser(description='Encodes values of dem into two 8bit bands of pngs.')
    parser.add_argument( "tileinput", type=extant_folder, nargs='+',help="Input tiles", metavar="TMS FOLDER")    
    parser.add_argument('-m','--multithread', help='If set, multithreading is deactivated (default true).',required=False, action='store_false')    
    parser.add_argument('-t','--threads', help='Number of threads (4). This functionality is only experimental',required=False)      
    parser.add_argument('-b','--buffer', help='Number of tiles in buffer (300).This functionality is only experimental',required=False)   
    parser.add_argument('-n','--dstnodata', help='Nodata value in tiles (default -500).',required=False)   
    return parser.parse_args()

def main():

    args = parseArguments()
    print 'Start colorencoding.'
    print "Input: {input}".format(input=args.tileinput)
    rootPath = args.tileinput[0]
    multiThread = args.multithread
    noData = args.dstnodata

    mThreads = args.threads and args.threads or 8
    mBuffer = args.buffer and args.buffer or 40
    noData = args.dstnodata and args.dstnodata or -500
  
    ColorEncoder(rootPath,noData,multiThread,mThreads,mBuffer).start()

   

if __name__ == '__main__':
    main()   
