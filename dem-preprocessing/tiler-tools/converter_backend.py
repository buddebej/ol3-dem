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

import os
import os.path
import glob
import shutil
import json
import tempfile
import StringIO
import struct
from multiprocessing import Pool
import itertools

from PIL import Image
#~ from PIL import WebPImagePlugin

from tiler_functions import *
from gdal_tiler import Pyramid

#############################

class Tile(object):

#############################
    def __init__(self, coord):
        self._coord = tuple(coord)
        self.path = None
        self.temp = False

    def coord(self):
        return self._coord

    def get_mime(self):
        return mime_from_ext(self.get_ext())

    def close_file(self):
        if self.temp and self.path and os.path.exists(self.path):
            ld('tile', self.coord())
            os.remove(self.path)
            self.path = None

#############################

class FileTile(Tile):

#############################
    def __init__(self, coord, path, temp=False):
        super(FileTile, self).__init__(coord)
        self.path = path
        self.temp = temp

    def data(self):
        with open(self.path, 'rb') as f:
            return f.read()

    def get_ext(self):
        return os.path.splitext(self.path)[1]

    def copy2file(self, dst, link=False):
        if link and os.name == 'posix':
            dst_dir = os.path.split(dst)[0]
            src = os.path.relpath(self.path, dst_dir)
            os.symlink(src, dst)
        else:
            shutil.copy(self.path, dst)

    def get_file(self):
        return self.path

#############################

class FileTileNoExt(FileTile):

#############################
    def get_ext(self):
        return ext_from_file(self.path)

#############################

class PixBufTile(Tile):

#############################
    def __init__(self, coord, pixbuf, key=None, dataType=None):
        super(PixBufTile, self).__init__(coord)
        self.pixbuf = pixbuf
        self.data_type = dataType

    def data(self):
        return self.pixbuf

    def get_ext(self):
        if self.data_type:
            ext = ext_from_mime(self.data_type)
        else:
            ext = ext_from_buffer(self.pixbuf)
        return ext

    def copy2file(self, dest_path, link=False):
        with open(dest_path, 'wb') as f:
            f.write(self.pixbuf)

    def get_file(self):
        self.temp = True
        f_handle, self.path = tempfile.mkstemp(prefix='s%d-%d-%d_' % self.coord(), suffix=self.get_ext())

        os.write(f_handle, self.pixbuf)
        os.close(f_handle)
        return self.path

#----------------------------

tile_converters = []

#############################

class TileConverter(object):

#############################
    profile_name = 'copy'
    dst_ext = None
    src_formats = () # by default do not convert tiles

    def __init__(self, options):
        self.options = options
        ld('TileConverter', self.profile_name)


    def __call__(self, tile):
        'convert tile'
        try:
            if tile.get_ext() in self.src_formats:
                return self.convert_tile(tile)
            else:
                return tile # w/o conversion
        except (EnvironmentError, KeyError):
            return None

    @staticmethod
    def get_class(profile, isDest=False):
        for cls in tile_converters:
            if profile == cls.profile_name:
                return cls
        else:
            raise Exception('Invalid format: %s' % profile)

    @staticmethod
    def list_tile_converters():
        for cls in tile_converters:
            print cls.profile_name

tile_converters.append(TileConverter)

#############################

class ShellConverter (TileConverter):

#############################
    prog_name = None

    def __init__(self, options):
        super(ShellConverter, self).__init__(options)
        self.dst_dir = tempfile.gettempdir()

        if self.prog_name:
            try: # check if converter programme is available
                prog_path = command(['which', self.prog_name]).strip()
            except:
                raise Exception('Can not find %s executable' % self.prog_name)

    def convert_tile(self, src_tile):

        src_path = src_tile.get_file()
        #~ ld('convert_tile', src_path)
        base_name = os.path.splitext(os.path.split(src_path)[1])[0]
        dst_dir = tempfile.gettempdir()
        coord = src_tile.coord()
        suffix = ('-%d-%d-%d' % coord) + self.dst_ext
        dst_path = os.path.join(dst_dir, base_name + suffix)

        self.call_converter(src_path, dst_path, suffix)

        src_tile.close_file()
        dst_tile = FileTile(coord, dst_path, temp=True)
        return dst_tile

#############################

class PngConverter (ShellConverter):
    'optimize png using pngnq utility'
#############################
    profile_name = 'pngnq'
    prog_name = 'pngnq'
    dst_ext = '-nq8.png'
    src_formats = ('.png',)

    def call_converter(self, src, dst, suffix):

        command(['pngnq', '-f', '-n', self.options.colors, '-e', suffix, '-d', self.dst_dir, src])

tile_converters.append(PngConverter)

#############################

class WebpConverter (ShellConverter):
    'convert to webp'
#############################
    profile_name = 'webp'
    dst_ext = '.webp'
    src_formats = ('.png','.jpg','.jpeg','.gif')

    def call_converter(self, src, dst, suffix):

        command(['cwebp', '-alpha_cleanup', '-q', str(self.options.quality), '-o', dst, src])

tile_converters.append(WebpConverter)

#############################

class WebpNoAlphaConverter (ShellConverter):
    'convert to webp; discard alpha channel'
#############################
    profile_name = 'webp-noalpha'
    dst_ext = '.webp'
    src_formats = ('.png','.jpg','.jpeg','.gif')

    def call_converter(self, src, dst, suffix):

        command(['cwebp', '-preset', 'drawing', '-noalpha', '-q', str(self.options.quality), '-o', dst, src])

tile_converters.append(WebpNoAlphaConverter)


#~ #############################
#~
#~ class WebpPilConverter (TileConverter):
    #~ 'convert to webp'
#~ #############################
    #~ profile_name = 'webppil'
    #~ dst_ext = '.webp'
    #~ src_formats = ('.png','.jpg','.jpeg','.gif')
#~
    #~ def convert_tile(self, src, dst, dpath):
        #~ img = Image.open(src)
        #~ img.save(dst, optimize=True, quality=self.options.quality)
#~
#~ tile_converters.append(WebpPilConverter)


#############################

class JpegConverter (TileConverter):
    'convert to jpeg'
#############################
    profile_name = 'jpeg'
    dst_ext = '.jpg'
    src_formats = ('.png', '.gif')

    def convert_tile(self, tile):
        src = StringIO.StringIO(tile.data())
        img = Image.open(src)
        dst = StringIO.StringIO()
        img.save(dst, 'jpeg', optimize=True, quality=self.options.quality)

        dtile = PixBufTile(tile.coord(), dst.getvalue())
        src.close()
        dst.close()

        return dtile

tile_converters.append(JpegConverter)

#----------------------------

tileset_profiles = []

tile_converter = None

def global_converter(tile):
    #~ log('tile', tile.coord())
    tile = tile_converter(tile)
    return tile

#############################

class TileSet(object):

#############################

    #~ tile_converter = None
    pool = None

    def __init__(self, root=None, options=None, src=None):
        options = LooseDict(options)
        options.isDest = src is not None

        self.root = root
        self.options = options
        self.src = src

        self.srs = self.options.proj4def or self.options.tiles_srs
        self.tilemap_crs = self.options.tiles_srs or self.tilemap_crs
        self.options.tiles_srs = self.srs

        self.zoom_levels = {}
        self.pyramid = Pyramid.profile_class('generic')(options=options)

        if not self.options.isDest:
            assert os.path.exists(root), 'No file or directory found: %s' % root
            self.ext = os.path.splitext(root)[1]
            if self.options.zoom:
                self.pyramid.set_zoom_range(self.options.zoom)
            if self.options.region:
                self.pyramid.load_region(self.options.region)
        else:
            basename = os.path.splitext(os.path.basename(self.root or src.root))[0]
            df_name = os.path.splitext(basename)[0]
            if self.options.region:
                df_name += '-' + os.path.splitext(self.options.region)[0]
            self.name = self.options.name or df_name

            if not self.root:
                suffix = self.ext if self.ext != src.ext else self.ext + '0'
                self.root = os.path.join(options.dst_dir, self.name + suffix)

            if os.path.exists(self.root):
                if self.options.remove_dest:
                    if os.path.isdir(self.root):
                        shutil.rmtree(self.root, ignore_errors=True)
                    else:
                        os.remove(self.root)
                else:
                    assert self.options.append, 'Destination already exists: %s' % root

            if self.options.convert_tile:
                global tile_converter
                tile_converter = TileConverter.get_class(self.options.convert_tile)(options)
                if not (self.options.nothreads or self.options.debug):
                    self.pool = Pool()

    @staticmethod
    def get_class(profile, isDest=False):
        for cls in tileset_profiles:
            if profile == cls.format and ((not isDest and cls.input) or (isDest and cls.output)):
                return cls
        else:
            raise Exception('Invalid format: %s' % profile)

    @staticmethod
    def list_profiles():
        for cl in tileset_profiles:
            print '%10s\t%s%s\t%s' % (
                cl.format,
                'r' if cl.input else ' ',
                'w' if cl.output else ' ',
                cl.__doc__
                )

    def in_range(self, ul_coords, lr_coords=None):
        if not ul_coords:
            return False
        if not self.pyramid:
            return True
        return self.pyramid.in_range(ul_coords, lr_coords)

    def __del__(self):
        log('self.count', self.count)

    def __iter__(self): # to be defined by a child
        raise Exception('Not implemented!')

    def convert(self):
        pf('%s -> %s ' % (self.src.root, self.root), end='')

        if self.pool:
            src = self.pool.imap_unordered(global_converter, self.src, chunksize=10)
        elif self.options.convert_tile:
            src = itertools.imap(global_converter, self.src)
        else:
            src = self.src

        for tile in src:
            if tile is not None:
                self.process_tile(tile)

        if self.pool:
            self.pool.close()
            self.pool.join()

        if self.count > 0:
            self.finalize_pyramid()
            self.finalize_tileset()
        else:
            pf('No tiles converted', end='')
        pf('')

    def process_tile(self, tile):
        log('process_tile', tile)
        self.store_tile(tile)
        self.counter()

        # collect min max values for tiles processed
        zxy = list(tile.coord())
        z = zxy[0]

        min_max = self.zoom_levels.get(z, []) # min, max
        zzz, xxx, yyy = zip(*(min_max+[zxy]))
        self.zoom_levels[z] = [[z, min(xxx), min(yyy)], [z, max(xxx), max(yyy)]]
        tile.close_file()

    def finalize_pyramid(self):
        log('self.zoom_levels', self.zoom_levels)

        # compute "effective" covered area
        prev_sq = 0
        for z in reversed(sorted(self.zoom_levels)):
            ul_zxy, lr_zxy = self.zoom_levels[z]
            ul_c = self.pyramid.tile_bounds(ul_zxy)[0]
            lr_c = self.pyramid.tile_bounds(lr_zxy)[1]
            sq = (lr_c[0]-ul_c[0])*(ul_c[1]-lr_c[1])
            area_diff = round(prev_sq/sq, 5)
            log('ul_c, lr_c', z, ul_c, lr_c, sq, area_diff)
            if area_diff == 0.25:
                break # this must be an exact zoom of a previous level
            area_coords = [ul_c, lr_c]
            prev_sq = sq

        self.pyramid.set_region(area_coords)
        self.pyramid.set_zoom_range(','.join(map(str, self.zoom_levels.keys())))

        self.pyramid.name = self.name

    def finalize_tileset(self):
        pass

    count = 0
    tick_rate = 10
    def counter(self):
        self.count += 1
        if self.count % self.tick_rate == 0:
            pf('.', end='')
            return True
        else:
            return False

# TileSet

#############################

class TileDir(TileSet):

#############################
    tile_class = FileTile

    def __init__(self, *args, **kw_args):
        super(TileDir, self).__init__(*args, **kw_args)

        if self.options.isDest:
            try:
                os.makedirs(self.root)
            except os.error: pass

    def __iter__(self):
        for f in glob.iglob(os.path.join(self.root, self.dir_pattern)):
            coord = self.path2coord(f)
            if not self.in_range(coord):
                continue
            yield self.tile_class(coord, f)

    def path2coord(self, tile_path):
        raise Exception('Unimplemented!')

    def coord2path(self, z, x, y):
        raise Exception('Unimplemented!')

    def dest_ext(self, tile):
        return tile.get_ext()

    def store_tile(self, tile):
        try:
            tile_ext = self.dest_ext(tile)
            self.tile_ext = tile_ext
        except KeyError:
            tile_ext = '.xxx' # invalid file type
        dest_path = os.path.join(self.root, self.coord2path(*tile.coord())) + tile_ext
        log('%s -> %s' % (tile.path, dest_path))
        try:
            os.makedirs(os.path.split(dest_path)[0])
        except os.error: pass
        tile.copy2file(dest_path, self.options.link)
# TileDir

#############################

class TileMapDir(TileDir):

#############################

    def finalize_tileset(self):
        self.pyramid.tile_ext = self.tile_ext
        self.pyramid.dest = self.root
        self.pyramid.write_metadata()

# TileMapDir
