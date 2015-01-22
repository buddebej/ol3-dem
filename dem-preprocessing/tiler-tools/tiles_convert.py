#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# Copyright (c) 2010, 2013 Vadim Shlyakhov
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

import sys
import logging
import optparse

from tiler_functions import *

from converter_backend import TileSet, TileConverter
import converter_xyz
import converter_maemomapper
import converter_sasplanet
try:
    import converter_mmaps
except ImportError:
    pass

#~ import rpdb2; rpdb2.start_embedded_debugger('nRAmgJHm')

#----------------------------

def convert(src_lst, options):

#----------------------------

    in_class = TileSet.get_class(options.in_fmt, isDest=False)
    out_class = TileSet.get_class(options.out_fmt, isDest=True)

    for src in src_lst:
        src_tile_set = in_class(src, options)
        out_class(options=options, src=src_tile_set).convert()

#----------------------------

def main(argv):

#----------------------------
    parser = optparse.OptionParser(
        usage='usage: %prog [<options>...] <source>...',
        version=version,
        description='copies map tiles from one structure to another')
    parser.add_option('--from', dest='in_fmt', default='zyx',
        help='input tiles profile (default: zyx)')
    if converter_mmaps:
        parser.add_option('--to', dest='out_fmt', default='mmaps',
            help='output tiles profile (default: mmaps)')
    else:
        parser.add_option('--to', dest='out_fmt', default=None,
            help='output tiles profile (default: None)')
    parser.add_option('--list-profiles', '--lp', action='store_true',
        help='list available profiles')
    parser.add_option('-f', '--tile-format', dest='convert_tile', metavar='FORMAT',
        help='convert output tiles to format (default: no conversion)')
    parser.add_option('--list-formats', '--lf', action='store_true',
        help='list tile format converters')
    parser.add_option("-n", "--colors", dest="colors", default='256',
        help='Specifies  the  number  of colors for pngnq profile (default: 256)')
    parser.add_option("-q", "--quality", dest="quality", type="int", default=75,
        help='JPEG/WEBP quality (default: 75)')
    parser.add_option('-a', '--append', action='store_true', dest='append',
        help='append tiles to an existing destination')
    parser.add_option('-r', '--remove-dest', action='store_true',dest='remove_dest',
        help='delete destination directory before merging')
    parser.add_option('-t', '--dest-dir', default='.', dest='dst_dir',
        help='destination directory (default: current)')
    parser.add_option('--name', default=None,
        help='layer name (default: derived from the source)')
    parser.add_option('--description', metavar='TXT', default='',
        help='layer decription (default: None)')
    parser.add_option('--overlay', action='store_true',
        help='non-base layer (default: False)')
    parser.add_option('--url', default=None,
        help='URL template (default: None)')
    parser.add_option('--link', action='store_true', dest='link',
        help='make links to source tiles instead of copying if possible')
    parser.add_option("--srs", default='EPSG:3857', dest="tiles_srs",
        help="code of a spatial reference system of a tile set (default is EPSG:3857, aka EPSG:900913)")
    parser.add_option("--proj4def", default=None, metavar="PROJ4_SRS",
        help="proj4 definition for the SRS")
    parser.add_option('-z', '--zoom', default=None,metavar='ZOOM_LIST',
        help='list of zoom ranges to process')
    parser.add_option('-g', '--region', default=None, metavar='DATASOURCE',
        help='region to process (OGR shape or Sasplanet .hlg)')
    parser.add_option('--region-zoom', metavar='N', type="int", default=None,
        help='apply region for zooms only higher than this one (default: None)')
    parser.add_option("--nothreads", action="store_true",
        help="do not use multiprocessing")

    parser.add_option('-d', '--debug', action='store_true', dest='debug')
    parser.add_option('--quiet', action='store_true', dest='quiet')

    #~ global options
    (options, args) = parser.parse_args(argv[1:])

    logging.basicConfig(level=logging.DEBUG if options.debug else
        (logging.ERROR if options.quiet else logging.INFO))
    log(options.__dict__)

    if options.list_profiles:
        TileSet.list_profiles()
        sys.exit(0)

    if options.list_formats:
        TileConverter.list_tile_converters()
        sys.exit(0)

    src_lst=args

    convert(src_lst, LooseDict(options))

# main()

if __name__ == '__main__':

    main(sys.argv)
