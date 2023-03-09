bl_info = {
    "name": "Copy Transforms Helper",
    "author": "Blender User 2017",
    "version": (1, 1),
    "blender": (2, 90, 0),
    "location": "View3D > N Panel",
    "description": "A set of tools to assist with copying transforms between bones.",
    "category": "Animation",
}


import bpy
from mathutils import Matrix

class AlignHandlesOperator(bpy.types.Operator):
    """Operator for aligning handles"""
    bl_idname = "pose.align_handles_operator"
    bl_label = "Align Handles"

    def apply_copy_rotation_constraint(self, target_bone, holding_bone):
        # Get the original transformation matrix of the holding bone
        holding_bone_matrix_orig = holding_bone.matrix.copy()

        # Create the copy rotation constraint
        copy_rotation_constraint = holding_bone.constraints.new('COPY_ROTATION')
        copy_rotation_constraint.target = target_bone.id_data
        copy_rotation_constraint.subtarget = target_bone.name
        copy_rotation_constraint.influence = 1.0

        # Update the scene to apply the constraint
        bpy.context.view_layer.update()

        # Return the constraint and original matrix
        return copy_rotation_constraint, holding_bone_matrix_orig

    def execute(self, context):
        # Get the active pose bone
        active_bone = context.active_pose_bone

        # Get the selected pose bones
        selected_bones = context.selected_pose_bones

        if len(selected_bones) != 2:
            self.report({'ERROR'}, "Please select two bones to enable the link.")
            return {'CANCELLED'}

        # Find the target and holding bones
        if selected_bones[0].id_data == selected_bones[1].id_data:
            if selected_bones[0] == active_bone:
                target_bone = selected_bones[1]
                holding_bone = selected_bones[0]
            else:
                target_bone = selected_bones[0]
                holding_bone = selected_bones[1]
        else:
            if selected_bones[0].id_data == active_bone.id_data:
                target_bone = selected_bones[1]
                holding_bone = selected_bones[0]
            elif selected_bones[1].id_data == active_bone.id_data:
                target_bone = selected_bones[0]
                holding_bone = selected_bones[1]
            else:
                # Swap the order of the selected bones to match the order of the active bone
                if active_bone.id_data == selected_bones[0].id_data:
                    target_bone = selected_bones[1]
                    holding_bone = selected_bones[0]
                else:
                    target_bone = selected_bones[0]
                    holding_bone = selected_bones[1]

                if target_bone.id_data != holding_bone.id_data:
                    self.report({'ERROR'}, "Please select two bones from the same armature to enable the link.")
                    return {'CANCELLED'}

        try:
            active_bone_rotation = active_bone.rotation_quaternion.copy()
            copy_rotation_constraint, holding_bone_matrix_orig = self.apply_copy_rotation_constraint(target_bone, holding_bone)
        except AttributeError as e:
            self.report({'ERROR'}, "Error aligning handles: {}".format(str(e)))
            return {'CANCELLED'}

        # Apply visual transform and delete constraint
        bpy.ops.pose.visual_transform_apply()
        holding_bone.constraints.remove(copy_rotation_constraint)

        # Insert the rotation keyframe for the holding bone if set_rotation_keyframes is True
        if context.scene.set_rotation_keyframes:
            holding_bone.keyframe_insert(data_path='rotation_quaternion')

        self.report({'INFO'}, "Handles aligned successfully.")
        return {'FINISHED'}




class EnableLinkOperator(bpy.types.Operator):
    """Enable """
    bl_idname = "pose.enable_link_operator"
    bl_label = "Enable"

    def execute(self, context):
        active_bone = context.active_pose_bone
        selected_bones = context.selected_pose_bones
        
        if len(selected_bones) != 2:
            self.report({'ERROR'}, "Please select two bones to enable the link.")
            return {'CANCELLED'}
        
        # Find the target bone
        if selected_bones[0] == active_bone:
            target_bone = selected_bones[1]
            holding_bone = selected_bones[0]
        else:
            target_bone = selected_bones[0]
            holding_bone = selected_bones[1]
        
        # Check if constraint already exists on this bone
        for const in holding_bone.constraints:
            if const.type == 'COPY_TRANSFORMS' and const.owner_space == 'WORLD' and const.target == target_bone.id_data and const.subtarget == target_bone.name:
                self.report({'INFO'}, "Link already enabled between {} and {}.".format(target_bone.name, holding_bone.name))
                
                # Set influence with keyframe
                const.influence = 0.0
                frame = context.scene.frame_current
                const.keyframe_insert(data_path='influence', frame=frame - 1)
                const.influence = 1.0
                const.keyframe_insert(data_path='influence', frame=frame)
                
                return {'FINISHED'}
        
        # Check if constraint already exists on other bones
        for bone in bpy.context.active_object.pose.bones:
            if bone != holding_bone and bone != target_bone:
                for const in bone.constraints:
                    if const.type == 'COPY_TRANSFORMS' and const.owner_space == 'WORLD' and const.target == target_bone.id_data and const.subtarget == target_bone.name:
                        self.report({'WARNING'}, "Link already exists between {} and {} on another bone.".format(target_bone.name, bone.name))
                        return {'CANCELLED'}
        
        # Create constraint
        const = holding_bone.constraints.new('COPY_TRANSFORMS')
        const.target_space = 'WORLD'
        const.owner_space = 'WORLD'
        const.target = target_bone.id_data
        const.subtarget = target_bone.name
        const.name = "Enabled " + target_bone.name + " and " + holding_bone.name
        
        # Set influence with keyframe
        const.influence = 0.0
        frame = context.scene.frame_current
        const.keyframe_insert(data_path='influence', frame=frame - 1)
        const.influence = 1.0
        const.keyframe_insert(data_path='influence', frame=frame)
        
        self.report({'INFO'}, "Link enabled between {} and {}.".format(target_bone.name, holding_bone.name))
        return {'FINISHED'}




class DisableLinkOperator(bpy.types.Operator):
    """Disable link"""
    bl_idname = "pose.disable_link_operator"
    bl_label = "Disable"
    
    def execute(self, context):
        active_bone = context.active_pose_bone
        if not active_bone:
            self.report({'ERROR'}, "Please select a bone with a Copy Transforms constraint to disable.")
            return {'CANCELLED'}
        
        constraints = []
        for c in active_bone.constraints:
            if c.type == 'COPY_TRANSFORMS' and c.influence == 1.0:
                constraints.append(c)
        if not constraints:
            self.report({'ERROR'}, "Selected bone does not have a Copy Transforms constraint with an influence of 1.")
            return {'CANCELLED'}
        elif len(constraints) > 1:
            self.report({'ERROR'}, "Selected bone has multiple Copy Transforms constraints with an influence of 1.")
            return {'CANCELLED'}
        
        constraint = constraints[0]
        
        # Set constraint influence to 1 with a keyframe for previous frame
        frame_current = bpy.context.scene.frame_current
        frame_previous = frame_current - 1
        constraint.influence = 1.0
        constraint.keyframe_insert('influence', frame=frame_previous)
        
        # Apply visual transform to bone
        bpy.ops.pose.visual_transform_apply()
        
        # Add keyframes for location, rotation, and scale
        active_bone.keyframe_insert(data_path='location', frame=frame_current)
        active_bone.keyframe_insert(data_path='rotation_quaternion', frame=frame_current)
        active_bone.keyframe_insert(data_path='scale', frame=frame_current)
        
        # Set constraint influence to 0 with keyframe on current frame
        constraint.influence = 0.0
        constraint.keyframe_insert('influence', frame=frame_current)
        
        self.report({'INFO'}, "Link disabled successfully.")
        return {'FINISHED'}



class LinkAvenuePanel(bpy.types.Panel):
    """Copy Transform Helper"""
    bl_idname = "POSE_PT_link_avenue_panel"
    bl_label = "Copy Transform Helper"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Transform Helper"
    bl_context = "posemode"

    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.prop(context.scene, "set_rotation_keyframes")
        
        row = layout.row()
        row.operator("pose.align_handles_operator")
        
        row = layout.row()
        row.operator("pose.enable_link_operator")
        
        row = layout.row()
        row.operator("pose.disable_link_operator")

def register():
    bpy.utils.register_class(AlignHandlesOperator)
    bpy.utils.register_class(DisableLinkOperator)
    bpy.utils.register_class(EnableLinkOperator)
    bpy.utils.register_class(LinkAvenuePanel)
    bpy.types.Scene.set_rotation_keyframes = bpy.props.BoolProperty(
        name="Set Rotation Keyframes",
        default=False
    )

def unregister():
    bpy.utils.unregister_class(AlignHandlesOperator)
    bpy.utils.unregister_class(DisableLinkOperator)
    bpy.utils.unregister_class(EnableLinkOperator)
    bpy.utils.unregister_class(LinkAvenuePanel)
    del bpy.types.Scene.set_rotation_keyframes

if __name__ == "__main__":
    register()


