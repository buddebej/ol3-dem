###ol3-dem development documentation

ol3-source:
------

For details take a look at the source code and read code comments.
The needed modifications of the ol3 alpha src were made in:

**src/ol/renderer/webgl/webgltilelayer.glsl**

Is responsible for the rendering of the tiles to the frameBuffer used in the webglmapdefault.glsl.

Vertex shader: Computes plan oblique relief.

Fragment shader: Computes hillshading, hypsometric colors, waterbodies.

---

**src/ol/renderer/webgl/webgltilelayerrenderer.js**

Serves the tile renderer with all needed input.
* creates triangle mesh for each tile 
  fills a vertex and an element buffer 
* creates a texture for the hypsometric colors with a colorramp
* computes the directions and the scale of the plan oblique shift
* computes the direction of the light source
* passes all flags from the user interface such as testing mode, water body detection ..
* serves the image files for each tile as a texture
* creates a buffer with all rendered single tiles
* calls src/ol/renderer/webgl/webglmapdefault.glsl 
  that renders the complete map view with the tile buffer

---

**src/ol/renderer/webgl/webglmaprenderer.js**

Renders the map with a framebuffer filled with tiles as a texture.
* enabled depth test

---

**src/ol/renderer/webgl/webgllayerrenderer.js**

* added a renderbuffer to store the depth values for the tiles because the z-test is done in the webglmapdefault renderer.
* just enabling depth as an argument of the getContext in webglmaprenderer.js is *not* sufficent for depth testing inside of the tilerenderer.
(thanks to http://learningwebgl.com/blog/?p=1786)

---

**src/ol/layer/layerbase.js**

Administrates the properties of each layer.
* some custom properties and get/set methods were added
* these methods are public and can be accessed for every layer.


ol3dem demo application:
------

**ol3dem/js/ol3demInit.js**

Initializes the ol3 map, the dem layer and a view.

---

**ol3dem/js/ol3demUi.js**

Initializes the ol3dem user interface.


Put or link tiles into data/tiles.


ol3-build routine:
------

**src/ol/webgl/shader.mustache**

changed shader build template
to remove ol-default medium precision for fragment shader

