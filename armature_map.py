
import bpy
import mathutils
import math

def make_layer_table(layers):
    layertbl='<TABLE BORDER="0" CELLBORDER="1" CELLPADDING="0" CELLSPACING="0" WIDTH="132" HEIGHT="16" FIXEDSIZE="TRUE">'
    for row in range(0,32,16):
        layertbl += '<TR>'
        for cspan in range(0,16,8):
            for col in range(0,8):
                color = 'black' if layers[row+cspan+col] else 'white'
                layertbl += '<TD FIXEDSIZE="TRUE" WIDTH="8" HEIGHT="8" BGCOLOR="%s"></TD>' % (color)
            if cspan == 0:
                layertbl += '<TD FIXEDSIZE="TRUE" WIDTH="4" HEIGHT="8" BORDER="0"></TD>'
        layertbl += '</TR>'
    layertbl += '</TABLE>'
    return layertbl

constraint_names = {
    'CAMERA_SOLVER': 'Cmra Slv',
    'FOLLOW_TRACK': 'Flw Trk',
    'OBJECT_SOLVER': 'Obj Slv',
    'COPY_LOCATION': 'Cpy Loc',
    'COPY_ROTATION': 'Cpy Rot',
    'COPY_SCALE': 'Cpy Scl',
    'COPY_TRANSFORMS': 'Cpy Trf',
    'LIMIT_DISTANCE': 'Lim Dst',
    'LIMIT_LOCATION': 'Lim Loc',
    'LIMIT_ROTATION': 'Lim Rot',
    'LIMIT_SCALE': 'Lim Scl',
    'MAINTAIN_VOLUME': 'Mnt Vol',
    'TRANSFORM': 'Trnsf',
    'DAMPED_TRACK': 'Dmp Trk',
    'IK': 'IK',
    'LOCKED_TRACK': 'Lck Trk',
    'SPLINE_IK': 'Spline IK',
    'TRACK_TO': 'Trk To',
    'STRETCH_TO': 'Strch To',
    'ACTION': 'Act',
    'CHILD_OF': 'Chld Of',
    'FLOOR': 'Flr',
    'FOLLOW_PATH': 'F Path',
    'PIVOT': 'Pvt',
    'RIGID_BODY_JOINT': 'Rg Bdy',
    'SHRINKWRAP': 'Srnk Wrp',
}

ignore_properties = set([ '_RNA_UI', 'rigify_parameters' ])

def custom_path_from_id(obj,propname):
    return obj.path_from_id() + '["' + propname + '"]'

def bone_key(bone,port=''):
    if port == '':
        return '"'+bone.name+'"'
    else:
        return '"'+bone.name+'":"'+port+'"'

def property_port(propname):
    return 'p_'+propname

def custom_property_port(propname):
    return 'cp_'+propname

def index_vector_prop(table,obj,name,vsize):
    path = obj.path_from_id(name)
    table[path] = bone_key(obj,property_port(name))
    fields = ['x','y','z','w']
    for i in range(0,vsize):
        key = bone_key(obj,property_port(name+'.'+str(i)))
        table[path+'['+str(i)+']'] = key
        table[path+'.'+fields[i]] = key

def index_properties(pose):
    proptable = {}
    for pbone in pose.bones:
        proptable[pbone.path_from_id()] = bone_key(pbone)
        index_vector_prop(proptable,pbone,'location',3)
        index_vector_prop(proptable,pbone,'scale',3)
        if pbone.rotation_mode == 'QUATERNION':
            index_vector_prop(proptable,pbone,'rotation_quaternion',4)
        else:
            index_vector_prop(proptable,pbone,'rotation_euler',3)
        for propname in pbone.keys():
            if propname not in ignore_properties:
                proptable[custom_path_from_id(pbone,propname)] = bone_key(pbone,custom_property_port(propname))
    return proptable

def resolve_bone_link(links,proprefs,proptable,path):
    found_best = False
    while len(path) > 0:
        if path in proptable:
            proprefs.add(path)
            if not found_best:
                links.append(proptable[path])
                found_best = True
        ipt = max(0, path.rfind('.'), path.rfind('['))
        path = path[0:ipt]

def index_drivers(obj, proptable, proprefs):
    dtable = {}
    if obj.animation_data is None:
        return dtable

    for fcurve in obj.animation_data.drivers:
        if fcurve.data_path not in dtable:
            dtable[fcurve.data_path] = {}
        varlinks = []
        trflinks = []
        for var in fcurve.driver.variables:
            for tgt in var.targets:
                if tgt.id == obj:
                    if var.type == 'SINGLE_PROP':
                        resolve_bone_link(varlinks,proprefs,proptable,tgt.data_path)
                    elif tgt.bone_target in obj.pose.bones:
                        path = obj.pose.bones[tgt.bone_target].path_from_id()
                        resolve_bone_link(trflinks,proprefs,proptable,path)
        dtable[fcurve.data_path][fcurve.array_index] = {
            "curve": fcurve,
            "links": set(varlinks),
            "tlinks": set(trflinks)
        }
    return dtable

def find_driver(drivers, path, idx):
    if path in drivers:
        arr = drivers[path]
        if idx in arr:
            return arr[idx]
    return None

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def process_driver(out, driver, key, value):
    if driver:
        for link in driver['links']:
            out.write('\t%s -> %s [style="solid" color="magenta3" arrowtail="odiamond"];\n' % (link,key))
        for link in driver['tlinks']:
            out.write('\t%s -> %s [style="dashed" color="magenta3" arrowtail="odiamond"];\n' % (link,key))
        drv = driver['curve'].driver
        if drv.type == 'SCRIPTED':
            expr = drv.expression
            if is_number(expr):
                return True, '='+str(expr)
            else:
                return False, '='
        elif drv.type == 'MAX':
            return False, '>'
        elif drv.type == 'MIN':
            return False, '<'
        elif drv.type == 'SUM':
            return False, '+'
        elif drv.type == 'AVERAGE':
            return False, '~'
    else:
        return False, str(value)


def format_vector_prop(out,pbone,drivers,proprefs,propname,fnames,flocks):
    path = pbone.path_from_id(propname)
    portname = property_port(propname)
    force = (bone_key(pbone,portname) in proprefs) or ((True in flocks) and (False in flocks))
    vsize = len(fnames)
    result_str = ('<TABLE PORT="%(port)s" BORDER="0" CELLBORDER="1" CELLPADDING="2" CELLSPACING="0"><TR>') % {
        "port": portname
    }
    for i in range(0,vsize):
        fport = portname+'.'+str(i)
        fkey = bone_key(pbone,fport)
        lock = flocks[i]
        driver = find_driver(drivers, path, i)
        if driver or fkey in proprefs:
            force = True
        dlock,dstr = process_driver(out, driver, fkey, fnames[i])
        if dlock:
            lock = True
            driver = None
            dstr = fnames[i]
        result_str += '<TD PORT="%(port)s" BGCOLOR="%(color)s">%(text)s</TD>' % {
            "port": fport,
            "color": 'magenta' if driver else 'lightgrey' if lock else 'white',
            "text": ('<B>%s</B>'%(dstr)) if driver else dstr
        }
    result_str += '</TR></TABLE>'
    return force, result_str

def format_transform_props(out,pbone,drivers,proprefs):
    force_loc,locstr = format_vector_prop(out,pbone,drivers,proprefs,'location',['X','Y','Z'],pbone.lock_location)
    force_scl,sclstr = format_vector_prop(out,pbone,drivers,proprefs,'scale',['SX','SY','SZ'],pbone.lock_scale)
    if pbone.rotation_mode == 'QUATERNION':
        lock = [r for r in pbone.lock_rotation]
        lock.append(pbone.lock_rotation_w)
        force_rot,rotstr = format_vector_prop(out,pbone,drivers,proprefs,'rotation_quaternion',['RX','RY','RZ','RW'],lock)
    else:
        force_rot,rotstr = format_vector_prop(out,pbone,drivers,proprefs,'rotation_euler',['RX','RY','RZ'],pbone.lock_rotation)
    rstr = '<TABLE BORDER="0" CELLPADDING="0"><TR><TD>%s</TD><TD></TD><TD>%s</TD><TD></TD><TD>%s</TD></TR></TABLE>' % (locstr, rotstr, sclstr)
    return (force_rot or force_loc or force_scl), rstr

def export_graph(obj, path):
    arm = obj.data
    out = open(path,'w')

    try:
        out.write('digraph "%s" {\n' % (obj.name))
        out.write('\tnode [shape=none width=0 height=0 margin=0 fontsize=10];\n')
        out.write('\tedge [dir=back];\n')
        out.write('\tnodesep=0.5; ranksep=0.8;\n')

        proptable = index_properties(obj.pose)
        proprefs = set()
        drivers = index_drivers(obj, proptable, proprefs)

        for bone in arm.bones:
            pbone = obj.pose.bones[bone.name]
            # bone flags
            flaglist = [("R",bone.use_inherit_rotation),("S",bone.use_inherit_scale),("L",bone.use_local_location),("P",bone.use_relative_parent)]
            flagstrings = [('<FONT COLOR="%s">%s</FONT>' % ('black' if d[1] else 'lightgrey',d[0])) for d in flaglist]
            # coordinates
            coords_str = ''
            force_coords, coord_line = format_transform_props(out,pbone,drivers,proprefs)
            if force_coords:
                coords_str = '<TR><TD COLSPAN="2">%s</TD></TR>' % (coord_line)
            # custom properties
            cprops_str = ''
            for (propname,propval) in pbone.items():
                if propname not in ignore_properties:
                    path = custom_path_from_id(pbone,propname)
                    key = custom_property_port(propname)
                    driver = find_driver(drivers, path, 0)
                    lock,dexpr = process_driver(out, driver, bone_key(pbone,key), propval)
                    cprops_str += (
                        '<TR><TD BGCOLOR="%(color)s" PORT="%(port)s" ALIGN="LEFT" COLSPAN="2" BORDER="1"><I><B>%(name)s:</B> %(value)s</I></TD></TR>\n'
                    ) % {
                        "name": propname, "value": dexpr, "port": key,
                        "color": 'magenta' if (driver and not lock) else 'white'
                    }
            # constraints
            constraint_str = ''
            constraint_id = 0
            for cons in pbone.constraints:
                typestr = constraint_names[cons.type] if cons.type in constraint_names else cons.type
                portstr = "cons%d" % (constraint_id)
                cols = 2
                influence_str = ''
                if hasattr(cons,'influence'):
                    path = cons.path_from_id('influence')
                    driver = find_driver(drivers, path, 0)
                    if driver or cons.influence != 1.0:
                        cols = 1
                        iport = portstr + '.inf'
                        lock,dtext = process_driver(out,driver,bone_key(pbone,iport),cons.influence)
                        icolor = 'magenta' if (driver and not lock) else 'white'
                        influence_str = '<TD PORT="%s" BGCOLOR="%s" BORDER="1">%s</TD>' % (iport,icolor,dtext[0:5])
                constraint_id += 1
                constraint_str += (
                    '<TR><TD PORT="%(port)s" ALIGN="LEFT" COLSPAN="%(cols)d" BORDER="1"><B>%(type)s:</B>&nbsp;&nbsp;%(name)s</TD>%(influence)s</TR>\n'
                ) % {
                    "type": typestr, "name": cons.name, "port": portstr,
                    "cols": cols, "influence": influence_str
                }
                targets = [cons]
                if hasattr(cons, 'targets'):
                    targets += list(cons.targets)
                for tgt in targets:
                    if hasattr(tgt,'target') and tgt.target == obj:
                        out.write('\t"%(pid)s" -> "%(cid)s":"%(cport)s" [style="solid" color="blue" arrowtail="vee"];\n' % {
                            'pid': tgt.subtarget, 'cid': bone.name, 'cport': portstr
                        })
                    
            # bone html label
            label = (
                '<TABLE ALIGN="CENTER" VALIGN="MIDDLE" BORDER="%(border)d" CELLBORDER="0" CELLSPACING="2" PORT="root">\n'
                '<TR><TD COLSPAN="2">&nbsp;%(title)s&nbsp;</TD></TR>\n'
                '<TR><TD>%(layers)s</TD><TD><B>%(flags)s</B></TD></TR>\n'
                '%(coords)s'
                '%(properties)s'
                '%(constraints)s'
                '</TABLE>'
            ) % {
                "border": 2 if bone.use_deform else 1,
                "title": bone.name,
                "layers": make_layer_table(bone.layers),
                "flags": ''.join(flagstrings),
                "coords": coords_str,
                "properties": cprops_str,
                "constraints": constraint_str
            }
            out.write('\t"%s" [label=<\n%s>];\n' % (bone.name,label))
            # bone parent link
            if bone.parent:
                out.write('\t"%(pid)s" -> "%(cid)s" [style="%(style)s"];\n' % {
                    'pid': bone.parent.name, 'cid': bone.name,
                    'style': ('bold' if bone.use_connect else 'solid')
                })

        out.write("}\n")
    finally:
        out.close()

export_graph(bpy.context.active_object,'rig.dot')
