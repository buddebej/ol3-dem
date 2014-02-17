ol3-dem
=========

This is an experimental fork of OpenLayers 3 to render digital elevation models using the integrated webgl functionality.
The application is not running stable yet and serves only testing purposes. 

For comments or contribution please contact [Cartography and Geovisualization Group, Oregon State University](http://cartography.oregonstate.edu/).

Features at current stage:

 * Plan Oblique Relief
 * Hypsometric Tinting
 * Waterbody Detection
 * Hillshading

The input data has to be encoded and converted into a set of tiles before it can be read by ol3. Regular raster dems such as GeoTiff can be used.
For data preprocessing see the scripts in dem-preprocessing. For the actual tile production we used a modified version of [tiler-tools](https://code.google.com/p/tilers-tools/).

A [working demo](http://ol3dem.boeppe.eu/) is currently available for the eu-dem (Digital Elevation Model of the European Environment Agency).

Click here for working demo [http://ol3dem.boeppe.eu/](http://ol3dem.boeppe.eu/)
Works best in chrome and make sure your browser allows webgl.

![Screenshots](https://raw.github.com/buddebej/ol3-dem/master/screenshots/ol3-dem-screenshot.png) 
