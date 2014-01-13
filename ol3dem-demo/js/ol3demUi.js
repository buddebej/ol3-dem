    var Ol3demUi = function(dem, view, map) {
      'use strict';

      $('.controlBox').show();

      var ui = this;
      
      // initial options for the ui
      ui.option = {
          'angleSteps' : 1.0,
          'inclination' : 50.0,
          'lightAzimuth' : 225.0,
          'lightZenith' : 45.0,
          'ambientLight' : 0,
          'waterBodies' : true,
          'testing' : false,
          'colorScale' : [0, 3000],
          'maxElevation' : 4900,
          'resolution' : 100,
          'hillShade' : true
      };
     
      dem.setObliqueInclination(ui.option.inclination);
      dem.setColorScale(ui.option.colorScale);
      dem.setLightAzimuth(ui.option.azimuth);
      dem.setLightZenith(ui.option.zenith);
      dem.setAmbientLight(ui.option.ambientLight / 100.0);
      dem.setWaterBodies(ui.option.waterBodies);
      dem.setTesting(ui.option.testing);
      dem.setResolution(ui.option.resolution / 100.0);
      dem.setHillShading(ui.option.hillShade);

      $('.t_Testing input').prop('checked', ui.option.testing);
      $('.t_WaterBodies input').prop('checked', ui.option.waterBodies);
      $('.t_HillShading input').prop('checked', ui.option.waterBodies);
      $('.inclination').val(ui.option.inclination);
      $('.lightAzimuth').val(ui.option.lightAzimuth);
      $('.lightZenith').val(ui.option.lightZenith);
      $('#colorScale .scaleMin').text(ui.option.colorScale[0]);
      $('#colorScale .scaleMax').text(ui.option.colorScale[1]);

      // FIXME: Find proper way to trigger re-rendering of map.
      var renderMap = function() {
        var center = view.getCenter();
        view.setCenter([0, 0]);
        view.setCenter(center);
      },

      // round given number to closest step
      toStep = function(n) {
        var rest = n % ui.option.angleSteps;
        if (rest <= (ui.option.angleSteps / 2)) {
          return n - rest;
        } else {
          return n + ui.option.angleSteps - rest;
        }
      },
      toRadians = function(a) {
        return a * Math.PI / 180.0;
      },
      toDegrees = function(a) {
        return Math.abs(a) * 180 / Math.PI;
      };

      // hide / show controlBox 
      $('.controlBoxHeader').click(function() {
        if ($('.controls').is(':visible')) {
          $('.controls').hide('blind', 300, function() {
            $('.controlBoxHeader .ui-icon-title').text('Show Controls');
            $('.controlBoxHeader .ui-icon').removeClass('ui-icon-minusthick');
            $('.controlBoxHeader .ui-icon').addClass('ui-icon-plusthick');
          });
        } else {
          $('.controls').show('blind', 300, function() {
            $('.controlBoxHeader .ui-icon-title').text('Hide Controls');
            $('.controlBoxHeader .ui-icon').removeClass('ui-icon-plusthick');
            $('.controlBoxHeader .ui-icon').addClass('ui-icon-minusthick');            
          });
        }
      });

      // set inclination for planoblique relief
      $('.inclination').knob({
        'width': 110,
        'height': 70,
        'max': 90,
        'min': 10,
        'value': ui.option.inclination,
        'step': ui.option.angleSteps,
        'thickness': '.15',
        'readOnly': false,
        'angleOffset': -90,
        'angleArc': 90,
        'cursor': 5,
        'displayInput': false,
        'bgColor': '#000000',
        'fgColor': '#888888',
        'change': function(v) {
          dem.setObliqueInclination(v);
          renderMap();
        }
      });

      // slider to stretch hypsometric colors  
      $('.colorSlider').slider({
        min: 0,
        max: ui.option.maxElevation,
        values: ui.option.colorScale,
        range: true,
        slide: function(event, ui) {
          dem.setColorScale(ui.values);
          $('#colorScale .scaleMin').text(ui.values[0]);
          $('#colorScale .scaleMax').text(ui.values[1]);
          renderMap();
        }
      });

      // slider to stretch resolution of dem mesh
      $('.resolutionSlider').slider({
        min: 1,
        max: 100,
        value: ui.option.resolution,
        slide: function(event, ui) {
          dem.setResolution(ui.value / 100.0);
          renderMap();
        }
      });

      // switch to toggle detection of inland waterbodies
      $('.t_WaterBodies').click(function() {
        var checkbox = $('.t_WaterBodies input');
        if (dem.getWaterBodies()) {
          dem.setWaterBodies(false);
          checkbox.prop('checked', false);
        } else {
          dem.setWaterBodies(true);
          checkbox.prop('checked', true);
        }
        renderMap();
      });

      // set azimuth to compute direction of light
      $('.lightAzimuth').knob({
        'width': 60,
        'height': 60,
        'max': 360,
        'min': 0,
        'step': ui.option.angleSteps,
        'thickness': '.3',
        'readOnly': false,
        'fgColor': '#888888',
        'bgColor': '#000000',
        'change': function(v) {
          dem.setLightAzimuth(toStep(v));
          renderMap();
        }
      });

      // set zenith to compute direction of light
      $('.lightZenith').knob({
        'width': 110,
        'height': 70,
        'max': 90,
        'min': 0,
        'step': ui.option.angleSteps,
        'thickness': '.15',
        'readOnly': false,        
        'angleOffset': -90,
        'angleArc': 90,
        'cursor': 5,
        'displayInput': false,
        'bgColor': '#000000',
        'fgColor': '#888888',
        'change': function(v) {
          dem.setLightZenith(toStep(v));
          renderMap();
        }
      });

      // slider to adjust the intensity of an ambient light
      $('.ambientLightSlider').slider({
        min: -100,
        max: 100,
        value: ui.option.ambientLight,
        slide: function(event, ui) {
          dem.setAmbientLight(ui.value / 200.0);
          renderMap();
        }
      });

      // switch to toggle shading
      $('.t_HillShading').click(function() {
        var checkbox = $('.t_HillShading input');
        if (dem.getHillShading()) {
          dem.setHillShading(false);
          checkbox.prop('checked', false);
          $('.shadingControls').hide('blind', 300);
        } else {
          dem.setHillShading(true);
          checkbox.prop('checked', true);
          $('.shadingControls').show('blind', 300);
        }
        renderMap();
      });

      // set angle to rotate map view
      $('.rotateView').knob({
        'width': 60,
        'height': 60,
        'max': 360,
        'min': 0,
        'step': ui.option.angleSteps,
        'thickness': '.3',
        'readOnly': false,        
        'fgColor': '#888888',
        'bgColor': '#000000',
        'change': function(v) {
          view.setRotation(toRadians(toStep(v)));
          renderMap();
        }
      });

      // switch to activate testing mode
      $('.t_Testing').click(function() {
        var checkbox = $('.t_Testing input');
        if (dem.getTesting()) {
          dem.setTesting(false);
          checkbox.prop('checked', false);
        } else {
          dem.setTesting(true);
          checkbox.prop('checked', true);
        }
        renderMap();
      });

      //$('.rotateView').focusout(function(){
      //   $('.rotateView').trigger('change');
      //   console.log("ocus out");
      //});

      // update control tool rotateView when rotated with alt+shift+mouse ol interaction
      // should probably better be solved with ol.MapBrowserEvent / ol.dom.input
      // TODO!
      map.on('postrender', function() {
        var angle = view.getRotation();
        if (angle < 0.0) {
          angle = 360.0 - toDegrees(view.getRotation() % (2.0 * Math.PI));
        } else {
          angle = toDegrees(view.getRotation() % (2.0 * Math.PI));
        }
        $('.rotateView').val(angle).trigger('change');
      });

//
// EXPORT FUNCTIONALITY
//
      // export functionality, causes memory problems in chrome
      // preserveDrawingBuffer has to be true for canvas (webglmaprenderer.js)
      // add following lines to ui
      /*    <div id="no-download" class="alert alert-error" style="display: none">
            Your Browser does not support the 
            <a href="http://caniuse.com/#feat=download">link download</a> attribute.
          </div>
          <a id="export-png" class="btn" download="map.png"><i class="icon-download"></i> Export PNG</a>
      */
      /*var exportPNGElement = document.getElementById('export-png');

      if ('download' in exportPNGElement) {
        exportPNGElement.addEventListener('click', function(e) {
          e.target.href = map.getRenderer().getCanvas().toDataURL('image/png');
        }, false);
      } else {
        var info = document.getElementById('no-download');
        info.style.display = '';
      }*/
};