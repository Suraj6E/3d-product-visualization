# foreground_processor.py

import cv2
import numpy as np
from PIL import Image
import torch

class ForegroundProcessor:
    """Handles foreground segmentation and depth refinement"""
    
    def __init__(self):
        self.edge_threshold1 = 100
        self.edge_threshold2 = 200
        self.blur_kernel = (5, 5)
        self.dilate_kernel = np.ones((5, 5), np.uint8)
    
    def process_image(self, image: np.ndarray) -> tuple:
        """
        Process image to extract foreground mask and refined depth
        Returns: (foreground_mask, refined_depth_map)
        """
        # Convert to correct format if needed
        if isinstance(image, torch.Tensor):
            image = image.cpu().numpy()
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            
        # Create initial mask using multiple methods
        mask1 = self._create_edge_based_mask(image)
        mask2 = self._create_color_based_mask(image)
        mask3 = self._create_grabcut_mask(image)
        
        # Combine masks
        combined_mask = cv2.bitwise_or(
            cv2.bitwise_or(mask1, mask2),
            mask3
        )
        
        # Clean up mask
        cleaned_mask = self._clean_mask(combined_mask)
        
        return cleaned_mask
    
    def _create_edge_based_mask(self, image: np.ndarray) -> np.ndarray:
        """Create mask using edge detection"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, self.edge_threshold1, self.edge_threshold2)
        dilated = cv2.dilate(edges, self.dilate_kernel, iterations=1)
        
        # Find contours and keep largest
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return np.zeros_like(gray)
            
        largest_contour = max(contours, key=cv2.contourArea)
        mask = np.zeros_like(gray)
        cv2.drawContours(mask, [largest_contour], -1, 255, thickness=cv2.FILLED)
        
        return mask
    
    def _create_color_based_mask(self, image: np.ndarray) -> np.ndarray:
        """Create mask using color thresholding"""
        # Convert to HSV for better color segmentation
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect white/very light backgrounds
        white_mask = cv2.inRange(hsv, (0, 0, 200), (180, 30, 255))
        white_mask = cv2.bitwise_not(white_mask)
        
        # Add other color-based segmentation as needed
        return white_mask
    
    def _create_grabcut_mask(self, image: np.ndarray) -> np.ndarray:
        """Create mask using GrabCut algorithm"""
        mask = np.zeros(image.shape[:2], np.uint8)
        rect = (10, 10, image.shape[1]-20, image.shape[0]-20)  # Margin from edges
        
        bgdModel = np.zeros((1,65), np.float64)
        fgdModel = np.zeros((1,65), np.float64)
        
        try:
            cv2.grabCut(image, mask, rect, bgdModel, fgdModel, 5, cv2.GC_INIT_WITH_RECT)
            mask = np.where((mask==2)|(mask==0), 0, 1).astype('uint8') * 255
        except:
            mask = np.ones_like(mask) * 255
            
        return mask
    
    def _clean_mask(self, mask: np.ndarray) -> np.ndarray:
        """Clean up the mask using morphological operations"""
        # Fill holes
        filled = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.dilate_kernel)
        
        # Remove small objects
        nb_components, output, stats, centroids = cv2.connectedComponentsWithStats(
            filled, connectivity=8
        )
        sizes = stats[1:, -1]
        max_label = 1 + np.argmax(sizes)
        cleaned = np.zeros_like(filled)
        cleaned[output == max_label] = 255
        
        return cleaned
    
    def refine_depth_map(self, depth_map: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Refine depth map using foreground mask"""
        # Ensure same size
        if depth_map.shape[:2] != mask.shape[:2]:
            mask = cv2.resize(mask, (depth_map.shape[1], depth_map.shape[0]))
        
        # Create binary mask
        binary_mask = mask > 127
        
        # Zero out background in depth map
        refined_depth = depth_map.copy()
        refined_depth[~binary_mask] = 0
        
        return refined_depth

def process_with_foreground(image_input, depth_map):
    """
    Process image and depth map with foreground segmentation.
    Returns refined depth map compatible with existing pipeline.
    """
    processor = ForegroundProcessor()
    
    # Get foreground mask
    fg_mask = processor.process_image(image_input)
    
    # Refine depth map
    refined_depth = processor.refine_depth_map(depth_map, fg_mask)
    
    return refined_depth

# Integration function for your existing pipeline
def integrate_foreground_processing(image, depth_map):
    """
    Wrapper function to integrate with your existing pipeline
    Returns depth map in the same format as your current code expects
    """
    # Process with foreground segmentation
    refined_depth = process_with_foreground(image, depth_map)
    
    # Normalize depth values (matching your existing normalization)
    valid_mask = refined_depth > 0
    if np.any(valid_mask):
        depth_min = np.min(refined_depth[valid_mask])
        depth_max = np.max(refined_depth[valid_mask])
        depth_norm = np.zeros_like(refined_depth)
        depth_norm[valid_mask] = (refined_depth[valid_mask] - depth_min) / (depth_max - depth_min)
    else:
        depth_norm = np.zeros_like(refined_depth)
    
    return depth_norm