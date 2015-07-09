bl_info = {
    "name": "Extrude Physics Lattice",
    "author": "angavrilov",
    "version": (1, 0),
    "blender": (2, 75, 0),
    "location": "View3D -> Search for Operator",
    "description": "An operator for creating multilayer objects with internal edges for physics simulation.",
    "warning": "",
    "wiki_url": "",
    "category": "Mesh",
    }

import bpy
import bmesh

def deselect_all(bm):
    for v in bm.verts:
        v.select = False
    for e in bm.edges:
        e.select = False
    for f in bm.faces:
        f.select = False
    bm.select_flush(False)

def select_faces(bm,faces):
    for f in faces:
        f.select = True
        for v in f.verts:
            v.select = True
        for e in f.edges:
            e.select = True
    bm.select_flush(False)

def get_selection(bm):
    faces = [f for f in bm.faces if f.select]
    edges = [e for e in bm.edges if e.select]
    verts = [v for v in bm.verts if v.select]
    return (faces,edges,verts)

def exec_extrude_operation(op, bm):
    fs,es,vs = get_selection(bm)
    dupret = bmesh.ops.duplicate(bm, geom=fs+es+vs)

    deselect_all(bm)
    for g in dupret["geom"]:
        g.select = True
    bm.select_flush(True)

    dup_verts = [g for g in dupret["geom"] if isinstance(g, bmesh.types.BMVert)]
    dup_edges = [g for g in dupret["geom"] if isinstance(g, bmesh.types.BMEdge)]
    dup_faces = [g for g in dupret["geom"] if isinstance(g, bmesh.types.BMFace)]
    dup_boundary_map = dupret["boundary_map"]
    dup_vert_map = dupret["vert_map"]
    dup_edge_map = dupret["edge_map"]
    dup_face_map = dupret["face_map"]

    boundary_edges = {e for e in es if e in dup_boundary_map}
    boundary_face_edges = boundary_edges if op.fill_boundary else set()
    boundary_verts = {v for e in boundary_face_edges for v in e.verts}
    straight_verts = set(vs) if op.fill_straight else set()
    cross_edges = set(es) if op.fill_cross else set()
    if op.fill_quad_cross:
        cross_edges |= {e for f in fs for e in f.edges if len(f.verts) == 3}
    quad_faces = {f for f in fs if len(f.verts) == 4} if op.fill_quad_cross else set()

    dissolve_edges = set()
    dissolve_verts = set()
    dissolve_dup_edges = set()
    dissolve_dup_verts = set()

    if op.dissolve_sharp:
        dissolve_edges = {e for e in es if not e.smooth} - boundary_edges
        dissolve_dup_edges = {dup_edge_map[e] for e in dissolve_edges}
        dissolve_dup_verts = {v for v in dup_verts if len(set(v.link_edges)-dissolve_dup_edges) <= 2}
        dissolve_verts = {dup_vert_map[v] for v in dissolve_dup_verts}
        if len([f for f in fs if len(set(f.verts)-dissolve_verts) == 0]) > 0:
            op.report({'WARNING'},"A face is completely dissolved")
        cross_edges |= {e for q in [f for f in quad_faces if len(set(f.verts)&dissolve_verts) > 0] for e in q.edges}
        straight_verts |= {v for e in [e for e in cross_edges if len(set(e.verts)&dissolve_verts) == 1] for v in e.verts}

    straight_verts -= boundary_verts
    cross_edges -= boundary_face_edges

    for e in boundary_face_edges:
        e2 = dup_edge_map[e]
        bm.faces.new([e.verts[0], e2.verts[0], e2.verts[1], e.verts[1]])

    dissolve_dup_edges |= {e for v in boundary_verts&dissolve_verts for e in v.link_edges if len(set(e.verts)&dissolve_dup_verts)>0}

    for v in straight_verts:
        v2 = dup_vert_map[v]
        if v2 not in dissolve_dup_verts:
            bm.edges.new([v, v2])

    for e in cross_edges:
        e2 = dup_edge_map[e]
        for i in range(2):
            v2 = e2.verts[(i+1)%2]
            if v2 not in dissolve_dup_verts:
                bm.edges.new([e.verts[i], v2])

    for f in quad_faces:
        f2 = dup_face_map[f]
        for i in range(4):
            v2 = f2.verts[(i+2)%4]
            if v2 not in dissolve_dup_verts:
                bm.edges.new([f.verts[i], v2])

    if op.dissolve_sharp:
        bmesh.ops.dissolve_edges(bm, edges=list(dissolve_dup_edges), use_verts=True, use_face_split=True)
        bm.select_flush_mode()
        bm.select_flush(True)


class ExtrudeLattice(bpy.types.Operator):
    """Extrude face region connected with edge lattice to the original."""
    bl_idname = "mesh.extrude_lattice"
    bl_label = "Extrude Physics Lattice"
    bl_options = {'REGISTER', 'UNDO'}

    fill_boundary = bpy.props.BoolProperty(name="Boundary faces",description="Fill the boundary of the extruded layer with faces",default=True)
    fill_straight = bpy.props.BoolProperty(name="Straight edges",description="Connect every new vertex to the old one with an edge",default=True)
    fill_cross = bpy.props.BoolProperty(name="Cross edges",description="Cross connect the ends of every new and old edge",default=False)
    fill_quad_cross = bpy.props.BoolProperty(name="Cross quads",description="Cross connect opposite corners of every quad face",default=True)
    dissolve_sharp = bpy.props.BoolProperty(name="Dissolve sharp",description="Dissolve sharp edges in the new layer, adjusting lattice accordingly",default=False)

    @classmethod
    def poll(cls, context):
        return context.mode == 'EDIT_MESH' and context.active_object is not None

    def execute(self, context):
        me = context.active_object.data
        bm = bmesh.from_edit_mesh(me)

        bm.select_mode = {'FACE'}
        bm.select_flush_mode()
        initial_faces = [f for f in bm.faces if f.select]

        if len(initial_faces) < 1:
            self.report({'ERROR_INVALID_INPUT'}, "At least one face must be selected.")
            return {'CANCELLED'}

        for f in initial_faces:
            if len(f.verts) > 4:
                self.report({'ERROR_INVALID_INPUT'}, "Only tri and quad faces may be selected.")
                return {'CANCELLED'}

        deselect_all(bm)
        select_faces(bm,initial_faces)

        exec_extrude_operation(self, bm)

        bmesh.update_edit_mesh(me, True)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)

def register():
    bpy.utils.register_class(ExtrudeLattice)

def unregister():
    bpy.utils.unregister_class(ExtrudeLattice)


if __name__ == "__main__":
    register()

    # test call
    #bpy.ops.mesh.extrude_lattice()
