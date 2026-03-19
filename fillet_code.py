import phidl.geometry as pg
from phidl import quickplot as qp
from phidl import Device

# Fillet radius
f_r = 5

D1 = pg.circle(radius = f_r, layer = 1).move([f_r,f_r])
D2 = pg.rectangle(size = [f_r, f_r], layer = 2)

# Make fillets for all 4 quadrants
F1 = pg.boolean(A = D2, B = D1, operation = 'not', precision = 1e-6,
               num_divisions = [1,1], layer = 0)

D2.move([f_r, 0])
F2 = pg.boolean(A = D2, B = D1, operation = 'not', precision = 1e-6,
               num_divisions = [1,1], layer = 0)
F2.move([-2 * f_r, 0])

D2.move([0, f_r])
F3 = pg.boolean(A = D2, B = D1, operation = 'not', precision = 1e-6,
               num_divisions = [1,1], layer = 0)
F3.move([-2 * f_r, -2 * f_r])

D2.move([-f_r, 0])
F4 = pg.boolean(A = D2, B = D1, operation = 'not', precision = 1e-6,
               num_divisions = [1,1], layer = 0)
F4.move([0, -2 * f_r])

# EXAMPLE:
B1 = pg.rectangle(size = [20, 20], layer = 0)
B2 = pg.rectangle(size = [10, 10], layer = 0).move([20, 0])

D = Device()
D.add_ref(B1)
D.add_ref(B2)
D.add_ref(F1).move([20, 10])  # use first quadrant fillet at the corner

D.flatten()

qp(D) # quickplot the geometry