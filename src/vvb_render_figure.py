# Copyright 2026 James Scott Graber
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# VVB annotated figure generator (Blender 4.x)
# Shows channels, equal-weight seam, Kiss point, and a hop arc.
import bpy, math, mathutils, os

# --------- parameters (feel free to tweak) ----------
R0    = 3.0
beta  = 0.18
k     = 0.35
H     = 4.0                # column height
chs   = [-4.0, 0.0, 4.0]   # channel centers along X
pair  = (0, 1)             # which neighbor pair to annotate: indices in 'chs' (0↔1 or 1↔2)
samples = 240              # curve sampling resolution
tube   = 0.025             # curve thickness
# ----------------------------------------------------

# robust outdir selection
def pick_outdir():
    # 1) try next to .blend
    base = bpy.path.abspath("//")
    if base and base not in {"//", ""}:
        out = os.path.join(base, "figs")
        try:
            os.makedirs(out, exist_ok=True)
            with open(os.path.join(out, ".write_test"), "w") as f: f.write("ok")
            os.remove(os.path.join(out, ".write_test"))
            return out
        except Exception:
            pass
    # 2) user Documents
    docs = os.path.join(os.path.expanduser("~"), "Documents", "vvb_figs")
    try:
        os.makedirs(docs, exist_ok=True)
        return docs
    except Exception:
        pass
    # 3) TEMP
    tmp = os.path.join(os.environ.get("TEMP", ""), "vvb_figs")
    os.makedirs(tmp, exist_ok=True)
    return tmp

OUTDIR = pick_outdir()

# cleanup previous collection if present
COLL_NAME = "VVB_Figure"
if COLL_NAME in bpy.data.collections:
    coll = bpy.data.collections[COLL_NAME]
    for obj in list(coll.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(coll)

coll = bpy.data.collections.new(COLL_NAME)
bpy.context.scene.collection.children.link(coll)

def make_emission_material(name, color=(1,1,1,1), strength=2.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in nt.nodes:
        nt.nodes.remove(n)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs[0].default_value = color
    e.inputs[1].default_value = strength
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(e.outputs[0], out.inputs[0])
    return mat

mat_chA = make_emission_material("mat_chA", (0.2,0.6,1.0,1), 1.8)
mat_chB = make_emission_material("mat_chB", (0.2,1.0,0.6,1), 1.8)
mat_seam= make_emission_material("mat_seam",(0.6,0.6,0.6,1), 1.2)
mat_kiss= make_emission_material("mat_kiss",(1.0,0.25,0.25,1), 3.0)
mat_hop = make_emission_material("mat_hop", (1.0,0.7,0.2,1), 2.5)
mat_text= make_emission_material("mat_text",(1,1,1,1), 5.0)

def radius(z): return R0 * math.exp(-beta * z)

# streamline point for constant phase φ0 around channel at Xc
def streamline_point(Xc, z, phi0):
    r = radius(z)
    phi = phi0 - k*z
    x = Xc + r*math.cos(phi)
    y =      r*math.sin(phi)
    return (x, y, z)

def add_curve(name, pts, mat, thickness=tube):
    crv = bpy.data.curves.new(name, type='CURVE')
    crv.dimensions = '3D'
    spline = crv.splines.new('POLY')
    spline.points.add(len(pts)-1)
    for i, p in enumerate(pts):
        spline.points[i].co = (*p, 1.0)
    crv.bevel_depth = thickness
    obj = bpy.data.objects.new(name, crv)
    obj.data.materials.append(mat)
    coll.objects.link(obj)
    return obj

def add_cylinder(name, start, end, radius=0.02, mat=None):
    v = mathutils.Vector(end) - mathutils.Vector(start)
    h = v.length
    if h < 1e-6: h = 1e-6
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=h, location=(0,0,0))
    cyl = bpy.context.object
    cyl.name = name
    cyl.location = mathutils.Vector(start) + v/2
    # orient so local Z aligns to v
    z_axis = mathutils.Vector((0,0,1))
    quat = z_axis.rotation_difference(v.normalized())
    cyl.rotation_mode = 'QUATERNION'
    cyl.rotation_quaternion = quat
    if mat:
        cyl.data.materials.clear()
        cyl.data.materials.append(mat)
    coll.objects.link(cyl)
    return cyl

def add_sphere(name, loc, r=0.07, mat=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc)
    sph = bpy.context.object
    sph.name = name
    if mat:
        sph.data.materials.clear()
        sph.data.materials.append(mat)
    coll.objects.link(sph)
    return sph

def add_text(tag, loc, size=0.35):
    bpy.ops.object.text_add(location=loc)
    txt = bpy.context.object
    txt.data.body = tag
    txt.data.align_x = 'CENTER'
    txt.data.size = size
    # give it emission look
    if len(txt.data.materials)==0:
        txt.data.materials.append(mat_text)
    else:
        txt.data.materials[0] = mat_text
    coll.objects.link(txt)
    return txt

# --- build two neighbor channels (pair) ---
ia, ib = pair
Xa, Xb = chs[ia], chs[ib]
dx = abs(Xb - Xa)
zkiss = (1.0/beta) * math.log((2.0*R0)/dx) if dx <= 2*R0 else None

# two streamlines (φ0 = 0 and π) around each of the two channels
zs = [i*(H/(samples-1)) for i in range(samples)]
pts_A0 = [streamline_point(Xa, z, 0.0) for z in zs]
pts_Bpi= [streamline_point(Xb, z, math.pi) for z in zs]  # opposite branch

obj_A0 = add_curve("channel_A_phi0", pts_A0, mat_chA)
obj_Bp = add_curve("channel_B_phipi", pts_Bpi, mat_chB)

# equal-weight seam: vertical line at midpoint x = (Xa+Xb)/2, y=0
xmid = 0.5*(Xa + Xb)
seam = add_cylinder("equal_weight_seam", (xmid, 0.0, 0.0), (xmid, 0.0, H), radius=0.01, mat=mat_seam)

# Kiss point marker (on y=0 branch intersection)
if zkiss is not None and 0.0 <= zkiss <= H:
    kiss = add_sphere("kiss_point", (xmid, 0.0, zkiss), r=0.07, mat=mat_kiss)
    add_text(f"Kiss z≈{zkiss:.2f}", (xmid, 0.4, zkiss+0.25), size=0.25)

# Hop arc across the seam at z_kiss (simple gentle C-curve)
def add_hop_arc(z0):
    x0 = Xa + radius(z0)  # point on A at y≈0
    x1 = Xb - radius(z0)  # point on B at y≈0
    y0 = 0.0
    # Bezier curve with mild sideways bulge
    crv = bpy.data.curves.new("hop_arc", type='CURVE')
    crv.dimensions = '3D'
    spl = crv.splines.new('BEZIER')
    spl.bezier_points.add(1)  # two-point bezier
    p0 = spl.bezier_points[0]; p1 = spl.bezier_points[1]
    p0.co = (x0, y0, z0); p1.co = (x1, y0, z0)
    # control handles to create a bulge in +Y
    bulge = 0.6 * radius(z0)
    p0.handle_right = (x0, bulge, z0)
    p0.handle_left  = (x0,-bulge, z0)
    p1.handle_left  = (x1, bulge, z0)
    p1.handle_right = (x1,-bulge, z0)
    for bp in spl.bezier_points:
        bp.handle_left_type = 'FREE'
        bp.handle_right_type= 'FREE'
        bp.radius = 1.0
    crv.bevel_depth = tube * 1.2
    obj = bpy.data.objects.new("hop_arc", crv)
    obj.data.materials.append(mat_hop)
    coll.objects.link(obj)
    return obj

if zkiss is not None and 0.0 <= zkiss <= H:
    add_hop_arc(zkiss)
    add_text("Hop", (xmid, 0.8, zkiss+0.02), size=0.30)

# Labels for channels
add_text(f"Channel {Xa:g}", (Xa, -1.3, 0.2), size=0.28)
add_text(f"Channel {Xb:g}", (Xb, -1.3, 0.2), size=0.28)
add_text("Equal-weight seam", (xmid, -1.3, H*0.5), size=0.24)

# Camera & light (simple studio)
def look_at(obj, target):
    direction = mathutils.Vector(target) - obj.location
    rot_quat = direction.to_track_quat('-Z', 'Y')
    obj.rotation_euler = rot_quat.to_euler()

# camera
cam = bpy.data.objects.new("VVB_Camera", bpy.data.cameras.new("VVB_Camera"))
coll.objects.link(cam)
cam.location = (0.0, -10.0, 3.8)
look_at(cam, (xmid, 0.0, H*0.5))
bpy.context.scene.camera = cam

# light
bpy.ops.object.light_add(type='SUN', location=(0, -6, 6))
sun = bpy.context.object
sun.data.energy = 2.0
coll.objects.link(sun)

# World a bit darker for glow
world = bpy.context.scene.world
world.color = (0.03, 0.03, 0.04)

# --- Render settings + save (engine-safe) ---
scene = bpy.context.scene
engines = {e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items}

if 'BLENDER_EEVEE_NEXT' in engines:
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
else:
    scene.render.engine = 'CYCLES'  # fallback if Eevee Next isn't available

scene.render.resolution_x = 1600
scene.render.resolution_y = 1000
scene.render.film_transparent = True  # OK for Eevee Next and Cycles

bpy.context.scene.render.filepath = outpath
bpy.ops.render.render(write_still=True)
print("Saved:", outpath)

