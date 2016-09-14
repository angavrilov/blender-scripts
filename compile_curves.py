bl_info = {
    "name": "Bake Expression to Curves",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "Select a Curves Node -> Search for Operator",
    "description": "Operator to generate points of a curves node from a python math expression.",
    "warning": "",
    "wiki_url": "",
    "category": "Node",
    }

import bpy

def get_active_node(context):
    space = context.space_data

    if space.type == 'NODE_EDITOR' and space.node_tree is not None:
        return context.active_node

    return None

def clear_curve(curve, reset=True):
    while len(curve.points) > 2:
        curve.points.remove(curve.points[2])

    if reset:
        curve.points[0].location = (0.0, 0.0)
        curve.points[1].location = (1.0, 1.0)

def generate_curve(curve, min_x, max_x, expr, count, mode='AUTO'):
    global_map = bpy.app.driver_namespace

    clear_curve(curve, False)

    try:
        v1 = float(eval(expr, global_map, {'x': min_x}))
    except:
        return None

    curve.points[0].location = (min_x, v1)
    curve.points[0].handle_type = mode

    try:
        v2 = float(eval(expr, global_map, {'x': max_x}))
    except:
        return None

    curve.points[1].location = (max_x, v2)
    curve.points[1].handle_type = mode

    scale = (max_x - min_x) / (count-1)
    min_y = min(v1, v2)
    max_y = max(v1, v2)

    for i in range(1,count-1):
        x = min_x + scale * i

        try:
            y = float(eval(expr, global_map, {'x': x}))
        except:
            return None

        min_y = min(min_y, y)
        max_y = max(max_y, y)

        pt = curve.points.new(x, y)
        pt.handle_type = mode

    return (min_y, max_y)

class NODE_OT_bake_expression_to_curves(bpy.types.Operator):
    """Generate curve points from label interpreted as expression."""
    bl_idname = "node.bake_expression_to_curves"
    bl_label = "Bake Expression to Curves"
    bl_options = {'REGISTER', 'UNDO'}

    num_points = bpy.props.IntProperty(name="Points",description="Number of points to generate",default=64,min=2,max=256)
    use_bezier = bpy.props.BoolProperty(name="Bezier",description="Use bezier handle type",default=True)

    @classmethod
    def poll(cls, context):
        node = get_active_node(context)
        return node and node.type == "CURVE_RGB"

    def execute(self, context):
        node = get_active_node(context)

        try:
            codefn = compile(node.label, '<expr>', 'eval')
        except SyntaxError:
            self.report({'ERROR_INVALID_INPUT'}, "Invalid python expression in node label.")
            return {'CANCELLED'}

        mode = 'AUTO' if self.use_bezier else 'VECTOR'

        mapping = node.mapping
        min_x = mapping.clip_min_x
        max_x = mapping.clip_max_x

        mapping.use_clip = False

        for i in range(0,3):
            clear_curve(mapping.curves[i])

        minmax = generate_curve(mapping.curves[3], min_x, max_x, codefn, self.num_points, mode)

        if minmax is None:
            self.report({'ERROR_INVALID_INPUT'}, "Error evaluating the python expression in node label.")
            return {'CANCELLED'}

        mapping.clip_min_y, mapping.clip_max_y = minmax
        mapping.use_clip = True

        mapping.update()
        context.space_data.node_tree.update_tag()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(NODE_OT_bake_expression_to_curves)

def unregister():
    bpy.utils.unregister_class(NODE_OT_bake_expression_to_curves)

if __name__ == "__main__":
    register()
