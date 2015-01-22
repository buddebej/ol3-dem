#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 2011-04-10 13:33:20

###############################################################################
# Copyright (c) 2011, Vadim Shlyakhov
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
#******************************************************************************

from __future__ import with_statement

import os
import logging

from optparse import OptionParser

from tiler_functions import *

import reader_backend
import reader_bsb
import reader_geo
import reader_ozi
import reader_kml

options = None

def process_src(src, no_error=False, opt=None):
    """
    if source is converted successfully returns
        (<generated VRT file>, True)
    otherwise returns
        (<source>, False)
    """
    global options

    src = src.decode(locale.getpreferredencoding(),'ignore')

    if not opt:
        opt = LooseDict(options)

    with open(src,'rU') as f:
        lines=[f.readline() for i in range(30)]

    err_msg = None
    for cls in reader_backend.reader_class_map:
        patt=cls.magic
        if any((l.startswith(patt) for l in lines)):
            try:
                res = [(layer.convert(), True) for layer in cls(src,options=opt).get_layers()]
                return res
            except RuntimeError as exc:
                err_msg = exc.message
                if not no_error:
                    raise
    else:
        if no_error:
            return [(src, False)]
        if err_msg is None:
            err_msg = '*** %s' % exc.message
        if self.options.skip_invalid:
            logging.error(err_msg)
            return False
        else:
            raise RuntimeError(err_msg)


parser = None
#----------------------------

def parse_args(arg_lst):

#----------------------------
    parser = OptionParser(
        usage="usage: %prog <options>... map_file...",
        version=version,
        description="Extends GDAL's builtin support for a few mapping formats: BSB/KAP, GEO/NOS, Ozi map. "
        "The script translates a map file with into GDAL .vrt")
    parser.add_option("--srs", default=None,
        help="specify a full coordinate system for an output file (PROJ.4 definition)")
    parser.add_option("--datum", default=None,
        help="override a datum part only (PROJ.4 definition)")
    parser.add_option("--proj", default=None,
        help="override a projection part only (PROJ.4 definition)")
    parser.add_option("--force-dtm", action="store_true",
        help='force using BSB datum shift to WGS84 instead of native BSB datum')
    parser.add_option("--dtm",dest="dtm_shift",default=None,metavar="SHIFT_LONG,SHIFT_LAT",
        help='northing and easting to WGS84 datum in seconds of arc')
    parser.add_option('--tps', action="store_true",
        help='Force use of thin plate spline transformer based on available GCPs)')
    parser.add_option("--get-cutline", action="store_true",
        help='print a definition of a cutline polygon, then exit')
    parser.add_option("--cut-file", action="store_true",
        help='create a .GMT file with a cutline polygon')
    parser.add_option("-t", "--dest-dir", default=None, dest="dst_dir",
        help='destination directory (default: current)')
    parser.add_option("-n", "--after-name", action="store_true",
        help='give an output file name after a map name (from metadata)')
    parser.add_option("-m", "--after-map", action="store_true",
        help='give an output file name  after name of a map file, otherwise after a name of an image file')
    parser.add_option("-l", "--long-name", action="store_true",
        help='give an output file a long name')
    parser.add_option("--skip-invalid", action="store_true",
        help='skip invalid/unrecognized source')
    parser.add_option("-d", "--debug", action="store_true", dest="debug")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet")
#    parser.add_option("--last-column-bug", action="store_true",
#        help='some BSB files are missing value for last column, here is a workaround')
#    parser.add_option("--broken-raster", action="store_true",
#        help='try to workaround some BSB broken rasters (requires "convert" from ImageMagick)')

    return parser.parse_args(arg_lst)

if __name__=='__main__':
    (options, args) = parse_args(sys.argv[1:])

    #~ if not args:
        #~ parser.error('No input file(s) specified')

    logging.basicConfig(level=logging.DEBUG if options.debug else
        (logging.ERROR if options.quiet else logging.INFO))

    ld(os.name)
    ld(options)

    map(process_src,args)
