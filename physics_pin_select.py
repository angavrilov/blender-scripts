bl_info = {
    "name": "Pin Physics Objects",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 75, 0),
    "location": "Properties > Physics > Object Dropdown",
    "description": "A dropdown with only objects with caches appears at the top of the physics tab when pinned.",
    "warning": "",
    "wiki_url": "",
    "category": "User Interface",
    }

import bpy

class SPACE_OT_pin_physics_object(bpy.types.Operator):
    bl_label = "Pin Physics Object"
    bl_idname = "space.pin_physics_object"
    bl_options = {'INTERNAL'}

    @classmethod
    def poll(cls, context):
        objname = context.scene.physics_pin_object
        return context.space_data.use_pin_id and objname != "" and objname in bpy.data.objects

    def execute(self, context):
        context.space_data.pin_id = bpy.data.objects[context.scene.physics_pin_object]
        return {'FINISHED'}

def draw_pin_selector(self, context):
    layout = self.layout
    space = context.space_data

    if space.use_pin_id:
        row = layout.row()
        row.prop_search(context.scene, "physics_pin_object", context.scene, "physics_pin_object_list", text='', icon='OBJECT_DATA')
        row.operator("space.pin_physics_object", text="", icon="UNPINNED")

def has_physics(obj):
    if len(obj.particle_systems) > 0:
        return True
    for mod in obj.modifiers:
        if (isinstance(mod, bpy.types.ClothModifier) or
            isinstance(mod, bpy.types.SoftBodyModifier) or
            isinstance(mod, bpy.types.DynamicPaintModifier) or
            isinstance(mod, bpy.types.SmokeModifier)):
            return True
    return False

def upd_handler(scene):
    oldpin = scene.physics_pin_object
    pinstr = ""
    scene.physics_pin_object_list.clear()
    for ob in bpy.data.objects:
        if has_physics(ob):
            item = scene.physics_pin_object_list.add()
            item.name = ob.name
            if (pinstr == "" or ob.name == oldpin):
                pinstr = ob.name
    scene.physics_pin_object = pinstr

def register():
    bpy.utils.register_class(SPACE_OT_pin_physics_object)
    bpy.types.Scene.physics_pin_object = bpy.props.StringProperty(options={'HIDDEN','SKIP_SAVE'})
    bpy.types.Scene.physics_pin_object_list = bpy.props.CollectionProperty(type=bpy.types.PropertyGroup, options={'HIDDEN','SKIP_SAVE'})
    bpy.types.PHYSICS_PT_add.prepend(draw_pin_selector)
    bpy.app.handlers.scene_update_post.append(upd_handler)

def unregister():
    bpy.utils.unregister_class(SPACE_OT_pin_physics_object)
    del bpy.types.Scene.physics_pin_object
    del bpy.types.Scene.physics_pin_object_list
    bpy.types.PHYSICS_PT_add.remove(draw_pin_selector)
    bpy.app.handlers.scene_update_post.remove(upd_handler)

if __name__ == '__main__':
    register()
