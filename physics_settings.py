import bpy
import sys

from bpy.app.handlers import persistent

scene_name = 'Scene'
physics_modules = set()

def get_group(name):
    if name is None:
        return None

    try:
        return bpy.data.groups[name]
    except KeyError:
        return None

def get_modifier(grp,obj,mod):
    try:
        return bpy.data.groups[grp].objects[obj].modifiers[mod]
    except KeyError:
        return None

def update_cache_range(cache, getopt):
    global scene_name
    scene = bpy.data.scenes[scene_name]

    start = getopt("frame_start", 1)
    if start is None:
        start = scene.frame_start
    if cache.frame_start != start:
        cache.frame_start = start

    end = getopt("frame_end")
    if end is None:
        end = scene.frame_end
    if cache.frame_end != end:
        cache.frame_end = end

def update_value_field(obj, attr, opt):
    if opt is not None:
        setattr(obj, attr, opt)

def update_effector_weights(weights, getopt):
    effector_names = [
        'gravity', 'all', 'force', 'harmonic', 'vortex', 'charge',
        'magnetic', 'lennardjones', 'wind', 'turbulence', 'curve_guide',
        'drag', 'texture', 'boid', 'smokeflow'
    ]

    for name in effector_names:
        update_value_field(weights, name, getopt('effector_'+name))

def update_group_assignment(obj, attr, group):
    grp = get_group(group)
    if grp is not None and getattr(obj, attr) != grp:
        print('setting group '+group)
        setattr(obj, attr, grp)

class BaseHandler(object):
    handlers = {}
    pending = []

    def __init__(self, key):
        self.key = key
        self.ready = False

        self._defaults = {}
        self._custom = {}

        print(key)
        BaseHandler.handlers[key] = self
        BaseHandler.pending.append(self)

    @property
    def defaults(self):
        return self._defaults

    @defaults.setter
    def defaults(self, value):
        self._defaults = value
        self.refresh()

    @property
    def custom(self):
        return self._custom

    @custom.setter
    def custom(self, value):
        self._custom = value
        self.refresh()

    def get_mapping(self):
        defvals = self._defaults
        custvals = self._custom
        return lambda key,dv=None: custvals.get(key, defvals.get(key, dv))

    def refresh(self):
        if self.ready:
            self.do_refresh()

    def do_refresh(self):
        pass

    def on_update_pre(self):
        pass

class ModifierHandler(BaseHandler):
    def __init__(self,grp,obj,mod,*subargs):
        BaseHandler.__init__(self, (grp,obj,mod)+subargs)

    def do_refresh(self):
        mod = get_modifier(*self.key[0:3])
        if mod is not None:
            self.do_refresh_modifier(mod)
        else:
            print('Could not find modifier: '+str(self.key))

    def do_refresh_modifier(self, mod):
        pass

    def on_update_pre(self):
        mod = get_modifier(*self.key[0:3])
        if mod is not None:
            self.on_update_pre_modifier(mod)

    def on_update_pre_modifier(self, mod):
        pass

class GroupHandler(BaseHandler):
    def do_refresh(self):
        tgt = get_group(self.key)
        if tgt is not None and tgt.library is None:
            getopt = self.get_mapping()
            sgroup = get_group(getopt("src_group"))
            objnames = getopt("src_objects")
            if sgroup is not None and objnames is not None:
                ingroup = {o for o in tgt.objects}
                for oname in objnames:
                    obj = sgroup.objects[oname]
                    if obj not in ingroup:
                        tgt.objects.link(obj)

class ClothHandler(ModifierHandler):
    def on_update_pre_modifier(self, mod):
        getopt = self.get_mapping()
        update_cache_range(mod.point_cache, getopt)
        update_group_assignment(mod.collision_settings, 'group', getopt('collision_group'))
        update_group_assignment(mod.settings.effector_weights, 'group', getopt('effector_group'))

    def do_refresh_modifier(self, mod):
        self.on_update_pre_modifier(mod)

        getopt = self.get_mapping()

        settings_fields = [
            'mass', 'quality', 'time_scale', 'pin_stiffness',
            'use_stiffness_scale',
            'structural_stiffness', 'structural_stiffness_max',
            'bending_stiffness', 'bending_stiffness_max',
            'spring_damping', 'air_damping', 'vel_damping',
            'use_sewing_springs', 'sewing_force_max', 'shrink_min', 'shrink_max',
        ]

        for name in settings_fields:
            update_value_field(mod.settings, name, getopt(name))

        collision_fields = [
            'use_collision', 'collision_quality', 'use_self_collision', 'self_collision_quality'
        ]

        for name in collision_fields:
            update_value_field(mod.collision_settings, name, getopt(name))

        update_value_field(mod.collision_settings, 'distance_min', getopt('collision_distance_min'))
        update_value_field(mod.collision_settings, 'friction', getopt('collision_friction'))
        update_value_field(mod.collision_settings, 'self_distance_min', getopt('self_collision_distance_min'))

        update_effector_weights(mod.settings.effector_weights, getopt)

class SoftbodyHandler(ModifierHandler):
    def on_update_pre_modifier(self, mod):
        getopt = self.get_mapping()
        update_cache_range(mod.point_cache, getopt)
        update_group_assignment(mod.settings, 'collision_group', getopt('collision_group'))
        update_group_assignment(mod.settings.effector_weights, 'group', getopt('effector_group'))

    def do_refresh_modifier(self, mod):
        self.on_update_pre_modifier(mod)

        getopt = self.get_mapping()

        settings_fields = [
            'mass', 'speed', 'friction',
            'goal_spring', 'goal_friction',
            'use_edges', 'pull', 'push', 'damping',
            'plastic', 'bend', 'spring_length',
            'use_stiff_quads', 'shear', 'aero',
            'use_edge_collision', 'use_face_collision',
            'use_self_collision', 'ball_size', 'ball_stiff', 'ball_damp',
            'step_min', 'step_max', 'use_auto_step', 'error_threshold',
            'choke', 'fuzzy'
        ]

        for name in settings_fields:
            update_value_field(mod.settings, name, getopt(name))

        update_effector_weights(mod.settings.effector_weights, getopt)

class BrushHandler(ModifierHandler):
    def do_refresh_modifier(self, mod):
        getopt = self.get_mapping()

        settings_fields = [
            'use_absolute_alpha', 'paint_color',
            'use_paint_erase', 'paint_alpha',
            'paint_wetness', 'paint_distance',
            'invert_proximity', 'proximity_falloff', 'use_negative_volume',
            'use_velocity_alpha', 'use_velocity_color', 'use_velocity_depth', 'velocity_max',
            'use_smudge', 'smudge_strength',
            'wave_factor', 'wave_clamp'
        ]

        for name in settings_fields:
            update_value_field(mod.brush_settings, name, getopt(name))

class CanvasHandler(ModifierHandler):
    def __init__(self,grp,obj,mod,surface):
        ModifierHandler.__init__(self,grp,obj,mod,surface)

    def on_update_pre_modifier(self, mod):
        getopt = self.get_mapping()
        surface = mod.canvas_settings.canvas_surfaces[self.key[3]]

        update_cache_range(surface, getopt)
        update_group_assignment(surface, 'brush_group', getopt('brush_group'))
        update_group_assignment(surface.effector_weights, 'group', getopt('effector_group'))

    def do_refresh_modifier(self, mod):
        getopt = self.get_mapping()
        surface = mod.canvas_settings.canvas_surfaces[self.key[3]]

        settings_fields = [
            'image_resolution', 'use_antialising','frame_substeps',
            'use_drying', 'dry_speed', 'color_dry_threshold', 'use_dry_log',
            'use_dissolve', 'dissolve_speed', 'use_dissolve_log',
            'brush_influence_scale', 'brush_radius_scale',
            'image_output_path', 'image_fileformat', 'use_premultiply',
            'use_output_a', 'output_name_a', 'use_output_b', 'output_name_b',
            'init_color',
            'use_spread', 'spread_speed', 'color_spread_speed',
            'use_drip', 'drip_velocity', 'drip_acceleration',
            'use_shrink', 'shrink_speed'
        ]

        for name in settings_fields:
            update_value_field(surface, name, getopt(name))


@persistent
def _on_scene_update_pre(usc):
    for handler in BaseHandler.pending:
        handler.ready = True
        handler.refresh()

    BaseHandler.pending.clear()

    for handler in BaseHandler.handlers.values():
        handler.on_update_pre()

@persistent
def _on_load_pre(usc):
    global scene_name, physics_modules

    print('cleaning up physics_settings')
    scene_name = 'Scene'
    BaseHandler.handlers = {}
    BaseHandler.pending = []

    for mod in physics_modules:
        if mod in sys.modules:
            del sys.modules[mod]

    physics_modules = set()

print('initializing physics_settings')

bpy.app.handlers.scene_update_pre.append(_on_scene_update_pre)
bpy.app.handlers.load_pre.append(_on_load_pre)
