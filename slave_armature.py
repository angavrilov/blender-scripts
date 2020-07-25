bl_info = {
    "name": "Deform Slave Armature",
    "author": "angavrilov",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "Add > Armature > Deform Slave",
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

    only_needed: bpy.props.BoolProperty(name='Only Needed Bones', description='When a mesh is active, only include bones actually necessary to deform it')
    with_bbones: bpy.props.BoolProperty(name='With B-Bones', default=False, description='Keep B-Bones in the generated armature')

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
        context.collection.objects.link(new_arm)

        for objt in scene.objects:
            objt.select_set(False)
        new_arm.select_set(True)
        context.view_layer.objects.active = new_arm

        bpy.ops.object.mode_set(mode='OBJECT')

        # Remove action
        new_arm.animation_data_clear()
        new_arm.data.animation_data_clear()

        # Remove constraints
        for bone in new_arm.pose.bones:
            for con in bone.constraints:
                bone.constraints.remove(con)

        bpy.ops.object.mode_set(mode='EDIT')

        # Unparent all bones and disable B-Bones
        for bone in new_arm.data.edit_bones:
            # Disable B-Bones unless needed
            if not self.with_bbones:
                bone.bbone_segments = 1
            elif bone.parent and bone.use_connect:
                # If keeping B-Bones, replace parenting with explicit handles
                if bone.bbone_segments > 1 and bone.bbone_handle_type_start == 'AUTO':
                    bone.bbone_handle_type_start = 'ABSOLUTE'
                    bone.bbone_custom_handle_start = bone.parent

                if bone.parent.bbone_segments > 1 and bone.parent.bbone_handle_type_end == 'AUTO':
                    bone.parent.bbone_handle_type_end = 'ABSOLUTE'
                    bone.parent.bbone_custom_handle_end = bone

            bone.parent = None

        # Delete non-deform bones
        include_set = set()

        for bone in new_arm.data.edit_bones:
            if bone.use_deform and (not vgset or bone.name in vgset):
                include_set.add(bone.name)

                # Also include B-Bone handle bones
                if bone.bbone_segments > 1:
                    if bone.bbone_custom_handle_start:
                        include_set.add(bone.bbone_custom_handle_start.name)
                    if bone.bbone_custom_handle_end:
                        include_set.add(bone.bbone_custom_handle_end.name)

        for bone in new_arm.data.edit_bones:
            if bone.name not in include_set:
                new_arm.data.edit_bones.remove(bone)

        bpy.ops.object.mode_set(mode='OBJECT')

        # Replace constraints with COPY_TRANSFORMS
        for bone in new_arm.pose.bones:
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

def add_menu(self, context):
    self.layout.operator(ARMATURE_OT_create_deform_slave.bl_idname, icon='CON_ARMATURE', text='Deform Slave')

def register():
    bpy.utils.register_class(ARMATURE_OT_create_deform_slave)
    bpy.types.VIEW3D_MT_armature_add.append(add_menu)

def unregister():
    bpy.utils.unregister_class(ARMATURE_OT_create_deform_slave)
    bpy.types.VIEW3D_MT_armature_add.remove(add_menu)

if __name__ == '__main__':
    register()
