  $(document).ready(function() {

    var dem = new ol.layer.Tile({
      source: new ol.source.XYZ({
        url: 'data/srtm/{z}/{x}/{y}.png'
      })
    });

    var view = new ol.View2D({
    //center: ol.proj.transform([7.754974, 46.375803], 'EPSG:4326', 'EPSG:3857'), // alps
      center: ol.proj.transform([61, 43], 'EPSG:4326', 'EPSG:3857'), // ural
      zoom: 9,
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
