##dem-preprocessing tools

Both tile_border_neighbours.py and tile_colorencode.py are standalone tools and can be used independently. 

You can use batch_dem2tiles.py as an interface to call all tools in their respective order.
In addition it takes care of the temporary files and offers several other options.
See the benchmark file for information about the multithreading feature.

Everything was tested in Sabayon Linux amd64 14.01 with GDAL 1.10 and Python 2.7.
Dependencies are Python, Python bindings (python-gdal), Python imaging library (PIL), GDAL binaries (gdal-bin 1.7+).
Optionally you would need tar to create archives of the tilesets.

To ensure that no artefacts occur during the resampling of the images the order of the workflow has to be:

* __tiler-tools__ (http://code.google.com/p/tilers-tools/ using version 3.2)
(creates tif tiles of a dem in a gdal readable format)

* __tile_border_neighbours.py__ 
(adjusts elevation values on tile borders with the help of neighbouring tiles to avoid rendering artefacts)

* __tile_colorencode.py__
(encodes up to Float32 values in tif and write into two 8 bit bands of a png)


##Usage

```
./batch_dem2tiles.py -i my_dem.vrt -o outputData/ -m -v
```

##batch_dem2tiles.py

See the help with batch_dem2tiles.py -h.

```
usage: batch_dem2tiles.py [-h] (-i DEMINPUT | -x TILEINPUT) -o OUTPUT
                          [-n DSTNODATA] [-s SCHEME] [-m] [-t THREADS]
                          [-b BUFFER] [-a] [-tf] [-v]

Produces a tileset of a input dem dataset. The resulting tiles can i.e. be
read by webgl applications

optional arguments:
  -h, --help            show this help message and exit
  -i DEMINPUT, --deminput DEMINPUT
                        Set input raw dem. Can be *vrt or any other format
                        that can be read by gdal.
  -x TILEINPUT, --tileinput TILEINPUT
                        Set input tileset (tif). Can be tileset created
                        previously by tiler-tools. Tile computing is not done
                        to save cpu time.
  -o OUTPUT, --output OUTPUT
                        Output path for temporary files and tiles.
  -n DSTNODATA, --dstnodata DSTNODATA
                        Nodata value in destination tileset (default -500).
  -s SCHEME, --scheme SCHEME
                        Tile Scheme of output tiles. Supported are TMS and XYZ
                        (default).
  -m, --multithread     If set, multithreading is enabled (default false).
                        This functionality is only experimental. You can play
                        with the -t and -b flag.
  -t THREADS, --threads THREADS
                        Number of threads (4). Experimental!
  -b BUFFER, --buffer BUFFER
                        Number of tiles in buffer (20). Experimental
  -a, --archive         Creates tar archive of tileset (default false).
  -tf, --temp           Keep temporary files (default false).
  -v, --verbose         Allow verbose console output (default false).
```



