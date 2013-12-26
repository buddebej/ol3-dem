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


#~ from tiler_functions import *
from tiler_backend import *

#############################

class GenericMap(Pyramid, ZYXtiling):
    'full profile options are to be specified'
#############################
    profile = 'generic'
    defaul_ext = '.generic'

    def __init__(self, src=None, dest=None, options=None):

        options = LooseDict(options)

        self.srs = txt2proj4(options.proj4def or options.tiles_srs)
        assert self.srs, 'Target SRS is not specified'
        self.tilemap_crs = options.tiles_srs

        if options.zoom0_tiles:
            self.zoom0_tiles = map(int, options.zoom0_tiles.split(','))
        if options.tile_size:
            tile_size = tuple(map(int, options.tile_size.split(',')))
            self.tile_dim = (tile_size[0], -tile_size[1])

        super(GenericMap, self).__init__(src, dest, options)
#
profile_map.append(GenericMap)
#

#############################

class Wgs84(Pyramid, ZYXtiling):
    'WGS 84 / World Mercator, EPSG:3395 (compatible with Yandex maps)'
##############################
    profile = 'wgs84'
    defaul_ext = '.wgs84'

    #~ srs = '+proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    srs = 'EPSG:3395'
    tilemap_crs = 'EPSG:3395'
#
profile_map.append(Wgs84)
#
