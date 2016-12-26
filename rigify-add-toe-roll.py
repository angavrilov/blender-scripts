# Adds an option to roll rigify foot forward on the tip of the toe.
# Also, if MCH-foot.aux?.L.001 exist, creates alternate roll rigs for different height of heels.

import bpy
import rigify.utils
import mathutils
import math

from rigify.utils import copy_bone_simple, angle_on_plane, align_bone_x_axis, align_bone_z_axis
from rna_prop_ui import rna_idprop_ui_prop_get
from mathutils import Vector

ORG_THIGH = 'ORG-thigh.'
ORG_PELVIS = 'ORG-pelvis.'

def one_layer(idx):
    return [i == idx for i in range(0,32)]

LAYER_MCH = one_layer(30)

def get_or_create_mch(eb,name,parent,head,tail,connect=False):
    if name not in eb:
        bone = eb.new(name)
        bone.head = head
        bone.tail = tail
        bone.roll = 0
        bone.use_deform = False
        bone.layers = LAYER_MCH
        bone.parent = parent
        if connect:
            bone.use_connect = True
        return bone
    else:
        return eb[name]

def copy_properties(pose_bone_1, pose_bone_2):
    for key in pose_bone_1.keys():
        if key != "_RNA_UI":
            prop1 = rna_idprop_ui_prop_get(pose_bone_1, key, create=False)
            pose_bone_2[key] = pose_bone_1[key]
            if prop1:
                prop2 = rna_idprop_ui_prop_get(pose_bone_2, key, create=True)
                for key in prop1.keys():
                    prop2[key] = prop1[key]

def constraint_named(pbone,name,type):
    if name in pbone.constraints:
        return pbone.constraints[name]
    else:
        cons = pbone.constraints.new(type)
        cons.name = name
        return cons

def target_bone(cons,obj,bone):
    cons.target = obj
    cons.subtarget = bone

def pole_target_bone(cons,obj,bone):
    cons.pole_target = obj
    cons.pole_subtarget = bone

def replace_driver(obj,name,idx=-1):
    obj.driver_remove(name,idx)
    return obj.driver_add(name,idx).driver

def driver_var_cprop(drv,name,obj,bone,prop,quote=True):
    var = drv.variables.new()
    var.name = name
    var.type = "SINGLE_PROP"
    var.targets[0].id = obj
    var.targets[0].data_path = obj.pose.bones[bone].path_from_id() + (('["%s"]' if quote else '.%s') % (prop))

def driver_expression(drv,expr):
    drv.type = 'SCRIPTED'
    drv.expression = expr

def replace_driver_single_cprop(obj,name,idx,tgt,bone,prop):
    drv = replace_driver(obj,name,idx)
    driver_var_cprop(drv,prop,tgt,bone,prop)
    drv.type = 'AVERAGE'

def pole_offset(first_bone, last_bone, pole):
    plane = (last_bone.tail - first_bone.head).normalized()
    vec1 = first_bone.x_axis.normalized()
    vec2 = (pole.head - first_bone.head).normalized()
    return angle_on_plane(plane, vec1, vec2)


ORG_TOE = 'ORG-toe.%s'
FOOT_IK = 'foot.ik.%s'
FOOT_ROLL = 'foot_roll.ik.%s'
FOOT_ROCKER_01 = 'MCH-foot.%s.rocker.01'
FOOT_ROCKER_02 = 'MCH-foot.%s.rocker.02'
FOOT_ROLL_01 = 'MCH-foot.%s.roll.01'
FOOT_ROLL_02 = 'MCH-foot.%s.roll.02'
FOOT_ROLL_01b = 'MCH-foot.%s.roll.01b'
TOE_SOCKET_1 = 'MCH-toe.%s.socket1'

FOOT_IKBASE = 'MCH-foot.%s.001'
FOOT_IKBASE_AUX = 'MCH-foot.%s'

def process_edit(obj):
    eb = obj.data.edit_bones

    for side in ['L', 'R']:
        org_toe = eb[ORG_TOE % (side)]

        foot_ik = eb[FOOT_IK % (side)]
        foot_roll = eb[FOOT_ROLL % (side)]
        foot_rocker_01 = eb[FOOT_ROCKER_01 % (side)]
        foot_rocker_02 = eb[FOOT_ROCKER_02 % (side)]
        foot_roll_01 = eb[FOOT_ROLL_01 % (side)]
        foot_roll_02 = eb[FOOT_ROLL_02 % (side)]
        foot_ikbase = eb[FOOT_IKBASE % (side)]
        toe_socket_1 = eb[TOE_SOCKET_1 % (side)]

        foot_roll_01b_name = FOOT_ROLL_01b % (side)

        ikbase_tail = foot_ikbase.tail
        toe_tail = org_toe.tail
        roll_x = ikbase_tail.x

        if foot_roll_01b_name not in eb:
            toe_pos = Vector((ikbase_tail.x, toe_tail.y, foot_roll_01.head.z))
            foot_roll_01b = get_or_create_mch(eb, foot_roll_01b_name, foot_roll_01, toe_pos, ikbase_tail)

            foot_roll_01.tail = toe_pos
            foot_roll_02.parent = foot_roll_01b
            toe_socket_1.parent = foot_roll_01b
        else:
            foot_roll_01b = eb[foot_roll_01b_name]

        foot_rocker_01.tail.y = foot_rocker_01.head.y
        foot_rocker_01.tail.z = foot_rocker_01.head.z
        foot_rocker_01.roll = 0

        foot_rocker_02.head = foot_rocker_01.tail
        foot_rocker_02.tail = foot_rocker_01.head
        foot_rocker_02.roll = 0

        foot_roll_02.head = foot_roll_01b.tail = ikbase_tail

        for bone in [foot_roll_01, foot_roll_01b, foot_roll_02]:
            bone.head.x = bone.tail.x = roll_x
            bone.roll = 0

        # High heel mode
        for i in range(1,5):
            auxside = 'aux%d.%s' % (i,side)
            foot_ikbase_aux_name = FOOT_IKBASE_AUX % (auxside)

            if foot_ikbase_aux_name not in eb:
                break

            foot_ikbase_aux = eb[foot_ikbase_aux_name]
            foot_ikbase_aux.head = foot_ikbase.head
            foot_ikbase_aux.length = foot_ikbase.length

            delta = Vector(foot_ikbase_aux.tail) - Vector(foot_ikbase.tail)
            delta_z = Vector((0,0,delta.z))

            rocker_a = delta_z + foot_rocker_01.head
            rocker_b = delta_z + foot_rocker_01.tail

            foot_rocker_01_aux = get_or_create_mch(eb, FOOT_ROCKER_01 % (auxside), foot_ik, rocker_a, rocker_b)
            foot_rocker_02_aux = get_or_create_mch(eb, FOOT_ROCKER_02 % (auxside), foot_rocker_01_aux, rocker_b, rocker_a)

            roll_a = delta_z + foot_roll_01.head
            roll_b = delta + foot_roll_01.tail

            foot_roll_01_aux = get_or_create_mch(eb, FOOT_ROLL_01 % (auxside), foot_rocker_02_aux, roll_a, roll_b)
            foot_roll_01b_aux = get_or_create_mch(eb, FOOT_ROLL_01b % (auxside), foot_roll_01_aux, roll_b, foot_ikbase_aux.tail)
            foot_roll_02_aux = get_or_create_mch(eb, FOOT_ROLL_02 % (auxside), foot_roll_01b_aux, foot_ikbase_aux.tail, roll_a)

            foot_ikbase_aux.parent = foot_roll_02_aux

    return {}

def assign_roll_drivers(obj, foot_rocker_01, foot_rocker_02, foot_roll_01, foot_roll_01b, foot_roll_02, foot_roll_name):
    for bone in [foot_rocker_01, foot_rocker_02, foot_roll_01, foot_roll_01b, foot_roll_02]:
        bone.rotation_mode = 'XYZ'
        bone.lock_location = (True,True,True)
        bone.lock_rotation = (True,True,True)
        bone.lock_scale = (True,True,True)

    drv = replace_driver(foot_rocker_01,'rotation_euler',0)
    driver_var_cprop(drv,'var',obj,foot_roll_name,'rotation_euler.y',False)
    driver_expression(drv,'max(0,-var)')

    drv = replace_driver(foot_rocker_02,'rotation_euler',0)
    driver_var_cprop(drv,'var',obj,foot_roll_name,'rotation_euler.y',False)
    driver_expression(drv,'max(0,var)')

    drv = replace_driver(foot_roll_01,'rotation_euler',0)
    driver_var_cprop(drv,'var',obj,foot_roll_name,'rotation_euler.x',False)
    driver_expression(drv,'max(0,-var)')

    drv = replace_driver(foot_roll_01b,'rotation_euler',0)
    driver_var_cprop(drv,'var',obj,foot_roll_name,'rotation_euler.x',False)
    driver_var_cprop(drv,'straight',obj,foot_roll_name,'straight_toe')
    driver_expression(drv,'max(0,var*straight)')

    drv = replace_driver(foot_roll_02,'rotation_euler',0)
    driver_var_cprop(drv,'var',obj,foot_roll_name,'rotation_euler.x',False)
    driver_var_cprop(drv,'straight',obj,foot_roll_name,'straight_toe')
    driver_expression(drv,'max(0,var*(1-straight))')

def process_pose(obj, info):
    pb = obj.pose.bones

    for side in ['L', 'R']:
        org_toe = pb[ORG_TOE % (side)]

        foot_ik_name = FOOT_IK % (side)
        foot_ik = pb[foot_ik_name]

        foot_roll_name = FOOT_ROLL % (side)
        foot_roll = pb[foot_roll_name]

        foot_rocker_01 = pb[FOOT_ROCKER_01 % (side)]
        foot_rocker_02 = pb[FOOT_ROCKER_02 % (side)]
        foot_roll_01 = pb[FOOT_ROLL_01 % (side)]
        foot_roll_01b = pb[FOOT_ROLL_01b % (side)]
        foot_roll_02 = pb[FOOT_ROLL_02 % (side)]
        foot_ikbase = pb[FOOT_IKBASE % (side)]

        # Straight toe property
        foot_roll['straight_toe'] = 0.0
        prop = rna_idprop_ui_prop_get(foot_roll, 'straight_toe')
        prop["min"] = 0.0
        prop["max"] = 1.0
        prop["soft_min"] = 0.0
        prop["soft_max"] = 1.0
        prop["description"] = 'Forward roll pivots on toe tip.'

        assign_roll_drivers(obj, foot_rocker_01, foot_rocker_02, foot_roll_01, foot_roll_01b, foot_roll_02, foot_roll_name)

        # High heel mode
        auxprop = None

        for i in range(1,5):
            auxside = 'aux%d.%s' % (i,side)
            foot_ikbase_aux_name = FOOT_IKBASE_AUX % (auxside)

            if foot_ikbase_aux_name not in pb:
                break

            if auxprop is None:
                foot_ik['heel_shape'] = 0
                auxprop = rna_idprop_ui_prop_get(foot_ik, 'heel_shape')
                auxprop["min"] = 0
                auxprop["soft_min"] = 0
                auxprop["description"] = 'High heel mode.'

            auxprop["max"] = i
            auxprop["soft_max"] = i

            foot_rocker_01_aux = pb[FOOT_ROCKER_01 % (auxside)]
            foot_rocker_02_aux = pb[FOOT_ROCKER_02 % (auxside)]
            foot_roll_01_aux = pb[FOOT_ROLL_01 % (auxside)]
            foot_roll_01b_aux = pb[FOOT_ROLL_01b % (auxside)]
            foot_roll_02_aux = pb[FOOT_ROLL_02 % (auxside)]
            foot_ikbase_aux = pb[foot_ikbase_aux_name]

            assign_roll_drivers(obj, foot_rocker_01_aux, foot_rocker_02_aux, foot_roll_01_aux, foot_roll_01b_aux, foot_roll_02_aux, foot_roll_name)

            cons = constraint_named(foot_ikbase,'heel_shape.%d' % (i),'COPY_TRANSFORMS')
            target_bone(cons,obj,foot_ikbase_aux_name)

            drv = replace_driver(cons,'influence')
            driver_var_cprop(drv,'var',obj,foot_ik_name,'heel_shape')
            driver_expression(drv,'1 if var == %d else 0' % (i))


def process(obj):
    if obj.type != 'ARMATURE':
        raise "Not armature"

    bpy.ops.object.mode_set(mode='EDIT')

    info = process_edit(obj)

    bpy.ops.object.mode_set(mode='OBJECT')

    process_pose(obj, info)

process(bpy.context.scene.objects.active)
