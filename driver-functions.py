import bpy
import math

# Soft MIN/MAX functions

def softmax_power_solve(radius,limit):
    """
    Iteratively solves for a power coefficient that produces target deviation at radius.
    """
    def delta(coeff):
        return math.log1p(math.exp(-coeff*radius))/coeff
    def deriv(dv,coeff):
        return -(dv + radius/(1+math.exp(coeff*radius)))/coeff

    # Find a starting point to the left of the root
    val = 1
    if delta(val) >= limit:
        while delta(2*val) >= limit:
            val = val * 2
    else:
        while delta(val) < limit:
            val = val / 2

    # Narrow down with binsearch on the far right side
    if val >= 2:
        right = val*2
        while (right-val) > 1:
            mid = (val+right)/2
            dv = delta(mid)
            #print(mid,dv)

            if dv < limit:
                right = mid
            else:
                val = mid

    # Use Newton's method: with an always positive second derivative
    # and starting to the left of the root, it should always converge
    while True:
        dv = delta(val)
        dvv = deriv(dv, val)
        dx = -(dv-limit)/dvv
        #print(val,dv,dvv,dx)

        val = val + dx
        if abs(dv/limit-1) < 1e-6:
            return val

#print(softmax_power_solve(1.0,1e-6))

logn_2 = math.log(2)
softmax_coeff_table = {} # cache table

def softmax_power(radius,limit):
    """
    Finds the power coefficient that matches radius & limit using cache or computation.
    """

    if radius < 0:
        raise ValueError("negative softmax radius")
    if limit <= 0:
        raise ValueError("non-positive softmax limit")

    # Easy special case
    if radius == 0:
        return logn_2/limit

    try:
        ctab = softmax_coeff_table[limit]
    except KeyError:
        ctab = softmax_coeff_table[limit] = {}

    try:
        return ctab[radius]
    except KeyError:
        val = ctab[radius] = softmax_power_solve(radius, limit)
        return val

def softmaxp(x,y,power):
    """
    A maximum like function with smoothed out corner.
    """
    return max(x,y) + math.log1p(math.exp(-power*abs(x-y)))/power

def softmax(x,y,radius=1.0,limit=0.01):
    """
    A maximum like function with smoothed out corner.
    At abs(x-y)=radius overshoots by limit.
    """
    return softmaxp(x,y,softmax_power(radius,limit))

def softminp(x,y,power):
    """
    A minimum like function with smoothed out corner.
    """
    return min(x,y) - math.log1p(math.exp(-power*abs(x-y)))/power

def softmin(x,y,radius=1.0,limit=0.01):
    """
    A minimum like function with smoothed out corner.
    At abs(x-y)=radius undershoots by limit.
    """
    return softminp(x,y,softmax_power(radius,limit))

bpy.app.driver_namespace['softmaxp'] = softmaxp
bpy.app.driver_namespace['softmax'] = softmax
bpy.app.driver_namespace['softminp'] = softminp
bpy.app.driver_namespace['softmin'] = softmin
