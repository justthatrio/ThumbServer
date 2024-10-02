import bpy
import bmesh
import json
import sys
import numpy as np
from mathutils import Matrix, Vector
from pathlib import Path

def parse_data(data_str):
    data = json.loads(data_str)
    return data

def tex(png_filepath, name):
    bpy.ops.image.open(filepath=png_filepath)
    bpy.data.images[name].pack()
    
    return bpy.data.images[name]

def create_material(name, texture_path=None, metallic_path=None, roughness_path=None, color=None, metallic=0.2, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    bsdf = nodes["Principled BSDF"]
    
    fresnel = nodes.new('ShaderNodeFresnel')
    links.new(fresnel.outputs['Fac'], bsdf.inputs['Specular'])
        
    if texture_path:
        # Create texture node
        tex_image = nodes.new('ShaderNodeTexImage')
        tex_image.image = bpy.data.images.load(texture_path)
        
        if metallic_path:
            # Create metalic node
            metalic_image = nodes.new('ShaderNodeTexImage')
            metalic_image.image = bpy.data.images.load(metallic_path)
            
            # Create divide node
            multiply_node = nodes.new('ShaderNodeMath')
            multiply_node.operation = 'DIVIDE'
            multiply_node.inputs[1].default_value = 1.2
                                                
            links.new(metalic_image.outputs['Color'], multiply_node.inputs[0])
            links.new(multiply_node.outputs['Value'], bsdf.inputs['Metallic'])
        if roughness_path:
            # Create metalic node
            rough_image = nodes.new('ShaderNodeTexImage')
            rough_image.image = bpy.data.images.load(roughness_path)
            links.new(rough_image.outputs['Color'], bsdf.inputs['Roughness'])
                
        # Create multiply node
        multiply_node = nodes.new('ShaderNodeMixRGB')
        multiply_node.blend_type = 'MULTIPLY'
        multiply_node.inputs['Fac'].default_value = 1.0
        
        # Link texture node to multiply node
        links.new(tex_image.outputs['Color'], multiply_node.inputs['Color1'])
        
        if color:
            # Link color input to multiply node
            multiply_node.inputs['Color2'].default_value = color
        
        # Link multiply node to Base Color input of the Principled BSDF
        links.new(multiply_node.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        if color:
            bsdf.inputs['Base Color'].default_value = color
    
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    
    return mat

MATERIALS = {
    "Steel": create_material("Steel", texture_path="//assets/Steel/albedo.jpg", metallic_path="//assets/Steel/metal.jpg", roughness_path="//assets/Steel/roughness.jpg"),
    "Glass": bpy.data.materials["GlassBase"],
    "Plastic": bpy.data.materials["PlasticBase"],
    "Aluminium": bpy.data.materials["AluminiumBase"],
    "Wood": bpy.data.materials["WoodBase"],
    "Rubber": bpy.data.materials["RubberBase"],
    "DiamondPlate": bpy.data.materials["DiamondPlateBase"]
}

def color_material(material, color):
    mat = MATERIALS[material].copy()
    mat.name = f"{mat.name}_colored"
    
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    alpha_node = nodes.get("Alpha")
    
    # Find the multiply node in the material
    multiply_node = None
    for node in nodes:
        if node.type == 'MIX_RGB' and node.blend_type == 'MULTIPLY':
            multiply_node = node
            break
    if alpha_node:
        alpha_node.outputs[0].default_value = color[3]
    if multiply_node:
        # Replace the color input of the multiply node
        multiply_node.inputs['Color2'].default_value = color
    else:
        # If no multiply node was found, this means the material did not have a texture
        # Just set the Base Color directly
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs['Base Color'].default_value = color
    
    return mat

def apply_intrinsic_rotation(obj, rotation):
    # Create individual rotation matrices
    rot_x = Matrix.Rotation(rotation[0], 4, 'X')
    rot_y = Matrix.Rotation(rotation[1], 4, 'Y')
    rot_z = Matrix.Rotation(rotation[2], 4, 'Z')
    
    # Apply rotations in order
    obj.matrix_world @= rot_x
    obj.matrix_world @= rot_y
    obj.matrix_world @= rot_z

bpy.ops.object.select_all(action='DESELECT')

sphere = bpy.data.objects.get("SphereModel")
cube = bpy.data.objects.get("CubeModel")
wedge = bpy.data.objects.get("WedgeModel")
cornerwedge = bpy.data.objects.get("CornerWedgeModel")
cylinder = bpy.data.objects.get("CylinderModel")

def create_mesh(shape):
    mesh = bpy.data.meshes.new('MeshPart')    
    if shape == "Block":
        obj = cube.copy()
        obj.data = cube.data.copy()
        bpy.context.collection.objects.link(obj)
    elif shape == "Ball":
        obj = sphere.copy()
        obj.data = sphere.data.copy()
        bpy.context.collection.objects.link(obj)
    elif shape == "Wedge":
        obj = wedge.copy()
        obj.data = wedge.data.copy()
        bpy.context.collection.objects.link(obj)
    elif shape == "CornerWedge":
        obj = cornerwedge.copy()
        obj.data = cornerwedge.data.copy()
        bpy.context.collection.objects.link(obj)
    elif shape == "Cylinder":
        obj = cylinder.copy()
        obj.data = cylinder.data.copy()
        bpy.context.collection.objects.link(obj)
    else:
        raise ValueError(f"Unknown shape: {shape}")        
    return obj

def center_camera_on_objects(camera_name, objects, padding=1.0):
    # Get the camera
    camera = bpy.data.objects.get(camera_name)
    if not camera:
        print(f"Camera '{camera_name}' not found.")
        return
    
    # Initialize the bounding box
    min_coord = Vector((float('inf'), float('inf'), float('inf')))
    max_coord = Vector((float('-inf'), float('-inf'), float('-inf')))
    
    # Iterate through the object names
    for obj in objects:
        # Update the bounding box coordinates
        for corner in obj.bound_box:
            world_coord = obj.matrix_world @ Vector(corner)
            min_coord = Vector((min(min_coord.x, world_coord.x), 
                                            min(min_coord.y, world_coord.y), 
                                            min(min_coord.z, world_coord.z)))
            max_coord = Vector((max(max_coord.x, world_coord.x), 
                                            max(max_coord.y, world_coord.y), 
                                            max(max_coord.z, world_coord.z)))
    
    # Check if any objects were found
    if min_coord == Vector((float('inf'), float('inf'), float('inf'))) or \
       max_coord == Vector((float('-inf'), float('-inf'), float('-inf'))):
        print("No valid objects provided.")
        return
    
    # Calculate the center of the bounding box
    center = (min_coord + max_coord) / 2
    
    # Calculate the camera position based on the current camera rotation
    camera_direction = camera.rotation_euler.to_matrix() @ Vector((0, 0, -1))  # Forward direction
    camera_distance = max((max_coord - min_coord).length, 1.0) * padding  # Distance to keep based on bounding box size
    
    # Update camera position
    camera.location = center - (camera_direction * camera_distance) + Vector((1.55, 1, 0))


def create_scene(data):
    min_coords = np.array([float('inf'), float('inf'), float('inf')])
    max_coords = np.array([float('-inf'), float('-inf'), float('-inf')])

    parts = []
    
    for obj in data["p"]:
        shape = obj['s']
        size = [obj['si']['x'] / 1000, obj['si']['y'] / 1000, obj['si']['z'] / 1000]
        position = np.array([obj['p']['x'], obj['p']['y'], obj['p']['z']]) / 1000
        rotation = np.array([obj['r']['x'], obj['r']['y'], obj['r']['z']]) / 1000
        
        part = create_mesh(shape)        
        apply_intrinsic_rotation(part, rotation)
        part.scale = size
        part.location = position        
        parts.append(part)
        
        bpy.ops.object.select_all(action='DESELECT')
        
        part.select_set(True)  # Select the object
        # Switch to Edit mode
        bpy.ops.object.mode_set(mode='EDIT')

        # Ensure all faces are selected
        bpy.ops.mesh.select_all(action='SELECT')

        # Apply box projection UV unwrap
        bpy.ops.uv.cube_project(cube_size=3/max(size))  # You can adjust the cube_size parameter as needed

        # Switch back to Object mode
        bpy.ops.object.mode_set(mode='OBJECT')
        
        # Update min and max coordinates
        min_coords = np.minimum(min_coords, part.bound_box[0])
        max_coords = np.maximum(max_coords, part.bound_box[6])
        
        opacity = 1
        if obj["m"]["t"] == "Glass":
            opacity = obj["m"]["o"] / 20

        color = [obj["m"]["c"]["r"]/50, obj["m"]["c"]["g"]/50, obj["m"]["c"]["b"]/50, opacity]
        mat = color_material(obj["m"]["t"], color)
        if part.data.materials:
            part.data.materials[0] = mat
        else:
            part.data.materials.append(mat)
    
    bpy.ops.object.mode_set(mode='OBJECT')        
    bpy.ops.object.select_all(action='DESELECT')    
    center_camera_on_objects("Camera", parts)
    return min_coords, max_coords

argv = sys.argv
argv = argv[argv.index("--") + 1:]  # get all args after "--"

f = Path(bpy.path.abspath(argv[0])) # make a path object of abs path

data = parse_data(f.read_text())
create_scene(data)

bpy.context.scene.render.filepath = '//output/'+argv[1]
bpy.context.scene.render.resolution_x = 400
bpy.context.scene.render.resolution_y = 400
bpy.ops.render.render(write_still=True)