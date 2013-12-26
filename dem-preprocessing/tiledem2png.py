import sys, os, argparse, fnmatch
from osgeo import gdal
from osgeo import osr
import numpy as np
import time

class Dem2Png:

    def __init__(self):

        pass

    def process(self, in_fn, out_fn):
       #print in_fn

       #Open Map
       start = time.time()
       self.openInputDataset(in_fn)
       #print "openDataset:", time.time() - start

       start = time.time()      
       self.createOutputDataset()
       #print "createOutputDataset:", time.time() - start

       start = time.time()  
       self.exportToPng(self.out_ds, out_fn)
       #print "exportToPng:", time.time() - start

       #print "------------------"

       self.in_ds = None
       self.out_ds = None

    def openInputDataset(self, in_fn):
        self.in_ds = gdal.Open(in_fn, gdal.GA_Update)
        if self.in_ds is None:
            return -1

        self.in_band_1 = self.in_ds.GetRasterBand(1)

        blockSizes = self.in_band_1.GetBlockSize()

        self.in_xBlockSize = blockSizes[0]
        self.in_yBlockSize = blockSizes[1]

        #Set NoData
        self.in_band_1.SetNoDataValue(-500)

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

        #print self.in_min, self.in_max

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

def extant_folder(x):
    """
    'Type' for argparse - checks if outputfolder exists, yes: return true (means to use existing output!!! UPDATE MODE) no: create folder + return false.
    """
    if not os.path.isdir(x):
        raise argparse.ArgumentError("{0} does not exist".format(x))
    return x

def extant_file(x):
    """
    'Type' for argparse - checks that file exists but does not open.
    """
    if not os.path.exists(x):
        raise argparse.ArgumentError("{0} does not exist".format(x))
    return x

def parseArguements():
    # Argument Parser
    parser = argparse.ArgumentParser(description='Landis2Vis')
    
    # projectfile Option
    parser.add_argument( "tmsfolder", type=extant_folder, nargs='+',
        help="Tile Map Service Folder ", metavar="TMS FOLDER")    
       
    return parser.parse_args()

def main():

    args = parseArguements()
    print 'start colorencoding..'
    print args.tmsfolder

    rootPath = args.tmsfolder[0]
    pattern = '*.tif'
    
    _Dem2Png = Dem2Png()

    for root, dirs, files in os.walk(rootPath):
        for filename in fnmatch.filter(files, pattern):
            inputFile = os.path.join(root, filename)
            y = os.path.splitext(filename)[0]
            fzx =os.path.split(root)
            x = fzx[1]
            fz = os.path.split(fzx[0])
            z = fz[1]
            f = fz[0] + '_png'
            if not os.path.isdir(f):
                os.mkdir(f)
            if not os.path.isdir(os.path.join(f,z)):
                os.mkdir(os.path.join(f,z))
            if not os.path.isdir(os.path.join(f,z,x)):
                os.mkdir(os.path.join(f,z,x))

            outputFile = os.path.join(f, z, x, y + '.png')
            #print inputFile, outputFile
            _Dem2Png.process(inputFile, outputFile)


if __name__ == '__main__':
    main()   