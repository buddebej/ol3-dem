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

class SASPlanet(TileDir): # http://sasgis.ru/forum/viewtopic.php?f=2&t=24
    'SASPlanet cache'
#############################
    format, ext, input, output = 'sasplanet', '.sasplanet', True, True
    dir_pattern = 'z[0-9]*/*/x[0-9]*/*/y[0-9]*.*'

    def path2coord(self, tile_path):
        z, dx, x, dy, y = path2list(tile_path)[-6:-1]
        z, x, y = map(int, (z[1:], x[1:], y[1:]))
        return (z-1, x, y)

    def coord2path(self, z, x, y):
        return 'z%d/%d/x%d/%d/y%d' % (z+1, x//1024, x, y//1024, y)

tileset_profiles.append(SASPlanet)

#############################

class SASBerkeley(TileDir):
    'SASPlanet Berkeley DB'
#############################
    format, ext, input, output = 'sdb', '.sdb', True, False
    dir_pattern = 'z[0-9]*/[0-9]*/[0-9]*/*.sdb'

    def __init__(self, root, options=None):
        super(SASBerkeley, self).__init__(root, options)

        from bsddb3 import db
        self.db = db

        #  0  4b 4s // magic
        #  4  4b I, // crc32
        #  8  4b I, // tile size
        #  12 8b d, // tile date
        #  20 2c string // tile version
        #     2c string // tile content-type
        #     BLOB // tile data
        self.header = struct.Struct('<3sBIId')
        self.key = struct.Struct('>Q') # 64 bit, swap bytes

    def __iter__(self):
        log('__iter__', os.path.join(self.root, self.dir_pattern), glob.iglob(os.path.join(self.root, self.dir_pattern)))
        for db_file in glob.iglob(os.path.join(self.root, self.dir_pattern)):
            log('db_file', db_file)
            for coord, tile, path in self.iter_tiles(db_file):
                #~ log('db tile', coord, tile[:20], path)
                yield PixBufTile(coord, tile, path)

    def iter_tiles(self, db_path):
        zoom = self.get_zoom(db_path) # also checks data in range
        if not zoom:
            return
        d = self.db.DB()
        d.open(db_path, '', self.db.DB_BTREE, self.db.DB_RDONLY)
        c = d.cursor()
        item = c.first(dlen=0, doff=0)
        while item:
            key = item[0]
            coord = self.get_coord(zoom, key)
            if self.in_range(coord):
                data = c.current()[1]
                tile = self.get_image(data)
                if tile:
                    log('tile', coord)
                    yield coord, tile, [db_path, key]
            item = c.next(dlen=0, doff=0)
        d.close()

    def get_zoom(self, db_path): # u_TileFileNameBerkeleyDB
        z, x10, y10, xy8 = path2list(db_path)[-5:-1]
        zoom = int(z[1:]) - 1
        x_min, y_min = [int(d) << 8 for d in xy8.split('.')]
        x_max, y_max = [d | 0xFF for d in x_min, y_min]

        if not self.in_range((zoom, x_min, y_min), (zoom, x_max, y_max)):
            return None
            pass
        log('get_zoom', zoom, x_min, x_max, y_min, y_max,db_path)
        return zoom

    def get_coord(self, zoom, key): # u_BerkeleyDBKey.pas TBerkeleyDBKey.PointToKey
        if key == '\xff\xff\xff\xff\xff\xff\xff\xff':
            return None
        kxy = self.key.unpack(key)[0] # swaps bytes
        xy = [0, 0]
        for bit_n in range(64): # bits for x and y are interleaved in the key
            x0y1 = bit_n % 2 # x, y
            xy[x0y1] += (kxy >> bit_n & 1) << (bit_n - x0y1) / 2

        coord = [zoom] + xy
        #~ log('get_coord', coord, zoom, key, hex(kxy), hex(xy[0]), hex(xy[1]))
        return coord

    def get_image(self, data): # u_BerkeleyDBValue

        magic, magic_v, crc32, tile_size, tile_date = self.header.unpack_from(data)
        if magic != 'TLD' or magic_v != 3:
            log('get_image', 'wrong magic', magic, magic_v)
            return None

        strings = []
        i = start = self.header.size
        while True:
            if data[i] == '\x00':
                strings.append(data[start: i: 2])
                start = i + 2
                if len(strings) == 2:
                    break
            i += 2

        tile_version, content_type = strings
        tile_data = data[start: start + tile_size]

        #~ log('get_image', self.header.size, magic, magic_v, tile_version, content_type, tile_size, tile_data[:20])#, data[4:60:2])
        return tile_data

tileset_profiles.append(SASBerkeley)

# SASBerkeley
