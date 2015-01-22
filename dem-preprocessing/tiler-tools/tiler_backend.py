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

from __future__ import print_function
import os
import os.path
import shutil
import math
import cgi
from PIL import Image

try:
    from osgeo import gdal
    from osgeo import osr
    from osgeo import ogr
    from osgeo.gdalconst import *
#    gdal.TermProgress = gdal.TermProgress_nocb
except ImportError:
    import gdal
    import osr
    import ogr
    from gdalconst import *

from tiler_functions import *
import map2gdal

profile_map = []

resampling_map = {
    'near':     Image.NEAREST,
    'nearest':  Image.NEAREST,
    'bilinear': Image.BILINEAR,
    'bicubic':  Image.BICUBIC,
    'antialias':Image.ANTIALIAS,
    }
def resampling_lst():
    return resampling_map.keys()

base_resampling_map = {
    'near':         'NearestNeighbour',
    'nearest':      'NearestNeighbour',
    'bilinear':     'Bilinear',
    'cubic':        'Cubic',
    'cubicspline':  'CubicSpline',
    'lanczos':      'Lanczos',
    }
def base_resampling_lst():
    return base_resampling_map.keys()

#############################

class TilingScheme(object):

#############################
    #----------------------------

    def tile_path(self, tile):
        'relative path to a tile'
    #----------------------------
        z, x, y = tile
        return '%i/%i/%i%s' % (z, x, y, self.tile_ext)

class TMStiling(TilingScheme):
    tile_geo_origin = (-180, -90)
    tile_dim = (256, 256) # tile size in pixels

class XYZtiling(TilingScheme):
    tile_geo_origin = (-180, 90)
    tile_dim = (256, -256) # tile size in pixels

class ZYXtiling(XYZtiling):
    #----------------------------

    def tile_path(self, tile):
        'relative path to a tile'
    #----------------------------
        z, x, y = tile
        return 'z%i/%i/%i%s' % (z, y, x, self.tile_ext)

#############################

class BaseImg(object):
    '''Tile feeder for a base zoom level'''
#############################

    def __init__(self, dataset, world_ul, transparency=None):
        self.ds = dataset
        self.world_ul = world_ul
        self.transparency = transparency

        self.size = self.ds.RasterXSize, self.ds.RasterYSize
        self.bands = [self.ds.GetRasterBand(i+1) for i in range(self.ds.RasterCount-1)] # planoblique: avoid loading of second channel
        stats = self.bands[0].GetStatistics(0, 1) # planoblique: avoid loading of second channel
        print(stats) # planoblique: avoid loading of second channel
    def __del__(self):
        del self.bands
        del self.ds

    def get_tile(self, corners):
        '''crop raster as per pair of world pixel coordinates'''

        ul = [corners[0][i]-self.world_ul[i] for i in (0, 1)]
        sz = [corners[1][i]-corners[0][i] for i in (0, 1)]

        tile_bands = [bnd.ReadRaster(ul[0], ul[1], sz[0], sz[1], sz[0], sz[1], GDT_Float32) # planoblique
                    for bnd in self.bands]
        n_bands = len(self.bands)
        if n_bands == 1:
            opacity = 1
            mode = 'L'
            if self.transparency is not None:
                if chr(self.transparency) in tile_bands[0]:
                    colorset = set(tile_bands[0])
                    if len(colorset) == 1:  # fully transparent
                        return None, 0
                    else:                   # semi-transparent
                        opacity = -1
            img = Image.frombuffer('F', sz, tile_bands[0], 'raw', 'F', 0, 1) # planoblique
        else:
            aplpha = tile_bands[-1]
            if min(aplpha) == '\xFF':       # fully opaque
                opacity = 1
                tile_bands = tile_bands[:-1]
                mode = 'RGB' if n_bands > 2 else 'L'
            elif max(aplpha) == '\x00':     # fully transparent
                return None, 0
            else:                           # semi-transparent
                opacity = -1
                mode = 'RGBA' if n_bands > 2 else 'LA'
            img = Image.merge(mode, [Image.frombuffer('L', sz, bnd, 'raw', 'L', 0, 1) for bnd in tile_bands])
        return img, opacity
# BaseImg


#############################

class Pyramid(object):
    '''Tile pyramid generator and utilities'''
#############################

    zoom0_tiles = [1, 1] # tiles at zoom 0, default value

    palette = None
    transparency = None
    zoom_range = None
    zoom0_res = None
    max_extent = None
    max_resolution = None

    #----------------------------

    def __init__(self, src=None, dest=None, options=None):

    #----------------------------
        gdal.UseExceptions()

        self.temp_files = []
        self.src = src
        self.dest = dest
        ld('src dest',src, dest)
        self.options = LooseDict(options)
        if self.options.delete_src:
            self.temp_files.append(self.src)
        self.name = self.options.name
        self.tile_ext = self.options.tile_ext
        self.description = ''

        self.init_tile_grid()

    #----------------------------

    def __del__(self):

    #----------------------------
        try:
            if self.options.verbose < 2:
                for f in self.temp_files:
                    os.remove(f)
        except: pass

    #----------------------------

    def init_tile_grid(self):
        # init tile grid parameters
    #----------------------------

        self.proj_srs = txt2proj4(self.srs) # self.proj_srs may be changed later to avoid crossing longitude 180
        self.geog_srs = proj_cs2geog_cs(self.proj_srs)
        ld('proj, longlat', self.proj_srs, self.geog_srs)

        self.proj2geog = GdalTransformer(SRC_SRS=self.proj_srs, DST_SRS=self.geog_srs)
        max_x = self.proj2geog.transform_point((180, 0), inv=True)[0] # Equator's half length
        ld('max_x', max_x)

        # pixel resolution at the zoom 0
        res0 = max_x*2/abs(self.zoom0_tiles[0]*self.tile_dim[0])
        self.zoom0_res = [res0, -res0] # pixel 'y' goes downwards
        #~ self.max_resolution = [res0, res0] # for tilemap

        # upper left corner of a world raster
        self.pix_origin = (-max_x, abs(self.zoom0_res[1]*self.tile_dim[1]*self.zoom0_tiles[1]/2))

        # adjust tile origins to the limits of a world raster
        max_lat = self.proj2geog.transform_point(self.pix_origin)[1]
        to_lon, to_lat = self.tile_geo_origin

        # self.tile_origin may be changed later to avoid crossing longitude 180
        # but self.tile_geo_origin will retain the original setting
        self.tile_geo_origin = (to_lon, (max_lat if max_lat < to_lat else (-max_lat if -max_lat > to_lat else to_lat)))
        self.tile_origin = self.proj2geog.transform_point(self.tile_geo_origin, inv=True)

        ld('zoom0_tiles', self.zoom0_tiles, 'tile_dim', self.tile_dim, 'pix_origin', self.pix_origin, 'tile_origin', self.tile_origin, self.tile_geo_origin)

        # default map bounds to maximum limits (world map)
        ul = self.pix2coord(0, (0, 0))
        lr = [-ul[0], -ul[1]]

        self.bounds = (  ul, # upper left
                     (-ul[0], -ul[1]))    # lower right

        self.max_extent = (ul[0], lr[1], lr[0], ul[1])
        ld('max extent', self.max_extent)

    #----------------------------

    def init_map(self, zoom_parm):
        'initialize geo-parameters and generate base zoom level'
    #----------------------------

        # init variables
        self.tiles_prefix = self.options.tiles_prefix
        self.src_dir, src_f = os.path.split(self.src)
        self.base = os.path.splitext(src_f)[0]
        self.base_resampling = base_resampling_map[self.options.base_resampling]
        self.resampling = resampling_map[self.options.overview_resampling]

        #~ if self.options.verbose > 0:
            #~ print('\n%s -> %s '%(self.src, self.dest), end='')
        logging.info(' %s -> %s '%(self.src, self.dest))

        if os.path.isdir(self.dest):
            if self.options.noclobber and os.path.exists(self.dest):
                logging.error('Target already exists: skipping')
                return False
            else:
                shutil.rmtree(self.dest, ignore_errors=True)

        # connect to src dataset
        try:
            self.get_src_ds()
        except RuntimeError as exc:
            if self.options.skip_invalid:
                logging.error('%s' % exc.message[:-1])
                return False
            else:
                raise

        # calculate zoom range
        self.calc_zoom(zoom_parm)
        self.max_zoom = self.zoom_range[0]

        # shift target SRS to avoid crossing 180 meridian
        shifted_srs = self.shift_srs(self.max_zoom)
        shift_x = GdalTransformer(SRC_SRS=shifted_srs, DST_SRS=self.proj_srs).transform_point((0, 0))[0]
        if shift_x != 0:
            self.proj_srs = shifted_srs
            self.proj2geog = GdalTransformer(SRC_SRS=self.proj_srs, DST_SRS=self.geog_srs)
            self.pix_origin = (self.pix_origin[0]-shift_x, self.pix_origin[1])
            self.tile_origin = (self.tile_origin[0]-shift_x, self.tile_origin[1])
            ld('new_srs', shifted_srs, 'shift_x', shift_x, 'pix_origin', self.pix_origin)

        # get corners at the target SRS
        target_ds = gdal.AutoCreateWarpedVRT(self.src_ds, None, txt2wkt(shifted_srs))
        target_bounds = GdalTransformer(target_ds).transform([
            (0, 0),
            (target_ds.RasterXSize, target_ds.RasterYSize)])

        # self.bounds are set to a world raster, now clip to the max tileset area
        self.bounds = ((target_bounds[0][0],
                      min(self.bounds[0][1], target_bounds[0][1])),
                     (target_bounds[1][0],
                      max(self.bounds[1][1], target_bounds[1][1])))

        ld('target raster')
        ld('Upper Left', self.bounds[0], target_bounds[0], self.proj2geog.transform([self.bounds[0], target_bounds[0]]))
        ld('Lower Right', self.bounds[1], target_bounds[1], self.proj2geog.transform([self.bounds[1], target_bounds[1]]))
#        orig_ul = GdalTransformer(SRC_SRS=self.geog_srs, DST_SRS=self.srs).transform_point(
#            self.proj2geog.transform_point(target_bounds[0]))
#        ld(orig_ul[0]-target_bounds[0][0], orig_ul)
        return True

    #----------------------------

    def get_src_ds(self):
        'get src dataset, convert to RGB(A) if required'
    #----------------------------

        self.src_path = self.src
        if os.path.exists(self.src):
            self.src_path = os.path.abspath(self.src)
            #~ pf('')
            ld('self.src_path',self.src_path, self.src)

        # check for source raster type
        src_ds = gdal.Open(self.src_path, GA_ReadOnly)
        self.src_ds = src_ds
        self.description = self.src_ds.GetMetadataItem('DESCRIPTION')

        # source is successfully opened, then create destination dir
        os.makedirs(self.dest)

        src_geotr = src_ds.GetGeoTransform()
        src_proj = txt2proj4(src_ds.GetProjection())
        gcps = src_ds.GetGCPs()
        if gcps:
            ld('src GCPsToGeoTransform', gdal.GCPsToGeoTransform(gcps))

        if not src_proj and gcps :
            src_proj = txt2proj4(src_ds.GetGCPProjection())

        override_srs = self.options.srs
        if override_srs is not None:
            src_proj = txt2proj4(override_srs)

        ld('src_proj', src_proj, 'src geotr', src_geotr)
        assert src_proj, 'The source does not have a spatial reference system assigned'

        src_bands = src_ds.RasterCount
        band1 = src_ds.GetRasterBand(1)
        if src_bands == 1 and band1.GetColorInterpretation() == GCI_PaletteIndex : # source is a paletted raster
            transparency = None
            if self.base_resampling == 'NearestNeighbour' and self.resampling == Image.NEAREST :
                # check if src can be rendered in paletted mode
                color_table = band1.GetColorTable()
                ncolors = color_table.GetCount()
                palette = [color_table.GetColorEntry(i) for i in range(ncolors)]
                r, g, b, a = zip(*palette)
                pil_palette = flatten(zip(r, g, b))             # PIL doesn't support RGBA palettes
                if self.options.dst_nodata is not None:
                    transparency = int(self.options.dst_nodata.split(',')[0])
                elif min(a) == 0:
                    transparency = a.index(0)
                elif ncolors < 256:
                    pil_palette += [0, 0, 0]                   # the last color index is a transparency
                    transparency = len(pil_palette)/3-1

            ld('transparency', transparency)
            if transparency is not None: # render in paletted mode
                self.transparency = transparency
                self.palette = pil_palette
                ld('self.palette', self.palette)

            else: # convert src to rgb VRT
                if not src_geotr or src_geotr == (0.0, 1.0, 0.0, 0.0, 0.0, 1.0):
                    geotr_txt = ''
                else:
                    geotr_txt = geotr_templ % src_geotr

                gcplst_txt = ''
                if gcps:
                    gcp_lst = '\n'.join((gcp_templ % (g.Id, g.GCPPixel, g.GCPLine, g.GCPX, g.GCPY, g.GCPZ)
                                        for g in gcps))
                    gcp_proj = txt2proj4(src_ds.GetGCPProjection()) if override_srs is None else src_proj
                    gcplst_txt = gcplst_templ % (gcp_proj, gcp_lst)

                metadata = src_ds.GetMetadata()
                ld('metadata', metadata)
                if metadata:
                    mtd_lst = [xml_txt('MDI', metadata[mdkey], 4, key=mdkey) for mdkey in metadata]
                    meta_txt = meta_templ % '\n'.join(mtd_lst)
                else:
                    meta_txt = ''

                xsize, ysize = (src_ds.RasterXSize, src_ds.RasterYSize)
                blxsize, blysize = band1.GetBlockSize()

                band_lst = ''.join((band_templ % {
                    'band':     band,
                    'color':    color,
                    'src':      cgi.escape(self.src_path, quote=True),
                    'srcband':  1,
                    'xsize':    xsize,
                    'ysize':    ysize,
                    'blxsize':  blxsize,
                    'blysize':  blysize,
                    } for band, color in ((1, 'Red'), (2, 'Green'), (3, 'Blue'))))

                vrt_txt = vrt_templ % {
                    'xsize':    xsize,
                    'ysize':    ysize,
                    'metadata': meta_txt,
                    'srs':      (srs_templ % src_proj) if src_proj else '',
                    'geotr':    geotr_txt,
                    'gcp_list': gcplst_txt,
                    'band_list':band_lst,
                    }

                src_vrt = os.path.abspath(os.path.join(self.dest, self.base+'.src.vrt')) # auxilary VRT file
                self.temp_files.append(src_vrt)
                self.src_path = src_vrt
                with open(src_vrt, 'w') as f:
                    f.write(vrt_txt.encode('utf-8'))

                self.src_ds = gdal.Open(src_vrt, GA_ReadOnly)
                return # rgb VRT created
            # finished with a paletted raster

        if override_srs is not None: # src SRS needs to be relpaced
            src_vrt = os.path.join(self.dest, self.base+'.src.vrt') # auxilary VRT file
            self.temp_files.append(src_vrt)
            self.src_path = src_vrt

            vrt_drv = gdal.GetDriverByName('VRT')
            self.src_ds = vrt_drv.CreateCopy(src_vrt, src_ds) # replace src dataset

            ld('override_srs', override_srs, 'txt2wkt(override_srs)', txt2wkt(override_srs))
            self.src_ds.SetProjection(txt2wkt(override_srs)) # replace source SRS
            gcps = self.src_ds.GetGCPs()
            if gcps :
                self.src_ds.SetGCPs(gcps, txt2wkt(override_srs))

        # debug print
#        src_origin, src_extent = GdalTransformer(src_ds).transform([(0, 0), (src_ds.RasterXSize, src_ds.RasterYSize)])
#        src_proj = txt2proj4(src_ds.GetProjection())
#        src_proj2geog = GdalTransformer(SRC_SRS=src_proj, DST_SRS=proj_cs2geog_cs(src_proj))
#        ld('source_raster')
#        ld('Upper Left', src_origin, src_proj2geog.transform([src_origin]))
#        ld('Lower Right', src_extent, src_proj2geog.transform([src_extent]))

    #----------------------------

    def shift_srs(self, zoom=None):
        'change prime meridian to allow charts crossing 180 meridian'
    #----------------------------
        ul, lr = GdalTransformer(self.src_ds, DST_SRS=self.geog_srs).transform([
            (0, 0),
            (self.src_ds.RasterXSize, self.src_ds.RasterYSize)])
        ld('shift_srs ul', ul, 'lr', lr)
        if lr[0] <= 180 and ul[0] >= -180 and ul[0] < lr[0]:
            return self.proj_srs

        left_lon = ul[0]
        if zoom is not None: # adjust to a tile boundary
            left_xy = self.proj2geog.transform_point((left_lon, 0), inv=True)
            tile_left_xy = self.tile_bounds(self.coord2tile(zoom, left_xy))[0]
            left_lon = self.proj2geog.transform_point(tile_left_xy)[0]
        lon_0 = left_lon + 180
        ld('left_lon', left_lon, 'lon_0', lon_0)
        new_srs = '%s +lon_0=%f' % (self.proj_srs, lon_0)
        if not (lr[0] <= 180 and ul[0] >= -180):
            new_srs += ' +over +wktext' # allow for a map to span beyond -180 -- +180 range
        return new_srs

    #----------------------------

    def calc_zoom(self, zoom_parm):
        'determine and set a list of zoom levels to generate'
    #----------------------------

        # check raster parameters to find default zoom range
        ld('automatic zoom levels')

        # modify target srs to allow charts crossing meridian 180
        shifted_srs = self.shift_srs()

        t_ds = gdal.AutoCreateWarpedVRT(self.src_ds, None, txt2wkt(shifted_srs))
        geotr = t_ds.GetGeoTransform()
        res = (geotr[1], geotr[5])
        max_zoom = max(self.res2zoom_xy(res))

        # calculate min_zoom
        ul_c = (geotr[0], geotr[3])
        lr_c = gdal.ApplyGeoTransform(geotr, t_ds.RasterXSize, t_ds.RasterYSize)
        wh = (lr_c[0]-ul_c[0], ul_c[1]-lr_c[1])
        ld('ul_c, lr_c, wh', ul_c, lr_c, wh)
        min_zoom = min(self.res2zoom_xy([wh[i]/abs(self.tile_dim[i]) for i in (0, 1)]))

        self.set_zoom_range(zoom_parm, (min_zoom, max_zoom))

    #----------------------------

    def make_raster(self, zoom):

    #----------------------------

        # adjust raster extents to tile boundaries
        tile_ul, tile_lr = self.corner_tiles(zoom)
        ld('base_raster')
        ld('tile_ul', tile_ul, 'tile_lr', tile_lr)
        ul_c = self.tile_bounds(tile_ul)[0]
        lr_c = self.tile_bounds(tile_lr)[1]
        ul_pix = self.tile_pixbounds(tile_ul)[0]
        lr_pix = self.tile_pixbounds(tile_lr)[1]

        # base zoom level raster size
        dst_xsize = lr_pix[0]-ul_pix[0]
        dst_ysize = lr_pix[1]-ul_pix[1]

        ld('target Upper Left', self.bounds[0], ul_c, self.proj2geog.transform([self.bounds[0], ul_c]))
        ld('target Lower Right', self.bounds[1], lr_c, self.proj2geog.transform([self.bounds[1], lr_c]))

        # create VRT for base image warp

        # generate warp transform
        src_geotr = self.src_ds.GetGeoTransform()
        src_proj = txt2proj4(self.src_ds.GetProjection())
        gcp_proj = None

        if not self.options.tps and src_geotr and src_geotr != (0.0, 1.0, 0.0, 0.0, 0.0, 1.0):
            ok, src_igeotr = gdal.InvGeoTransform(src_geotr)
            assert ok
            src_transform = '%s\n%s' % (warp_src_geotr % src_geotr, warp_src_igeotr % src_igeotr)
        else:
            gcps = self.src_ds.GetGCPs()
            assert gcps, 'Neither geotransform, nor gpcs are in the source file %s' % self.src

            gcp_lst = [(g.Id, g.GCPPixel, g.GCPLine, g.GCPX, g.GCPY, g.GCPZ) for g in gcps]
            ld('src_proj', self.src_ds.GetProjection(), 'gcp_proj', self.src_ds.GetGCPProjection())
            gcp_proj = txt2proj4(self.src_ds.GetGCPProjection())
            if src_proj and gcp_proj != src_proj:
                coords = GdalTransformer(SRC_SRS=gcp_proj, DST_SRS=src_proj).transform([g[3:6] for g in gcp_lst])
                gcp_lst = [tuple(p[:3]+c) for p, c in zip(gcp_lst, coords)]

            gcp_txt = '\n'.join((gcp_templ % g for g in gcp_lst))
            #src_transform = warp_src_gcp_transformer % (0, gcp_txt)
            src_transform = warp_src_tps_transformer % gcp_txt

        res = self.zoom2res(zoom)
        #ul_ll, lr_ll = self.coords2longlat([ul_c, lr_c])
        ld('max_zoom', zoom, 'size', dst_xsize, dst_ysize, '-tr', res[0], res[1], '-te', ul_c[0], lr_c[1], lr_c[0], ul_c[1], '-t_srs', self.proj_srs)
        dst_geotr = ( ul_c[0], res[0], 0.0,
                    ul_c[1], 0.0, res[1] )
        ok, dst_igeotr = gdal.InvGeoTransform(dst_geotr)
        assert ok
        dst_transform = '%s\n%s' % (warp_dst_geotr % dst_geotr, warp_dst_igeotr % dst_igeotr)

        # generate warp options
        warp_options = []
        def w_option(name, value): # warp options template
            return '    <Option name="%s">%s</Option>' % (name, value)

        warp_options.append(w_option('INIT_DEST', 'NO_DATA'))

        # generate cut line
        if self.options.cut or self.options.cutline:
            cut_wkt = self.get_cutline()
        else:
            cut_wkt = None
        if cut_wkt:
            warp_options.append(w_option('CUTLINE', cut_wkt))
            if self.options.blend_dist:
                warp_options.append(w_option('CUTLINE_BLEND_DIST', self.options.blend_dist))

        src_bands = self.src_ds.RasterCount
        ld('src_bands', src_bands)

        # process nodata info
        src_nodata = None
        if self.options.src_nodata:
            src_nodata = map(int, self.options.src_nodata.split(','))
            assert len(src_nodata) == src_bands, 'Nodata must match the number of bands'
            if src_bands > 1:
                warp_options.append(w_option('UNIFIED_SRC_NODATA', 'YES'))
        dst_nodata = None
        if self.palette is not None:
            dst_nodata = [self.transparency]
        ld('nodata', src_nodata, dst_nodata)

        # src raster bands mapping
        vrt_bands = []
        wo_BandList = []
        for i in range(src_bands):
            vrt_bands.append(warp_band % (i+1, '/'))
            if src_nodata or dst_nodata:
                band_mapping_info = warp_band_mapping_nodata % (
                        warp_band_src_nodata % (src_nodata[i], 0) if src_nodata else '',
                        warp_band_dst_nodata % (dst_nodata[i], 0) if dst_nodata else '')
            else:
                band_mapping_info = '/'
            wo_BandList.append(warp_band_mapping % (i+1, i+1, band_mapping_info))

        if src_bands < 4 and self.palette is None:
            vrt_bands.append(warp_band % (src_bands+1, warp_band_color % 'Alpha'))

        vrt_text = warp_vrt % {
            'xsize':            dst_xsize,
            'ysize':            dst_ysize,
            'srs':              self.proj_srs,
            'geotr':            geotr_templ % dst_geotr,
            'band_list':        '\n'.join(vrt_bands),
            'blxsize':          abs(self.tile_dim[0]),
            'blysize':          abs(self.tile_dim[1]),
            'wo_ResampleAlg':   self.base_resampling,
            'wo_src_path':      cgi.escape(self.src_path, quote=True),
            'warp_options':     '\n'.join(warp_options),
            'wo_src_srs':       gcp_proj if gcp_proj else src_proj,
            'wo_dst_srs':       self.proj_srs,
            'wo_src_transform': src_transform,
            'wo_dst_transform': dst_transform,
            'wo_BandList':      '\n'.join(wo_BandList),
            'wo_DstAlphaBand':  warp_dst_alpha_band % (src_bands+1) if src_bands < 4  and self.palette is None else '',
            'wo_Cutline':       (warp_cutline % cut_wkt) if cut_wkt else '',
            }

        temp_vrt = os.path.join(self.dest, self.base+'.tmp.vrt') # auxilary VRT file
        self.temp_files.append(temp_vrt)
        with open(temp_vrt, 'w') as f:
            f.write(vrt_text.encode('utf-8'))

        # warp base raster
        base_ds = gdal.Open(vrt_text, GA_ReadOnly)
        self.progress()

        # close datasets in a proper order
        del self.src_ds

        # create base_image raster
        self.base_img = BaseImg(base_ds, ul_pix, self.transparency)

    #----------------------------

    def get_cutline(self):

    #----------------------------
        cutline = self.src_ds.GetMetadataItem('CUTLINE')
        ld('cutline', cutline)
        if cutline and not self.options.cutline:
            return cutline

        # try to find an external cut line
        if self.options.cutline:
            cut_file = self.options.cutline
        else: # try to find a file with a cut shape
            for ext in ('.gmt', '.shp', '.kml'):
                cut_file = os.path.join(self.src_dir, self.base+ext)
                if os.path.exists(cut_file):
                    break
            else:
                return None

        feature_name = self.base if self.options.cutline_match_name else None
        return shape2cutline(cut_file, self.src_ds, feature_name)

    #----------------------------

    def walk_pyramid(self):
        'generate pyramid'
    #----------------------------

        if not self.init_map(self.options.zoom):
            return

        # create a raster source for a base zoom
        self.make_raster(self.max_zoom)

        if not self.name:
            self.name = os.path.basename(self.dest)

        # map 'logical' tiles to 'physical' tiles
        ld('walk')
        self.tile_map = {}
        for zoom in self.zoom_range:
            tile_ul, tile_lr = self.corner_tiles(zoom)
            xx = (tile_ul[1], tile_lr[1])
            yy = (tile_ul[2], tile_lr[2])
            zoom_tiles = flatten([[
                        (zoom, x, y)
                    for x in range(min(xx), max(xx)+1)]
                for y in range(min(yy), max(yy)+1)])
            #ld('zoom_tiles', zoom_tiles, tile_ul, tile_lr)

            ntiles_x, ntiles_y = self.tiles_xy(zoom)
            zoom_tiles_map = dict([((z, x % ntiles_x, y), (z, x, y)) for z, x, y in zoom_tiles])
            self.tile_map.update(zoom_tiles_map)

        self.all_tiles = frozenset(self.tile_map) # store all tiles into a set
        ld('min_zoom', zoom, 'tile_ul', tile_ul, 'tile_lr', tile_lr, 'tiles', zoom_tiles_map)

        # top level tiles are in zoom_tiles_map now
        top_results = filter(None, map(self.proc_tile, zoom_tiles_map.keys()))

        # write top-level metadata (html/kml)
        self.write_metadata(None, [ch for img, ch, opacities in top_results])

        # cache back tiles transparency
        transparency = dict((
            (self.tile_path(tile), opc)
            for tile, opc in flatten((
                opacities for img, ch, opacities in top_results
                ))
            ))
        write_transparency(self.dest, transparency)

        self.progress(finished=True)

    #----------------------------

    def proc_tile(self, tile):

    #----------------------------

        ch_opacities = []
        ch_results = []
        zoom, x, y = tile
        if zoom == self.max_zoom: # get from the base image
            src_tile = self.tile_map[tile]
            tile_img, opacity = self.base_img.get_tile(self.tile_pixbounds(src_tile))
            if tile_img and self.palette:
                tile_img.putpalette(self.palette)
        else: # merge children
            opacity = 0
            ch_zoom = self.zoom_range[self.zoom_range.index(zoom)-1] # child's zoom
            dz = int(2**(ch_zoom-zoom))

            # compute children locations inside the parent raster
            tsz = [self.tile_dim[0], -self.tile_dim[1]] # align tiling ditrection according to the pixel direction ('y' goes downwards)
            ch_sz = [tsz[i]//dz for i in (0, 1)]        # raster offset increment
            ofs = [0 if tsz[i] > 0 else -tsz[i]+ch_sz[i] for i in (0, 1)]   # if negative -- needs to go in descending order
            #~ ld('tsz, ch_sz, ofs', tsz, ch_sz, ofs)

            ch_mozaic = dict(flatten(  # child tile: offsets to inside a parent tile
                [[((ch_zoom, x*dz+dx, y*dz+dy),
                        (ofs[0]+dx*ch_sz[0], ofs[1]+dy*ch_sz[1]))
                    for dx in range(dz)]
                for dy in range(dz)]))
            #ld(tile, ch_mozaic)

            children = self.all_tiles & frozenset(ch_mozaic) # get only real children
            ch_results = filter(None, map(self.proc_tile, children))
            #~ ld('tile', tile, 'children', children, 'ch_results', ch_results)

            # combine into a parent tile
            if len(ch_results) == 4 and all([opacities[0][1] == 1 for img, ch, opacities in ch_results]):
                opacity = 1
                mode_opacity = ''
            else:
                opacity=-1
                mode_opacity='A'

            tile_img=None
            for img, ch, opacity_lst in ch_results:
                ch_img=img.resize([i//dz for i in img.size], self.resampling)
                ch_mask=ch_img.split()[-1] if 'A' in ch_img.mode else None

                if tile_img is None:
                    if 'F' in ch_img.mode: # planoblique
                        tile_mode = 'F'
                    elif 'F' in ch_img.mode:
                        tile_mode = 'F' + mode_opacity
                    else:
                        tile_mode = 'RGB' + mode_opacity

                    if self.transparency is not None:
                        tile_img=Image.new(tile_mode, img.size, self.transparency)
                    else:
                        tile_img=Image.new(tile_mode, img.size)

                    if self.palette is not None:
                        tile_img.putpalette(self.palette)

                tile_img.paste(ch_img, ch_mozaic[ch], ch_mask)
                ch_opacities.extend(opacity_lst)

        #~ ld('proc_tile', tile, tile_img, opacity)
        if tile_img is not None and opacity != 0:
            self.write_tile(tile, tile_img)

            # write tile-level metadata (html/kml)
            self.write_metadata(tile, [ch for img, ch, opacities in ch_results])
            return tile_img, tile, [(tile, opacity)]+ch_opacities

    #----------------------------

    def write_tile(self, tile, tile_img):

    #----------------------------
        rel_path = self.tile_path(tile)
        full_path = os.path.join(self.dest, rel_path)
        try:
            os.makedirs(os.path.dirname(full_path))
        except: pass

        tile_format = self.options.tile_format
        if self.options.paletted and tile_format == 'png':
            try:
                tile_img = tile_img.convert('P', palette=Image.ADAPTIVE, colors=255)
            except ValueError:
                #ld('tile_img.mode', tile_img.mode)
                pass
        elif tile_img.mode == 'P' and tile_format in ('jpeg', 'webp'):
            mode = 'RGB' # + 'A' if self.transparency else ''
            try:
                tile_img = tile_img.convert(mode)
            except ValueError:
                #ld('tile_img.mode', tile_img.mode)
                pass

        if self.transparency is not None:
            tile_img.save(full_path, transparency=self.transparency)
        else:
            tile_img.save(full_path)

        self.progress()

    #----------------------------

    def map_tiles2longlat_bounds(self, tiles):
        'translate "logical" tiles to latlong boxes'
    #----------------------------
        # via 'logical' to 'physical' tile mapping
        return self.bounds_lst2longlat([self.tile_bounds(self.tile_map[t]) for t in tiles])

    #----------------------------

    def write_metadata(self, tile=None, children=[]):

    #----------------------------
        if tile is None:
            self.write_tilemap()

    #----------------------------

    def write_tilemap(self):
        '''Generate JSON for a tileset description'''
    #----------------------------

        # reproject extents back to the unshifted SRS
        bbox = GdalTransformer(SRC_SRS=self.proj_srs, DST_SRS=self.srs).transform(self.bounds)
        # get back unshifted tile origin
        un_tile_origin = GdalTransformer(SRC_SRS=self.geog_srs, DST_SRS=self.srs).transform_point(self.tile_geo_origin)
        ld('un_tile_origin', un_tile_origin, self.tile_geo_origin, self.geog_srs, self.srs)

        tile_mime = mime_from_ext(self.tile_ext)
        tilemap = {
            'type':       'TileMap',
            'properties': {
                'title':        self.name,
                'description':  self.description,
                },
            'tiles': {
                'size':         map(abs, self.tile_dim),
                'inversion':    [i<0 for i in self.tile_dim],
                'ext':          self.tile_ext[1:],
                'mime':         tile_mime,
                'origin':       un_tile_origin,
                'max_extent': self.max_extent
                },
            'bbox': (
                bbox[0][0],
                bbox[1][1],
                bbox[1][0],
                bbox[0][1]),
            'crs': {
                "type": "name",
                "properties": {
                    "name":     self.tilemap_crs,
                    }
                },
            'tilesets': dict([
                (zoom,
                    {"href": 'z%d' % zoom,
                    "units_per_pixel": self.zoom2res(zoom)[0]})
                for zoom in reversed(self.zoom_range)]),
            }


        write_tilemap(self.dest, tilemap)
        ld(tilemap)

    #----------------------------
    #
    # utility functions
    #
    #----------------------------

    @staticmethod
    def profile_class(profile_name):
        for cls in profile_map:
            if cls.profile == profile_name:
                return cls
        else:
            raise Exception("Invalid profile: %s" % profile_name)

    @staticmethod
    def profile_lst(tty=False):
        if not tty:
            return [c.profile for c in profile_map]
        print('\nOutput profiles and compatibility:\n')
        [print('%10s - %s' % (c.profile, c.__doc__)) for c in profile_map]
        print()

    def zoom2res(self, zoom):
        return [self.zoom0_res[i]/2**zoom for i in (0, 1)]

    def res2zoom_xy(self, res):
        'resolution to zoom levels (separate for x and y)'
        z = [int(math.floor(math.log(abs(self.zoom0_res[i]/res[i]), 2))) for i in (0, 1)]
        return [v if v>0 else 0 for v in z]

    def pix2tile(self, zoom, pix_coord):
        'pixel coordinates to tile (z, x, y)'
        res = self.zoom2res(zoom)
        tile_xy = [int(round(
                (pix_coord[i]*res[i] + self.pix_origin[i] - self.tile_origin[i])/abs(res[i])
                )) // self.tile_dim[i]
                for i in (0, 1)] # NB tile_dim can be negative!
        return [zoom]+tile_xy

    def coord2tile(self, zoom, coord):
        'cartesian coordinates to tile numbers'
        return self.pix2tile(zoom, self.coord2pix(zoom, coord))

    def tile_pixbounds(self, tile):
        'pixel coordinates of a tile'
        z = tile[0]
        return [self.coord2pix(z, c) for c in self.tile_bounds(tile)]

    def tile_bounds(self, tile):
        "cartesian coordinates of a tile's corners"
        res = self.zoom2res(tile[0])
        xy1 = [   tile[1+i] *self.tile_dim[i]*abs(res[i])+self.tile_origin[i] for i in (0, 1)]
        xy2 = [(1+tile[1+i])*self.tile_dim[i]*abs(res[i])+self.tile_origin[i] for i in (0, 1)]
        xx, yy = zip(xy1, xy2)
        ul = [min(xx), max(yy)]
        lr = [max(xx), min(yy)]
        return (ul, lr)

    def coord2pix(self, zoom, coord):
        'cartesian coordinates to pixel coordinates'
        res = self.zoom2res(zoom)
        return [int(round((coord[i]-self.pix_origin[i])/res[i])) for i in (0, 1)]

    def pix2coord(self, zoom, pix_coord):
        res = self.zoom2res(zoom)
        return [pix_coord[i]*res[i]+self.pix_origin[i] for i in (0, 1)]

    def tiles_xy(self, zoom):
        'number of tiles along X and Y axes'
        return map(lambda v: v*2**zoom, self.zoom0_tiles)

    def coords2longlat(self, coords):
        longlat = [i[:2] for i in self.proj2geog.transform(coords)]
        return longlat

    def bounds_lst2longlat(self, box_lst):
        deg_lst = self.coords2longlat(flatten(box_lst))
        ul_lst = deg_lst[0::2]
        lr_lst = deg_lst[1::2]
        return [[
            (ul[0] if ul[0] <  180 else ul[0]-360, ul[1]),
            (lr[0] if lr[0] > -180 else lr[0]+360, lr[1]),
            ] for ul, lr in zip(ul_lst, lr_lst)]

    def corner_tiles(self, zoom):
        p_ul = self.coord2pix(zoom, self.bounds[0])
        t_ul = self.pix2tile(zoom, (p_ul[0], p_ul[1]))

        p_lr = self.coord2pix(zoom, self.bounds[1])
        t_lr = self.pix2tile(zoom, (p_lr[0], p_lr[1]))

        box_ul, box_lr = [self.tile_bounds(t) for t in (t_ul, t_lr)]
        #~ ld('corner_tiles zoom', zoom,
            #~ 'p_ul', p_ul, 'p_lr', p_lr, 't_ul', t_ul, 't_lr', t_lr,
            #~ 'longlat', self.coords2longlat([box_ul[0], box_lr[1]])
            #~ )
        return t_ul, t_lr

    def set_zoom_range(self, zoom_parm, defaults=(0, 22)):
        'set a list of zoom levels from a parameter list'

        if not zoom_parm:
            zoom_parm = '%d:%d' % defaults

        zchunk_lst = [z.split(':') for z in zoom_parm.split(',')]
        zlist = []
        for zchunk in zchunk_lst:
            if len(zchunk) == 1:
                zlist.append(int(zchunk[0]))
            else:
                # calculate zoom range
                zrange = []
                for n, d in zip(zchunk, defaults):
                    if n == '':              # set to default
                        z = d
                    elif n.startswith('-'): # set to default - n
                        z = d-int(n[1:])
                    elif n.startswith('+'): # set to default + n
                        z = d+int(n[1:])
                    else:                   # set to n
                        z = int(n)
                    zrange.append(z)

                # update range list
                zlist += range(min(zrange), max(zrange)+1)

        self.zoom_range = list(reversed(sorted(set(zlist))))
        ld('zoom_range', self.zoom_range, defaults)

    def in_range(self, ul_tile, lr_tile=None):
        if not ul_tile:
            return False
        if not lr_tile:
             lr_tile = ul_tile

        # y axis goes downwards
        zoom, tile_xmin, tile_ymin = ul_tile
        zoom, tile_xmax, tile_ymax = lr_tile

        if self.zoom_range and zoom not in self.zoom_range:
            return False

        ul_zoom, lr_zoom = self.corner_tiles(zoom)
        # y axis goes downwards
        z, zoom_xmin, zoom_ymin = ul_zoom
        z, zoom_xmax, zoom_ymax = lr_zoom

        res = not (
            tile_xmin > zoom_xmax or tile_xmax < zoom_xmin or
            tile_ymin > zoom_ymax or tile_ymax < zoom_ymin
            )

        #~ ld('in_range zoom', ul_zoom, lr_zoom)
        #~ ld('in_range tile', ul_tile, lr_tile, res)

        return res

    def set_region(self, point_lst, source_srs=None):
        if source_srs and source_srs != self.proj_srs:
            point_lst = GdalTransformer(SRC_SRS=source_srs, DST_SRS=self.proj_srs).transform(point_lst)

        x_coords, y_coords = zip(*point_lst)[0:2]
        upper_left = min(x_coords), max(y_coords)
        lower_right = max(x_coords), min(y_coords)
        self.bounds = [upper_left, lower_right]

    def load_region(self, datasource):
        if not datasource:
            return
        point_lst = flatten(shape2mpointlst(datasource, self.proj_srs))
        #~ ld(datasource, point_lst)
        self.set_region(point_lst)

    # progress display
    tick_rate = 50
    count = 0
    def progress(self, finished=False):
        if self.options.verbose == 0:
            pass
        elif finished:
            pf('')
        elif self.count % self.tick_rate == 0:
            pf('.', end='')
        self.count += 1

# Pyramid

#----------------------------
#
# templates for VRT XML
#
#----------------------------

def xml_txt(name, value=None, indent=0, **attr_dict):
    attr_txt = ''.join((' %s="%s"' % (key, attr_dict[key]) for key in attr_dict))
    val_txt = ('>%s</%s' % (cgi.escape(value, quote=True), name)) if value else '/'
    return '%s<%s%s%s>' % (' '*indent, name, attr_txt, val_txt)

warp_vrt = '''<VRTDataset rasterXSize="%(xsize)d" rasterYSize="%(ysize)d" subClass="VRTWarpedDataset">
  <SRS>%(srs)s</SRS>
%(geotr)s%(band_list)s
  <BlockXSize>%(blxsize)d</BlockXSize>
  <BlockYSize>%(blysize)d</BlockYSize>
  <GDALWarpOptions>
    <!-- <WarpMemoryLimit>6.71089e+07</WarpMemoryLimit> -->
    <ResampleAlg>%(wo_ResampleAlg)s</ResampleAlg>
    <WorkingDataType>Float32</WorkingDataType>
    <SourceDataset relativeToVRT="0">%(wo_src_path)s</SourceDataset>
%(warp_options)s
    <Transformer>
      <ApproxTransformer>
        <MaxError>0.125</MaxError>
        <BaseTransformer>
          <GenImgProjTransformer>
%(wo_src_transform)s
%(wo_dst_transform)s
            <ReprojectTransformer>
              <ReprojectionTransformer>
                <SourceSRS>%(wo_src_srs)s</SourceSRS>
                <TargetSRS>%(wo_dst_srs)s</TargetSRS>
              </ReprojectionTransformer>
            </ReprojectTransformer>
          </GenImgProjTransformer>
        </BaseTransformer>
      </ApproxTransformer>
    </Transformer>
    <BandList>
%(wo_BandList)s
    </BandList>
%(wo_DstAlphaBand)s%(wo_Cutline)s  </GDALWarpOptions>
</VRTDataset>
'''
warp_band = '  <VRTRasterBand dataType="Float32" band="%d" subClass="VRTWarpedRasterBand"%s>'
warp_band_color = '>\n    <ColorInterp>%s</ColorInterp>\n  </VRTRasterBand'
warp_dst_alpha_band = '    <DstAlphaBand>%d</DstAlphaBand>\n'
warp_cutline = '    <Cutline>%s</Cutline>\n'
warp_dst_geotr = '            <DstGeoTransform> %r, %r, %r, %r, %r, %r</DstGeoTransform>'
warp_dst_igeotr = '            <DstInvGeoTransform> %r, %r, %r, %r, %r, %r</DstInvGeoTransform>'
warp_src_geotr = '            <SrcGeoTransform> %r, %r, %r, %r, %r, %r</SrcGeoTransform>'
warp_src_igeotr = '            <SrcInvGeoTransform> %r, %r, %r, %r, %r, %r</SrcInvGeoTransform>'
warp_band_mapping = '      <BandMapping src="%d" dst="%d"%s>'
warp_band_src_nodata = '''
        <SrcNoDataReal>%d</SrcNoDataReal>
        <SrcNoDataImag>%d</SrcNoDataImag>'''
warp_band_dst_nodata = '''
        <DstNoDataReal>%d</DstNoDataReal>
        <DstNoDataImag>%d</DstNoDataImag>'''
warp_band_mapping_nodata = '''>%s%s
      </BandMapping'''
warp_src_gcp_transformer = '''            <SrcGCPTransformer>
              <GCPTransformer>
                <Order>%d</Order>
                <Reversed>0</Reversed>
                <GCPList>
%s
                </GCPList>
              </GCPTransformer>
            </SrcGCPTransformer>'''
warp_src_tps_transformer = '''            <SrcTPSTransformer>
              <TPSTransformer>
                <Reversed>0</Reversed>
                <GCPList>
%s
                </GCPList>
              </TPSTransformer>
            </SrcTPSTransformer>'''

gcp_templ = '    <GCP Id="%s" Pixel="%r" Line="%r" X="%r" Y="%r" Z="%r"/>'
gcplst_templ = '  <GCPList Projection="%s">\n%s\n  </GCPList>\n'
geotr_templ = '  <GeoTransform> %r, %r, %r, %r, %r, %r</GeoTransform>\n'
meta_templ = '  <Metadata>\n%s\n  </Metadata>\n'
band_templ = '''  <VRTRasterBand dataType="Float32" band="%(band)d">
    <ColorInterp>%(color)s</ColorInterp>
    <ComplexSource>
      <SourceFilename relativeToVRT="0">%(src)s</SourceFilename>
      <SourceBand>%(srcband)d</SourceBand>
      <SourceProperties RasterXSize="%(xsize)d" RasterYSize="%(ysize)d" DataType="Float32" BlockXSize="%(blxsize)d" BlockYSize="%(blysize)d"/>
      <SrcRect xOff="0" yOff="0" xSize="%(xsize)d" ySize="%(ysize)d"/>
      <DstRect xOff="0" yOff="0" xSize="%(xsize)d" ySize="%(ysize)d"/>
      <ColorTableComponent>%(band)d</ColorTableComponent>
    </ComplexSource>
  </VRTRasterBand>
'''
srs_templ = '  <SRS>%s</SRS>\n'
vrt_templ = '''<VRTDataset rasterXSize="%(xsize)d" rasterYSize="%(ysize)d">
%(metadata)s%(srs)s%(geotr)s%(gcp_list)s%(band_list)s</VRTDataset>
'''
