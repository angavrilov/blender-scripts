bl_info = {
    "name": "Bake Expression to Curves",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "Select a Curves Node -> Panel containing the Label property",
    "description": "Operator to generate points of a curves node from a python math expression in node label.",
    "warning": "",
    "wiki_url": "",
    "category": "Node",
    }

'''

Implements an operator that bakes a python expression contained in
the curves node label to curve points. F6 menu allows changing the
number of points or toggle bezier vs linear mode.

The label may be either one expression to specify a common transform,
or multiple '|' separated expressions for the individual curves.

The expressions access the input (horizontal axis) value as 'x',
and may also refer to each other, provided there are no cycles.

RGB Curves:

C
R | G | B
C | R | G | B

Vector Curves:

XYZ
X | Y | Z

'''

import bpy

def get_active_node(context):
    space = context.space_data

    if space.type == 'NODE_EDITOR' and space.node_tree is not None:
        return context.active_node

    return None

# Set curve data

def apply_curve(curve, xlist, ylist, mode='AUTO'):
    while len(curve.points) > 2:
        curve.points.remove(curve.points[2])

    curve.points[0].location = (xlist[0], ylist[0])
    curve.points[0].handle_type = mode

    curve.points[1].location = (xlist[1], ylist[1])
    curve.points[1].handle_type = mode

    for i in range(2, len(xlist)):
        pt = curve.points.new(xlist[i], ylist[i])
        pt.handle_type = mode

# Compute data

def generate_x_list(min_x, max_x, count):
    return [ min_x + i*(max_x-min_x) / (count-1) for i in range(0,count) ]

def generate_expr_data(expr, count, inputs):
    global_map = bpy.app.driver_namespace

    def evalfn(i):
        locmap = { k:v[i] for k,v in inputs.items() }
        return float(eval(expr, global_map, locmap))

    return [ evalfn(i) for i in range(0,count) ]

# Compute curve values in dependency order

def evaluate_curves(op, count, min_x, max_x, label, invar, shapes):
    # Split sub-expressions
    exprs = label.split('|')

    if len(exprs) not in shapes:
        op.report({'ERROR_INVALID_INPUT'}, "Invalid number of expressions in node label.")
        return None

    # Compile expressions
    expr_table = {}
    shape = shapes[len(exprs)]

    for i,expr in enumerate(exprs):
        try:
            expr_table[shape[i]] = compile(expr, '<expr>', 'eval')
        except SyntaxError:
            op.report({'ERROR_INVALID_INPUT'}, "Invalid python expression in node label.")
            return None

    # Evaluate in dependency order
    results = {}
    results[invar] = generate_x_list(min_x, max_x, count)

    min_y, max_y = None, None

    while len(expr_table) > 0:
        for eid, expr in expr_table.items():
            unresolved = [ ids for ids in expr.co_names if ids in expr_table ]
            if unresolved == []:
                try:
                    earr = generate_expr_data(expr, count, results)
                except Exception as e:
                    op.report({'ERROR_INVALID_INPUT'}, "Error evaluating the python expression for %s in node label: %s." % (eid, e))
                    return None

                results[eid] = earr
                del expr_table[eid]

                if min_y is None:
                    min_y, max_y = min(earr), max(earr)
                else:
                    min_y, max_y = min(min_y, min(earr)), max(max_y, max(earr))

                break
        else:
            op.report({'ERROR_INVALID_INPUT'}, "Circular dependency between sub-expressions in node label.")
            return None

    return results, min_y, max_y


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
        return node and (node.type == "CURVE_RGB" or node.type == "CURVE_VEC")

    def execute(self, context):
        node = get_active_node(context)
        mapping = node.mapping
        min_x = mapping.clip_min_x
        max_x = mapping.clip_max_x

        # Compute curve values
        if node.type == "CURVE_VEC":
            shapes = { 1: ['XYZ'], 3: ['X','Y','Z'] }
            curvenames = ['X','Y','Z']
        else:
            shapes = { 1: ['C'], 3: ['R','G','B'], 4: ['C','R','G','B'] }
            curvenames = ['R','G','B','C']

        curve_data = evaluate_curves(self, self.num_points, min_x, max_x, node.label, 'x', shapes)

        if curve_data is None:
            return {'CANCELLED'}

        # Apply values to node data
        curve_vals, mapping.clip_min_y, mapping.clip_max_y = curve_data
        xvec = curve_vals['x']
        fallback = curve_vals.get('XYZ')

        mode = 'AUTO' if self.use_bezier else 'VECTOR'

        for i,v in enumerate(curvenames):
            if v in curve_vals:
                apply_curve(mapping.curves[i], xvec, curve_vals[v], mode)
            elif fallback:
                apply_curve(mapping.curves[i], xvec, fallback, mode)
            else:
                apply_curve(mapping.curves[i], [0.0, 1.0], [0.0, 1.0], mode)

        # Update mapping, UI and force shader refresh
        mapping.update()
        node.width = node.width
        context.space_data.node_tree.update_tag()

        return {'FINISHED'}


class NODE_MT_bake_expression_to_curves_help(bpy.types.Menu):
    bl_description = "Help"
    bl_label = "Help"
    bl_options = {'REGISTER'}

    def draw(self, context):
        layout = self.layout
        node = get_active_node(context)

        layout.label("Bakes a python expression in node label to curve points.")
        layout.label("Set input range via Min X and Max X in Clipping Options.")
        layout.label("Use F6 menu to set the number of points or toggle bezier.")
        layout.separator()
        layout.label("The label may contain multiple '|' separated expressions.")
        layout.label("It can use any python functions accessible in drivers.")

        if node.type == "CURVE_VEC":
            layout.label("Access input as x or other sub-curves as X,Y,Z:")
            layout.separator()
            layout.label("XYZ")
            layout.label("X | Y | Z")
        else:
            layout.label("Access input as x or other sub-curves as C,R,G,B:")
            layout.separator()
            layout.label("C")
            layout.label("R | G | B")
            layout.label("C | R | G | B")


def panel_func(self, context):
    layout = self.layout
    node = get_active_node(context)

    if node and node.type in {"CURVE_RGB", "CURVE_VEC"}:
        layout.separator()
        row = layout.split(percentage=0.63)
        row.column().operator(NODE_OT_bake_expression_to_curves.bl_idname, text="Bake Expression")
        row.column().menu("NODE_MT_bake_expression_to_curves_help", icon="INFO")


def register():
    bpy.utils.register_class(NODE_OT_bake_expression_to_curves)
    bpy.utils.register_class(NODE_MT_bake_expression_to_curves_help)

    if bpy.types.NODE_PT_active_node_generic:
        bpy.types.NODE_PT_active_node_generic.append(panel_func)

def unregister():
    bpy.utils.unregister_class(NODE_OT_bake_expression_to_curves)
    bpy.utils.unregister_class(NODE_MT_bake_expression_to_curves_help)

    if bpy.types.NODE_PT_active_node_generic:
        bpy.types.NODE_PT_active_node_generic.remove(panel_func)

if __name__ == "__main__":
    register()
