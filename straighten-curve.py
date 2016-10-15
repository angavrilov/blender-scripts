# #####BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# #####END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Straighten Curve",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "Select Curve -> Search -> Straighten Curve",
    "description": "Operator to straighten a bezier curve without changing its length.",
    "warning": "",
    "wiki_url": "",
    "category": "Add Curve",
    }


import bpy
import operator
import math
import mathutils

from mathutils import *

# Code from the Curve Tools add-on by Zak

def getbezpoints(spl, mt, seg=0):
    points = spl.bezier_points
    p0 = mt * points[seg].co
    p1 = mt * points[seg].handle_right
    p2 = mt * points[seg+1].handle_left
    p3 = mt * points[seg+1].co
    return p0, p1, p2, p3

def cubic(p, t):
    return p[0]*(1.0-t)**3.0 + 3.0*p[1]*t*(1.0-t)**2.0 + 3.0*p[2]*(t**2.0)*(1.0-t) + p[3]*t**3.0

# End of Curve Tools code

def get_active_spline(context):
    obj = context.active_object

    if obj == None or obj.type != "CURVE":
        return None

    spl = obj.data.splines.active

    if spl == None and len(obj.data.splines) > 0:
        spl=obj.data.splines[0]

    return spl

class CURVE_OT_straighten(bpy.types.Operator):
    """Straighten the bezier curve, preserving its length."""
    bl_idname = "curve.straighten"
    bl_label = "Straighten Curve"
    bl_options = {'REGISTER', 'UNDO'}

    reset_tilt = bpy.props.BoolProperty(name="Reset Tilt",description="Reset point tilt values to zero",default=True)

    @classmethod
    def poll(cls, context):
        spl = get_active_spline(context)
        return spl != None and spl.type == 'BEZIER'

    def execute(self, context):
        spl = get_active_spline(context)

        points = spl.bezier_points
        nsegs = len(points)-1
        mt = Matrix.Identity(4)

        res = spl.resolution_u
        lens = [0]
        seglen = 0

        for i in range(0,nsegs):
            p = getbezpoints(spl, mt, i)

            pp = p[0]

            for j in range(0,res):
                cp = cubic(p, (j+1)/res)
                seglen += (cp-pp).magnitude
                pp = cp

            lens.append(seglen)

        origin = Vector(points[0].co)
        coordfn = lambda x: Vector((x,0,0))

        for i, pt in enumerate(points):
            ll = (pt.handle_left - pt.co).magnitude
            lr = (pt.handle_right - pt.co).magnitude

            pt.co = origin + coordfn(lens[i])

            if pt.handle_left_type != 'AUTO':
                pt.handle_left = pt.co - coordfn(ll)
            if pt.handle_right_type != 'AUTO':
                pt.handle_right = pt.co + coordfn(lr)

            if self.reset_tilt:
                pt.tilt = 0.0

        return {'FINISHED'}


def register():
    bpy.utils.register_class(CURVE_OT_straighten)

def unregister():
    bpy.utils.unregister_class(CURVE_OT_straighten)

if __name__ == "__main__":
    register()
