import emerge as em
import numpy as np
from emerge.plot import plot_sp, smith, plot_ff_polar, plot_ff
from emerge._emerge.geo.shapes import Alignment


"""
Originally based on the "demo4_patch_antenna.py" example from emerge

instead of a  patch, we're starting with a "standard" PIFA to check we're getting things we expect,
then we'll move forward to the lolpole.


(just experimenting with generating geometries...)
PATCH ANTENNA DEMO

This design is modeled after this Comsol Demo: https://www.comsol.com/model/microstrip-patch-antenna-11742

In this demo we build and simulate a rectangular patch antenna on a dielectric
substrate with airbox and lumped port excitation, then visualize S-parameters
and far-field radiation patterns. 

This simulation is quite heavy and might take a while to fully compute with SuperLU on ARM Mac's (UMFPACK Advised)

Due to the relatively coarse mesh, the resonance frequency is lower than in reality (expected around 1.59GHz)
"""

# --- Unit and simulation parameters --------------------------------------
mm = 0.001              # meters per millimeter

# --- Antenna geometry dimensions ----------------------------------------


#Wpatch = 53 * mm        # patch width (meters)
#Lpatch = 52 * mm        # patch length
wline = 0.5 * mm        # feed line width
#wstub = 7 * mm          # stub width for inset feed
lstub = 15.5 * mm       # stub (feed) length
wsub = 50 * mm         # substrate width
hsub = 30 * mm         # substrate length
th = 1.524 * mm         # substrate thickness
Rair = 100 * mm         # air sphere radius
infeedL = 6*mm

# Refined frequency range for antenna resonance around 1.54–1.6 GHz
#f1 = 2.38e9             # start frequency
#f2 = 2.50e9             # stop frequency
f1 = 1.5e9
f2 = 3.5e9

# --- Create simulation object -------------------------------------------
model = em.Simulation('pifa1')

model.check_version("2.4") # Checks version compatibility.

# --- Define geometry primitives -----------------------------------------
# Substrate block centered at origin in XY, thickness in Z (negative down)
dielectric = em.geo.Box(wsub, hsub, th,
                        position=(-wsub/2, -hsub/2, -th))

# Air box above substrate (Z positive)
air = em.geo.Sphere(Rair).background() 
# Background makes sure no materials of overlapping domains are overwritten

# So, trace width, 0.5mm, 6mm infeed, right turn, lets' say 2.5mm legs, 
# infeed, R 2.5mm, L 2.5, L2.5, R2.5, R2.5, L2.5, L2.5, R2.5, R outfeed.
# plus the ground on the backside of the infeed,
# infeed, L 1mm, Left, then outfeed at... 0.9mm wide, same length as infeed...
# huh, this wch shit isn't even remotely symmetric. we're going to ... not model that exactly right now...
# (We're going to need to learn mid-points or outside points I guess..)

# pifa = em.geo.XYPlate(wline, infeedL, position=(0,0,0))
# pifa_h1up = em.geo.XYPlate(2.5*mm, wline, position=(0, infeedL, 0))
# pifa_h2lo = em.geo.XYPlate(2.5*mm, wline, position=(2.5*mm * 1, infeedL - 2.5*mm, 0))
# pifa_h3up = em.geo.XYPlate(2.5*mm, wline, position=(2.5*mm * 2, infeedL, 0))
# pifa_h4lo = em.geo.XYPlate(2.5*mm, wline, position=(2.5*mm * 3, infeedL - 2.5*mm, 0))
# pifa_h5up = em.geo.XYPlate(2.5*mm, wline, position=(2.5*mm * 4, infeedL, 0))

# pifa_v1 = em.geo.XYPlate(wline, 2.5*mm, position=(2.5*mm * 1, infeedL - 2.5*mm, 0))
# pifa_v2 = em.geo.XYPlate(wline, 2.5*mm, position=(2.5*mm * 2, infeedL - 2.5*mm, 0))
# pifa_v3 = em.geo.XYPlate(wline, 2.5*mm, position=(2.5*mm * 3, infeedL - 2.5*mm, 0))
# pifa_v4 = em.geo.XYPlate(wline, 2.5*mm, position=(2.5*mm * 4, infeedL - 2.5*mm, 0))

pifa_segs = []
pifa_segs.append(em.geo.XYPolygon((5.650011*mm,6.150008*mm,6.150008*mm, 5.650011*mm),
                                  (-2.572706*mm,-2.572706*mm,1.547294*mm,1.547294*mm)))

# Can we just use stretch?

# lets start with this...
# Metal patch rectangle on top of substrate
# rpatch = em.geo.XYPlate(Wpatch, Lpatch,
#                         position=(-Wpatch/2, -Lpatch/2, 0))

ground = em.geo.XYPlate(wsub, hsub, position=(-wsub/2, -hsub/2, -th)).set_material(em.lib.PEC)

# Define cutouts for inset feed: two rectangular plates to subtract
# cutout1 = em.geo.XYPlate(wstub, lstub,
#                         position=(-wline/2 - wstub, -Lpatch/2, 0))
# cutout2 = em.geo.XYPlate(wstub, lstub,
#                         position=( wline/2, -Lpatch/2, 0))
# # Feed line plate to add back between cutouts
# line = em.geo.XYPlate(wline, lstub,
#                          position=(-wline/2, -Lpatch/2, 0))

# Plate defining lumped port geometry (origin + width/height vectors)
port = em.geo.Plate(
    #np.array([-wline/2, -Lpatch/2, -th]),  # lower port corner
    np.array([0, 0, -th]),  # lower port corner
    np.array([wline, 0, 0]),                # width vector along X
    np.array([0, 0, th])                    # height vector along Z
)

# Build final patch shape: subtract cutouts, add feed line
# rpatch = em.geo.remove(rpatch, cutout1)
# rpatch = em.geo.remove(rpatch, cutout2)
# rpatch = em.geo.add(rpatch, line)
# rpatch.set_material(em.lib.PEC)

pifa = em.geo.add(pifa, pifa_h1up)
pifa = em.geo.add(pifa, pifa_h2lo)
pifa = em.geo.add(pifa, pifa_h3up)
pifa = em.geo.add(pifa, pifa_h4lo)
pifa = em.geo.add(pifa, pifa_h5up)
pifa = em.geo.add(pifa, pifa_v1)
pifa = em.geo.add(pifa, pifa_v2)
pifa = em.geo.add(pifa, pifa_v3)
pifa = em.geo.add(pifa, pifa_v4)

# --- Assign materials and simulation settings ---------------------------
# Dielectric material with some transparency for display
dielectric.set_material(em.Material(3.38, color="#207020", opacity=0.9))

# Mesh resolution: fraction of wavelength
model.mw.set_resolution(0.2)

# Frequency sweep across the resonance
model.mw.set_frequency_range(f1, f2, 7)

# --- Combine geometry into simulation -----------------------------------
model.commit_geometry()

# --- Mesh refinement settings --------------------------------------------
# Finer boundary mesh on patch edges for accuracy
model.mesher.set_boundary_size(pifa, 2 * mm)
# Refined mesh on port face for excitation accuracy
model.mesher.set_face_size(port, 1 * mm)

# --- Generate mesh and preview ------------------------------------------
model.generate_mesh()                             # build the finite-element mesh
model.view(selections=[port])     # show the mesh around the port
