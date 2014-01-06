  $(document).ready(function() {

    var dem = new ol.layer.Tile({
      source: new ol.source.XYZ({
        url: 'http://128.193.213.150/tiles/eudem/{z}/{x}/{y}.png' 
      })
    });

    // help openlayers to read TMS tile scheme, http://wiki.osgeo.org/wiki/Tile_Map_Service_Specification
    // http://alastaira.wordpress.com/2011/07/06/converting-tms-tile-coordinates-to-googlebingosm-tile-coordinates/
    var getTMSTilePath = function(tile) {
      var y = (1 << tile.z) - tile.y - 1;
      //return 'http://128.193.213.150/eudem/processing/eudem-v3/eu-dem_tif_neighbourhood_png/' + tile.z + "/" + tile.x + "/" + y + ".png";
      return 'data/tiles/eudem/' + tile.z + "/" + tile.x + "/" + y + ".png";
    };

    var tmsdem = new ol.layer.Tile({
      source: new ol.source.XYZ({
        attributions: [new ol.Attribution({
          html: '<a href="http://www.eea.europa.eu/data-and-maps/data/eu-dem"> eu-dem / plan oblique ol3</a>'
        })],
        tileUrlFunction: getTMSTilePath
      })
    });

    var view = new ol.View2D({
    center: ol.proj.transform([7.754974, 46.375803], 'EPSG:4326', 'EPSG:3857'), // alps
    //  center: ol.proj.transform([61, 43], 'EPSG:4326', 'EPSG:3857'), // ural
      zoom: 11,
      maxZoom: 11
    });

    // OL MAP INIT
    var map = new ol.Map({
      controls: ol.control.defaults().extend([
        new ol.control.ScaleLine(),
      ]),
      target: 'map',
      renderers: ol.RendererHints.createFromQueryData(),
      layers: [tmsdem],
      view: view
    });

    // INIT OL3DEM USERINTERFACE
    ol3demUi(tmsdem,view);
  });
