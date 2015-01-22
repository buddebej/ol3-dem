#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# Copyright (c) 2011-2013 Vadim Shlyakhov
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
###############################################################################

from optparse import OptionParser

from tiler_functions import *
from tiler_backend import Pyramid, resampling_lst, base_resampling_lst
import tiler_global_mercator
import tiler_plate_carree
import tiler_misc

import map2gdal

#~ import rpdb2; rpdb2.start_embedded_debugger('nRAmgJHm')

#----------------------------

def preprocess_src(src):

#----------------------------
    global options
    opt = LooseDict(options)
    res = map2gdal.process_src(src, no_error=True, opt=opt)
    ld('preprocess_src', res)
    return res

#----------------------------

def process_src(src_def):

#----------------------------
    global options
    opt = LooseDict(options)
    opt.tile_format = opt.tile_format.lower()
    opt.tile_ext = '.' + opt.tile_format
    src, delete_src = src_def
    opt.delete_src = delete_src

    profile = Pyramid.profile_class(opt.profile)
    ext = profile.defaul_ext if opt.strip_dest_ext is None else ''
    dest = dest_path(src, opt.dest_dir, ext)

    prm = profile(src, dest, opt)
    prm.walk_pyramid()

#----------------------------

def parse_args(arg_lst):

#----------------------------
    parser = OptionParser(
        usage = "usage: %prog <options>... source...",
        version=version,
        description='Tile cutter for GDAL-compatible raster maps')
    parser.add_option('-p', '--profile', '--to', dest="profile", metavar='PROFILE',
        default='zyx', choices=Pyramid.profile_lst(),
        help='output tiles profile (default: zyx)')
    parser.add_option("-f", "--list-profiles", action="store_true",
        help='list tile profiles')
    parser.add_option("-z", "--zoom", default=None, metavar="ZOOM_LIST",
        help='list of zoom ranges to generate')
    parser.add_option("--srs", default=None, metavar="SOURCE_SRS",
        help="override source's spatial reference system")
    parser.add_option("--tiles-srs", default=None, metavar="TILES_SRS",
        help="target SRS for generic profile")
    parser.add_option("--tile-size", default='256,256', metavar="SIZE_X,SIZE_Y",
        help='generic profile: tile size (default: 256,256)')
    parser.add_option("--zoom0-tiles", default='1,1', metavar="NTILES_X,NTILES_Y",
        help='generic profile: number of tiles along the axis at the zoom 0 (default: 1,1)')
    parser.add_option('--overview-resampling', default='nearest', metavar="METHOD1",
        choices=resampling_lst(),
        help='overview tiles resampling method (default: nearest)')
    parser.add_option('--base-resampling', default='nearest', metavar="METHOD2",
        choices=base_resampling_lst(),
        help='base image resampling method (default: nearest)')
    parser.add_option('-r', '--release', action="store_true",
        help='set resampling options to (antialias,bilinear)')
    parser.add_option('--tps', action="store_true",
        help='Force use of thin plate spline transformer based on available GCPs)')
    parser.add_option("-c", "--cut", action="store_true",
        help='cut the raster as per cutline provided either by source or by "--cutline" option')
    parser.add_option("--cutline", default=None, metavar="DATASOURCE",
        help='cutline data: OGR datasource')
    parser.add_option("--cutline-match-name", action="store_true",
        help='match OGR feature field "Name" against source name')
    parser.add_option("--cutline-blend", dest="blend_dist", default=None, metavar="N",
        help='CUTLINE_BLEND_DIST in pixels')
    parser.add_option("--src-nodata", dest="src_nodata", metavar='N[,N]...',
        help='Nodata values for input bands')
    parser.add_option("--dst-nodata", dest="dst_nodata", metavar='N',
        help='Assign nodata value for output paletted band')
    parser.add_option("--tiles-prefix", default='', metavar="URL",
        help='prefix for tile URLs at googlemaps.hml')
    parser.add_option("--tile-format", default='png', metavar="FMT",
        help='tile image format (default: png)')
    parser.add_option("--paletted", action="store_true",
        help='convert tiles to paletted format (8 bit/pixel)')
    parser.add_option("-t", "--dest-dir", dest="dest_dir", default=None,
        help='destination directory (default: source)')
    parser.add_option("--noclobber", action="store_true",
        help='skip processing if the target pyramid already exists')
    parser.add_option("-s", "--strip-dest-ext", action="store_true",
        help='do not add a default extension suffix from a destination directory')
#    parser.add_option("--viewer-copy", action="store_true",
#        help='on POSIX systems copy html viewer instead of hardlinking to the original location')
    parser.add_option("-q", "--quiet", action="store_const",
        const=0, default=1, dest="verbose")
    parser.add_option("-d", "--debug", action="store_const",
        const=2, dest="verbose")
    parser.add_option("-l", "--long-name", action="store_true",
        help='give an output file a long name')
    parser.add_option("-n", "--after-name", action="store_true",
        help='give an output file name after a map name (from metadata)')
    parser.add_option("-m", "--after-map", action="store_true",
        help='give an output file name  after name of a map file, otherwise after a name of an image file')
    parser.add_option("--skip-invalid", action="store_true",
        help='skip invalid/unrecognized source')

    (options, args) = parser.parse_args(arg_lst)

    return (options, args)

#----------------------------

def main(argv):

#----------------------------

    global options
    (options, args) = parse_args(argv[1:])

    logging.basicConfig(level=logging.DEBUG if options.verbose == 2 else
        (logging.ERROR if options.verbose == 0 else logging.INFO))

    ld(os.name)
    ld(options)

    if options.list_profiles:
        Pyramid.profile_lst(tty=True)
        return

    if not args:
        logging.error('No input file(s) specified')
        sys.exit(1)

    if options.verbose == 2:
        set_nothreads()

    if options.release:
        options.overview_resampling, options.base_resampling = ('antialias', 'cubic')

    res = parallel_map(preprocess_src, args)
    parallel_map(process_src, flatten(res))

# main()

if __name__ == '__main__':

    main(sys.argv)
