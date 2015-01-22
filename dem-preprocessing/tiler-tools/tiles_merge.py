#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# Copyright (c) 2010-2013 Vadim Shlyakhov
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

import sys
import os
import os.path
import glob
import shutil
import logging
import optparse
from PIL import Image
import pickle

from tiler_functions import *

class KeyboardInterruptError(Exception):
    pass

def f_approx_eq(a, b, eps):
    return (abs(a - b) / (abs(a) + abs(b))/2) < eps

def transparency(img):
    'estimate transparency of an image'
    (r, g, b, a) = img.split()
    (a_min, a_max) = a.getextrema() # get min/max values for alpha channel
    return 1 if a_min == 255 else 0 if a_max == 0 else -1


class MergeSet:
    def __init__(self, src_dir, dst_dir):

        if options.strip_src_ext:
            src_dir = os.path.splitext(src)[0]
        if options.add_src_ext is not None:
            src_dir += options.add_src_ext
        pf(src_dir+' ', end='')

        self.src_dir = src_dir
        self.dst_dir = dst_dir

        copy_viewer(self.dst_dir)
        # copy tilemap
        src_f = os.path.join(src_dir, 'tilemap.json')
        dst_f = os.path.join(dst_dir, 'tilemap.json')
        if os.path.exists(src_f) and not os.path.exists(dst_f):
            shutil.copy(src_f, dst_f)

        # read metadata
        self.src = read_tilemap(src_dir)
        self.dst = read_tilemap(dst_dir)
        self.tile_size = self.src['tiles']['size']

        # get a list of source tiles
        try:
            cwd = os.getcwd()
            os.chdir(src_dir)
            self.sources = dict.fromkeys(
                glob.iglob('z[0-9]*/*/*.%s' % self.src['tiles']['ext']),
                None
                )
        finally:
            os.chdir(cwd)
        #ld(self.sources)

        # load cached tile transparency data if any
        self.sources.update(read_transparency(src_dir))
        #ld(repr(self.src_transp))

        # define crop map for underlay function
        szx, szy = self.tile_size
        if self.src['tiles']['inversion'][1]: # google
            self.underlay_offsets = [
                # left   top
                (   0,   0), (szx,   0),
                (   0, szy), (szx, szy),
                ]
        else:                   # TMS
            self.underlay_offsets = [
                # left   top
                (   0, szy), (szx, szy),
                (   0,   0), (szx,   0),
                ]

    def merge_metadata(self):
        'adjust destination metadata'

        src = self.src
        dst = self.dst

        dst["properties"]["title"] = os.path.split(dst_dir)[1]
        dst["properties"]["description"] = 'merged tileset'

        ld([round(i/1000) for i in src["bbox"]], [round(i/1000) for i in dst["bbox"]])
        for i, min_max in zip(range(4), (min, min, max, max)):
            dst["bbox"][i] = min_max(src["bbox"][i], dst["bbox"][i])

        dst["tilesets"].update(src["tilesets"])

        write_tilemap(self.dst_dir, dst)

    def underlay(self, tile, upper_path, upper_raster, upper_origin=(0, 0), level=1):
        if level > options.underlay:
            return

        (s, ext) = os.path.splitext(tile)
        (s, x) = os.path.split(s)
        (z, y) = os.path.split(s)
        (z, y, x) = map(int, (z[1:], y, x))
        dz, dx, dy = z+1, x*2, y*2
        dst_tiles = [(dx, dy), (dx+1, dy),
                   (dx, dy+1), (dx+1, dy+1)]

        for dst_xy, crop_offset in zip(dst_tiles, self.underlay_offsets):
            dst_tile = 'z%i/%i/%i%s' % (dz, dst_xy[1], dst_xy[0], ext)
            dst_path = os.path.join(self.dst_dir, dst_tile)
            if dst_tile in self.sources:
                continue # higher level zoom source exists

            l2 = 2**level
            crop_origin = [p1 + p2/l2 for p1, p2 in zip(upper_origin, crop_offset)]

            if os.path.exists(dst_path):
                dst_raster = Image.open(dst_path).convert("RGBA")
                if transparency(dst_raster) == 1: # lower tile is fully opaque
                    continue
                if not upper_raster: # check if opening was deferred
                    upper_raster = Image.open(upper_path).convert("RGBA")

                szx, szy = self.tile_size
                crop_area = (
                    crop_origin[0],
                    crop_origin[1],
                    crop_origin[0] + szx/l2,
                    crop_origin[1] + szy/l2
                    )
                ld('crop_area', level, crop_area)

                out_raster = upper_raster.crop(crop_area).resize(self.tile_size, Image.BICUBIC)
                out_raster = Image.composite(dst_raster, out_raster, dst_raster)
                del dst_raster
                out_raster.save(dst_path)

                pf('#', end='')

            self.underlay(dst_tile, upper_path, upper_raster, crop_origin, level+1)

    def __call__(self, tile):
        '''called by map() to merge a source tile into the destination tile set'''
        return self.merge_tile(tile)

    def merge_tile(self, tile):
        try:
            #~ ld(self.src_dir, self.dst_dir, tile)
            src_file = os.path.join(self.src_dir, tile)
            if not os.path.exists(src_file):
                return None, None

            src_raster = None
            transp = self.sources[tile]
            if transp is None: # transparency value not cached yet
                #~ pf('!', end='')
                src_raster = Image.open(src_file).convert("RGBA")
                transp = transparency(src_raster)
            if  transp == 0 : # fully transparent
                #~ pf('-', end='')
                os.remove(src_file)
                return None, None

            dst_file = os.path.join(self.dst_dir, tile)
            dpath = os.path.dirname(dst_file)
            if not os.path.exists(dpath):
                try: # thread race safety
                    os.makedirs(dpath)
                except os.error:
                    pass
            if transp == 1 or not os.path.exists(dst_file):
                # fully opaque or no destination tile exists yet
                #~ pf('>', end='')
                link_or_copy(src_file, dst_file)
            else: # partially transparent, combine with destination (exists! see previous check)
                pf('+', end='')
                if not src_raster:
                    src_raster = Image.open(src_file).convert("RGBA")
                try:
                    dst_raster = Image.composite(src_raster, Image.open(dst_file).convert("RGBA"), src_raster)
                except IOError, exception:
                    error('merge_tile', exception.message, dst_file)

                dst_raster.save(dst_file)

            if options.underlay and transp != 0:
                self.underlay(tile, src_file, src_raster)

        except KeyboardInterrupt: # http://jessenoller.com/2009/01/08/multiprocessingpool-and-keyboardinterrupt/
            print 'got KeyboardInterrupt'
            raise KeyboardInterruptError()
        return (tile, transp) # send back transparency values for caching

    def merge_dirs(self):

        transparency = parallel_map(self, self.sources.keys())
        self.sources = None
        self.sources = dict(transparency)
        if None in self.sources:
            del self.sources[None]

        self.merge_metadata()

        # save transparency data
        write_transparency(self.src_dir, self.sources)
        pf('')

# MergeSet end

if __name__ == '__main__':
    parser = optparse.OptionParser(
        usage="usage: %prog [--cut] [--dest-dir=DST_DIR] <tile_dirs>... <target_dir>",
        version=version,
        description="")
    parser.add_option("-r", "--remove-dest", action="store_true",
        help='delete destination directory before merging')
    parser.add_option("-l", "--src-list", default=None,
        help='read a list of source directories from a file; if no destination is provided then name destination after the list file without a suffix')
    parser.add_option("-s", "--strip-src-ext", action="store_true",
        help='strip extension suffix from a source parameter')
    parser.add_option("-x", "--add-src-ext", default=None,
        help='add extension suffix to a source parameter')
    parser.add_option('-u', "--underlay", type='int', default=0,
        help="underlay partially filled tiles with a zoomed-in raster from a higher level")
    parser.add_option("-q", "--quiet", action="store_true")
    parser.add_option("-d", "--debug", action="store_true")
    parser.add_option("--nothreads", action="store_true",
        help="do not use multiprocessing")

    (options, args) = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if options.debug else
        (logging.ERROR if options.quiet else logging.INFO))

    ld(options)

    args = [i.decode(locale.getpreferredencoding(), 'ignore') for i in args]
    if options.src_list:
        with open(options.src_list, 'r') as f:
            src_dirs = [i.rstrip('\n\r').decode(locale.getpreferredencoding(), 'ignore') for i in f]
            try:
                dst_dir = args[-1]
            except:
                dst_dir = os.path.splitext(options.src_list)[0].decode(locale.getpreferredencoding(), 'ignore')
    else:
        try:
            src_dirs = args[0:-1]
            dst_dir = args[-1]
        except:
            raise Exception("No source(s) or/and destination specified")

    if options.nothreads or options.debug:
        set_nothreads()

    if options.remove_dest:
        shutil.rmtree(dst_dir, ignore_errors=True)

    if not os.path.exists(dst_dir):
        try:
            os.makedirs(dst_dir)
        except os.error: pass

    for src in src_dirs:
        if src.startswith("#") or src.strip() == '': # ignore sources with names starting with "#"
            continue
        MergeSet(src, dst_dir).merge_dirs()

