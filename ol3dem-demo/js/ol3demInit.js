  $(document).ready(function() {

    var dem = new ol.layer.Tile({
      source: new ol.source.XYZ({
         attributions: [new ol.Attribution({
           html: '<a href="http://www.eea.europa.eu/data-and-maps/data/eu-dem" target="_blank">Produced using Copernicus data and information funded by the European Union - EU-DEM layers</a>'
         })],
        url: 'data/tiles/{z}/{x}/{y}.png' 

      })
    });

    var view = new ol.View2D({
    center: ol.proj.transform([7.754974, 46.375803], 'EPSG:4326', 'EPSG:3857'), // alps
      zoom: 10,
      maxZoom: 11
    });

    // OL MAP INIT
    var map = new ol.Map({
      controls: ol.control.defaults().extend([
        new ol.control.ScaleLine(),
      ]),
      target: 'map',
      renderers: ol.RendererHints.createFromQueryData(),
      layers: [dem],
      view: view
    });

    // INIT OL3DEM USERINTERFACE
    ol3demUi(dem,view);
  });
