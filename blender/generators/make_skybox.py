import bpy, math, sys
# Procedural golden-hour skybox: physical sky + layered procedural clouds, rendered as a 2:1 equirectangular panorama.
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
W = int(argv[0]) if argv else 2048
OUT = argv[1] if len(argv) > 1 else "/home/claude/skybox.png"

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
world = bpy.data.worlds.new("Sky"); sc.world = world; world.use_nodes = True
nt = world.node_tree; N = nt.nodes; L = nt.links
N.clear()
out = N.new("ShaderNodeOutputWorld")
bg = N.new("ShaderNodeBackground")
sky = N.new("ShaderNodeTexSky"); sky.sky_type = 'NISHITA'
sky.sun_elevation = math.radians(4.5); sky.sun_rotation = math.radians(215)
sky.air_density = 1.0; sky.dust_density = 4.0; sky.ozone_density = 1.0; sky.sun_size = math.radians(1.2)
sky.sun_intensity = 0.6

# cloud coverage: noise on the view direction projected onto a flat cloud deck
coord = N.new("ShaderNodeTexCoord")
sep = N.new("ShaderNodeSeparateXYZ"); L.new(coord.outputs["Generated"], sep.inputs[0])
# project direction onto plane z = 1  -> (x/z, y/z)
dz = N.new("ShaderNodeMath"); dz.operation = 'MAXIMUM'; dz.inputs[1].default_value = 0.02; L.new(sep.outputs["Z"], dz.inputs[0])
px = N.new("ShaderNodeMath"); px.operation = 'DIVIDE'; L.new(sep.outputs["X"], px.inputs[0]); L.new(dz.outputs[0], px.inputs[1])
py = N.new("ShaderNodeMath"); py.operation = 'DIVIDE'; L.new(sep.outputs["Y"], py.inputs[0]); L.new(dz.outputs[0], py.inputs[1])
comb = N.new("ShaderNodeCombineXYZ"); L.new(px.outputs[0], comb.inputs[0]); L.new(py.outputs[0], comb.inputs[1])
noise = N.new("ShaderNodeTexNoise"); noise.inputs["Scale"].default_value = 1.6; noise.inputs["Detail"].default_value = 12
noise.inputs["Roughness"].default_value = 0.62; noise.inputs["Distortion"].default_value = 0.25
L.new(comb.outputs[0], noise.inputs["Vector"])
cov = N.new("ShaderNodeMapRange"); cov.inputs["From Min"].default_value = 0.52; cov.inputs["From Max"].default_value = 0.72
L.new(noise.outputs["Fac"], cov.inputs["Value"])
# fade clouds toward the horizon and away at zenith edge
hz = N.new("ShaderNodeMapRange"); hz.inputs["From Min"].default_value = 0.05; hz.inputs["From Max"].default_value = 0.3
L.new(sep.outputs["Z"], hz.inputs["Value"])
mask = N.new("ShaderNodeMath"); mask.operation = 'MULTIPLY'; L.new(cov.outputs[0], mask.inputs[0]); L.new(hz.outputs[0], mask.inputs[1])
dens = N.new("ShaderNodeMath"); dens.operation = 'MULTIPLY'; dens.inputs[1].default_value = 0.85; L.new(mask.outputs[0], dens.inputs[0])
# cloud colour: warm lit tops, cool shaded body, varies with a second noise
n2 = N.new("ShaderNodeTexNoise"); n2.inputs["Scale"].default_value = 3.5; n2.inputs["Detail"].default_value = 6
L.new(comb.outputs[0], n2.inputs["Vector"])
cr = N.new("ShaderNodeValToRGB")
cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[0].color = (0.40, 0.31, 0.36, 1)
cr.color_ramp.elements[1].position = 0.75; cr.color_ramp.elements[1].color = (1.0, 0.60, 0.36, 1)
L.new(n2.outputs["Fac"], cr.inputs[0])
cbright = N.new("ShaderNodeMix"); cbright.data_type = 'RGBA'; cbright.blend_type = 'MULTIPLY'
cbright.inputs["Factor"].default_value = 1.0; cbright.inputs[7].default_value = (6.0, 6.0, 6.0, 1)
L.new(cr.outputs["Color"], cbright.inputs[6])
mix = N.new("ShaderNodeMix"); mix.data_type = 'RGBA'
L.new(dens.outputs[0], mix.inputs["Factor"]); L.new(sky.outputs["Color"], mix.inputs[6]); L.new(cbright.outputs[2], mix.inputs[7])
# feed the sky a direction lifted just above the horizon, removing Nishita's dark ground band
zc = N.new("ShaderNodeMath"); zc.operation = 'MAXIMUM'; zc.inputs[1].default_value = 0.10; L.new(sep.outputs["Z"], zc.inputs[0])
cv = N.new("ShaderNodeCombineXYZ"); L.new(sep.outputs["X"], cv.inputs[0]); L.new(sep.outputs["Y"], cv.inputs[1]); L.new(zc.outputs[0], cv.inputs[2])
L.new(cv.outputs[0], sky.inputs[0])
# below the horizon: warm sea haze instead of black, so the panorama works as a full skybox
below = N.new("ShaderNodeMapRange"); below.inputs["From Min"].default_value = 0.0; below.inputs["From Max"].default_value = -0.35
L.new(sep.outputs["Z"], below.inputs["Value"])
haze = N.new("ShaderNodeMix"); haze.data_type = 'RGBA'
L.new(below.outputs[0], haze.inputs["Factor"]); L.new(sky.outputs['Color'], haze.inputs[6]); haze.inputs[7].default_value = (0.55, 0.45, 0.36, 1)
hz2 = N.new("ShaderNodeMath"); hz2.operation = 'GREATER_THAN'; hz2.inputs[1].default_value = 0.0; L.new(sep.outputs["Z"], hz2.inputs[0])
fin = N.new("ShaderNodeMix"); fin.data_type = 'RGBA'
L.new(hz2.outputs[0], fin.inputs["Factor"]); L.new(haze.outputs[2], fin.inputs[6]); L.new(mix.outputs[2], fin.inputs[7])
L.new(fin.outputs[2], bg.inputs["Color"]); bg.inputs["Strength"].default_value = 0.22
L.new(bg.outputs[0], out.inputs["Surface"])

cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = 'PANO'
sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
cam.data.panorama_type = 'EQUIRECTANGULAR'
cam.rotation_euler = (math.radians(90), 0, 0)
sc.cycles.samples = 4; sc.cycles.use_denoising = False
sc.render.resolution_x, sc.render.resolution_y = W, W // 2
sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Base Contrast'
sc.render.image_settings.file_format = 'PNG'
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
img = bpy.data.images['Render Result']
sc.render.image_settings.file_format = 'HDR'; sc.view_settings.view_transform = 'Standard'
img.save_render(OUT.replace('.png', '.hdr'), scene=sc)
