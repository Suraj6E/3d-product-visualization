import torch
import cv2
import numpy as np
from torchvision.transforms import Compose, Resize, ToTensor, Normalize
from PIL import Image
import plotly.graph_objects as go
from plotly.offline import plot
from transformers import pipeline
import os

def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    checkpoint = "depth-anything/Depth-Anything-V2-base-hf"
    pipe = pipeline("depth-estimation", model=checkpoint, device=device)
    return pipe

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

def plot_3d(output_image, depth_map, depth_threshold = 0.75):
    output_rgb = cv2.cvtColor(output_image, cv2.COLOR_BGR2RGB)
    height, width, _ = output_image.shape
    depth_map_resized = cv2.resize(depth_map, (width, height))
    depth_norm = (depth_map_resized - depth_map_resized.min()) / (depth_map_resized.max() - depth_map_resized.min())
    depth_norm[depth_norm < depth_threshold] = 0

    x_coords, y_coords = np.meshgrid(np.arange(width), np.arange(height))
    x_coords_flat = x_coords.ravel()
    y_coords_flat = y_coords.ravel()
    z_coords_flat = depth_norm.ravel()
    colors_flat = output_rgb.reshape(-1, 3)

    mask = (z_coords_flat > 0) & np.all(colors_flat != [0, 0, 0], axis=1)
    x_filtered = x_coords_flat[mask]
    y_filtered = y_coords_flat[mask]
    z_filtered = z_coords_flat[mask]
    colors_filtered = colors_flat[mask]

    z_filtered_adjusted = z_filtered - depth_threshold
    x_mirrored = x_filtered
    y_mirrored = y_filtered
    z_mirrored = -z_filtered + depth_threshold

    x_combined = np.concatenate([x_filtered, x_mirrored])
    y_combined = np.concatenate([y_filtered, y_mirrored])
    z_combined = np.concatenate([z_filtered_adjusted, z_mirrored])
    colors_combined = np.vstack([colors_filtered, colors_filtered])

    colors_hex = ['rgb({}, {}, {})'.format(r, g, b) for r, g, b in colors_combined]

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

    return fig

def process_image(image_path):
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