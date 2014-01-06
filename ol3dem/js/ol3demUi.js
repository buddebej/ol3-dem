    var ol3demUi = function(layer,view) {
      var dem = layer,
          view = view;
      // init map controls
      this.angleSteps = 1.0;
      this.inclination = 50.0;
      this.lightAzimuth = 225.0;
      this.lightZenith = 45.0;
      this.waterBodies = true;
      this.testing = false;
      this.colorScale = [0, 3000];
      this.maxElevation = 4900;
      this.resolution = 100;
      this.hillShade = true;

      dem.setObliqueInclination(this.inclination);
      dem.setColorScale(this.colorScale);
      dem.setLightAzimuth(this.azimuth);
      dem.setLightZenith(this.zenith)
      dem.setWaterBodies(this.waterBodies);
      dem.setTesting(this.testing);
      dem.setResolution(this.resolution/100.0);
      dem.setHillShading(this.hillShade);

      $('.t_Testing input').prop('checked', this.testing);
      $('.t_WaterBodies input').prop('checked', this.waterBodies);
      $('.t_HillShading input').prop('checked', this.waterBodies);
      $('.inclination').val(this.inclination);
      $('.lightAzimuth').val(this.lightAzimuth);
      $('.lightZenith').val(this.lightZenith);
      $('#colorScale .scaleMin').text(this.colorScale[0]);
      $('#colorScale .scaleMax').text(this.colorScale[1]);

      // FIXME: Find proper way to trigger re-rendering of map.
      renderMap = function() {
        var center = view.getCenter();
        view.setCenter([0, 0]);
        view.setCenter(center);
      },

      // round given number to closest step
      toStep = function(n, step) {
        var rest = n % step;
        if (rest <= (step / 2)) {
          return n - rest;
        } else {
          return n + step - rest;
        }
      },
      toRadians = function(a) {
        return a * Math.PI / 180.0;
      },
      toDegrees = function(a) {
        return Math.abs(a) * 180 / Math.PI;
      };

      // hide / show controlBox 
      $('.boxControl').click(function(){
        $('.controls').hide('blind', 500, function(){$('.controls').text('show controls');});
      });

      // slider to stretch hypsometric colors  
      $('.colorSlider').slider({
        min: 0,
        max: this.maxElevation,
        values: this.colorScale,
        range: true,
        slide: function(event, ui) {
          dem.setColorScale(ui.values);
          $('#colorScale .scaleMin').text(ui.values[0]);
          $('#colorScale .scaleMax').text(ui.values[1]);
          renderMap();
        }
      });

      // slider to stretch hypsometric colors  
      $('.resolutionSlider').slider({
        min: 1,
        max: 100,
        value: this.resolution,
        slide: function(event, ui) {
          dem.setResolution(ui.value/100.0);
          renderMap();
        }
      });

      // switch to toggle blue colors for waterbodies
      $('.t_WaterBodies').click(function() {
        checkbox = $('.t_WaterBodies input');
        if (dem.getWaterBodies()) {
          dem.setWaterBodies(false);
          checkbox.prop('checked', false);
        } else {
          dem.setWaterBodies(true);
          checkbox.prop('checked', true);
        }
        renderMap();
      });

      // switch to toggle hillshading
      $('.t_HillShading').click(function() {
        checkbox = $('.t_HillShading input');
        if (dem.getHillShading()) {
          dem.setHillShading(false);
          checkbox.prop('checked', false);
        } else {
          dem.setHillShading(true);
          checkbox.prop('checked', true);
        }
        renderMap();
      });

      // switch to activate testing mode
      $('.t_Testing').click(function() {
        checkbox = $('.t_Testing input');
        if (dem.getTesting()) {
          dem.setTesting(false);
          checkbox.prop('checked', false);
        } else {
          dem.setTesting(true);
          checkbox.prop('checked', true);
        }
        renderMap();
      });

      // set inclination for plan oblique relief
      $('.inclination').knob({
        'width': 110,
        'height': 70,
        'max': 90,
        'min': 1,
        'value': this.inclination,
        'step': angleSteps,
        'thickness': '.15',
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

      // set azimuth to compute direction of light
      $('.lightAzimuth').knob({
        'width': 60,
        'height': 60,
        'max': 360,
        'min': 0,
        'step': angleSteps,
        'thickness': '.3',
        'fgColor': '#888888',
        'bgColor': '#000000',
        'change': function(v) {
          dem.setLightAzimuth(toStep(v, angleSteps));
          renderMap();
        }
      });

      // set zenith to compute direction of light
      $('.lightZenith').knob({
        'width': 110,
        'height': 70,
        'max': 90,
        'min': 0,
        'step': angleSteps,
        'thickness': '.15',
        'angleOffset': -90,
        'angleArc': 90,
        'cursor': 5,
        'displayInput': false,
        'bgColor': '#000000',
        'fgColor': '#888888',
        'change': function(v) {
          dem.setLightZenith(toStep(v, angleSteps));
          renderMap();
        }
      });

      // set angle to rotate map view
      $('.rotateView').knob({
        'width': 60,
        'height': 60,
        'max': 360,
        'min': 0,
        'step': angleSteps,
        'thickness': '.3',
        'fgColor': '#888888',
        'bgColor': '#000000',
        'change': function(v) {
          view.setRotation(toRadians(toStep(v, angleSteps)));
          renderMap();
        }
      });

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