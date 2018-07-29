bl_info = {
    "name": "Deform Slave Armature",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 79, 0),
    "location": "Search > Create Deform Slave Armature",
    "description": "Creates a copy of the armature deform bones bound to follow the original.",
    "warning": "",
    "wiki_url": "",
    "category": "Rigging",
    }

import bpy

def find_armature(obj):
    if obj:
        if obj.type == 'ARMATURE':
            return obj, None

        for mod in obj.modifiers:
            if mod.type == 'ARMATURE':
                return mod.object, mod

    return None, None

class ARMATURE_OT_create_deform_slave(bpy.types.Operator):
    bl_label = "Create Deform Slave Armature"
    bl_description = "Create a slave copy of the armature with only deform bones"
    bl_idname = "armature.create_deform_slave"
    bl_options = {'UNDO','REGISTER'}

    only_needed = bpy.props.BoolProperty(name='Only Needed Bones', description='When a mesh is active, only include bones actually necessary to deform it')

    @classmethod
    def poll(cls, context):
        arm, mod = find_armature(context.object)
        return arm is not None

    def execute(self, context):
        scene = context.scene
        arm, mod = find_armature(context.object)

        if mod and mod.use_vertex_groups and self.only_needed:
            vgset = set(context.object.vertex_groups.keys())
        else:
            vgset = None

        bpy.ops.object.mode_set(mode='OBJECT')

        # Duplicate and select the armature
        new_arm = arm.copy()
        new_arm.data = arm.data.copy()
        scene.objects.link(new_arm)

        for objt in scene.objects:
            objt.select = False
        new_arm.select = True
        scene.objects.active = new_arm

        bpy.ops.object.mode_set(mode='OBJECT')

        # Remove action
        new_arm.animation_data.action = None

        # Remove drivers
        for drv in new_arm.animation_data.drivers:
            new_arm.driver_remove(drv.data_path, drv.array_index)

        bpy.ops.object.mode_set(mode='EDIT')

        # Unparent all bones and disable B-Bones
        for bone in new_arm.data.edit_bones:
            bone.parent = None
            bone.bbone_segments = 1

        # Delete non-deform bones
        for bone in new_arm.data.edit_bones:
            if not bone.use_deform or (vgset and bone.name not in vgset):
                new_arm.data.edit_bones.remove(bone)

        bpy.ops.object.mode_set(mode='OBJECT')

        # Replace constraints with COPY_TRANSFORMS
        for bone in new_arm.pose.bones:
            for con in bone.constraints:
                bone.constraints.remove(con)

            bone.location = (0,0,0)
            bone.scale = (1,1,1)
            bone.rotation_quaternion = (1,0,0,0)
            bone.rotation_mode = 'QUATERNION'

            con = bone.constraints.new(type='COPY_TRANSFORMS')
            con.target = arm
            con.subtarget = bone.name

        # Replace the armature in the modifier if any
        if mod:
            mod.object = new_arm

        return {'FINISHED'}

def register():
    bpy.utils.register_class(ARMATURE_OT_create_deform_slave)

def unregister():
    bpy.utils.unregister_class(ARMATURE_OT_create_deform_slave)

if __name__ == '__main__':
    register()
