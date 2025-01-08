import torch
import cv2
import numpy as np
from torchvision.transforms import Compose, Resize, ToTensor, Normalize
from PIL import Image
import plotly.graph_objects as go
from transformers import pipeline
import scipy.interpolate as interp

# Original functions needed for backward compatibility
def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    checkpoint = "depth-anything/Depth-Anything-V2-base-hf"
    return pipeline("depth-estimation", model=checkpoint, device=device)

def transform_image(img):
    transform = Compose([
        Resize((384, 384)),
        ToTensor(),
        Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return transform(img_pil).unsqueeze(0)

def estimate_depth(model, img):
    if isinstance(img, np.ndarray):
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    else:
        img_pil = img

    predictions = model(img_pil)
    depth_map = predictions["depth"]
    depth_map_np = np.array(depth_map).squeeze()
    depth_map_resized = cv2.resize(depth_map_np, (img_pil.size[0], img_pil.size[1]))
    
    return depth_map_resized

def extract_edges_and_contour(image_color):
    image_gray = cv2.cvtColor(image_color, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(image_gray, 100, 200)
    kernel = np.ones((5, 5), np.uint8)
    dilated_edges = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_contour = max(contours, key=cv2.contourArea) if contours else None
    mask = np.zeros(image_gray.shape, dtype=np.uint8)

    if largest_contour is not None:
        cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)
        mask_blurred = cv2.GaussianBlur(mask, (1, 1), 0)
        output_image = np.zeros_like(image_color)
        output_image[mask_blurred > 0] = image_color[mask_blurred > 0]
        return output_image, edges, mask_blurred
    return None, edges, mask

def find_depth_for_edges(model, image, mask):
    if isinstance(image, np.ndarray):
        input_batch = transform_image(image)
    else:
        raise ValueError("Input image should be a numpy array.")

    depth_map = estimate_depth(model, image)
    mask_resized = cv2.resize(mask, (depth_map.shape[1], depth_map.shape[0]))
    mask_contour = mask_resized > 0
    
    depth_edges = np.zeros_like(depth_map)
    depth_edges[mask_contour] = depth_map[mask_contour]
    depth_edges_smoothed = cv2.GaussianBlur(depth_edges, (5, 5), 0)

    return depth_edges_smoothed

def plot_3d(output_image, depth_map, depth_threshold=0.75):
    """Creates a 3D visualization of an image using depth information."""
    output_rgb = cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB)
    height, width, _ = output_image.shape
    depth_map_resized = cv2.resize(depth_map, (width, height))
    
    # Normalize depth values
    depth_norm = (depth_map_resized - depth_map_resized.min()) / (depth_map_resized.max() - depth_map_resized.min())
    depth_norm[depth_norm < depth_threshold] = 0

    # Create coordinate grids
    x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))
    
    # Flatten arrays and convert to lists
    x_coords_flat = x_coords.ravel().tolist()
    y_coords_flat = y_coords.ravel().tolist()
    z_coords_flat = depth_norm.ravel().tolist()
    colors_flat = output_rgb.reshape(-1, 3).tolist()

    # Create mask for valid points
    mask = []
    for z, color in zip(z_coords_flat, colors_flat):
        is_valid = (z > 0) and not (color[0] == 0 and color[1] == 0 and color[2] == 0)
        mask.append(is_valid)

    # Filter coordinates and colors
    x_filtered = [x for x, m in zip(x_coords_flat, mask) if m]
    y_filtered = [y for y, m in zip(y_coords_flat, mask) if m]
    z_filtered = [z for z, m in zip(z_coords_flat, mask) if m]
    colors_filtered = [c for c, m in zip(colors_flat, mask) if m]

    # Create mirrored points
    z_filtered_adjusted = [z - depth_threshold for z in z_filtered]
    x_mirrored = x_filtered
    y_mirrored = y_filtered
    z_mirrored = [-z + depth_threshold for z in z_filtered]

    # Combine original and mirrored points
    x_combined = x_filtered + x_mirrored
    y_combined = y_filtered + y_mirrored
    z_combined = z_filtered_adjusted + z_mirrored
    colors_combined = colors_filtered + colors_filtered

    # Convert RGB colors to hex format
    colors_hex = [f'rgb({r}, {g}, {b})' for r, g, b in colors_combined]

    # Create the Plotly figure
    fig = go.Figure(data=[go.Scatter3d(
        x=x_combined,
        y=y_combined,
        z=z_combined,
        mode='markers',
        marker=dict(
            size=2,
            color=colors_hex,
            opacity=1
        )
    )])

    fig.update_layout(
        scene=dict(
            xaxis=dict(nticks=10, range=[0, width]),
            yaxis=dict(nticks=10, range=[0, height]),
            zaxis=dict(nticks=10, range=[-depth_threshold, depth_threshold]),
        ),
        margin=dict(l=0, r=0, b=0, t=0)
    )

    return fig.to_dict()

def process_image(image_path):
    """Original single-view processing function for backward compatibility"""
    image = cv2.imread(image_path)
    if image is None:
        return None

    model = load_model()
    output_image, edges, mask = extract_edges_and_contour(image)

    if output_image is None:
        return None

    depth_edges = find_depth_for_edges(model, image, mask)
    depth_norm = (depth_edges - depth_edges.min()) / (depth_edges.max() - depth_edges.min())
    threshold = 0.75
    fig = plot_3d(output_image, depth_norm, threshold)
    
    return fig

class OrthogonalViewProcessor:
    """New class for processing multiple orthogonal views"""
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = load_model()  # Reuse existing model loading function
        
    def normalize_coordinates(self, points, width, height):
        """Normalize coordinates to [-1, 1] range"""
        x = (2 * points[:, 0] / width) - 1
        y = (2 * points[:, 1] / height) - 1
        z = points[:, 2]
        return np.stack([x, y, z], axis=1)

    def estimate_depth(self, image):
        """Estimate depth from single view"""
        return estimate_depth(self.model, image)  # Reuse existing depth estimation

    def generate_point_cloud(self, depth_map, view_type='front'):
        """Generate point cloud from depth map for specific view"""
        height, width = depth_map.shape
        x, y = np.meshgrid(np.arange(width), np.arange(height))
        
        if view_type == 'front':
            points = np.stack([x, y, depth_map * width], axis=-1)
        elif view_type == 'back':
            points = np.stack([x, y, -depth_map * width], axis=-1)
        elif view_type == 'top':
            points = np.stack([x, depth_map * height, y], axis=-1)
            
        return self.normalize_coordinates(points.reshape(-1, 3), width, height)

    def compute_consistency(self, point, front_depth, back_depth, top_depth):
        """Compute consistency score for a 3D point across all views"""
        x, y, z = point
        
        # Get interpolated depth values
        f_depth = front_depth[int(y), int(x)] if 0 <= y < front_depth.shape[0] and 0 <= x < front_depth.shape[1] else 0
        b_depth = back_depth[int(y), int(x)] if 0 <= y < back_depth.shape[0] and 0 <= x < back_depth.shape[1] else 0
        t_depth = top_depth[int(x), int(z)] if 0 <= x < top_depth.shape[0] and 0 <= z < top_depth.shape[1] else 0
        
        # Compute consistency metrics
        front_consistency = np.abs(z - f_depth)
        back_consistency = np.abs(z + b_depth)
        top_consistency = np.abs(y - t_depth)
        
        weights = [0.4, 0.4, 0.2]  # front, back, top weights
        return weights[0] * front_consistency + weights[1] * back_consistency + weights[2] * top_consistency

    def integrate_views(self, front_img, back_img, top_img):
        """Integrate three orthogonal views into a single 3D model"""
        # Generate depth maps
        front_depth = self.estimate_depth(front_img)
        back_depth = self.estimate_depth(back_img)
        top_depth = self.estimate_depth(top_img)
        
        # Generate initial point clouds
        front_points = self.generate_point_cloud(front_depth, 'front')
        back_points = self.generate_point_cloud(back_depth, 'back')
        top_points = self.generate_point_cloud(top_depth, 'top')
        
        # Combine points and filter based on consistency
        all_points = np.vstack([front_points, back_points, top_points])
        consistencies = np.array([
            self.compute_consistency(p, front_depth, back_depth, top_depth)
            for p in all_points
        ])
        
        # Filter points based on consistency threshold
        consistency_threshold = 0.5
        valid_points = all_points[consistencies < consistency_threshold]
        
        return valid_points

def preprocess_images(front_img, back_img, top_img):
    """
    Preprocess images to ensure consistent sizes and formats.
    
    This function performs several important steps:
    1. Validates input images are not None
    2. Determines target size based on the smallest image dimension
    3. Resizes all images to the same dimensions while maintaining aspect ratio
    4. Applies padding if necessary to ensure perfect squares
    5. Normalizes pixel values
    
    Returns:
        tuple: (processed_front, processed_back, processed_top, target_size)
    """
    print("\nDEBUG: Starting image preprocessing")
    
    # First validate all images are loaded
    if any(img is None for img in [front_img, back_img, top_img]):
        raise ValueError("One or more input images are None")
    
    # Log original dimensions
    print(f"DEBUG: Original dimensions:")
    print(f"Front: {front_img.shape}")
    print(f"Back: {back_img.shape}")
    print(f"Top: {top_img.shape}")
    
    # Find the smallest dimension across all images
    min_dim = min(
        min(front_img.shape[:2]),
        min(back_img.shape[:2]),
        min(top_img.shape[:2])
    )
    
    # Round to nearest multiple of 32 (common requirement for deep learning models)
    target_size = ((min_dim // 32) * 32)
    print(f"DEBUG: Selected target size: {target_size}x{target_size}")
    
    def process_single_image(img, name):
        """Helper function to process a single image"""
        # Convert to float32 for better precision during transformations
        img = img.astype(np.float32)
        
        # Calculate aspect ratio
        h, w = img.shape[:2]
        aspect = w / h
        
        # Determine new dimensions maintaining aspect ratio
        if aspect > 1:
            new_w = target_size
            new_h = int(target_size / aspect)
        else:
            new_h = target_size
            new_w = int(target_size * aspect)
            
        # Resize image
        resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        # Create square canvas
        square = np.zeros((target_size, target_size, 3), dtype=np.float32)
        
        # Calculate padding
        pad_y = (target_size - new_h) // 2
        pad_x = (target_size - new_w) // 2
        
        # Place resized image in center
        square[pad_y:pad_y+new_h, pad_x:pad_x+new_w] = resized
        
        # Normalize to [0, 1]
        square = square / 255.0
        
        print(f"DEBUG: {name} processed - Final shape: {square.shape}")
        return square
    
    # Process each image
    processed_front = process_single_image(front_img, "Front")
    processed_back = process_single_image(back_img, "Back")
    processed_top = process_single_image(top_img, "Top")
    
    return processed_front, processed_back, processed_top, target_size

def process_orthogonal_views(front_path, back_path=None, top_path=None):
    """Process multiple orthogonal views to create 3D visualization"""
    print("\nDEBUG: Starting orthogonal view processing")
    print(f"DEBUG: Front path: {front_path}")
    print(f"DEBUG: Back path: {back_path}")
    print(f"DEBUG: Top path: {top_path}")
    
    # Validate input paths
    if not all([front_path, back_path, top_path]):
        print("DEBUG: Not all views provided, falling back to single view")
        return process_image(front_path)
        
    try:
        # Load images
        print("DEBUG: Loading images...")
        front_img = cv2.imread(front_path)
        back_img = cv2.imread(back_path)
        top_img = cv2.imread(top_path)
        
        print(f"DEBUG: Front image shape: {front_img.shape if front_img is not None else 'None'}")
        print(f"DEBUG: Back image shape: {back_img.shape if back_img is not None else 'None'}")
        print(f"DEBUG: Top image shape: {top_img.shape if top_img is not None else 'None'}")
        
        if any(img is None for img in [front_img, back_img, top_img]):
            print("DEBUG: Failed to load one or more images")
            raise ValueError("Failed to load one or more images")
            
        # Preprocess images to ensure consistent sizes
        front_proc, back_proc, top_proc, target_size = preprocess_images(front_img, back_img, top_img)
        
        # Initialize processor
        print("DEBUG: Initializing OrthogonalViewProcessor")
        processor = OrthogonalViewProcessor()
        
        # Process views and generate 3D model using preprocessed images
        print("DEBUG: Starting view integration")
        points = processor.integrate_views(
            (front_proc * 255).astype(np.uint8),
            (back_proc * 255).astype(np.uint8),
            (top_proc * 255).astype(np.uint8)
        )
        print(f"DEBUG: Generated {len(points)} valid points")
        
        # Create visualization
        print("DEBUG: Creating 3D visualization")
        fig = go.Figure(data=[go.Scatter3d(
            x=points[:, 0].tolist(),
            y=points[:, 1].tolist(),
            z=points[:, 2].tolist(),
            mode='markers',
            marker=dict(
                size=2,
                color=['rgb(0, 0, 255)'] * len(points),
                opacity=0.8
            )
        )])
        
        fig.update_layout(
            scene=dict(
                aspectmode='data',
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z'
            ),
            margin=dict(l=0, r=0, b=0, t=0)
        )
        
        print("DEBUG: Successfully created visualization")
        return fig.to_dict()
        
    except Exception as e:
        print(f"DEBUG: Error in process_orthogonal_views: {str(e)}")
        import traceback
        print("DEBUG: Full traceback:")
        print(traceback.format_exc())
        raise