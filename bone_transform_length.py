bl_info = {
    "name": "Copy/Paste Bone Length",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "Properties > Bone > Transform",
    "description": "Shows and allows copy & paste of bone length in properties.",
    "warning": "",
    "wiki_url": "",
    "category": "User Interface",
    }

import bpy

def get_length_bone(context):
    ob = context.object
    bone = context.bone

    if bone and ob:
        return ob.pose.bones[bone.name]
    elif context.edit_bone:
        return context.edit_bone

    return None

class WM_OT_copy_bone_length(bpy.types.Operator):
    bl_label = "Copy Bone Length"
    bl_description = "Copy bone length to clipboard"
    bl_idname = "ot.copy_bone_length"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return get_length_bone(context)

    def execute(self, context):
        bone = get_length_bone(context)
        context.window_manager.clipboard = str(bone.length)
        return {'FINISHED'}

def try_parse_length(strv):
    try:
        return max(0,float(strv))
    except ValueError:
        return 0

class WM_OT_paste_bone_length(bpy.types.Operator):
    bl_label = "Paste Bone Length"
    bl_description = "Paste bone length from clipboard"
    bl_idname = "ot.paste_bone_length"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        return context.edit_bone is not None

    def execute(self, context):
        bone = context.edit_bone
        val = try_parse_length(context.window_manager.clipboard)
        if val <= 0:
            return {'CANCELLED'}
        bone.length = val
        return {'FINISHED'}

def render_property(self, context):
    layout = self.layout
    bone = get_length_bone(context)

    if bone:
        row = layout.row()
        row.label(text="Length: %.5f" % (bone.length))
        row.operator(WM_OT_copy_bone_length.bl_idname, text="", icon="COPYDOWN", emboss=True)
        row.operator(WM_OT_paste_bone_length.bl_idname, text="", icon="PASTEDOWN", emboss=True)

def register():
    bpy.utils.register_class(WM_OT_copy_bone_length)
    bpy.utils.register_class(WM_OT_paste_bone_length)
    bpy.types.BONE_PT_transform.append(render_property)

def unregister():
    bpy.utils.unregister_class(WM_OT_copy_bone_length)
    bpy.utils.unregister_class(WM_OT_paste_bone_length)
    bpy.types.BONE_PT_transform.remove(render_property)

if __name__ == '__main__':
    register()
