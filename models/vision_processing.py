import torch
import os
import cv2
import numpy as np
from PIL import Image
import plotly.graph_objects as go
from transformers import pipeline
from models.refined_background_removal import refined_background_removal, detect_background_color
from models.process_outliers import remove_outliers


# def combine_front_back_meshes(front_fig, back_fig, depth_threshold=0.25, sampling_rate=0.5):
#     """
#     Creates an optimized 3D visualization combining front and back mesh views.
    
#     Args:
#         front_fig: Plotly figure of front mesh
#         back_fig: Plotly figure of back mesh
#         depth_threshold: Depth threshold value
#         sampling_rate: Fraction of points to keep (0.0 to 1.0)
#     """
#     def extract_points(fig):
#         if fig is None or not fig.data:
#             return [], [], [], []
#         trace = fig.data[0]
#         return (
#             np.array(trace.x), 
#             np.array(trace.y), 
#             np.array(trace.z), 
#             [c.strip('rgb()').split(',') for c in trace.marker.color]
#         )
    
#     def sample_points(x, y, z, colors, rate):
#         """Efficiently sample points using numpy"""
#         n_points = len(x)
#         n_sample = int(n_points * rate)
#         if n_sample >= n_points:
#             return x, y, z, colors
        
#         # Use numpy's random choice for efficient sampling
#         indices = np.random.choice(n_points, n_sample, replace=False)
#         indices.sort()  # Sort for better memory access patterns
        
#         return (x[indices], y[indices], z[indices],
#                 [colors[i] for i in indices])
    
#     # Extract points and convert to numpy arrays for faster processing
#     front_x, front_y, front_z, front_colors = extract_points(front_fig)
#     back_x, back_y, back_z, back_colors = extract_points(back_fig)
    
#     # Sample points if needed
#     front_x, front_y, front_z, front_colors = sample_points(
#         front_x, front_y, front_z, front_colors, sampling_rate)
#     back_x, back_y, back_z, back_colors = sample_points(
#         back_x, back_y, back_z, back_colors, sampling_rate)
    
#     # Calculate dimensions using numpy operations
#     original_width = max(np.max(front_x), np.max(back_x))
#     original_height = max(np.max(front_y), np.max(back_y))
#     aspect_ratio = original_width / original_height
    
#     # Center views using vectorized operations
#     front_width = np.max(front_x) - np.min(front_x)
#     back_width = np.max(back_x) - np.min(back_x)
    
#     front_x_centered = front_x - np.min(front_x) - front_width/2
#     back_x_centered = -(back_x - np.min(back_x) - back_width/2)
    
#     # Normalize z-coordinates using vectorized operations
#     front_z_norm = 0.5 + (front_z - np.min(front_z)) * depth_threshold / (np.max(front_z) - np.min(front_z))
#     back_z_norm = 0.5 - (back_z - np.min(back_z)) * depth_threshold / (np.max(back_z) - np.min(back_z))
    
#     # Convert colors to RGB strings efficiently
#     def process_colors(colors):
#         return [f'rgb({",".join(c)})' for c in colors]
    
#     front_colors_processed = process_colors(front_colors)
#     back_colors_processed = process_colors(back_colors)
    
#     # Combine points using numpy concatenation
#     combined_x = np.concatenate([front_x_centered, back_x_centered])
#     combined_y = np.concatenate([front_y, back_y])
#     combined_z = np.concatenate([front_z_norm, back_z_norm])
#     combined_colors = front_colors_processed + back_colors_processed
    
#     # Create the figure
#     combined_fig = go.Figure(data=[go.Scatter3d(
#         x=combined_x,
#         y=combined_y,
#         z=combined_z,
#         mode='markers',
#         marker=dict(
#             size=2,
#             color=combined_colors,
#             opacity=1
#         ),
#         showlegend=False
#     )])
    
#     # Update layout with minimal settings
#     combined_fig.update_layout(
#         scene=dict(
#             aspectratio=dict(x=1, y=1/aspect_ratio, z=0.5),
#             aspectmode='manual',
#             camera=dict(
#                 eye=dict(x=1.25, y=-0.25, z=1.25),
#                 up=dict(x=0, y=0, z=0),
#                 center=dict(x=0, y=0, z=0)
#             ),
#             xaxis=dict(
#                 range=[-original_width/2, original_width/2],
#                 showticklabels=False, showgrid=False,
#                 zeroline=False, showline=False, showbackground=False
#             ),
#             yaxis=dict(
#                 range=[0, original_height],
#                 showticklabels=False, showgrid=False,
#                 zeroline=False, showline=False, showbackground=False
#             ),
#             zaxis=dict(
#                 range=[0, 1],
#                 showticklabels=False, showgrid=False,
#                 zeroline=False, showline=False, showbackground=False
#             )
#         ),
#         uirevision='true',
#         showlegend=False,
#         margin=dict(l=0, r=0, t=0, b=0, pad=0),
#         paper_bgcolor='rgba(0,0,0,0)',
#         plot_bgcolor='rgba(0,0,0,0)'
#     )
    
#     return combined_fig

def load_and_normalize_images(image_paths, target_size=256):
    """
    Load and normalize all images to the specified target size while maintaining aspect ratios.
    Uses background color detection for padding.
    
    The function:
    1. Loads each image
    2. Detects the background color
    3. Resizes while maintaining aspect ratio
    4. Creates a square canvas with the detected background color
    5. Centers the resized image in the canvas
    """
    print("\nLoading and normalizing images...")
    
    images = {}
    for view_type, path in image_paths.items():
        if path is None:
            continue
            
        # Load the image
        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"Failed to load image: {path}")
        
        # Detect background color (returns RGB)
        bg_color_rgb = detect_background_color(img)
        # Convert RGB to BGR for OpenCV
        bg_color_bgr = bg_color_rgb[::-1]
        print(f"{view_type.capitalize()} view background color (RGB): {bg_color_rgb}")
        
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
        
        # Create square canvas with detected background color (in BGR)
        square_img = np.full((target_size, target_size, 3), bg_color_bgr, dtype=np.uint8)
        
        # Calculate padding to center the image
        pad_y = (target_size - new_h) // 2
        pad_x = (target_size - new_w) // 2
        
        # Place resized image in center
        square_img[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
        
        images[view_type] = square_img
        print(f"{view_type.capitalize()} view normalized size: {square_img.shape[1]}x{square_img.shape[0]}")
    
    return images, target_size

def create_object_mesh(image_input, depth_threshold=0.0, target_size=256):
    """
    Creates a 3D mesh from either an image path or a numpy array using refined background removal.
    """
    # Input validation and conversion
    if isinstance(image_input, str):
        # Normalize the image first using our original normalization function
        images, _ = load_and_normalize_images({"input": image_input}, target_size)
        image = images["input"]
    elif isinstance(image_input, np.ndarray):
        image = image_input
    elif isinstance(image_input, Image.Image):
        image_array = np.array(image_input)
        image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    else:
        raise TypeError(
            "Image input must be either a file path, numpy array, or PIL Image"
        )

    try:

        # After background removal
        _, alpha_mask, result_rgb, _, _ = refined_background_removal(image)
        print(f"\nAfter background removal:")
        print(f"Result RGB shape: {result_rgb.shape}")
        print(f"Alpha mask shape: {alpha_mask.shape}")
        print(f"Non-zero alpha pixels: {np.count_nonzero(alpha_mask)}")

        # Get depth map
        device = "cuda" if torch.cuda.is_available() else "cpu"
        depth_model = pipeline(
            "depth-estimation",
            model="depth-anything/Depth-Anything-V2-base-hf",
            device=device,
        )
        depth_predictions = depth_model(Image.fromarray(result_rgb))
        depth_map = np.array(depth_predictions["depth"])

        print(f"\nDepth map statistics:")
        print(f"Depth map shape: {depth_map.shape}")
        print(f"Depth range: {depth_map.min():.3f} to {depth_map.max():.3f}")

        # Process depth map
        height, width = result_rgb.shape[:2]
        depth_map_resized = cv2.resize(depth_map, (width, height))
        alpha_mask_resized = cv2.resize(
            alpha_mask, (depth_map_resized.shape[1], depth_map_resized.shape[0])
        )
        depth_mask = alpha_mask_resized > 0

        print(f"\nAfter resizing:")
        print(f"Resized depth map shape: {depth_map_resized.shape}")
        print(f"Valid mask points: {np.count_nonzero(depth_mask)}")

        # Normalize depth map
        depth_norm = (depth_map_resized - depth_map_resized.min()) / (
            depth_map_resized.max() - depth_map_resized.min()
        )
        print(
            f"\nNormalized depth range: {depth_norm.min():.3f} to {depth_norm.max():.3f}"
        )

        # Create points
        x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))
        valid_points = depth_mask & (depth_norm > depth_threshold)

        x_filtered = x_coords[valid_points].tolist()
        y_filtered = y_coords[valid_points].tolist()
        z_filtered = depth_norm[valid_points].tolist()
        colors_filtered = result_rgb[valid_points].tolist()

        print(f"\nPoint generation results:")
        print(f"Total possible points: {width * height}")
        print(f"Points after masking: {np.count_nonzero(depth_mask)}")
        print(f"Final points after depth threshold: {len(x_filtered)}")

        # Create the figure and return
        fig = go.Figure(
            data=[
                go.Scatter3d(
                    x=x_filtered,
                    y=y_filtered,
                    z=z_filtered,
                    mode="markers",
                    marker=dict(
                        size=2,
                        color=[f"rgb({r},{g},{b})" for r, g, b in colors_filtered],
                        opacity=1,
                    ),
                )
            ]
        )

        print("\n=== Mesh Creation Complete ===")
        return fig

    except Exception as e:
        print(f"Error during mesh creation: {str(e)}")
        return None

def combine_views_with_gap_filling(combined_fig, point_spacing=2):
    """
    Creates straight parallel lines with consistent, vibrant colors.
    """
    def create_fade_color(original_color, fade_factor):
        """
        Creates a color transition that maintains vibrancy.
        Instead of fading to black, we keep colors bright but adjust their intensity.
        """
        original_color = np.array(original_color, dtype=float)
        
        # Ensure fade factor never goes below 0.3 to maintain color visibility
        fade_factor = max(0.3, fade_factor)
        
        # Apply gamma correction for natural color appearance
        gamma = 2.2
        color_linear = (original_color / 255.0) ** gamma
        
        # Calculate faded color while maintaining vibrancy
        faded_linear = color_linear * fade_factor
        faded_color = 255.0 * (faded_linear ** (1.0/gamma))
        
        return np.clip(faded_color, 0, 255).astype(np.uint8)

    def fill_straight(points, colors, is_front):
        """
        Creates straight lines from points toward center with vibrant colors.
        """
        filled_points = []
        filled_colors = []
        
        center_z = 0.5  # Center point
        
        for point, color in zip(points, colors):
            # Calculate distance to center
            z_distance = abs(center_z - point[2])
            
            # Calculate number of points needed
            num_points = max(2, int(z_distance / (point_spacing * 0.01)) + 1)
            
            # Create sequence of points
            for i in range(num_points):
                progress = i / (num_points - 1)
                
                # Create new point
                new_point = point.copy()
                
                # Only modify z coordinate
                new_point[2] = point[2] + progress * (center_z - point[2])
                
                # Calculate color with maintained vibrancy
                # Use a gentler fade that never goes too dark
                fade_factor = 1.0 - (progress * 0.5)  # Only fade to 50% intensity
                faded_color = create_fade_color(color, fade_factor)
                
                filled_points.append(new_point)
                filled_colors.append(faded_color)
        
        if filled_points:
            return np.array(filled_points), np.array(filled_colors)
        return np.array([]), np.array([])

    # Extract points and colors
    points = np.column_stack([
        combined_fig.data[0].x,
        combined_fig.data[0].y,
        combined_fig.data[0].z
    ])
    colors = np.array([list(map(int, c.strip('rgb()').split(','))) 
                      for c in combined_fig.data[0].marker.color])
    
    # Split front and back
    split_x = np.median(points[:, 0])
    front_mask = points[:, 0] > split_x
    back_mask = ~front_mask
    
    # Fill from both surfaces
    front_filled_points, front_filled_colors = fill_straight(
        points[front_mask], colors[front_mask], True)
    back_filled_points, back_filled_colors = fill_straight(
        points[back_mask], colors[back_mask], False)
    
    print(f"\nFill Results:")
    print(f"Front fill points: {len(front_filled_points)}")
    print(f"Back fill points: {len(back_filled_points)}")
    
    # Combine all points
    all_points = np.vstack([
        points,  # Original points
        front_filled_points,
        back_filled_points
    ])
    all_colors = np.vstack([
        colors,  # Original colors
        front_filled_colors,
        back_filled_colors
    ])
    
    # Create visualization
    filled_fig = go.Figure(data=[go.Scatter3d(
        x=all_points[:, 0],
        y=all_points[:, 1],
        z=all_points[:, 2],
        mode='markers',
        marker=dict(
            size=5,
            color=[f'rgb({r},{g},{b})' for r,g,b in all_colors],
            opacity=combined_fig.data[0].marker.opacity
        )
    )])
    
    filled_fig.update_layout(combined_fig.layout)
    
    return filled_fig


def combine_front_back_meshes(
    front_fig, back_fig, depth_threshold=0.25, sampling_rate=1.0
):
    """Combines front and back meshes with detailed debugging information."""
    print("\n=== Starting Mesh Combination ===")

    def extract_points(fig, view_name):
        if fig is None or not fig.data:
            print(f"No data found for {view_name} view")
            return [], [], [], []

        trace = fig.data[0]
        points = (
            np.array(trace.x),
            np.array(trace.y),
            np.array(trace.z),
            [c.strip("rgb()").split(",") for c in trace.marker.color],
        )
        print(f"\n{view_name} view initial points: {len(points[0])}")
        return points

    def sample_points(x, y, z, colors, rate, view_name):
        n_points = len(x)
        n_sample = int(n_points * rate)
        print(f"\nSampling {view_name} view:")
        print(f"Original points: {n_points}")
        print(f"Target points: {n_sample}")

        if n_sample >= n_points:
            return x, y, z, colors

        indices = np.random.choice(n_points, n_sample, replace=False)
        indices.sort()

        sampled = (x[indices], y[indices], z[indices], [colors[i] for i in indices])
        print(f"Points after sampling: {len(sampled[0])}")
        return sampled

    # Extract points
    front_x, front_y, front_z, front_colors = extract_points(front_fig, "Front")
    back_x, back_y, back_z, back_colors = extract_points(back_fig, "Back")

    if len(front_x) == 0 and len(back_x) == 0:
        print("No points found in either view")
        return None

    # Sample points if needed
    front_x, front_y, front_z, front_colors = sample_points(
        front_x, front_y, front_z, front_colors, sampling_rate, "Front"
    )
    back_x, back_y, back_z, back_colors = sample_points(
        back_x, back_y, back_z, back_colors, sampling_rate, "Back"
    )

    # Process dimensions
    original_width = max(
        np.max(front_x) if len(front_x) > 0 else 0,
        np.max(back_x) if len(back_x) > 0 else 0,
    )
    original_height = max(
        np.max(front_y) if len(front_y) > 0 else 0,
        np.max(back_y) if len(back_y) > 0 else 0,
    )

    print(f"\nDimensions:")
    print(f"Original width: {original_width}")
    print(f"Original height: {original_height}")
    print(
        f"Aspect ratio: {original_width/original_height if original_height != 0 else 'N/A'}"
    )

    # Normalize and combine points
    print("\nNormalizing depths:")
    for view_name, points in [
        ("Front", (front_x, front_y, front_z)),
        ("Back", (back_x, back_y, back_z)),
    ]:
        if len(points[0]) > 0:
            print(
                f"{view_name} z-range: {points[2].min():.3f} to {points[2].max():.3f}"
            )

    # Center and normalize points
    if len(front_x) > 0:
        front_width = np.max(front_x) - np.min(front_x)
        front_x_centered = front_x - np.min(front_x) - front_width / 2
        front_z_norm = 0.5 + (front_z - np.min(front_z)) * depth_threshold / (
            np.max(front_z) - np.min(front_z)
        )

    if len(back_x) > 0:
        back_width = np.max(back_x) - np.min(back_x)
        back_x_centered = -(back_x - np.min(back_x) - back_width / 2)
        back_z_norm = 0.5 - (back_z - np.min(back_z)) * depth_threshold / (
            np.max(back_z) - np.min(back_z)
        )

    # Combine points
    combined_x = np.concatenate([front_x_centered, back_x_centered])
    combined_y = np.concatenate([front_y, back_y])
    combined_z = np.concatenate([front_z_norm, back_z_norm])
    combined_colors = [f'rgb({",".join(c)})' for c in front_colors] + [
        f'rgb({",".join(c)})' for c in back_colors
    ]

    print(f"\nFinal combined point count: {len(combined_x)}")
    print(f"Combined z-range: {combined_z.min():.3f} to {combined_z.max():.3f}")

    # Create combined figure
    combined_fig = go.Figure(
        data=[
            go.Scatter3d(
                x=combined_x,
                y=combined_y,
                z=combined_z,
                mode="markers",
                marker=dict(size=10, color=combined_colors, opacity=1),
                showlegend=False,
            )
        ]
    )

    # Update layout
    combined_fig.update_layout(
        scene=dict(
            aspectratio=dict(x=1, y=1 / (original_width / original_height), z=0.5),
            aspectmode="manual",
            camera=dict(
                eye=dict(x=1.25, y=-0.25, z=1.25),
                up=dict(x=0, y=0, z=0),
                center=dict(x=0, y=0, z=0),
            ),
            xaxis=dict(
                range=[-original_width / 2, original_width / 2],
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                showline=False,
                showbackground=False,
            ),
            yaxis=dict(
                range=[0, original_height],
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                showline=False,
                showbackground=False,
            ),
            zaxis=dict(
                range=[0, 1],
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                showline=False,
                showbackground=False,
            ),
        ),
        uirevision="true",
        showlegend=False,
        margin=dict(l=0, r=0, t=0, b=0, pad=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )

    print("\n=== Mesh Combination Complete ===")
    return combined_fig


def process_orthogonal_views(
    front,
    back=None,
    top=None,
    target_size=256,
    spatial_strictness=0.5,
    color_threshold=0.99,
):
    """
    Process orthogonal views with normalized image sizes.
    """
    # Process all three views
    image_paths = {"front": front, "back": back, "top": top}

    try:
        # First normalize all images
        normalized_images, _ = load_and_normalize_images(
            image_paths, target_size=target_size
        )

        # Create meshes for each view
        front_fig = create_object_mesh(
            normalized_images["front"], depth_threshold=0.1, target_size=target_size
        )
        front_fig = remove_outliers(
            front_fig,
            spatial_strictness=spatial_strictness,
            color_threshold=color_threshold,
        )

        back_fig = None
        if back is not None:
            back_fig = create_object_mesh(
                normalized_images["back"], depth_threshold=0.1, target_size=target_size
            )
            back_fig = remove_outliers(
                back_fig,
                spatial_strictness=spatial_strictness,
                color_threshold=color_threshold,
            )

        # top_fig = None
        # if back is not None:
        #     top_fig = create_object_mesh(normalized_images['top'],  target_size=target_size)
        #     top_fig = remove_outliers(top_fig, spatial_strictness=0.5, color_threshold=0.05)

        # Combine meshes
        combined_mesh = combine_front_back_meshes(front_fig, back_fig)
        # combined_mesh.show()
        filled_mesh = combine_views_with_gap_filling(
            combined_mesh
        )
        # filled_mesh.show()
        return filled_mesh.to_dict()

    except Exception as e:
        print(f"Error during processing: {str(e)}")
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