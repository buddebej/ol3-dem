  $(document).ready(function() {
    'use strict';

    var dem, ol3View, ol3Map, ol3demUi, osm;

    if (webgl_detect()) {

      dem = new ol.layer.Tile({
        source: new ol.source.XYZ({
          attributions: [new ol.Attribution({
            html: '<a href="http://www.eea.europa.eu/data-and-maps/data/eu-dem" target="_blank">Produced using Copernicus data and information funded by the European Union - EU-DEM layers</a>'
          })],
          url: 'data/tiles/{z}/{x}/{y}.png'
        })
      });


      ol3View = new ol.View({
        center: ol.proj.transform([7.754974, 46.375803], 'EPSG:4326', 'EPSG:3857'), // alps
        zoom: 10,
        maxZoom: 11
      });

      ol3Map = new ol.Map({
        controls: ol.control.defaults().extend([
          new ol.control.ScaleLine(),
        ]),
        target: 'map',
        renderer: 'webgl',
        layers: [dem//, 
        //new ol.layer.Tile({
          //source: new ol.source.TileDebug({
            //projection: 'EPSG:3857',
            //tileGrid: new ol.tilegrid.XYZ({
              //maxZoom: 22
            //})
          //})
        //})
        ],
        view: ol3View
      });

      // INIT OL3DEM USERINTERFACE
      ol3demUi = new Ol3demUi(dem, ol3View, ol3Map);

    } else {
      $('body').append('<div class="webglMissing"><p><span class="title">WebGL Not Supported!</span><br> WebGL is required for this application, and your Web browser does not support WebGL. Google Chrome or Firefox are recommended browsers with WebGL support. Click <a href="http://www.browserleaks.com/webgl" target="_blank">here</a> to check the WebGL specifications of your browser.</p></div>')
    }
  });
