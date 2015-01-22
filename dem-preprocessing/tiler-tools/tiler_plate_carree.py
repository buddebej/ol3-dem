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

class PlateCarree(Pyramid):
    '''Plate Carrée, top-to-bottom tile numbering  (a la Google Earth)'''
#############################
    zoom0_tiles = [2, 1] # tiles at zoom 0

    tilemap_crs = 'EPSG:4326'

    # http://earth.google.com/support/bin/static.py?page=guide.cs&guide=22373&topic=23750
    # "Google Earth uses Simple Cylindrical projection for its imagery base. This is a simple map
    # projection where the meridians and parallels are equidistant, straight lines, with the two sets
    # crossing at right angles. This projection is also known as Lat/Lon WGS84"

    # Equirectangular (EPSG:32662 aka plate carrée, aka Simple Cylindrical)
    # we use this because the SRS might be shifted later to work around 180 meridian
    srs = '+proj=eqc +datum=WGS84 +ellps=WGS84'

    # set units to degrees, this makes this SRS essentially equivalent to EPSG:4326
    srs += ' +to_meter=%f' % (GdalTransformer(DST_SRS=srs, SRC_SRS=proj_cs2geog_cs(srs)).transform_point((1, 0))[0])

    #~ srs = 'EPSG:4326'

    def kml_child_links(self, children, parent=None, path_prefix=''):
        kml_links = []
        # convert tiles to degree boxes
        longlat_boxes = self.map_tiles2longlat_bounds(children)

        for tile, longlat in zip(children, longlat_boxes):
            #ld(tile, longlat)
            w, n, e, s = ['%.11f'%v for v in flatten(longlat)]
            name = os.path.splitext(self.tile_path(tile))[0]
            # fill in kml link template
            kml_links.append( kml_link_templ % {
                'name':    name,
                'href':    path_prefix+'%s.kml' % name,
                'west':    w, 'north':    n,
                'east':    e, 'south':    s,
                'min_lod': 128,
                'max_lod': 2048 if parent else -1,
                })
        return ''.join(kml_links)

    def write_kml(self, rel_path, name, links='', overlay=''):
        kml = kml_templ % {
            'name':      name,
            'links':     links,
            'overlay':   overlay,
            'dbg_start': '' if self.options.verbose < 2 else '    <!--\n',
            'dbg_end':   '' if self.options.verbose < 2 else '      -->\n',
            }
        open(os.path.join(self.dest, rel_path+'.kml'), 'w+').write(kml)

    def write_metadata(self, tile=None, children=[]):
        super(PlateCarree, self).write_metadata(tile, children)

        if tile is None: # create top level kml
            self.write_kml(os.path.basename(self.base), os.path.basename(self.base), self.kml_child_links(children))
            return
        # fill in kml templates
        rel_path = self.tile_path(tile)
        name = os.path.splitext(rel_path)[0]
        kml_links = self.kml_child_links(children, tile, '../../')
        tile_box = self.map_tiles2longlat_bounds([tile])[0]
        w, n, e, s = ['%.11G'%v for v in flatten(tile_box)]
        kml_overlay = kml_overlay_templ % {
            'name':    name,
            'href':    os.path.basename(rel_path),
            'min_lod': 128,
            'max_lod': 2048 if kml_links else -1,
            'order':   tile[0],
            'west':    w, 'north':    n,
            'east':    e, 'south':    s,
            }
        self.write_kml(name, name, kml_links, kml_overlay)
# PlateCarree

#############################

class PlateCarreeZYX(PlateCarree, ZYXtiling):
    'Plate Carrée, top-to-bottom tile numbering (a la Google Earth) ZYX directory structure'
#############################
    profile = 'geo'
    defaul_ext = '.zyx-geo'
    tms_profile = 'zyx-geodetic' # non-standard profile
#
profile_map.append(PlateCarreeZYX)
#

#############################

class PlateCarreeXYZ(PlateCarree, XYZtiling):
    'Plate Carrée, top-to-bottom tile numbering  (a la Google Earth)'
#############################
    profile = 'xyz-geo'
    defaul_ext = '.xyz-geo'
    tms_profile = 'xyz-geodetic' # non-standard profile
#
profile_map.append(PlateCarreeXYZ)
#

#############################

class PlateCarreeTMS(PlateCarree, TMStiling):
    'Plate Carrée, TMS tile numbering (bottom-to-top, global-geodetic - compatible tiles)'
#############################
    profile = 'tms-geo'
    defaul_ext = '.tms-geo'
    tms_profile = 'global-geodetic'
#
profile_map.append(PlateCarreeTMS)
#

kml_templ = '''<?xml version="1.0" encoding="utf-8"?>
<kml xmlns="http://earth.google.com/kml/2.1">

<!-- Generated by gdal_tiler.py (http://code.google.com/p/tilers-tools/) -->

    <Document>
%(dbg_start)s        <Style>
            <ListStyle id="hideChildren"> <listItemType>checkHideChildren</listItemType> </ListStyle>
        </Style>
%(dbg_end)s        <name>%(name)s</name>%(overlay)s%(links)s
    </Document>
</kml>
'''

kml_overlay_templ = '''
        <Region>
            <Lod>
                <minLodPixels>%(min_lod)s</minLodPixels>
                <maxLodPixels>%(max_lod)s</maxLodPixels>
            </Lod>
            <LatLonAltBox>
                <west>%(west)s</west> <north>%(north)s</north>
                <east>%(east)s</east> <south>%(south)s</south>
            </LatLonAltBox>
        </Region>
        <GroundOverlay>
            <name>%(name)s</name>
            <drawOrder>%(order)s</drawOrder>
            <Icon> <href>%(href)s</href> </Icon>
            <LatLonBox>
                <west>%(west)s</west> <north>%(north)s</north>
                <east>%(east)s</east> <south>%(south)s</south>
            </LatLonBox>
        </GroundOverlay>'''

kml_link_templ = '''
        <NetworkLink>
            <name>%(name)s</name>
            <Region>
                <Lod>
                    <minLodPixels>%(min_lod)s</minLodPixels>
                    <maxLodPixels>%(max_lod)s</maxLodPixels>
                </Lod>
                <LatLonAltBox>
                    <west>%(west)s</west> <north>%(north)s</north>
                    <east>%(east)s</east> <south>%(south)s</south>
                </LatLonAltBox>
            </Region>
            <Link> <viewRefreshMode>onRegion</viewRefreshMode>
                <href>%(href)s</href>
            </Link>
        </NetworkLink>'''
