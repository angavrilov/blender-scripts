import bpy
import math

# Soft MIN/MAX functions

def softmax_powercoeff(radius,limit):
    """
    Iteratively solves for a power coefficient that produces target deviation at radius.
    """
    def delta(coeff):
        return math.log1p(math.exp(-coeff*radius))/coeff

    if limit >= 1:
        limit = math.pow(10, -limit)

    right = 1
    while delta(right) > limit:
        right = right * 2
    if right < 2:
        return right

    left = right / 2
    while True:
        mid = (left+right)/2
        dv = delta(mid)
        #print(mid,dv,dv/limit)

        if dv > limit:
            left = mid
        elif dv/limit > 0.999:
            return mid
        else:
            right = mid

softmax_coeff_table = {} # cache table for softmax_powercoeff results

def softmax(x,y,radius=1.0,digits=2):
    """
    Implements a maximum like function with smoothed out corner.
    At abs(x-y)=radius overshoots by digits<1 ? digits : 10^-digits.
    The radius and digits parameters are expected to be constants.
    """
    if radius < 0 or digits <= 0:
        raise ValueError("invalid radius or digits")

    try:
        ctab = softmax_coeff_table[digits]
    except KeyError:
        ctab = softmax_coeff_table[digits] = {}

    try:
        power = ctab[radius]
    except KeyError:
        power = ctab[radius] = softmax_powercoeff(radius, digits)

    return max(x,y) + math.log1p(math.exp(-power*abs(x-y)))/power

def softmin(x,y,radius=1.0,digits=2):
    """
    Implements a minimum like function with smoothed out corner.
    At abs(x-y)=radius undershoots by digits<1 ? digits : 10^-digits.
    The radius and digits parameters are expected to be constants.
    """
    return -softmax(-x,-y,radius,digits)

bpy.app.driver_namespace['softmax'] = softmax
bpy.app.driver_namespace['softmin'] = softmin
