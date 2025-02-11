import torch
import os
import cv2
import numpy as np
from PIL import Image
import plotly.graph_objects as go
from transformers import pipeline
from models.refined_background_removal import refined_background_removal

def load_and_normalize_images(image_paths):
    """
    Load and normalize all images to the same size while maintaining aspect ratios.
    We first determine the target size based on the smallest image dimension,
    then resize all images accordingly with proper padding.
    """
    print("\nLoading and normalizing images...")
    
    # First, load all images and get their dimensions
    images = {}
    dimensions = []
    for view_type, path in image_paths.items():
        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"Failed to load image: {path}")
        images[view_type] = img
        dimensions.append(img.shape[:2])
        print(f"{view_type.capitalize()} view original size: {img.shape[1]}x{img.shape[0]}")
    
    # Find the smallest dimension across all images
    min_dim = min(min(dim) for dim in dimensions)
    # Round to nearest multiple of 32 (common requirement for deep learning models)
    target_size = ((min_dim // 32) * 32)
    print(f"\nTarget size determined: {target_size}x{target_size}")
    
    normalized_images = {}
    for view_type, img in images.items():
        # Calculate aspect ratio preserving dimensions
        h, w = img.shape[:2]
        aspect = w / h
        
        if aspect > 1:
            new_w = target_size
            new_h = int(target_size / aspect)
        else:
            new_h = target_size
            new_w = int(target_size * aspect)
            
        # Resize image
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Create square canvas with padding
        square_img = np.zeros((target_size, target_size, 3), dtype=np.uint8)
        
        # Calculate padding to center the image
        pad_y = (target_size - new_h) // 2
        pad_x = (target_size - new_w) // 2
        
        # Place resized image in center
        square_img[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
        
        normalized_images[view_type] = square_img
        print(f"{view_type.capitalize()} view normalized size: {square_img.shape[1]}x{square_img.shape[0]}")
    
    return normalized_images, target_size

# def create_object_mesh(image_input, depth_threshold=0.75):
#     """
#     Creates a 3D mesh from either an image path or a numpy array.
    
#     Args:
#         image_input: Can be either a file path (str) or a pre-loaded image (numpy array)
#         depth_threshold: Threshold for depth filtering (0.0 to 1.0)
#     """
#    # Step 1: Convert input to numpy array with proper format
#     if isinstance(image_input, str):
#         # Loading from file path
#         image = cv2.imread(image_input)
#         if image is None:
#             raise ValueError(f"Failed to load image from path: {image_input}")
#     elif isinstance(image_input, Image.Image):
#         # Convert PIL Image to numpy array
#         # First convert to RGB numpy array
#         image_array = np.array(image_input)
#         # Then convert from RGB to BGR for OpenCV
#         image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
#     else:
#         # Assume it's already a numpy array
#         image = image_input
    
#     # Step 2: Verify array format
#     if not isinstance(image, np.ndarray):
#         raise TypeError("Image must be converted to numpy array")
#     if len(image.shape) != 3:
#         raise ValueError("Image must be a 3-channel color image")
    
#     # Step 3: Convert to grayscale
#     try:
#         image_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#     except cv2.error as e:
#         print("Error during color conversion. Image shape:", image.shape)
#         print("Image dtype:", image.dtype)
#         raise ValueError("Failed to convert image to grayscale") from e
    
#      # Step 5: Edge detection
#     try:
#         edges = cv2.Canny(image_gray, 100, 200)
#         kernel = np.ones((5, 5), np.uint8)
#         dilated_edges = cv2.dilate(edges, kernel, iterations=1)
#     except cv2.error as e:
#         print("Error during edge detection. Grayscale image shape:", image_gray.shape)
#         print("Grayscale image dtype:", image_gray.dtype)
#         raise ValueError("Failed during edge detection") from e
    
#     contours, _ = cv2.findContours(dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
#     if not contours:
#         return None
        
#     largest_contour = max(contours, key=cv2.contourArea)
#     mask = np.zeros(image_gray.shape, dtype=np.uint8)
#     cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)
#     mask_blurred = cv2.GaussianBlur(mask, (1, 1), 0)
    
#     output_image = np.zeros_like(image)
#     output_image[mask_blurred > 0] = image[mask_blurred > 0]
    
#     # Get depth map using Depth Anything model
#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     depth_model = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-base-hf", device=device)
    
#     # Convert to PIL Image for depth estimation
#     image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
#     image_pil = Image.fromarray(image_rgb)
#     depth_predictions = depth_model(image_pil)
#     depth_map = np.array(depth_predictions["depth"])

#     # Add this section
    
#     # depth_map = integrate_foreground_processing(image, depth_map)
    
#     # Process depth map
#     height, width, _ = output_image.shape
#     depth_map_resized = cv2.resize(depth_map, (width, height))
    
#     # Apply mask to depth map
#     mask_resized = cv2.resize(mask, (depth_map_resized.shape[1], depth_map_resized.shape[0]))
#     mask_contour = mask_resized > 0
#     depth_edges = np.zeros_like(depth_map_resized)
#     depth_edges[mask_contour] = depth_map_resized[mask_contour]
#     depth_edges_smoothed = cv2.GaussianBlur(depth_edges, (5, 5), 0)
    
#     # Normalize depth values
#     depth_norm = (depth_edges_smoothed - depth_edges_smoothed.min()) / (depth_edges_smoothed.max() - depth_edges_smoothed.min())
    
#     # Convert to RGB for visualization
#     output_rgb = cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB)
    
#     # Create coordinate grids
#     x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))
    
#     # Flatten arrays
#     x_coords_flat = x_coords.ravel().tolist()
#     y_coords_flat = y_coords.ravel().tolist()
#     z_coords_flat = depth_norm.ravel().tolist()
#     colors_flat = output_rgb.reshape(-1, 3).tolist()
    
#     # Apply depth threshold and create mask for valid points
#     mask = []
#     for z, color in zip(z_coords_flat, colors_flat):
#         is_valid = (z > depth_threshold) and not (color[0] == 0 and color[1] == 0 and color[2] == 0)
#         mask.append(is_valid)
    
#     # Filter points based on mask
#     x_filtered = [x for x, m in zip(x_coords_flat, mask) if m]
#     y_filtered = [y for y, m in zip(y_coords_flat, mask) if m]
#     z_filtered = [z for z, m in zip(z_coords_flat, mask) if m]
#     colors_filtered = [c for c, m in zip(colors_flat, mask) if m]
    
#     # Create the Plotly figure
#     fig = go.Figure(data=[go.Scatter3d(
#         x=x_filtered,
#         y=y_filtered,
#         z=z_filtered,
#         mode='markers',
#         marker=dict(
#             size=2,
#             color=[f'rgb({r}, {g}, {b})' for r, g, b in colors_filtered],
#             opacity=1
#         )
#     )])
    
#     # Update layout
#     fig.update_layout(
#         scene=dict(
#             xaxis=dict(nticks=10, range=[0, width]),
#             yaxis=dict(nticks=10, range=[0, height]),
#             zaxis=dict(nticks=10, range=[0, max(z_filtered)]),
#         ),
#         margin=dict(l=0, r=0, b=0, t=30)
#     )
    
#     return fig

def create_object_mesh(image_input, depth_threshold=0.75):
    """
    Creates a 3D mesh from either an image path or a numpy array using refined background removal.
    The function works directly with image data without saving temporary files.
    
    Args:
        image_input: Can be either a file path (str), PIL Image, or a numpy array
        depth_threshold: Threshold for depth filtering (0.0 to 1.0)
    """
    # Input validation and conversion
    if isinstance(image_input, str):
        # It's a file path - load the image
        if not os.path.exists(image_input):
            raise ValueError(f"Image file not found: {image_input}")
        image = cv2.imread(image_input)
        if image is None:
            raise ValueError(f"Failed to load image from {image_input}")
    elif isinstance(image_input, np.ndarray):
        # It's already a numpy array - verify format
        if len(image_input.shape) != 3 or image_input.shape[2] != 3:
            raise ValueError("Image array must be a 3-channel color image")
        image = image_input
    elif isinstance(image_input, Image.Image):
        # Convert PIL Image to numpy array in BGR format
        image_array = np.array(image_input)
        image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    else:
        raise TypeError("Image input must be either a file path, numpy array, or PIL Image")

    try:
        # Apply refined background removal directly to the image
        # Note: refined_background_removal expects BGR input and returns RGB output
        _, alpha_mask, result_rgb, _, _ = refined_background_removal(image)
        
        # Get depth map using Depth Anything model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        depth_model = pipeline("depth-estimation", model="depth-anything/Depth-Anything-V2-base-hf", device=device)
        
        # Use result_rgb directly for depth estimation (it's already in RGB format)
        image_pil = Image.fromarray(result_rgb)
        depth_predictions = depth_model(image_pil)
        depth_map = np.array(depth_predictions["depth"])
        
        # Process depth map with dimensions from result_rgb
        height, width = result_rgb.shape[:2]
        depth_map_resized = cv2.resize(depth_map, (width, height))
        
        # Apply alpha mask to depth map
        alpha_mask_resized = cv2.resize(alpha_mask, (depth_map_resized.shape[1], depth_map_resized.shape[0]))
        depth_mask = alpha_mask_resized > 0
        depth_edges = np.zeros_like(depth_map_resized)
        depth_edges[depth_mask] = depth_map_resized[depth_mask]
        depth_edges_smoothed = cv2.GaussianBlur(depth_edges, (5, 5), 0)
        
        # Normalize depth values
        valid_depths = depth_edges_smoothed[depth_mask]
        if len(valid_depths) > 0:
            depth_min = valid_depths.min()
            depth_max = valid_depths.max()
            depth_norm = np.zeros_like(depth_edges_smoothed)
            depth_norm[depth_mask] = (depth_edges_smoothed[depth_mask] - depth_min) / (depth_max - depth_min)
        else:
            return None
        
        # Create coordinate grids
        x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))
        
        # Create points only for valid mask areas
        valid_points = depth_mask & (depth_norm > depth_threshold)
        x_filtered = x_coords[valid_points].tolist()
        y_filtered = y_coords[valid_points].tolist()
        z_filtered = depth_norm[valid_points].tolist()
        colors_filtered = result_rgb[valid_points].tolist()
        
        # Create the Plotly figure
        fig = go.Figure(data=[go.Scatter3d(
            x=x_filtered,
            y=y_filtered,
            z=z_filtered,
            mode='markers',
            marker=dict(
                size=2,
                color=[f'rgb({r}, {g}, {b})' for r, g, b in colors_filtered],
                opacity=1
            )
        )])
        
        # Update layout
        fig.update_layout(
            scene=dict(
                xaxis=dict(nticks=10, range=[0, width]),
                yaxis=dict(nticks=10, range=[0, height]),
                zaxis=dict(nticks=10, range=[0, 1]),
            ),
            margin=dict(l=0, r=0, b=0, t=30)
        )
        
        return fig
        
    except Exception as e:
        print(f"Error during mesh creation: {str(e)}")
        return None


def combine_front_back_meshes(front_fig, back_fig, depth_threshold=0.25, sampling_rate=0.5):
    """
    Creates an optimized 3D visualization combining front and back mesh views.
    
    Args:
        front_fig: Plotly figure of front mesh
        back_fig: Plotly figure of back mesh
        depth_threshold: Depth threshold value
        sampling_rate: Fraction of points to keep (0.0 to 1.0)
    """
    def extract_points(fig):
        if fig is None or not fig.data:
            return [], [], [], []
        trace = fig.data[0]
        return (
            np.array(trace.x), 
            np.array(trace.y), 
            np.array(trace.z), 
            [c.strip('rgb()').split(',') for c in trace.marker.color]
        )
    
    def sample_points(x, y, z, colors, rate):
        """Efficiently sample points using numpy"""
        n_points = len(x)
        n_sample = int(n_points * rate)
        if n_sample >= n_points:
            return x, y, z, colors
        
        # Use numpy's random choice for efficient sampling
        indices = np.random.choice(n_points, n_sample, replace=False)
        indices.sort()  # Sort for better memory access patterns
        
        return (x[indices], y[indices], z[indices],
                [colors[i] for i in indices])
    
    # Extract points and convert to numpy arrays for faster processing
    front_x, front_y, front_z, front_colors = extract_points(front_fig)
    back_x, back_y, back_z, back_colors = extract_points(back_fig)
    
    # Sample points if needed
    front_x, front_y, front_z, front_colors = sample_points(
        front_x, front_y, front_z, front_colors, sampling_rate)
    back_x, back_y, back_z, back_colors = sample_points(
        back_x, back_y, back_z, back_colors, sampling_rate)
    
    # Calculate dimensions using numpy operations
    original_width = max(np.max(front_x), np.max(back_x))
    original_height = max(np.max(front_y), np.max(back_y))
    aspect_ratio = original_width / original_height
    
    # Center views using vectorized operations
    front_width = np.max(front_x) - np.min(front_x)
    back_width = np.max(back_x) - np.min(back_x)
    
    front_x_centered = front_x - np.min(front_x) - front_width/2
    back_x_centered = -(back_x - np.min(back_x) - back_width/2)
    
    # Normalize z-coordinates using vectorized operations
    front_z_norm = 0.5 + (front_z - np.min(front_z)) * depth_threshold / (np.max(front_z) - np.min(front_z))
    back_z_norm = 0.5 - (back_z - np.min(back_z)) * depth_threshold / (np.max(back_z) - np.min(back_z))
    
    # Convert colors to RGB strings efficiently
    def process_colors(colors):
        return [f'rgb({",".join(c)})' for c in colors]
    
    front_colors_processed = process_colors(front_colors)
    back_colors_processed = process_colors(back_colors)
    
    # Combine points using numpy concatenation
    combined_x = np.concatenate([front_x_centered, back_x_centered])
    combined_y = np.concatenate([front_y, back_y])
    combined_z = np.concatenate([front_z_norm, back_z_norm])
    combined_colors = front_colors_processed + back_colors_processed
    
    # Create the figure
    combined_fig = go.Figure(data=[go.Scatter3d(
        x=combined_x,
        y=combined_y,
        z=combined_z,
        mode='markers',
        marker=dict(
            size=2,
            color=combined_colors,
            opacity=1
        ),
        showlegend=False
    )])
    
    # Update layout with minimal settings
    combined_fig.update_layout(
        scene=dict(
            aspectratio=dict(x=1, y=1/aspect_ratio, z=0.5),
            aspectmode='manual',
            camera=dict(
                eye=dict(x=1.25, y=-0.25, z=1.25),
                up=dict(x=0, y=0, z=0),
                center=dict(x=0, y=0, z=0)
            ),
            xaxis=dict(
                range=[-original_width/2, original_width/2],
                showticklabels=False, showgrid=False,
                zeroline=False, showline=False, showbackground=False
            ),
            yaxis=dict(
                range=[0, original_height],
                showticklabels=False, showgrid=False,
                zeroline=False, showline=False, showbackground=False
            ),
            zaxis=dict(
                range=[0, 1],
                showticklabels=False, showgrid=False,
                zeroline=False, showline=False, showbackground=False
            )
        ),
        uirevision='true',
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0, pad=0),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return combined_fig



def process_orthogonal_views(front, back=None, top=None, depth_threshold=0.25, sampling_rate=1.0):
    # Process all three views
    image_paths = {
        'front': f"{front}",
        'back': f"{back}",
        'top': f"{top}"
    }

    # First normalize all images
    try:
        normalized_images, target_size = load_and_normalize_images(image_paths)
        print("\nAll images successfully normalized to size:", target_size)

        # First, let's get our three normalized meshes individually
        front_fig = create_object_mesh(normalized_images['front'], depth_threshold=depth_threshold)
        back_fig = create_object_mesh(normalized_images['back'], depth_threshold=depth_threshold)
        top_fig = create_object_mesh(normalized_images['top'], depth_threshold=depth_threshold)

         # For maximum quality (but slower)
        combined_mesh = combine_front_back_meshes(front_fig, back_fig, sampling_rate=sampling_rate)
        return combined_mesh.to_dict()
    
    except Exception as e:
        print(f"Error during image normalization: {str(e)}")
        return None



# for single image
def process_image(image_path, depth_threshold=0.5):
    # First normalize all images
    image_paths = {
        'front': f"{image_path}"
    }
    try:
        normalized_images, target_size = load_and_normalize_images(image_paths)
        print("\nAll images successfully normalized to size:", target_size)

        # First, let's get our three normalized meshes individually
        front_fig = create_object_mesh(normalized_images['front'], depth_threshold=depth_threshold)

        if front_fig is not None:
            front_fig.update_layout(
                title=dict(
                    text=f"3D Mesh - front View (Size: {target_size}x{target_size})",
                    y=0.95
                )
            )
            # front_fig.show()
        else:
            print(f"Failed to create mesh for front view")
    except Exception as e:
        print(f"Error during image normalization: {str(e)}")

    # Convert the Plotly figure to JSON-serializable format
    return front_fig.to_dict()  # This converts the Plotly figure to a dictionary