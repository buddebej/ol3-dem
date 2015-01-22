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

from tiler_functions import *
from tiler_backend import *

#############################

class GMercator(Pyramid):
    'base class for Global Mercator'
#############################

    # OpenLayers-2.12/lib/OpenLayers/Projection.js
    #
    # "EPSG:900913": {
    #     units: "m",
    #     maxExtent: [-20037508.34, -20037508.34, 20037508.34, 20037508.34]
    # }

    zoom0_tiles = [1, 1] # tiles at zoom 0

    # Global Mercator (EPSG:3857, aka EPSG:900913) http://docs.openlayers.org/library/spherical_mercator.html
    #~ srs = '+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs'
    srs = 'EPSG:3857'

    tilemap_crs = 'EPSG:3857'

#############################

class GMercatorZYX(GMercator, ZYXtiling):
    'Global Mercator, top-to-bottom tile numbering ZYX directory structure'
#############################
    profile = 'zyx'
    defaul_ext = '.zyx'
    tms_profile = 'zyx-mercator' # non-standard profile

    def write_metadata(self, tile=None, children=[]):
        super(GMercatorZYX, self).write_metadata(tile, children)

        if tile is None:
            copy_viewer(self.dest)
#
profile_map.append(GMercatorZYX)
#

#############################

class GMercatorXYZ(GMercator, XYZtiling):
    'Global Mercator, top-to-bottom tile numbering OSM directory structure'
#############################
    profile = 'xyz'
    defaul_ext = '.xyz'
    tms_profile = 'xyz-mercator' # non-standard profile
#
profile_map.append(GMercatorXYZ)
#

#############################

class GMercatorTMS(GMercator, TMStiling):
    'Global Mercator, TMS tile numbering'
#############################
    profile = 'tms'
    defaul_ext = '.tms'
    tms_profile = 'global-mercator'
#
profile_map.append(GMercatorTMS)
#
