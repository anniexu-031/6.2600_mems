#%%
from phidl import Device
import math
import phidl.geometry as pg

##########################################
# Layers:
# 1 = contact opening etch
# 2 = aluminum metal wiring
# 3 = dummy fill pattern
# 11 = active device area
##########################################    
# WRITE ON MLA
# Mask 1 = Layer 1
# Mask 2 = Layer 2 OR 3
# Ignore Layer 11, it's for visualization
##########################################
#
# IMPORTANT: Flatten design in KLayout
# and remove all hierarchy references before
# sending to MLA.  MLA code stalls otherwise
#
##########################################


### Building blocks for our solar cell ###

# die outline
def outline(mc):
    D = pg.basic_die(
          size = (mc.width, mc.height), # Size of die
              street_width = 50,   # Width of corner marks for die-sawing
              street_length = 5000, # Length of corner marks for die-sawing
              layer = 2,
              draw_bbox = False,
              bbox_layer = 99,
              )            
    return D

# metal contact pad 
def solarpad(mc):
    P = Device()
    P << pg.rectangle( size=(mc.width-2*mc.spacing,mc.padsize), layer=2 ).move( (mc.spacing,-mc.padsize-mc.spacing))
    P << pg.rectangle( size=(mc.width-2*mc.spacing-2*mc.contactBuffer,mc.padsize-2*mc.contactBuffer), layer=1 ).move( (mc.spacing+mc.contactBuffer,-mc.padsize-mc.spacing+mc.contactBuffer))
    P.move( (-mc.width/2.0,mc.height/2.0) )    
    return P

# wires
def solarwire(mc):
    W = Device()
    if (mc.linecount>0):
        wsection = mc.devicewidth/mc.linecount
        y0 = -mc.deviceheight/2-mc.padsize/2
        for n in range(0,mc.linecount):
            x0 = n*wsection - (mc.linecount-1)*wsection/2
            W << pg.rectangle(  size=(mc.linewidth-mc.contactBuffer*2 , mc.deviceheight), layer = 1).move( (x0+mc.contactBuffer,y0+mc.contactBuffer) )
            W << pg.rectangle(  size=(mc.linewidth, mc.deviceheight), layer = 2).move( (x0,y0) )        
    return W

### The actual solar cell ###

# the complete cell, put together from the parts
def solarcell(mc):
    D = Device('solarcell')    
    D << outline(mysolar)
    D << solarpad(mysolar)
    D << solarwire(mysolar)
    # add label into cleaving street, as backup
    D << pg.text(text=mysolar.name, size=(mysolar.dicingwidth*2-mc.dummybuffer*2), justify='center', layer=2,  font="Arial").move( (0,-mysolar.height/2 - mysolar.dicingwidth+mc.dummybuffer) )
        
    ### the next part is optional:
    if mc.usedummy:
        # add dummy squares to block the light    
        DFiller = Device()
        DFiller << pg.rectangle( size=(mysolar.width-mysolar.dicingwidth*2,mysolar.height-mysolar.dicingwidth*2), layer=10 ).move( (-mysolar.width/2 + mysolar.dicingwidth,-mysolar.height/2 + mysolar.dicingwidth))    
        # run boolean operation to cut out the dummy blocks where there's a device...
        DBlock = Device()
        DBlock << pg.text(text=mysolar.name, size=mysolar.text_size, justify='center', layer=11,  font="Arial").move( (0,mysolar.height/2 - mysolar.spacing + mysolar.text_size/2) )
        DBlock << pg.rectangle(  size=(mc.devicewidth + mc.dummybuffer*2 , mc.deviceheight+mc.padsize + mc.dummybuffer*2), layer = 11).move( (-mc.devicewidth/2 - mc.dummybuffer,-(mc.deviceheight+mc.padsize)/2 -mc.dummybuffer) )
        for x in range(math.floor(mysolar.width/mysolar.dummysize)):
            DBlock << pg.rectangle( size=(mysolar.dummygap,mysolar.height), layer=11 ).move( (-mysolar.width/2 + x * mysolar.dummysize,-mysolar.height/2))
        for y in range(math.floor(mysolar.height/mysolar.dummysize)):
            DBlock << pg.rectangle( size=(mysolar.width,mysolar.dummygap), layer=11 ).move( (-mysolar.width/2,-mysolar.height/2 + y * mysolar.dummysize))    
        D.add_ref( pg.boolean(A = DFiller, B = pg.union(DBlock,layer=11), operation='A-B', precision=1e-6,layer=3))
        D << pg.rectangle(  size=(mc.devicewidth + mc.dummybuffer*2 , mc.deviceheight+mc.padsize + mc.dummybuffer*2), layer = 11).move( (-mc.devicewidth/2 - mc.dummybuffer,-(mc.deviceheight+mc.padsize)/2 -mc.dummybuffer) )
    else:
        D << pg.text(text=mysolar.name, size=mysolar.text_size, justify='center', layer=3,  font="Arial").move( (0,mysolar.height/2 - mysolar.spacing + mysolar.text_size/2) )
    
    return D


# solar cell parameters, use object to store parameters:
class EmptyClass:
    pass
mysolar = EmptyClass()
# total size of each die
mysolar.width=20000
mysolar.height=20000
# the actual cell is inside the die, with a spacing. the contact pad height needs to be large enough to probe it
mysolar.spacing=2000
mysolar.padsize=2500
mysolar.diegap=15
# metal wiring, width and count - this will be modified for different cells
mysolar.linewidth=40
mysolar.linecount=100
# we don't want to protect against misalignment, so there's a buffer for the contact opening inside the metal shape
mysolar.contactBuffer = 6
# cell labeling (name will be overwritten)
mysolar.name = '6.2600'
mysolar.text_size = 300
# to have a more precise idea of the actual area, we'll shade the area around the cell. 
# it'll be done with metal dummy squares, so accidental contact to a square will not risk short circuiting near the cleave line
mysolar.usedummy = True
mysolar.dummygap = 5
mysolar.dummysize = 2000
mysolar.dummybuffer = 10 # how close to put the dummy fillers to the actual device
mysolar.dicingwidth = 125 # leave edges free from fillers to make it easier to aim when cleaving

# pre-calculate the actual device area
mysolar.deviceheight = mysolar.height - 2* mysolar.spacing - mysolar.padsize
mysolar.devicewidth = mysolar.width - 2* mysolar.spacing

################################################################
# generate the cells: explore different line widths and metal densities:
#aW = [30, 10, 20, 30, 40, 30, 30, 30,30,30, 20, 30,50,100,200]
#aN = [45,200,200,200,200,300,200,100,50,25,150,100,60, 30, 15]

aW = [204, 36, 24, 24, 24, 24, 54, 24, 24,24,14,24,104,404,24]
aN = [ 20, 20, 50,800,600,400, 20,100,200, 0,20,20, 20, 20, 5]

W = Device('wafer')
px = 0
py = 0
for n in range(len(aW)):
    # configure the cell parameters
    mysolar.linewidth = aW[n]
    mysolar.linecount = aN[n]
    mysolar.name = '6.2600 S26 -=-  #' +str(n)+'  -=-  [ W='+str(aW[n]-4)+' , N='+str(aN[n])+' ]'    
    D = solarcell(mysolar)
    W << D.move( (px*mysolar.width,py*mysolar.height) )
    px=px+1
    if (px>4):
        px=0
        py=py+1

W.write_gds('solarcell_s26.gds')
