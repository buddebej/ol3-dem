#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
# Copyright (c) 2011, Vadim Shlyakhov
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

from __future__ import with_statement
from __future__ import print_function

version = '%prog version 3.1.0'

import sys
import os
import os.path
import logging
from subprocess import *
import itertools
import re
import shutil
import locale
import csv
import htmlentitydefs
import json

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

try:
    import multiprocessing # available in python 2.6 and above

    class KeyboardInterruptError(Exception):
        pass
except:
    multiprocessing = None

def data_dir():
    return sys.path[0]

def log(*parms):
    logging.debug(' '.join(itertools.imap(repr, parms)))

ld = log

def error(*parms):
    logging.error(' '.join(itertools.imap(repr, parms)))

def ld_nothing(*parms):
    return

def pf(*parms, **kparms):
    end = kparms['end'] if 'end' in kparms else '\n'
    parms = [i.encode(locale.getpreferredencoding()) if isinstance(i, unicode) else str(i) for i in parms]
    sys.stdout.write(' '.join(parms) + end)
    sys.stdout.flush()

def pf_nothing(*parms, **kparms):
    return

def set_nothreads():
    ld('set_nothreads')
    global multiprocessing
    multiprocessing = None

def parallel_map(func, iterable):
    ld('parallel_map', multiprocessing)
    #~ return map(func, iterable)

    if multiprocessing is None or len(iterable) < 2:
        return map(func, iterable)
    else:
        # map in parallel
        mp_pool = multiprocessing.Pool() # multiprocessing pool
        res = mp_pool.map(func, iterable)
        # wait for threads to finish
        mp_pool.close()
        mp_pool.join()
    return res

def flatten(two_level_list):
    return list(itertools.chain(*two_level_list))

htmlentitydefs.name2codepoint['apos'] = ord(u"'")

def strip_html(text):
    'Removes HTML markup from a text string. http://effbot.org/zone/re-sub.htm#strip-html'

    def replace(match): # pattern replacement function
        text = match.group(0)
        if text == '<br>':
            return '\n'
        if text[0] == '<':
            return '' # ignore tags
        if text[0] == '&':
            if text[1] == '#':
                try:
                    if text[2] == 'x':
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except ValueError:
                    pass
            else:
                return unichr(htmlentitydefs.name2codepoint[text[1:-1]])
        return text # leave as is
        # fixup end

    return re.sub('(?s)<[^>]*>|&#?\w+;', replace, text)

def if_set(x, default=None):
    return x if x is not None else default

def path2list(path):
    head, ext = os.path.splitext(path)
    split = [ext]
    while head:
        head, p = os.path.split(head)
        if p == '': # head must be '/'
            p = head
            head = None
        split.append(p)
    split.reverse()
    return split

try:
    import win32pipe
except:
    win32pipe = None

def command(params, child_in=None):
    cmd_str = ' '.join(('"%s"' % i if ' ' in i else i for i in params))
    ld('>', cmd_str, child_in)
    if win32pipe:
        (stdin, stdout, stderr) = win32pipe.popen3(cmd_str, 't')
        if child_in:
            stdin.write(child_in)
        stdin.close()
        child_out = stdout.read()
        child_err = stderr.read()
        if child_err:
            logging.warning(child_err)
    else:
        process = Popen(params, stdin=PIPE, stdout=PIPE, stderr=PIPE, universal_newlines=True)
        (child_out, child_err) = process.communicate(child_in)
        if process.returncode != 0:
            error("*** External program error: %s\n%s" % (cmd_str, child_err))
            raise EnvironmentError(process.returncode, child_err)
    ld('<', child_out, child_err)
    return child_out

def dest_path(src, dest_dir, ext='', template='%s'):
    src_dir, src_file = os.path.split(src)
    base, sext = os.path.splitext(src_file)
    dest = (template % base)+ext
    if not dest_dir:
        dest_dir = src_dir
    if dest_dir:
        dest = '%s/%s' % (dest_dir, dest)
    ld(base, dest)
    return dest

def re_sub_file(fname, subs_list):
    'stream edit file using reg exp substitution list'
    new = fname+'.new'
    with open(new, 'w') as out:
        for l in open(fname, 'rU'):
            for (pattern, repl) in subs_list:
                l = re.sub(pattern, repl, string=l)
            out.write(l)
    shutil.move(new, fname)

class LooseDict(object):
    def __init__(self, init=None, **kw):
        if init is None:
            init = dict()
        elif isinstance(init, dict):
            pass
        else: #optparse.Values
            init = init.__dict__
        self.update(init)
        self.update(kw)

    def __getattr__(self, name):
        self.__dict__.get(name)

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def update(self, other_dict):
        self.__dict__.update(other_dict)

#############################
#
# GDAL utility functions
#
#############################

def load_geo_defs(csv_file):
    'load datum definitions, ellipses, projections from a file'
    defs = {
        'proj':{},
        'datum':{},
        'ellps':{},
    }
    try:
        csv.register_dialect('strip', skipinitialspace=True)
        with open(os.path.join(data_dir(),csv_file),'rb') as data_f:
            data_csv=csv.reader(data_f,'strip')
            for row in data_csv:
                row=[s.decode('utf-8') for s in row]
                try:
                    rec_type = row[0]
                    rec_id = row[1]
                    rec_data = row[2:]
                    if not rec_type in defs:
                        defs[rec_type] = {}
                    defs[rec_type][rec_id.upper()] = rec_data
                except IndexError:
                    pass
                except KeyError:
                    pass
    except IOError:
        pass
    return defs

geo_defs_override_file = 'data_override.csv'
geo_defs_override = load_geo_defs(geo_defs_override_file)

def txt2srs(proj):
    srs = osr.SpatialReference()
    proj_ovr = geo_defs_override['proj'].get(proj)
    if proj_ovr:
        proj = str(proj_ovr[0])
    if proj.startswith(("GEOGCS", "GEOCCS", "PROJCS", "LOCAL_CS")):
        srs.ImportFromWkt(proj)
    if proj.startswith('EPSG'):
        epsg = int(proj.split(':')[1])
        srs.ImportFromEPSG(epsg)
    if proj.startswith('+'):
        srs.ImportFromProj4(proj)
    return srs

def txt2wkt(proj):
    srs = txt2srs(proj)
    return srs.ExportToWkt()

def txt2proj4(proj):
    srs = txt2srs(proj)
    return srs.ExportToProj4()

def proj_cs2geog_cs(proj):
    srs = txt2srs(proj)
    srs_geo = osr.SpatialReference()
    srs_geo.CopyGeogCSFrom(srs)
    return srs_geo.ExportToProj4()

class GdalTransformer(gdal.Transformer):
    def __init__(self, src_ds=None, dst_ds=None, **options):
        for key in ('SRC_SRS', 'DST_SRS'):
            try:
                options[key] = txt2wkt(options[key]) # convert to wkt
            except: pass
        opt_lst = ['%s=%s' % (key, options[key]) for key in options]
        super(GdalTransformer, self).__init__(src_ds, dst_ds, opt_lst)

    def transform(self, points, inv=False):
        if not points:
            return []
        transformed, ok = self.TransformPoints(inv, points)
        assert ok
        return [i[:2] for i in transformed]

    def transform_point(self, point, inv=False):
        return self.transform([point], inv=inv)[0]
# GdalTransformer

def sasplanet_hlg2ogr(fname):
    with open(fname) as f:
        lines = f.readlines(4096)
        if not lines[0].startswith('[HIGHLIGHTING]'):
            return None
        coords = [[], []]
        for l in lines[2:]:
            val = float(l.split('=')[1].replace(',','.'))
            coords[1 if 'Lat' in l else 0].append(val)
        points = zip(*coords)
        ld('sasplanet_hlg2ogr', 'points', points)

    ring = ogr.Geometry(ogr.wkbLinearRing)
    for p in points:
        ring.AddPoint(*p)
    polygon = ogr.Geometry(ogr.wkbPolygon)
    polygon.AddGeometry(ring)

    ds = ogr.GetDriverByName('Memory').CreateDataSource( 'wrk' )
    assert ds is not None, 'Unable to create datasource'

    #~ src_srs = txt2srs('EPSG:4326')
    src_srs = txt2srs('+proj=latlong +a=6378137 +b=6378137 +datum=WGS84  +nadgrids=@null +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +no_defs')

    layer = ds.CreateLayer('sasplanet_hlg', srs=src_srs)

    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetGeometry(polygon)
    layer.CreateFeature(feature)

    del feature
    del polygon
    del ring

    return ds

def shape2mpointlst(datasource, dst_srs, feature_name=None):
    ds = ogr.Open(datasource.encode(locale.getpreferredencoding()))
    if not ds:
        gdal.ErrorReset()
        ds = sasplanet_hlg2ogr(datasource)
    if not ds:
        ld('shape2mpointlst: Invalid datasource %s' % datasource)
        return []

    drv_name = ds.GetDriver().GetName()
    is_kml = 'KML' in drv_name
    ld('shape2mpointlst drv', drv_name, is_kml)

    n_layers = ds.GetLayerCount()
    for j in range(n_layers):
        layer = ds.GetLayer(j)
        n_features = layer.GetFeatureCount()
        ld('shape2mpointlst layer', j, n_layers, n_features, feature_name, layer)

        for i in range(n_features):
            feature = layer.GetNextFeature()

            fc = feature.GetFieldCount()
            for l in range(fc):
                fdef = feature.GetFieldDefnRef(l)
                ld(l, fdef.GetNameRef(), feature.GetFieldAsString(l))

            if is_kml:
                i_icon = feature.GetFieldIndex('icon')
                #~ ld('shape2mpointlst i_icon', i_icon)
                if i_icon != -1:
                    icon = feature.GetFieldAsString(i_icon)
                    #~ ld('shape2mpointlst icon', icon)
                    if icon != '':
                        continue
            if feature_name is None:
                name = None
            else:
                i_name = feature.GetFieldIndex('Name')
                if i_name == -1:
                    continue
                name = feature.GetFieldAsString(i_name).decode('utf-8')

            ld('shape2mpointlst name', name == feature_name, name, feature_name)
            if name == feature_name:
                #~ feature.DumpReadable()

                geom = feature.GetGeometryRef()
                geom_name = geom.GetGeometryName()
                geom_lst = {
                    'MULTIPOLYGON':(geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())),
                    'POLYGON': (geom, ),
                    }[geom_name]

                layer_srs = layer.GetSpatialRef()
                if layer_srs:
                    layer_proj = layer_srs.ExportToProj4()
                else:
                    layer_proj = dst_srs
                srs_tr = GdalTransformer(SRC_SRS=layer_proj, DST_SRS=dst_srs)
                if layer_proj == dst_srs:
                    srs_tr.transform = lambda x:x

                multipoint_lst = []
                for geometry in geom_lst:
                    assert geometry.GetGeometryName() == 'POLYGON'
                    for ln in (geometry.GetGeometryRef(j) for j in range(geometry.GetGeometryCount())):
                        assert ln.GetGeometryName() == 'LINEARRING'
                        src_points = [ln.GetPoint(n) for n in range(ln.GetPointCount())]
                        dst_points = srs_tr.transform(src_points)
                        #~ ld(src_points)
                        multipoint_lst.append(dst_points)
                ld('mpointlst', layer_proj, dst_srs, multipoint_lst)

                feature.Destroy()
                return multipoint_lst
    return []

def shape2cutline(cutline_ds, raster_ds, feature_name=None):
    mpoly = []
    raster_proj = txt2proj4(raster_ds.GetProjection())
    if not raster_proj:
        raster_proj = txt2proj4(raster_ds.GetGCPProjection())
    ld(raster_proj, raster_ds.GetProjection(), raster_ds)

    pix_tr = GdalTransformer(raster_ds)
    for points in shape2mpointlst(cutline_ds, raster_proj, feature_name):
        p_pix = pix_tr.transform(points, inv=True)
        mpoly.append(','.join(['%r %r' % (p[0], p[1]) for p in p_pix]))
    cutline = 'MULTIPOLYGON(%s)' % ','.join(['((%s))' % poly for poly in mpoly]) if mpoly else None
    ld('cutline', cutline)
    return cutline

def elem0(doc, id):
    return doc.getElementsByTagName(id)[0]

def read_tilemap(src_dir):
    #src_dir = src_dir.decode('utf-8', 'ignore')
    src = os.path.join(src_dir, 'tilemap.json')

    try:
        with open(src, 'r') as f:
            tilemap = json.load(f)

        # convert tilesets keys to int
        tilesets = tilemap['tilesets']
        tilemap['tilesets'] = dict([ (int(key), val) for key, val in tilesets.items()])
    except ValueError: # No JSON object could be decoded
            raise Exception('Invalid tilemap file: %s' % src)
    return tilemap

def write_tilemap(dst_dir, tilemap):
    f = os.path.join(dst_dir, 'tilemap.json')
    if os.path.exists(f):
        os.remove(f)
    with open(f, 'w') as f:
         json.dump(tilemap, f, indent=2)

def link_or_copy(src, dst):
        try:
            if os.path.exists(dst):
                os.remove(dst)
            os.link(src, dst)
        except (OSError, AttributeError): # non POSIX or cross-device link?
            try:
                shutil.copy(src, dst)
            except shutil.Error, shutil_exception:
                raise shutil_exception

def copy_viewer(dest):
    for f in ['viewer-google.html', 'viewer-openlayers.html']:
        src = os.path.join(data_dir(), f)
        dst = os.path.join(dest, f)
        link_or_copy(src, dst) # hard links as FF dereferences softlinks

def read_transparency(src_dir):
    try:
        with open(os.path.join(src_dir, 'transparency.json'), 'r') as f:
            transparency = json.load(f)
    except:
        ld("transparency cache load failure")
        transparency = {}
    return transparency

def write_transparency(dst_dir, transparency):
    try:
        with open(os.path.join(dst_dir, 'transparency.json'), 'w') as f:
            json.dump(transparency, f, indent=0)
    except:
        logging.warning("transparency cache save failure")

type_map = (
    ('image/png', '.png', '\x89PNG\x0D\x0A\x1A\x0A'),
    ('image/jpeg', '.jpg', '\xFF\xD8\xFF\xE0'),
    ('image/jpeg', '.jpeg', '\xFF\xD8\xFF\xE0'),
    ('image/gif', '.gif', 'GIF89a'),
    ('image/gif', '.gif', 'GIF87a'),
    ('image/webp', '.webp', 'RIFF'),
    ('image/tif', '.tif', 'TIFF'),
    )

def type_ext_from_buffer(buf):
    for mime_type, ext, magic in type_map:
        if buf.startswith(magic):
            if magic == 'RIFF' and buf[8:12] != 'WEBP':
                contnue
            return mime_type, ext
    error('Cannot determing image type in a buffer:', buf[:20])
    raise KeyError('Cannot determing image type in a buffer')

def ext_from_buffer(buf):
    return type_ext_from_buffer(buf)[1]

def mime_from_ext(ext_to_find):
    for mime_type, ext, magic in type_map:
        if ext_to_find == ext:
            return mime_type
    else:
        error('Cannot determing image MIME type')
        raise KeyError('Cannot determing image MIME type')

def ext_from_mime(mime_to_find):
    for mime_type, ext, magic in type_map:
        if mime_to_find == mime_type:
            return ext
    else:
        error('Cannot determing image MIME type')
        raise KeyError('Cannot determing image MIME type')

def ext_from_file(path):
    with file(path, "r") as f:
        buf = f.read(512)
        return ext_from_buffer(buf)
