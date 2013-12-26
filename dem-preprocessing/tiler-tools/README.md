A few scripts for creating and handling a tile sets from digital raster maps. The scripts are based on GDAL tools.

Download from http://code.google.com/p/tilers-tools/downloads/list
----
 * `gdal_tiler.py` -- creates a tile set tree directory from a GDAL dataset (including BSB/KAP, GEO/NOS, OZI map, KML image overlays);

 * `tiles_merge.py` -- sequentially merges a few tile sets in a single one to cover the area required;
 * `tiles_convert.py` -- converts tile sets between a different tile structures: TMS, Google map-compatible (maemo mappero), SASPlanet cache, maemo-mapper sqlite3 and gmdb databases;

 * `ozf_decoder.py` -- converts .ozf2 or .ozfx3 file into .tiff (tiled format)
 * `hdr_pcx_merge.py` -- converts hdr-pcx chart image into .png

<wiki:comment>
 * `tiles-opt.py` -- optimizes png tiles into a palleted form using pngnq tool;
 * `tiles-scale.py`

 * `bsb2gdal.py` -- creates geo-referenced GDAL .vrt file from BSB chart;
 * `ozi2gdal.py` -- creates geo-referenced GDAL .vrt file from Ozi map;
 * gdal2kmz.py
 * kml2gdal.py
 * kml2gpx.sh
 * mk-merge-order.sh
 * vrt-bsb-cut.sh
</wiki:comment>
