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

class MapperSQLite(TileSet):
    'maemo-mapper SQLite cache'
#############################
    format, ext, input, output = 'mapper', '.db', True, True
    max_zoom = 20

    def __init__(self, root, options=None):
        super(MapperSQLite, self).__init__(root, options)

        import sqlite3

        self.db = sqlite3.connect(self.root)
        self.dbc = self.db.cursor()
        if self.options.isDest:
            try:
                self.dbc.execute (
                    'CREATE TABLE maps ('
                        'zoom INTEGER, '
                        'tilex INTEGER, '
                        'tiley INTEGER, '
                        'pixbuf BLOB, '
                        'PRIMARY KEY (zoom, tilex, tiley));'
                    )
            except:
                pass

    def finalize_tileset(self):
        self.db.commit()
        self.db.close()

    def __iter__(self):
        self.dbc.execute('SELECT * FROM maps')
        for z, x, y, pixbuf in self.dbc:
            coord = self.max_zoom+1-z, x, y
            if not self.in_range(coord):
                continue
            yield PixBufTile(coord, str(pixbuf), (z, x, y))

    def store_tile(self, tile):
        z, x, y = tile.coord()
        # convert to maemo-mapper coords
        z = self.max_zoom+1-z
        log('%s -> SQLite %d, %d, %d' % (tile.path, z, x, y))
        self.dbc.execute('INSERT OR REPLACE INTO maps (zoom, tilex, tiley, pixbuf) VALUES (?, ?, ?, ?);',
            (z, x, y, buffer(tile.data())))

tileset_profiles.append(MapperSQLite)

# MapperSQLite

#############################

class MapperGDBM(TileSet): # due to GDBM weirdness on ARM this only works if run on the tablet itself
    'maemo-mapper GDBM cache (works only on Nokia tablet)'
#############################
    format, ext, input, output = 'gdbm', '.gdbm', True, True
    max_zoom = 20

    def __init__(self, root, options=None):

        super(MapperGDBM, self).__init__(root, options)
        #print self.root

        import platform
        assert platform.machine().startswith('arm'), 'This convertion works only on a Nokia tablet'

        import gdbm
        self.db = gdbm.open(self.root, 'cf' if write else 'r')

        self.key = struct.Struct('>III')

    def finalize_tileset(self):
        self.db.sync()
        self.db.close()

    def __iter__(self):
        key = self.db.firstkey()
        while key:
            z, x, y = self.key.unpack(key)
            coord = self.max_zoom+1-z, x, y
            if not self.in_range(coord):
                continue
            yield PixBufTile(coord, self.db[key], (z, x, y))
            key = self.db.nextkey(key)

    def store_tile(self, tile):
        z, x, y = tile.coord()
        # convert to maemo-mapper coords
        z = self.max_zoom+1-z
        log('%s -> GDBM %d, %d, %d' % (tile.path, z, x, y))
        key = self.key.pack(z, x, y)
        self.db[key] = tile.data()

tileset_profiles.append(MapperGDBM)
# MapperGDBM
