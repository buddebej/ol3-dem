// FIXME large resolutions lead to too large framebuffers :-(
// FIXME animated shaders! check in redraw

goog.provide('ol.renderer.webgl.TileLayer');

goog.require('goog.array');
goog.require('goog.asserts');
goog.require('goog.object');
goog.require('goog.vec.Mat4');
goog.require('goog.vec.Vec4');
goog.require('goog.webgl');
goog.require('ol.TileRange');
goog.require('ol.TileState');
goog.require('ol.extent');
goog.require('ol.layer.Tile');
goog.require('ol.math');
goog.require('ol.renderer.webgl.Layer');
goog.require('ol.renderer.webgl.tilelayer.shader');
goog.require('ol.tilecoord');
goog.require('ol.webgl.Buffer');




/**
 * @constructor
 * @extends {ol.renderer.webgl.Layer}
 * @param {ol.renderer.Map} mapRenderer Map renderer.
 * @param {ol.layer.Tile} tileLayer Tile layer.
 */
ol.renderer.webgl.TileLayer = function(mapRenderer, tileLayer) {

  goog.base(this, mapRenderer, tileLayer);

  /**
   * @private
   * @type {ol.webgl.shader.Fragment}
   */
  this.fragmentShader_ =
      ol.renderer.webgl.tilelayer.shader.Fragment.getInstance();

  /**
   * @private
   * @type {ol.webgl.shader.Vertex}
   */
  this.vertexShader_ = ol.renderer.webgl.tilelayer.shader.Vertex.getInstance();

  /**
   * @private
   * @type {ol.renderer.webgl.tilelayer.shader.Locations}
   */
  this.locations_ = null;

  
  // //
  // //
  // // PLAN OBLIQUE MODIFICATIONS
  // //
  // /**
  //  * returns a mesh for each tile with 256x256 vertices
  //  * vertexBuffer contains all vertices
  //  * indexBuffer contains all triangles and reuses vertices from vertexBuffer
  //  *
  //  * @private
  //  * @return {Object.<string, ol.webgl.Buffer>} vertexBuffer, indexBuffer
  //  */
  
  ol.renderer.webgl.TileLayer.prototype.getTileMesh = function(meshResolution) {
    var vb = [],
      tb = [],
      ib = [],
      v = 0,
      vertices = meshResolution, // number of vertices per edge
      cellSize = 1 / (vertices - 1);
    // rows
    for (var x = 0; x < vertices; x += 1) {
      // columns
      for (var y = 0; y < vertices; y += 1) {
        // vertex coordinates
        vb.push(x * cellSize, y * cellSize);
        // dont draw triangles beyond tile extend!      
        if (x < vertices - 1 && y < vertices - 1) {
          // two triangles
          // v+vertices *\ * v+vertices+1
          //          v * \* v+1
          ib.push(v, v + vertices, v + 1, v + vertices, v + vertices + 1, v + 1);
        }
        v += 1;
      }
    }
    return {
      vertexBuffer: new ol.webgl.Buffer(vb),
      indexBuffer: new ol.webgl.Buffer(ib)
    };
  };

  /**
   * returns color ramp texture for hypsometric tinting of dem
   * @private
   * @return {Uint8Array} .
   */
  ol.renderer.webgl.TileLayer.prototype.getColorRampTexture = function() {
    var colors = new Array(
      66, 120, 40, 255,
      78, 129, 49, 255,
      90, 138, 58, 255,
      103, 147, 67, 255,
      115, 156, 76, 255,
      127, 165, 85, 255,
      140, 174, 94, 255,
      146, 175, 95, 255,
      152, 176, 96, 255,
      159, 178, 98, 255,
      165, 179, 99, 255,
      171, 181, 101, 255,
      178, 182, 102, 255,
      184, 184, 104, 255,
      190, 185, 105, 255,
      197, 187, 107, 255,
      203, 188, 108, 255,
      210, 190, 110, 255,
      213, 195, 122, 255,
      217, 200, 134, 255,
      221, 205, 146, 255,
      225, 211, 158, 255,
      228, 216, 170, 255,
      232, 222, 182, 255,
      236, 227, 194, 255,
      240, 233, 206, 255,
      243, 238, 218, 255,
      247, 244, 230, 255,
      251, 249, 242, 255,
      255, 255, 255, 255);
    return new Uint8Array(colors);
  };

  /**
   * @private
   * @type {Uint8Array}
   */
  this.arrayColorRamp_ = this.getColorRampTexture();


  //
  //
  // END PLAN OBLIQUE MODIFICATIONS
  //

  /**
   * @private
   * @type {ol.TileRange}
   */
  this.renderedTileRange_ = null;

  /**
   * @private
   * @type {ol.Extent}
   */
  this.renderedFramebufferExtent_ = null;

  /**
   * @private
   * @type {number}
   */
  this.renderedRevision_ = -1;

};
goog.inherits(ol.renderer.webgl.TileLayer, ol.renderer.webgl.Layer);


/**
 * @inheritDoc
 */
ol.renderer.webgl.TileLayer.prototype.disposeInternal = function() {
  var mapRenderer = this.getWebGLMapRenderer();
  var context = mapRenderer.getContext();
  context.deleteBuffer(this.tileMesh_.vertexBuffer);
  context.deleteBuffer(this.tileMesh_.indexBuffer);  
  goog.base(this, 'disposeInternal');
};


/**
 * @inheritDoc
 */
ol.renderer.webgl.TileLayer.prototype.handleWebGLContextLost = function() {
  goog.base(this, 'handleWebGLContextLost');
  this.locations_ = null;
};


/**
 * @inheritDoc
 */
ol.renderer.webgl.TileLayer.prototype.prepareFrame =
    function(frameState, layerState, context) {
  // get gl Context
  var mapRenderer = this.getWebGLMapRenderer();
  var gl = context.getGL();

  var viewState = frameState.viewState;
  var projection = viewState.projection;

  var tileLayer = this.getLayer();
  goog.asserts.assertInstanceof(tileLayer, ol.layer.Tile);
  var tileSource = tileLayer.getSource();
  var tileGrid = tileSource.getTileGridForProjection(projection);
  var z = tileGrid.getZForResolution(viewState.resolution);
  var tileResolution = tileGrid.getResolution(z);

  var tilePixelSize =
      tileSource.getTilePixelSize(z, frameState.pixelRatio, projection);

  var pixelRatio = tilePixelSize / tileGrid.getTileSize(z);

  var tilePixelResolution = tileResolution / pixelRatio;
  var tileGutter = tileSource.getGutter();

  var center = viewState.center;
  var extent;
  if (tileResolution == viewState.resolution) {
    center = this.snapCenterToPixel(center, tileResolution, frameState.size);
    extent = ol.extent.getForViewAndSize(
        center, tileResolution, viewState.rotation, frameState.size);
  } else {
    extent = frameState.extent;
  }
  var tileRange = tileGrid.getTileRangeForExtentAndResolution(
      extent, tileResolution);

  var framebufferExtent;
  if (!goog.isNull(this.renderedTileRange_) &&
      this.renderedTileRange_.equals(tileRange) &&
      this.renderedRevision_ == tileSource.getRevision()) {
    framebufferExtent = this.renderedFramebufferExtent_;
  } else {

    var tileRangeSize = tileRange.getSize();

    var maxDimension = Math.max(
        tileRangeSize[0] * tilePixelSize, tileRangeSize[1] * tilePixelSize);
    var framebufferDimension = ol.math.roundUpToPowerOfTwo(maxDimension);
    var framebufferExtentDimension = tilePixelResolution * framebufferDimension;
    var origin = tileGrid.getOrigin(z);
    var minX = origin[0] + tileRange.minX * tilePixelSize * tilePixelResolution;
    var minY = origin[1] + tileRange.minY * tilePixelSize * tilePixelResolution;
    framebufferExtent = [
      minX, minY,
      minX + framebufferExtentDimension, minY + framebufferExtentDimension
    ];

    this.bindFramebuffer(frameState, framebufferDimension);
    gl.viewport(0, 0, framebufferDimension, framebufferDimension);

    gl.clearColor(0, 0, 0, 0);
    gl.clear(goog.webgl.COLOR_BUFFER_BIT);
    gl.disable(goog.webgl.BLEND);

    gl.clearDepth(1.0);
    gl.clear(goog.webgl.DEPTH_BUFFER_BIT);

    var program = context.getProgram(this.fragmentShader_, this.vertexShader_);
    context.useProgram(program);
    if (goog.isNull(this.locations_)) {
      this.locations_ =
          new ol.renderer.webgl.tilelayer.shader.Locations(gl, program);
    }

          // UNIFORM definition: u_tileSizeM
      // estimated size of one tile in meter at the equator (dependend of current zoomlevel z)
      var tileSizeM = 40000000.0 / Math.pow(2.0, z);
      gl.uniform1f(this.locations_.u_tileSizeM, tileSizeM);

      // UNIFORM definition: u_scaleFactor
      // compute direction for oblique Shifting from current rotation and obliqueInclination Angle
      var scaleFactor = 1.0 / Math.tan(goog.math.toRadians(layerState.obliqueInclination));
      gl.uniform2f(this.locations_.u_scaleFactor, scaleFactor*Math.sin(-viewState.rotation), scaleFactor*Math.cos(-viewState.rotation));

      // UNIFORM definition: u_colorScale
      // pass colorScale factor to adapt color ramp dynamically
      gl.uniform2f(this.locations_.u_colorScale, layerState.colorScale[0],layerState.colorScale[1]);
   
      // UNIFORM definition: u_waterBodies
      // pass waterBodies to toggle rendering of inland waterBodies
      gl.uniform1f(this.locations_.u_waterBodies, layerState.waterBodies === true ? 1.0 : 0.0);

      // UNIFORM definition: u_testing
      // pass flag to activate testing mode
      gl.uniform1f(this.locations_.u_testing, layerState.testing === true ? 1.0 : 0.0);

      // UNIFORM definition: u_hillShading
      // pass flag to activate hillShading
      gl.uniform1f(this.locations_.u_hillShading, layerState.hillShading === true ? 1.0 : 0.0);

      // UNIFORM definition: u_light
      // compute light direction from Zenith and Azimuth and dependend of current map rotation
      var zenithRad = goog.math.toRadians(90.0-layerState.lightZenith),
           azimuthRad = goog.math.toRadians(layerState.lightAzimuth)+viewState.rotation,
           lightZ = Math.cos(zenithRad),
           lightX = Math.sin(zenithRad) * Math.cos(azimuthRad),
           lightY = Math.sin(zenithRad) * Math.sin(azimuthRad);
      gl.uniform3f(this.locations_.u_light, lightX, lightY, lightZ);

      // UNIFORM definition: u_ambient_light
      // pass intensity for an ambient light source
      gl.uniform1f(this.locations_.u_ambient_light, layerState.ambientLight);

      // COLOR TEXTURE
      // Create lookup texture for hyposometric tints from arrayColorRamp  
      var textureColorRamp = gl.createTexture();
      gl.activeTexture(goog.webgl.TEXTURE1);
      gl.bindTexture(goog.webgl.TEXTURE_2D, textureColorRamp);

      // read color ramp array and store it in textureColorRamp
      gl.texImage2D(goog.webgl.TEXTURE_2D, 0, goog.webgl.RGBA, 1, this.arrayColorRamp_.length / 4, 0, goog.webgl.RGBA, goog.webgl.UNSIGNED_BYTE, this.arrayColorRamp_);
      gl.texParameteri(goog.webgl.TEXTURE_2D, goog.webgl.TEXTURE_MIN_FILTER, goog.webgl.LINEAR);
      gl.texParameteri(goog.webgl.TEXTURE_2D, goog.webgl.TEXTURE_MAG_FILTER, goog.webgl.LINEAR);
      gl.texParameteri(goog.webgl.TEXTURE_2D, goog.webgl.TEXTURE_WRAP_S, goog.webgl.CLAMP_TO_EDGE);
      gl.texParameteri(goog.webgl.TEXTURE_2D, goog.webgl.TEXTURE_WRAP_T, goog.webgl.CLAMP_TO_EDGE);
      gl.uniform1i(this.locations_.u_colorRamp, 1);
      
      // TILE TEXTURE
      // pass current tile image as u_texture to shader
      gl.activeTexture(goog.webgl.TEXTURE0);
      gl.uniform1i(this.locations_.u_texture, 0);


      if(!goog.isObject(this.tileMesh_) ||  this.tileMesh_.resolution!=layerState.resolution){
        // compute mesh for current resolution
        /**
         * @private
         * @type {Object.<string, ol.webgl.Buffer>}
         */
        this.tileMesh_ = this.getTileMesh(goog.math.safeCeil(layerState.resolution*256));
        this.tileMesh_.resolution=layerState.resolution;
      }

      // TRIANGLE MESH
      // Write the vertex coordinates to the buffer object
      context.bindBuffer(goog.webgl.ARRAY_BUFFER, this.tileMesh_.vertexBuffer);
      // enables generic vertex attribute array
      gl.enableVertexAttribArray(this.locations_.a_position);
      // define an array of generic vertex attribute data
      gl.vertexAttribPointer(this.locations_.a_position, 2, goog.webgl.FLOAT, false, 0, 0);
      // Write the indices to the buffer object
      context.bindBuffer(goog.webgl.ELEMENT_ARRAY_BUFFER, this.tileMesh_.indexBuffer);

    /**
     * @type {Object.<number, Object.<string, ol.Tile>>}
     */
    var tilesToDrawByZ = {};
    tilesToDrawByZ[z] = {};

    var getTileIfLoaded = this.createGetTileIfLoadedFunction(function(tile) {
      return !goog.isNull(tile) && tile.getState() == ol.TileState.LOADED &&
          mapRenderer.isTileTextureLoaded(tile);
    }, tileSource, pixelRatio, projection);
    var findLoadedTiles = goog.bind(tileSource.findLoadedTiles, tileSource,
        tilesToDrawByZ, getTileIfLoaded);

    var useInterimTilesOnError = tileLayer.getUseInterimTilesOnError();
    var allTilesLoaded = true;
    var tmpExtent = ol.extent.createEmpty();
    var tmpTileRange = new ol.TileRange(0, 0, 0, 0);
    var childTileRange, fullyLoaded, tile, tileState, x, y, tileExtent;
    for (x = tileRange.minX; x <= tileRange.maxX; ++x) {
      for (y = tileRange.minY; y <= tileRange.maxY; ++y) {

        tile = tileSource.getTile(z, x, y, pixelRatio, projection);
        if (goog.isDef(layerState.extent)) {
          // ignore tiles outside layer extent
          tileExtent = tileGrid.getTileCoordExtent(tile.tileCoord, tmpExtent);
          if (!ol.extent.intersects(tileExtent, layerState.extent)) {
            continue;
          }
        }
        tileState = tile.getState();
        if (tileState == ol.TileState.LOADED) {
          if (mapRenderer.isTileTextureLoaded(tile)) {
            tilesToDrawByZ[z][ol.tilecoord.toString(tile.tileCoord)] = tile;
            continue;
          }
        } else if (tileState == ol.TileState.EMPTY ||
                   (tileState == ol.TileState.ERROR &&
                    !useInterimTilesOnError)) {
          continue;
        }

        allTilesLoaded = false;
        fullyLoaded = tileGrid.forEachTileCoordParentTileRange(
            tile.tileCoord, findLoadedTiles, null, tmpTileRange, tmpExtent);
        if (!fullyLoaded) {
          childTileRange = tileGrid.getTileCoordChildTileRange(
              tile.tileCoord, tmpTileRange, tmpExtent);
          if (!goog.isNull(childTileRange)) {
            findLoadedTiles(z + 1, childTileRange);
          }
        }

      }

    }

    /** @type {Array.<number>} */
    var zs = goog.array.map(goog.object.getKeys(tilesToDrawByZ), Number);
    goog.array.sort(zs);
    var u_tileOffset = goog.vec.Vec4.createFloat32();
    var i, ii, sx, sy, tileKey, tilesToDraw, tx, ty;
    for (i = 0, ii = zs.length; i < ii; ++i) {
      tilesToDraw = tilesToDrawByZ[zs[i]];
      for (tileKey in tilesToDraw) {
        //
        // call rendering for each tile, bind texture, draw mesh, call shader
        //
        tile = tilesToDraw[tileKey];
        tileExtent = tileGrid.getTileCoordExtent(tile.tileCoord, tmpExtent);
        sx = 2 * (tileExtent[2] - tileExtent[0]) /
            framebufferExtentDimension;
        sy = 2 * (tileExtent[3] - tileExtent[1]) /
            framebufferExtentDimension;
        tx = 2 * (tileExtent[0] - framebufferExtent[0]) /
            framebufferExtentDimension - 1;
        ty = 2 * (tileExtent[1] - framebufferExtent[1]) /
            framebufferExtentDimension - 1;
        goog.vec.Vec4.setFromValues(u_tileOffset, sx, sy, tx, ty);
        gl.uniform4fv(this.locations_.u_tileOffset, u_tileOffset);

        mapRenderer.bindTileTexture(tile, tilePixelSize,
            tileGutter * pixelRatio, goog.webgl.NEAREST, goog.webgl.NEAREST);

        // draw triangle mesh. getCount is number of triangles * 2, method added in webgl.buffer
        gl.drawElements(goog.webgl.TRIANGLES, this.tileMesh_.indexBuffer.getCount(), goog.webgl.UNSIGNED_INT, 0);

      }
    }

    if (allTilesLoaded) {
      this.renderedTileRange_ = tileRange;
      this.renderedFramebufferExtent_ = framebufferExtent;
      this.renderedRevision_ = tileSource.getRevision();
    } else {
      this.renderedTileRange_ = null;
      this.renderedFramebufferExtent_ = null;
      this.renderedRevision_ = -1;
      frameState.animate = true;
    }

  }

  this.updateUsedTiles(frameState.usedTiles, tileSource, z, tileRange);
  var tileTextureQueue = mapRenderer.getTileTextureQueue();
  this.manageTilePyramid(
      frameState, tileSource, tileGrid, pixelRatio, projection, extent, z,
      tileLayer.getPreload(),
      /**
       * @param {ol.Tile} tile Tile.
       */
      function(tile) {
        if (tile.getState() == ol.TileState.LOADED &&
            !mapRenderer.isTileTextureLoaded(tile) &&
            !tileTextureQueue.isKeyQueued(tile.getKey())) {
          tileTextureQueue.enqueue([
            tile,
            tileGrid.getTileCoordCenter(tile.tileCoord),
            tileGrid.getResolution(tile.tileCoord[0]),
            tilePixelSize, tileGutter * pixelRatio
          ]);
        }
      }, this);
  this.scheduleExpireCache(frameState, tileSource);
  this.updateLogos(frameState, tileSource);

  var texCoordMatrix = this.texCoordMatrix;
  goog.vec.Mat4.makeIdentity(texCoordMatrix);
  goog.vec.Mat4.translate(texCoordMatrix,
      (center[0] - framebufferExtent[0]) /
          (framebufferExtent[2] - framebufferExtent[0]),
      (center[1] - framebufferExtent[1]) /
          (framebufferExtent[3] - framebufferExtent[1]),
      0);
  if (viewState.rotation !== 0) {
    goog.vec.Mat4.rotateZ(texCoordMatrix, viewState.rotation);
  }
  goog.vec.Mat4.scale(texCoordMatrix,
      frameState.size[0] * viewState.resolution /
          (framebufferExtent[2] - framebufferExtent[0]),
      frameState.size[1] * viewState.resolution /
          (framebufferExtent[3] - framebufferExtent[1]),
      1);
  goog.vec.Mat4.translate(texCoordMatrix,
      -0.5,
      -0.5,
      0);

  return true;
};
