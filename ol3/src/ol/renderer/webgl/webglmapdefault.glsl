//! NAMESPACE=ol.renderer.webgl.map.shader.Default
//! CLASS=ol.renderer.webgl.map.shader.Default


//! COMMON
varying vec2 v_texCoord;


//! VERTEX
attribute vec2 a_position;
attribute vec2 a_texCoord;

uniform mat4 u_texCoordMatrix;
uniform mat4 u_projectionMatrix;

//float alpha = radians(-180.);
//float cosinus = cos(alpha);
//float sinus = sin(alpha);
//mat4 rotatex = mat4(vec4(1.,0.,0.,0.),vec4(0.,cosinus,sinus,0.),vec4(0.,-sinus,cosinus,0.),vec4(0.,0.,0.,1.));
//mat4 rotatez = mat4(vec4(cosinus,sinus,0.,0.),vec4(-sinus,cosinus,0.,0.),vec4(0.,0.,1.,0.),vec4(0.,0.,0.,1.));
//mat4 scale = mat4(vec4(1.,0.,0.,0.),vec4(0.,1.,0.,0.),vec4(0.,0.,1.,0.),vec4(1.5,1.5,1.,1.));

void main(void) {
  gl_Position = u_projectionMatrix * vec4(a_position, 0., 1.);
  v_texCoord = (u_texCoordMatrix * (vec4(a_texCoord, 0., 1.))).st;
}


//! FRAGMENT
uniform float u_opacity;
uniform sampler2D u_texture;

void main(void) {
  vec4 texColor = texture2D(u_texture, v_texCoord);
  gl_FragColor.rgb = texColor.rgb;
  gl_FragColor.a = texColor.a * u_opacity;
}
