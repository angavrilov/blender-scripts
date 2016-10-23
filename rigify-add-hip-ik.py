import bpy
import rigify.utils
import mathutils
import math

from rigify.utils import copy_bone_simple, angle_on_plane, align_bone_x_axis, align_bone_z_axis
from rna_prop_ui import rna_idprop_ui_prop_get
from mathutils import Vector

ORG_THIGH = 'ORG-thigh.'
ORG_PELVIS = 'ORG-pelvis.'

MCH_HIPS = 'MCH-hips-ik'
MCH_DELTA = 'MCH-hips-ik-delta.'
MCH_IK_TGT = 'MCH-hips-ik-tgt'
MCH_IK_L_DIST = 'MCH-hips-ik-leg-L-dist'
MCH_IK_R_DIST = 'MCH-hips-ik-leg-R-dist'

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

def driver_var_cprop(drv,name,obj,bone,prop):
    var = drv.variables.new()
    var.name = name
    var.type = "SINGLE_PROP"
    var.targets[0].id = obj
    var.targets[0].data_path = obj.pose.bones[bone].path_from_id() + '["' + prop + '"]'

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

def process_edit(obj, spine_root_name):
    eb = obj.data.edit_bones
    org_hips = eb[spine_root_name]

    if MCH_HIPS not in eb:
        mch_hips = org_hips
        mch_hips.name = MCH_HIPS

        copy_bone_simple(obj, mch_hips.name, spine_root_name)

        org_hips = eb[spine_root_name]
        org_hips.use_deform = False

        for child in list(mch_hips.children):
            child.parent = org_hips

        mch_hips.layers = LAYER_MCH
        org_hips.parent = mch_hips
    else:
        mch_hips = eb[MCH_HIPS]

    org_thigh_l = midpoint_l = eb[ORG_THIGH+'L']
    org_thigh_r = midpoint_r = eb[ORG_THIGH+'R']
    #if ORG_PELVIS+'L' in eb:
    #    midpoint_l = eb[ORG_PELVIS+'L']
    #    midpoint_r = eb[ORG_PELVIS+'R']

    #midpoint = (Vector(midpoint_l.head) + Vector(midpoint_r.head))/2
    midpoint = mch_hips.head

    delta_l = get_or_create_mch(eb,MCH_DELTA+'L',mch_hips,org_thigh_l.head,midpoint)
    delta_r = get_or_create_mch(eb,MCH_DELTA+'R',mch_hips,org_thigh_r.head,midpoint)

    lencoeff = abs(midpoint[0] - org_thigh_l.head[0]) * 0.3

    ik_tgt = get_or_create_mch(eb,MCH_IK_TGT,delta_r,midpoint,midpoint+Vector((0,0,lencoeff)),True)

    end_l = midpoint + Vector((-lencoeff,0,org_thigh_l.length))
    leg_l_dist = get_or_create_mch(eb,MCH_IK_L_DIST,delta_l,midpoint,end_l,True)
    leg_l_dist.length = org_thigh_l.length
    leg_l_dist.use_inherit_scale = False
    align_bone_x_axis(obj, MCH_IK_L_DIST, Vector((1,0,0)))

    end_r = midpoint + Vector((2*(leg_l_dist.tail[0] - midpoint[0]),0,0))
    leg_r_dist = get_or_create_mch(eb,MCH_IK_R_DIST,leg_l_dist,leg_l_dist.tail,end_r,True)
    leg_r_dist.length = org_thigh_r.length
    leg_r_dist.use_inherit_scale = False
    align_bone_x_axis(obj, MCH_IK_R_DIST, Vector((1,0,0)))

    return {
        'pole_angle': pole_offset(leg_l_dist, leg_r_dist, leg_r_dist),
        'shin_length': eb['ORG-shin.L'].length,
        'thigh_length': org_thigh_l.length,
    }

def process_pose(obj, spine_root_name, info):
    pb = obj.pose.bones
    mch_hips = pb[MCH_HIPS]
    org_hips = pb[spine_root_name]
    delta_l = pb[MCH_DELTA+'L']
    delta_r = pb[MCH_DELTA+'R']
    dist_l = pb[MCH_IK_L_DIST]
    dist_r = pb[MCH_IK_R_DIST]
    ik_tgt = pb[MCH_IK_TGT]

    copy_properties(mch_hips, org_hips)

    for bone in pb:
        if bone.custom_shape_transform == mch_hips:
            bone.custom_shape_transform = org_hips

        for cons in bone.constraints:
            if getattr(cons,'subtarget',None) == MCH_HIPS:
                cons.subtarget = spine_root_name

    # MCH-hips-ik-delta.L
    cons = constraint_named(delta_l,'pole_location','COPY_LOCATION')
    target_bone(cons,obj,'knee_target.ik.L')

    cons = constraint_named(delta_l,'foot_distance','LIMIT_DISTANCE')
    target_bone(cons,obj,'MCH-foot.L.001')
    cons.limit_mode = 'LIMITDIST_ONSURFACE'
    cons.target_space = cons.owner_space = 'POSE'

    drv = replace_driver(cons,'distance')
    driver_var_cprop(drv,'stretch_length',obj,'foot.ik.L','stretch_length')
    driver_expression(drv,'stretch_length*%f'%(info['shin_length']))

    # MCH-hips-ik-delta.R
    cons = constraint_named(delta_r,'pole_location','COPY_LOCATION')
    target_bone(cons,obj,'knee_target.ik.R')

    cons = constraint_named(delta_r,'foot_distance','LIMIT_DISTANCE')
    target_bone(cons,obj,'MCH-foot.R.001')
    cons.limit_mode = 'LIMITDIST_ONSURFACE'
    cons.target_space = cons.owner_space = 'POSE'

    drv = replace_driver(cons,'distance')
    driver_var_cprop(drv,'stretch_length',obj,'foot.ik.R','stretch_length')
    driver_expression(drv,'stretch_length*%f'%(info['shin_length']))

    # MCH-hips-ik-leg-L-dist
    replace_driver_single_cprop(dist_l,'scale',0,obj,'foot.ik.L','stretch_length')
    replace_driver_single_cprop(dist_l,'scale',1,obj,'foot.ik.L','stretch_length')
    replace_driver_single_cprop(dist_l,'scale',2,obj,'foot.ik.L','stretch_length')

    # MCH-hips-ik-leg-R-dist
    replace_driver_single_cprop(dist_r,'scale',0,obj,'foot.ik.R','stretch_length')
    replace_driver_single_cprop(dist_r,'scale',1,obj,'foot.ik.R','stretch_length')
    replace_driver_single_cprop(dist_r,'scale',2,obj,'foot.ik.R','stretch_length')

    cons = constraint_named(dist_r,'IK','IK')
    cons.chain_count = 2
    cons.use_stretch = False
    target_bone(cons,obj,MCH_IK_TGT)
    pole_target_bone(cons,obj,MCH_HIPS)
    cons.pole_angle = info['pole_angle']

    # Pole variables
    for bone in [pb['knee_target.ik.R'], pb['knee_target.ik.L']]:
        bone['hips_ik'] = 0.0
        prop = rna_idprop_ui_prop_get(bone, 'hips_ik')
        prop["min"] = 0.0
        prop["max"] = 1.0
        prop["soft_min"] = 0.0
        prop["soft_max"] = 1.0
        prop["description"] = 'Move body to keep the knee at the target.'

    # ORG-hips
    # LR
    cons = constraint_named(org_hips,'location_ik_LR','COPY_LOCATION')
    target_bone(cons,obj,MCH_IK_R_DIST)

    drv = replace_driver(cons,'influence')
    driver_var_cprop(drv,'ikl',obj,'knee_target.ik.L','hips_ik')
    driver_var_cprop(drv,'ikr',obj,'knee_target.ik.R','hips_ik')
    driver_expression(drv,'min(ikl,ikr)')

    # L
    cons = constraint_named(org_hips,'distance_ik_L','LIMIT_DISTANCE')
    target_bone(cons,obj,MCH_DELTA+'L')
    cons.head_tail = 1.0
    cons.limit_mode = 'LIMITDIST_ONSURFACE'
    cons.target_space = cons.owner_space = 'POSE'

    drv = replace_driver(cons,'distance')
    driver_var_cprop(drv,'stretch_length',obj,'foot.ik.L','stretch_length')
    driver_expression(drv,'stretch_length*%f'%(info['thigh_length']))

    drv = replace_driver(cons,'influence')
    driver_var_cprop(drv,'ikl',obj,'knee_target.ik.L','hips_ik')
    driver_var_cprop(drv,'ikr',obj,'knee_target.ik.R','hips_ik')
    driver_expression(drv,'(ikl-ikr)/(1-ikr) if ikr < ikl else 0')

    # R
    cons = constraint_named(org_hips,'distance_ik_R','LIMIT_DISTANCE')
    target_bone(cons,obj,MCH_DELTA+'R')
    cons.head_tail = 1.0
    cons.limit_mode = 'LIMITDIST_ONSURFACE'
    cons.target_space = cons.owner_space = 'POSE'

    drv = replace_driver(cons,'distance')
    driver_var_cprop(drv,'stretch_length',obj,'foot.ik.R','stretch_length')
    driver_expression(drv,'stretch_length*%f'%(info['thigh_length']))

    drv = replace_driver(cons,'influence')
    driver_var_cprop(drv,'ikl',obj,'knee_target.ik.L','hips_ik')
    driver_var_cprop(drv,'ikr',obj,'knee_target.ik.R','hips_ik')
    driver_expression(drv,'(ikr-ikl)/(1-ikl) if ikl < ikr else 0')

def process(obj):
    if obj.type != 'ARMATURE':
        raise "Not armature"

    bpy.ops.object.mode_set(mode ='OBJECT')

    spine_root_name = None

    for bone in obj.pose.bones:
        if bone.name.startswith('ORG-') and not bone.bone.use_connect:
            if  'rigify_type' in bone and bone['rigify_type'] == 'spine':
                spine_root_name = bone.name
                break
    else:
        raise "Cannot find rigify spine root bone"

    bpy.ops.object.mode_set(mode ='EDIT')

    info = process_edit(obj, spine_root_name)

    bpy.ops.object.mode_set(mode ='OBJECT')

    process_pose(obj, spine_root_name, info)

process(bpy.context.scene.objects.active)
