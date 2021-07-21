bl_info = {
    "name": "Nodes To Python",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 83, 0),
    "location": "Node > Generate Python Script",
    "description": "Generates a python script that creates the current node layout.",
    "warning": "",
    "wiki_url": "",
    "category": "Development",
    }

import bpy

import re
import collections

from bpy.types import (
    bpy_struct, bpy_prop_array,
    NodeSocketInterface, Node, NodeTree,
    CurveMapping
)

from mathutils import Color


NODE_DEFAULT_WIDTH = {
    bpy.types.NodeReroute: 16,
    bpy.types.CompositorNodeSwitch: 100,
    bpy.types.CompositorNodeValue: 100,
    bpy.types.ShaderNodeBlackbody: 150,
    bpy.types.ShaderNodeBsdfAnisotropic: 150,
    bpy.types.ShaderNodeBsdfDiffuse: 150,
    bpy.types.ShaderNodeBsdfGlass: 150,
    bpy.types.ShaderNodeBsdfGlossy: 150,
    bpy.types.ShaderNodeBsdfRefraction: 150,
    bpy.types.ShaderNodeBsdfToon: 150,
    bpy.types.ShaderNodeHueSaturation: 150,
    bpy.types.ShaderNodeLightFalloff: 150,
    bpy.types.ShaderNodeNormalMap: 150,
    bpy.types.ShaderNodeSubsurfaceScattering: 150,
    bpy.types.ShaderNodeTangent: 150,
    bpy.types.ShaderNodeTexBrick: 150,
    bpy.types.ShaderNodeTexMusgrave: 150,
    bpy.types.ShaderNodeTexSky: 150,
    bpy.types.ShaderNodeTexWave: 150,
    bpy.types.ShaderNodeUVMap: 150,
    bpy.types.ShaderNodeWavelength: 150,
    bpy.types.TextureNodeBricks: 150,
    bpy.types.TextureNodeHueSaturation: 150,
    bpy.types.TextureNodeOutput: 150,
    bpy.types.CompositorNodeImage: 240,
    bpy.types.ShaderNodeBsdfHairPrincipled: 240,
    bpy.types.ShaderNodeBsdfPrincipled: 240,
    bpy.types.ShaderNodeRGBCurve: 240,
    bpy.types.ShaderNodeVectorCurve: 240,
    bpy.types.ShaderNodeTexEnvironment: 240,
    bpy.types.ShaderNodeTexImage: 240,
    bpy.types.ShaderNodeValToRGB: 240,
    bpy.types.ShaderNodeVolumePrincipled: 240,
    bpy.types.TextureNodeCurveRGB: 240,
    bpy.types.TextureNodeCurveTime: 240,
    bpy.types.TextureNodeValToRGB: 240,
}

NODE_DEFAULTS = {
    bpy.types.ShaderNodeOutputMaterial: { 'target': 'ALL' },
    bpy.types.ShaderNodeMath: { 'use_clamp': False },
    bpy.types.ShaderNodeVectorMath: {},
    bpy.types.ShaderNodeMixRGB: { 'use_alpha': False, 'use_clamp': False },
    bpy.types.ShaderNodeRGBCurve: {
        'mapping': {
            'tone': 'STANDARD',
            'use_clip': True,
            'clip_min_x': 0.0,
            'clip_min_y': 0.0,
            'clip_max_x': 1.0,
            'clip_max_y': 1.0,
            'extend': 'EXTRAPOLATED',
            'black_level': Color((0.0, 0.0, 0.0)),
            'white_level': Color((1.0, 1.0, 1.0)),
            'curves.points': [ (0, 0), (1, 1) ],
        },
    },
    bpy.types.ShaderNodeVectorCurve: {
        'mapping': {
            'tone': 'STANDARD',
            'use_clip': True,
            'clip_min_x': -1.0,
            'clip_min_y': -1.0,
            'clip_max_x': 1.0,
            'clip_max_y': 1.0,
            'extend': 'EXTRAPOLATED',
            'black_level': Color((0.0, 0.0, 0.0)),
            'white_level': Color((1.0, 1.0, 1.0)),
            'curves.points': [ (-1, -1), (1, 1) ],
        },
    },
    bpy.types.ShaderNodeBsdfPrincipled: {
        'distribution': 'GGX',
        'subsurface_method': 'BURLEY'
    },
}

NODE_INPUT_DEFAULTS = {
    bpy.types.ShaderNodeOutputMaterial: { 'Displacement': (0, 0, 0) },
    bpy.types.ShaderNodeMath: { 1: 0.5, 2: 0.0 },
    bpy.types.ShaderNodeVectorMath: { 1: (0,0,0), 2: (0,0,0), 'Scale':1 },
    bpy.types.ShaderNodeMapRange: { 'Steps': 4 },
    bpy.types.ShaderNodeRGBCurve: { 'Fac': 1 },
    bpy.types.ShaderNodeVectorCurve: { 'Fac': 1 },
    bpy.types.ShaderNodeBsdfPrincipled: {
        'Base Color': (0.800000011920929, 0.800000011920929, 0.800000011920929, 1.0),
        'Subsurface': 0, 'Metallic': 0, 'Roughness': 0.5,
        'Subsurface Radius': (1.0, 0.20000000298023224, 0.10000000149011612),
        'Subsurface Color': (0.800000011920929, 0.800000011920929, 0.800000011920929, 1.0),
        'Specular': 0.5, 'Specular Tint': 0,
        'Anisotropic': 0, 'Anisotropic Rotation': 0,
        'Sheen': 0, 'Sheen Tint': 0.5,
        'Clearcoat': 0, 'Clearcoat Roughness': 0.029999999329447746,
        'IOR': 1.4500000476837158,
        'Transmission': 0, 'Transmission Roughness': 0,
        'Emission': (0, 0, 0, 1), 'Emission Strength': 1, 'Alpha': 1,
        'Normal': (0, 0, 0), 'Clearcoat Normal': (0, 0, 0),
        'Tangent': (0, 0, 0),
    },
}

def get_property_value(obj, name):
    value = getattr(obj, name, None)
    if isinstance(value, bpy_prop_array):
        value = tuple(value)
    return value

def get_socket_id(slist, socket):
    if sum(1 for s in slist if s.name == socket.name) > 1:
        for i, s in enumerate(slist):
            if s == socket:
                return i
        else:
            raise KeyError
    else:
        return socket.name

def generate_properties(prefix, obj, base_class, force=set(), *, block=set(), defaults=None):
    if base_class:
        block_props = set(prop.identifier for prop in base_class.bl_rna.properties)
    else:
        block_props = {'rna_type'}

    block_props = (block_props - set(force)) | block

    lines = []

    for prop in type(obj).bl_rna.properties:
        if prop.identifier in block_props:
            continue

        cur_value = get_property_value(obj, prop.identifier)

        if isinstance(cur_value, CurveMapping):
            lines += generate_curve_mapping(
                f'{prefix}.{prop.identifier}', cur_value,
                defaults.get(prop.identifier, None) if defaults else None,
            )
            continue

        if not prop.is_readonly:
            if isinstance(cur_value, bpy_struct):
                if isinstance(cur_value, NodeTree):
                    lines.append('%s.%s = bpy.data.node_groups[%r]' % (prefix, prop.identifier, cur_value.name))
                continue

            if defaults is not None:
                if cur_value == defaults.get(prop.identifier):
                    continue
            else:
                if hasattr(prop, 'default'):
                    if cur_value == get_property_value(prop, 'default'):
                        continue
                if hasattr(prop, 'default_array'):
                    if cur_value == get_property_value(prop, 'default_array'):
                        continue

            lines.append('%s.%s = %r' % (prefix, prop.identifier, cur_value))
    return lines

def generate_curve_mapping(prefix, mapping, defaults):
    lines = generate_properties(prefix, mapping, None, defaults=defaults)

    changed = False

    for i, curve in enumerate(mapping.curves):
        ptlines = []

        for i, pt in enumerate(curve.points):
            if i < 2:
                if not defaults or tuple(pt.location) != defaults['curves.points'][i]:
                    ptlines.append(f'points[{i}].location = ({pt.location.x}, {pt.location.y})')
            else:
                ptlines.append(f'points.new({pt.location.x}, {pt.location.y})')

            if pt.handle_type != 'AUTO':
                ptlines.append(f"points[{i}].handle_type = '{pt.handle_type}'")

        if ptlines:
            lines.append(f'points = {prefix}.curves[{i}].points')
            lines += ptlines
            changed = True

    if changed:
        lines.append(f'{prefix}.update()')

    return lines

def generate_socket(list_name, socket, with_properties=True):
    lines = [
        'socket = %s.new(%r,%r)' % (list_name, socket.bl_socket_idname, socket.name)
    ]
    if with_properties:
        lines += generate_properties('socket', socket, NodeSocketInterface, {'hide_value'}, defaults={'hide_value':False})
    return lines

def generate_node(node, links_in):
    lines = [
        'nodes[%r] = node = node_tree.nodes.new(%r)' % (node.name, type(node).bl_rna.identifier),
        'node.name = %r' % (node.name),
        'node.location = (%d, %d)' % (round(node.location.x), round(node.location.y)),
    ]

    lines += generate_properties(
        'node', node, Node,
        {'label','width','height','hide','use_custom_color'},
        defaults={
            'label':'', 'hide':False, 'use_custom_color':False,
            'width': NODE_DEFAULT_WIDTH.get(type(node), 140), 'height': 100,
            **NODE_DEFAULTS.get(type(node), {}),
        },
        block={'is_active_output'},
    )
    if node.use_custom_color:
        lines.append('node.color = %r' % (get_property_value(node, 'color')))
    socket_defaults = NODE_INPUT_DEFAULTS.get(type(node), {})
    for i, socket in enumerate(node.inputs):
        if socket not in links_in:
            val = get_property_value(socket, 'default_value')
            if val is not None:
                if socket.name in socket_defaults and val == socket_defaults[socket.name]:
                    continue
                if i in socket_defaults and val == socket_defaults[i]:
                    continue
                lines.append('node.inputs[%r].default_value = %r' % (get_socket_id(node.inputs, socket), val))
    return lines

def generate_script(node_tree):
    lines = []

    for socket in node_tree.inputs:
        lines += generate_socket('node_tree.inputs', socket)
    for socket in node_tree.outputs:
        lines += generate_socket('node_tree.outputs', socket, with_properties=False)

    lines.append('')

    links_in = collections.defaultdict(set)
    links_out = collections.defaultdict(set)

    for link in node_tree.links:
        links_out[link.from_node.name].add(link.from_socket)
        links_in[link.to_node.name].add(link.to_socket)

    lines.append('nodes = {}')
    for node in node_tree.nodes:
        lines += generate_node(node, links_in[node.name])

    lines.append('')

    for node in node_tree.nodes:
        if node.parent:
            lines.append('nodes[%r].parent = nodes[%r]' % (node.name, node.parent.name))

    for link in node_tree.links:
        lines.append('node_tree.links.new(nodes[%r].outputs[%r],nodes[%r].inputs[%r])' % (
            link.from_node.name, get_socket_id(link.from_node.outputs, link.from_socket),
            link.to_node.name, get_socket_id(link.to_node.inputs, link.to_socket)
        ))

    code_name = re.sub(r'[^0-9a-zA-Z]', '_', node_tree.name)

    return [
        'import bpy',
        'from mathutils import Vector, Color, Euler',
        '',
        'def build_group_%s():' % (code_name),
        '\t# Generated by Nodes To Python',
        '\tnode_tree = bpy.data.node_groups.new(%r, %r)' % (node_tree.name, type(node_tree).bl_rna.identifier),
        *[('\t'+l if l else '') for l in lines],
        '\treturn node_tree',
        '',
        'if __name__ == "__main__":',
        '\tbuild_group_%s()' % (code_name),
    ]

class NODE_OT_generate_python_script(bpy.types.Operator):
    bl_label = "Generate Python Script"
    bl_description = "Create a python script that builds the currently active node group"
    bl_idname = "node.generate_python_script"
    bl_options = {'UNDO','REGISTER'}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'NODE_EDITOR' and space.edit_tree is not None

    def execute(self, context):
        node_tree = context.space_data.edit_tree
        script_name = 'generate_%s.py' % (node_tree.name)

        lines = generate_script(node_tree)

        text_block = bpy.data.texts.new(script_name)
        text_block.write('\n'.join(lines))
        return {'FINISHED'}

def add_menu(self, context):
    self.layout.separator()
    self.layout.operator(NODE_OT_generate_python_script.bl_idname)

def register():
    bpy.utils.register_class(NODE_OT_generate_python_script)
    bpy.types.NODE_MT_node.append(add_menu)

def unregister():
    bpy.utils.unregister_class(NODE_OT_generate_python_script)
    bpy.types.NODE_MT_node.remove(add_menu)

if __name__ == '__main__':
    register()
