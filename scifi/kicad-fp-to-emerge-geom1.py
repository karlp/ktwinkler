#!python3
"""
Extract the geometry of a specific refdes from a running kicad...
goal is feeding straight into emerge then...

This version uses kipy, which is the "official" api via IPC, 
so it connects to a _running_ kicad!
"""

import emerge as em
import kipy
import numpy as np

mm = 0.001              # meters per millimeter
nm2m = 1e-9 # nanometers per meter (kicad is all in nm)

# The refdes of the antenna I want to evaluate
ant_refdes = "AE2"

model = em.Simulation("ki-ant")
model.check_version("2.4")

b = kipy.KiCad().get_board()
footprints = b.get_footprints()

# SO.. you can decode [print(l) for l in b.get_stackup().layers]
# and decide what layer is the reference ground layer, and add it all up?
# or, 
th = 0.1*mm

numbered_cu_l = [x for x in enumerate(b.get_stackup().layers) if x[1].material_name == "copper"]
# Now, distance from first to second copper... (you'd need to adjust this otherwise..)
inter_layers = b.get_stackup().layers[numbered_cu_l[0][0]+1:numbered_cu_l[1][0]]

th_12 = sum([l.thickness for l in inter_layers]) * nm2m

print(f"hardcoded: {th}, via board stack, cu1 to cu2: {th_12}")


ant_fp = [f for f in footprints if f.reference_field.text.value==ant_refdes][0]

# we're totally glossing over effects of mask, yolo
copper_bits = [s for s in ant_fp.definition.shapes if s.layer==kipy.board_types.BoardLayer.BL_F_Cu]



# BoardPolygon(points=[PolygonWithHoles(
#   outline=PolyLine(nodes=[
#       PolyLineNode(point=Vector2(150959989, 148662706)), 
#       PolyLineNode(point=Vector2(150459992, 148662706)), 
#       PolyLineNode(point=Vector2(150459992, 144542706)), 
#       PolyLineNode(point=Vector2(150959989, 144542706))], 
#       closed=True), holes=[])], layer=BL_F_Cu, net=)

em_fp_segs = []

for chunk in copper_bits:
    for poly in chunk.polygons:
        assert len(poly.holes) == 0
        assert poly.outline.closed
        xs = [node.point.x * nm2m for node in poly.outline.nodes]
        ys = [node.point.y * nm2m for node in poly.outline.nodes]
        # umm, I'm only looking at boardpolygon right now, but there's probably others?
        emch = em.geo.XYPolygon(xs, ys)
        emch = emch.geo(em.GCS.displace(0,0,-th_12)) # maybe?
        em_fp_segs.append(emch)



# nominally, we could get the ground under from the board...
wsub = 60 * mm
hsub = 40 * mm
dielectric = em.geo.Box(wsub, hsub, th_12, position=(-wsub/2, -hsub/2, -th))
# Air box above substrate (Z positive)
Rair = 100 * mm         # air sphere radius
air = em.geo.Sphere(Rair).background()
ground = em.geo.XYPlate(wsub, hsub, position=(-wsub/2, -hsub/2, -th)).set_material(em.lib.PEC)

#em_ant = em.geo.unite(em_fp_segs)
em_ant = em_fp_segs[0]
for seg in em_fp_segs[1:]:
    em_ant = em.geo.add(em_ant, seg)
em_ant.set_material(em.lib.PEC)

# FIXME - this needs to be autoconnected to the "pad1" ?
wline = 0.5 * mm        # feed line width
port = em.geo.Plate(
    #np.array([-wline/2, -Lpatch/2, -th]),  # lower port corner
    np.array([0, 0, -th]),  # lower port corner
    np.array([wline, 0, 0]),                # width vector along X
    np.array([0, 0, th])                    # height vector along Z
)

# fuck this ipc, I just want the sexp parser
# ok, geo time...

dielectric.set_material(em.Material(3.38, color="#207020", opacity=0.9))

# Mesh resolution: fraction of wavelength
model.mw.set_resolution(0.2)

f1 = 1.5e9
f2 = 3.5e9
# Frequency sweep across the resonance
model.mw.set_frequency_range(f1, f2, 7)

# --- Combine geometry into simulation -----------------------------------
model.commit_geometry()


# --- Mesh refinement settings --------------------------------------------
# Finer boundary mesh on patch edges for accuracy
model.mesher.set_boundary_size(em_ant, 2 * mm)
# Refined mesh on port face for excitation accuracy
model.mesher.set_face_size(port, 1 * mm)

# --- Generate mesh and preview ------------------------------------------
model.generate_mesh()                             # build the finite-element mesh
model.view(selections=[port])     # show the mesh around the port