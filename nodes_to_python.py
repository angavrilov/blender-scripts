bl_info = {
    "name": "Nodes To Python",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 90, 0),
    "location": "Node > Generate Python Script",
    "description": "Generates a python script that creates the current node layout.",
    "warning": "",
    "wiki_url": "",
    "category": "Development",
    }

import bpy
import collections

from bpy.types import bpy_struct, bpy_prop_array, NodeSocketInterface, Node, NodeTree

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

def generate_properties(prefix, obj, base_class, force={}, *, defaults=None):
    block_props = set(prop.identifier for prop in base_class.bl_rna.properties) - set(force)
    lines = []

    for prop in type(obj).bl_rna.properties:
        if prop.identifier not in block_props and not prop.is_readonly:
            cur_value = get_property_value(obj, prop.identifier)

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

def generate_socket(list_name, socket):
    lines = [
        'socket = %s.new(%r,%r)' % (list_name, socket.bl_socket_idname, socket.name)
    ]
    lines += generate_properties('socket', socket, NodeSocketInterface, {'hide_value'}, defaults={'hide_value':False})
    return lines

def generate_node(node, links_in):
    lines = [
        'nodes[%r] = node = node_tree.nodes.new(%r)' % (node.name, type(node).bl_rna.identifier),
        'node.name = %r' % (node.name),
    ]
    lines += generate_properties(
        'node', node, Node,
        {'label','location','width','height','use_custom_color'},
        defaults={'label':'', 'use_custom_color':False}
    )
    if node.use_custom_color:
        lines.append('node.color = %r' % (get_property_value(node, 'color')))
    for socket in node.inputs:
        if socket.identifier not in links_in:
            val = get_property_value(socket, 'default_value')
            if val is not None:
                lines.append('node.inputs[%r].default_value = %r' % (get_socket_id(node.inputs, socket), val))
    return lines

def generate_script(node_tree):
    lines = []

    for socket in node_tree.inputs:
        lines += generate_socket('node_tree.inputs', socket)
    for socket in node_tree.outputs:
        lines += generate_socket('node_tree.outputs', socket)

    lines.append('')

    links_in = collections.defaultdict(set)
    links_out = collections.defaultdict(set)

    for link in node_tree.links:
        links_out[link.from_node.name].add(link.from_socket.identifier)
        links_in[link.to_node.name].add(link.to_socket.identifier)

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

    return [
        'import bpy',
        'from mathutils import Vector, Color, Euler',
        '',
        'def generate_nodes(node_tree):',
        *[('\t'+l if l else '') for l in lines],
        '\treturn nodes',
        '',
        'def generate_group():',
        '\ttree = bpy.data.node_groups.new(%r, %r)' % (node_tree.name, type(node_tree).bl_rna.identifier),
        '\tgenerate_nodes(tree)',
        '\treturn tree',
        '',
        'if __name__ == "__main__":',
        '\tgenerate_group()'
    ]

class NODE_OT_generate_python_script(bpy.types.Operator):
    bl_label = "Generate Python Script"
    bl_description = "Create a slave copy of the armature with only deform bones"
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
