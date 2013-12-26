import sys, os, argparse, fnmatch
from osgeo import gdal
from osgeo import osr
import numpy as np
import time

class Dem2Png:

    def __init__(self):

        pass

    def process(self, in_fn, in_zxy, out_fn):
       #print in_fn

       #Open Map
       start = time.time()
       self.openInputDataset(in_fn)
       #print "openDataset:", time.time() - start

       start = time.time()      
       self.createOutputDataset(self.getTileNeighbours(in_zxy))
       #print "createOutputDataset:", time.time() - start

       start = time.time()  
       self.exportToTif(self.out_ds, out_fn)
       #print "exportToTif:", time.time() - start

       #print "------------------"

       # reset in and output file for next image
       self.in_ds = None
       self.out_ds = None

    def openInputDataset(self, in_fn):
        self.in_ds = gdal.Open(in_fn, gdal.GA_Update)

        # if file not exists exit
        if self.in_ds is None: 
            return -1

        # read band 1 and blocksize from input image
        self.in_band_1 = self.in_ds.GetRasterBand(1)
    
        #Set NoData
        self.in_band_1.SetNoDataValue(-500)

    def getTileNeighbours(self, in_zxy):
        root=in_zxy[0] # contains z
        x=int(in_zxy[1])
        y=int(in_zxy[2])
        #   Neighbours
        #   NW  N  NE 
        #   W   X  E
        #   SW  S  SE 

        # path to tile in tms (root,x,y), offsett x, offset y, nbr  of pixel in x and y direction
        NW = [root,x-1,y+1,255,255,1,1]
        N = [root,x,y+1,0,255,256,1]
        NE = [root,x+1,y+1,0,255,1,1]
        E = [root,x+1,y,0,0,1,256]
        SE = [root,x+1,y-1,0,0,1,1]
        S = [root,x,y-1,0,0,256,1]
        SW = [root,x-1,y-1,255,0,1,1]
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

        # corners and borders have to be computed in two seperated runs
        # my approach was to compute everything inside of this function
        # but it lead to strange floating point problems so apparantly
        # it works as long as the numpy operations are called in createOutputDataset()
        # may be related to the pointers to the numpy arrays?

        if( not corners):
            # list has to be flattened to fit into stempel_data column
            def flatten(*args):
                for x in args:
                    if hasattr(x, '__iter__'):
                        for y in flatten(*x):
                            yield y
                    else:
                        yield x
          
            #   Neighbours
            #   NW  N  NE 
            #   W   X  E
            #   SW  S  SE 
            #   [N,S,E,W,NW,NE,SE,SW]


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

        # unfortunately this method has to be called again because of a strange floating point issue (see getToKnowTheNeighbours())
        self.getToKnowTheNeighbours(True,input_grid,in_neighbourValues) 


        # save to output dataset
        self.out_ds.GetRasterBand(1).WriteArray(input_grid)
                    

    def exportToTif(self, ds, out_fn):
        format = "GTiff"  
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

def parseArguments():
    # Argument Parser
    parser = argparse.ArgumentParser(description='Landis2Vis')
    
    # projectfile Option
    parser.add_argument( "tmsfolder", type=extant_folder, nargs='+',
        help="Tile Map Service Folder ", metavar="TMS FOLDER")    
       
    return parser.parse_args()

def main():

    args = parseArguments()
    print 'getToKnowTheNeighbours (borderline)'
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
            zxy = [fzx[0],x,y]
            f = fz[0] + '_tif_neighbourhood'
            if not os.path.isdir(f):
                os.mkdir(f)
            if not os.path.isdir(os.path.join(f,z)):
                os.mkdir(os.path.join(f,z))
            if not os.path.isdir(os.path.join(f,z,x)):
                os.mkdir(os.path.join(f,z,x))

            outputFile = os.path.join(f, z, x, y + '.tif')
            #print inputFile, outputFile
            
            _Dem2Png.process(inputFile, zxy, outputFile)

if __name__ == '__main__':
    main()   