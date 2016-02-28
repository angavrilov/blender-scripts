# Resets all Stretch To constraints in the selected armature.
# Useful for fixing things after applying scale.

import bpy

obj = bpy.context.scene.objects.active
arm = obj.data

for bone in arm.bones:
    pbone = obj.pose.bones[bone.name]
    for cons in pbone.constraints:
        if cons.type == 'STRETCH_TO':
            # length of 0 makes it auto-reset when it next updates
            cons.rest_length = 0
