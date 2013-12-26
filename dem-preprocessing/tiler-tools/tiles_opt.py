#!/usr/bin/env python

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
import os
import stat
import shutil
import logging
import optparse
from PIL import Image
#~ from PIL import WebPImagePlugin

from tiler_functions import *

class KeyboardInterruptError(Exception): pass

converters = []

#############################

class Converter (object):

#############################
    prog_name = None
    dst_ext = None
    src_formats = ('.png',)

    def __init__(self, src_dir, options):
        if self.prog_name:
            try: # check if converter programme is available
                prog_path = command(['which', self.prog_name]).strip()
            except:
                raise Exception('Can not find %s executable' % self.prog_name)

        self.options = options
        self.src_dir = src_dir
        self.dst_dir = src_dir + self.dst_ext
        pf('%s -> %s ' % (self.src_dir, self.dst_dir), end='')

        if options.remove_dest:
            shutil.rmtree(self.dst_dir, ignore_errors=True)
        elif os.path.exists(self.dst_dir):
            raise Exception('Destination already exists: %s' % self.dst_dir)

    def convert(self):
        # find all source files
        try:
            cwd = os.getcwd()
            os.chdir(self.src_dir)
            src_lst = flatten([os.path.join(path, name) for name in files]
                        for path, dirs, files in os.walk('.'))
        finally:
            os.chdir(cwd)

        parallel_map(self, src_lst)

        tilemap = os.path.join(self.dst_dir, 'tilemap.json')
        if os.path.exists(tilemap):
            re_sub_file(tilemap, [
                ('"mime":[^,]*"', '"mime": "%s"' % mime_from_ext(self.dst_ext)),
                ('"ext":[^,]*"', '"ext": "%s"' % self.dst_ext[1:]),
                ])
        pf('')

    def __call__(self, f):
        'process file'
        try:
            src = os.path.join(self.src_dir, f)
            dst = os.path.splitext(os.path.join(self.dst_dir, f))[0] + self.dst_ext

            dpath = os.path.split(dst)[0]
            if not os.path.exists(dpath):
                os.makedirs(dpath)

            src_ext = os.path.splitext(f)[1].lower()
            if src_ext in self.src_formats:
                self.convert_tile(src, dst, dpath)
            else:
                shutil.copy(src, dpath)

            self.counter()
        except KeyboardInterrupt: # http://jessenoller.com/2009/01/08/multiprocessingpool-and-keyboardinterrupt/
            pf('got KeyboardInterrupt')
            raise KeyboardInterruptError()

    def convert_tile(self, src, dst, dpath):
        pass

    tick_rate = 10
    tick_count = 0

    def counter(self):
        self.tick_count += 1
        #~ pf(self.tick_count)
        if self.tick_count % self.tick_rate == 0:
            pf('.', end='')
            return True
        else:
            return False

    @staticmethod
    def get_class(profile, write=False):
        for cls in converters:
            if profile == cls.profile_name:
                return cls
        else:
            raise Exception('Invalid format: %s' % profile)

    @staticmethod
    def list_converters():
        for cls in converters:
            print cls.profile_name

#############################

class PngConverter (Converter):

#############################
    profile_name = 'pngnq'
    prog_name = 'pngnq'
    dst_ext = '.png'

    def convert_tile(self, src, dst, dpath):
        'optimize png using pngnq utility'
        command(['pngnq', '-n', self.options.colors, '-e', self.dst_ext, '-d', dpath, src])

converters.append(PngConverter)

#############################

class WebpConverter (Converter):
    'convert to webp'
#############################
    profile_name = 'webp'
    dst_ext = '.webp'
    src_formats = ('.png','.jpg','.jpeg','.gif')

    def convert_tile(self, src, dst, dpath):
        command(['cwebp', src, '-o', dst, '-q', str(self.options.quality)])

converters.append(WebpConverter)


#~ #############################
#~
#~ class WebpPilConverter (Converter):
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
#~ converters.append(WebpPilConverter)


#############################

class JpegConverter (Converter):
    'convert to jpeg'
#############################
    profile_name = 'jpeg'
    dst_ext = '.jpg'

    def convert_tile(self, src, dst, dpath):
        img = Image.open(src)
        img.save(dst, optimize=True, quality=self.options.quality)

converters.append(JpegConverter)

#############################

def main(argv):

#############################

    parser = optparse.OptionParser(
        usage="usage: %prog [options] arg",
        version=version,
        )
    parser.add_option('-p', '--profile', default='webp',
        help='output tiles profile (default: webp)')
    parser.add_option('-l', '--profiles', action='store_true', dest='list_profiles',
        help='list available profiles')
    parser.add_option("-n", "--colors", dest="colors", default='256',
        help='Specifies  the  number  of colors for pngnq profile (default: 256)')
    parser.add_option("-q", "--quality", dest="quality", type="int", default=75,
        help='JPEG/WEBP quality (default: 75)')
    parser.add_option("-r", "--remove-dest", action="store_true",
        help='delete destination directory if any')
    parser.add_option("--quiet", action="store_true")
    parser.add_option("-d", "--debug", action="store_true")
    parser.add_option("--nothreads", action="store_true",
        help="do not use multiprocessing")

    (options, args) = parser.parse_args(argv[1:])

    logging.basicConfig(level=logging.DEBUG if options.debug else
        (logging.ERROR if options.quiet else logging.INFO))
    log(options.__dict__)

    if options.list_profiles:
        Converter.list_profiles()
        sys.exit(0)

    if options.nothreads or options.debug:
        set_nothreads()

    if not args:
        parser.error('No input directory(s) specified')

    for src_dir in args:
        Converter.get_class(options.profile)(src_dir, options).convert()


if __name__=='__main__':

    main(sys.argv)
