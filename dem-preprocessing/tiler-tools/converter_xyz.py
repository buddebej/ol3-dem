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

from converter_backend import *

#############################

class TMStiles(TileMapDir): # see TileMap Diagram at http://wiki.osgeo.org/wiki/Tile_Map_Service_Specification
    'TMS tiles'
#############################
    format, ext, input, output = 'tms', '.tms', True, True
    dir_pattern = '[0-9]*/*/*.*'

    def path2coord(self, tile_path):
        z, x, y = map(int, path2list(tile_path)[-4:-1])
        return (z, x, 2**z-y-1)

    def coord2path(self, z, x, y):
        return '%d/%d/%d' % (z, x, 2**z-y-1)

tileset_profiles.append(TMStiles)

#############################

class XYZtiles(TileMapDir): # http://code.google.com/apis/maps/documentation/javascript/v2/overlays.html#Google_Maps_Coordinates
    'Popular XYZ format (Google Maps, OSM, mappero-compatible)'
#############################
    format, ext, input, output = 'xyz', '.xyz', True, True
    dir_pattern = '[0-9]*/*/*.*'

    def path2coord(self, tile_path):
        return map(int, path2list(tile_path)[-4:-1])

    def coord2path(self, z, x, y):
        return '%d/%d/%d' % (z, x, y)

tileset_profiles.append(XYZtiles)

#############################

class ZYXtiles(TileMapDir):
    'ZYX aka Global Mapper (SASPlanet compatible)'
#############################
    format, ext, input, output = 'zyx', '.zyx', True, True
    dir_pattern = 'z[0-9]*/*/*.*'

    def path2coord(self, tile_path):
        z, y, x = path2list(tile_path)[-4:-1]
        return map(int, (z[1:], x, y))

    def coord2path(self, z, x, y):
        return 'z%d/%d/%d' % (z, y, x)

tileset_profiles.append(ZYXtiles)

#############################

class MapNav(TileDir): # http://mapnav.spb.ru/site/e107_plugins/forum/forum_viewtopic.php?29047.post
    'MapNav (Global Mapper - compatible)'
#############################
    format, ext, input, output = 'mapnav', '.mapnav', True, True
    dir_pattern = 'Z[0-9]*/*/*.pic'
    tile_class = FileTileNoExt

    def dest_ext(self, tile):
        return '.pic'

    def path2coord(self, tile_path):
        z, y, x = path2list(tile_path)[-4:-1]
        return map(int, (z[1:], x, y))

    def coord2path(self, z, x, y):
        return 'Z%d/%d/%d' % (z, y, x)

tileset_profiles.append(MapNav)
