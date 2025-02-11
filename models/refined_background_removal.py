import cv2
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from PIL import Image
import os

def detect_background_color(img, samples_per_edge=100):
    """
    Safely detect the background color by analyzing image edges.
    Uses a more robust sampling approach that avoids zero-step slicing.
    
    Args:
        img: Input image in BGR format
        samples_per_edge: Number of samples to take from each edge
        
    Returns:
        tuple: RGB color values of detected background
    """
    height, width = img.shape[:2]
    
    # Ensure we take at least one sample per edge
    samples_per_edge = max(1, min(samples_per_edge, min(height, width)))
    
    # Calculate step sizes (ensure non-zero)
    width_step = max(1, width // samples_per_edge)
    height_step = max(1, height // samples_per_edge)
    
    # Sample pixels from edges
    edge_pixels = []
    
    # Sample top and bottom edges
    for x in range(0, width, width_step):
        edge_pixels.append(img[0, x])        # Top edge
        edge_pixels.append(img[-1, x])       # Bottom edge
    
    # Sample left and right edges
    for y in range(0, height, height_step):
        edge_pixels.append(img[y, 0])        # Left edge
        edge_pixels.append(img[y, -1])       # Right edge
    
    # Convert to numpy array
    edge_pixels = np.array(edge_pixels)
    
    # Use K-means clustering to find dominant color
    kmeans = KMeans(n_clusters=3, n_init=10)
    kmeans.fit(edge_pixels)
    
    # Get the most frequent color cluster
    unique, counts = np.unique(kmeans.labels_, return_counts=True)
    dominant_cluster = unique[np.argmax(counts)]
    background_color = kmeans.cluster_centers_[dominant_cluster].astype(int)
    
    # Convert from BGR to RGB
    return tuple(background_color[::-1])

def detect_shadows_enhanced(img, background_color):
    """
    Enhanced shadow detection that preserves subtle lighting transitions and reflections.
    This function analyzes both global and local lighting patterns to identify shadows
    while being careful not to misclassify object details as shadows.
    
    Args:
        img: Input image in BGR format
        background_color: RGB tuple of the background color
    Returns:
        numpy.ndarray: Shadow mask where 1 indicates shadow pixels
    """
    # First, convert background color from RGB to BGR for OpenCV
    bg_color = background_color[::-1]
    
    # Create a background image matching our detected background color
    background = np.full_like(img, bg_color)
    
    # Convert both images to LAB color space for better lighting analysis
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    bg_lab = cv2.cvtColor(background, cv2.COLOR_BGR2LAB)
    
    # Extract L (lightness) channels
    l_img = lab[:,:,0].astype(np.float32)
    l_bg = bg_lab[:,:,0].astype(np.float32)
    
    # Calculate local average of lightness using multiple scales
    shadow_masks = []
    for kernel_size in [(21, 21), (41, 41)]:  # Multiple scales for different shadow sizes
        # Calculate local lightness average
        local_mean = cv2.GaussianBlur(l_img, kernel_size, 0)
        
        # Calculate lightness difference from background
        l_diff = np.abs(l_img - l_bg)
        local_diff = np.abs(local_mean - l_bg)
        
        # Create adaptive threshold based on local contrast
        threshold = np.mean(l_diff) * 0.5 + local_diff * 0.2
        
        # Identify shadow regions
        shadow = (l_diff < threshold) & (l_img < l_bg)
        shadow_masks.append(shadow)
    
    # Combine shadow masks from different scales
    shadow_mask = np.logical_or.reduce(shadow_masks)
    
    # Analyze color differences to prevent misclassifying colored regions as shadows
    a_diff = np.abs(lab[:,:,1] - bg_lab[:,:,1])
    b_diff = np.abs(lab[:,:,2] - bg_lab[:,:,2])
    color_diff = np.sqrt(a_diff**2 + b_diff**2)
    
    # Only keep shadow pixels where color difference is small
    shadow_mask &= (color_diff < 30)
    
    # Clean up the mask
    kernel = np.ones((3,3), np.uint8)
    shadow_mask = cv2.morphologyEx(shadow_mask.astype(np.uint8), 
                                 cv2.MORPH_CLOSE, kernel)
    shadow_mask = cv2.morphologyEx(shadow_mask.astype(np.uint8), 
                                 cv2.MORPH_OPEN, kernel)
    
    return shadow_mask

def refined_background_removal(image_input, background_color=None, edge_smoothing=5, preserve_whites=True):
    """
    Advanced background removal with automatic background color detection and
    improved edge handling.
    
    Args:
        image_input: Path to input image or Image.Image or numpy array
        background_color: RGB tuple or None for auto-detection
        edge_smoothing: Amount of edge smoothing (higher = smoother)
        preserve_whites: Whether to preserve white colors in the object
    """
    def create_color_range_mask(img, target_color, tolerance=20):  # Reduced tolerance
        """Create a more precise mask for colors within tolerance of target color"""
        target_bgr = target_color[::-1]

        # Convert to LAB color space for better color similarity matching
        lab_image = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        lab_target = cv2.cvtColor(np.uint8([[target_bgr]]), cv2.COLOR_BGR2LAB)[0,0]

        # Create bounds with tolerance in LAB space
        lower_bound = np.array([max(0, c - tolerance) for c in lab_target])
        upper_bound = np.array([min(255, c + tolerance) for c in lab_target])

        # Create mask in LAB space
        mask = cv2.inRange(lab_image, lower_bound, upper_bound)

        # Clean up the mask
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        return mask

    def smooth_edges(mask, smooth_factor):
        """Apply edge smoothing with outline removal"""
        # Convert to float
        mask_float = mask.astype(np.float32) / 255.0
        
        # Apply erosion first to remove thin outlines
        kernel = np.ones((2,2), np.uint8)
        eroded = cv2.erode(mask_float, kernel, iterations=1)
        
        # Multi-scale smoothing
        smoothed = np.zeros_like(mask_float)
        weights_sum = 0
        
        for i in range(1, 4):
            kernel_size = smooth_factor * 2 * i + 1
            current_smooth = cv2.GaussianBlur(eroded, 
                                            (kernel_size, kernel_size), 
                                            0)
            weight = 1.0 / i
            smoothed += current_smooth * weight
            weights_sum += weight
        
        smoothed /= weights_sum
        
        # Threshold the result to make edges cleaner
        smoothed = np.where(smoothed > 0.5, 1.0, 0.0)
        
        return (smoothed * 255).astype(np.uint8)

    def preserve_white_details(img, mask, threshold=250):
        """
        Preserve white details with proper handling of edge cases and division.
        
        Args:
            img: Input image in BGR format
            mask: Binary mask
            threshold: Brightness threshold for white detection
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Create adaptive threshold with safety checks
        local_mean = cv2.GaussianBlur(gray, (15, 15), 0)
        
        # Avoid division by zero and invalid values
        local_mean = np.clip(local_mean, 1, 254)  # Ensure no zeros or 255s
        adjustment = np.clip((255 - local_mean) * 0.05, 0, threshold)
        local_threshold = threshold - adjustment
        
        # Create white mask with safety checks
        white_areas = gray > local_threshold
        
        # Reduce connectivity to main object
        kernel = np.ones((2,2), np.uint8)
        dilated_mask = cv2.dilate(mask, kernel, iterations=1)
        preserved_whites = white_areas & dilated_mask
        
        # Clean up artifacts
        preserved_whites = cv2.morphologyEx(preserved_whites.astype(np.uint8), 
                                        cv2.MORPH_OPEN, kernel)
        preserved_whites = cv2.morphologyEx(preserved_whites, 
                                        cv2.MORPH_CLOSE, kernel)
        
        return mask | preserved_whites

    def shrink_mask(mask, shrink_percent=1):
        """
        Shrink the mask by a percentage of its dimensions
        Args:
            mask: Binary mask
            shrink_percent: Percentage to shrink (1 = 1%)
        Returns:
            Shrunk mask
        """
        # Get mask dimensions
        height, width = mask.shape[:2]
        
        # Calculate pixels to shrink on each side
        shrink_pixels_y = int(height * (shrink_percent / 100))
        shrink_pixels_x = int(width * (shrink_percent / 100))
        
        # Ensure at least 1 pixel if percentage is too small
        shrink_pixels_y = max(1, shrink_pixels_y)
        shrink_pixels_x = max(1, shrink_pixels_x)
        
        # Create structuring element for erosion
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (2 * shrink_pixels_x + 1, 2 * shrink_pixels_y + 1)
        )
        
        # Erode the mask
        shrunk_mask = cv2.erode(mask, kernel, iterations=1)
        
        return shrunk_mask

    # Main processing pipeline
    try:
        print("Loading image...")
        # Input validation and conversion
        if isinstance(image_input, str):
            print("It's a file path - load the image")
            if not os.path.exists(image_input):
                raise ValueError(f"Image file not found: {image_input}")
            image = cv2.imread(image_input)
            if image is None:
                raise ValueError(f"Failed to load image from {image_input}")
        elif isinstance(image_input, np.ndarray):
            print("It's already a numpy array - verify format")
            if len(image_input.shape) != 3 or image_input.shape[2] != 3:
                raise ValueError("Image array must be a 3-channel color image")
            image = image_input
        elif isinstance(image_input, Image.Image):
            
            print("Convert PIL Image to numpy array in BGR format")
            image_array = np.array(image_input)
            image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
        else:
            raise TypeError("Image input must be either a file path, numpy array, or PIL Image")
        
        print(image.__class__)
        # Handle background color detection
        if background_color is None:
            print("Detecting background color...")
            detected_color = detect_background_color(image)
            print(f"Detected background color (RGB): {detected_color}")
            bg_color = detected_color
        else:
            bg_color = background_color
        
        print("Detecting shadows...")
        shadow_mask = detect_shadows_enhanced(image, bg_color)
        
        print("Creating color-based mask...")
        color_mask = create_color_range_mask(image, bg_color)
        
        # Combine color and shadow masks
        combined_mask = (color_mask | shadow_mask)

        
        
        # Invert mask (we want to keep the object, not the background)
        object_mask = cv2.bitwise_not(combined_mask)
        
        # Preserve white details if requested
        if preserve_whites:
            print("Preserving white details...")
            object_mask = preserve_white_details(image, object_mask)

        
        # Apply edge smoothing
        if edge_smoothing > 0:
            print("Smoothing edges...")
            object_mask = smooth_edges(object_mask, edge_smoothing)

        # Shrinking mask
        print("Shrinking mask...")
        object_mask = shrink_mask(object_mask, shrink_percent=0.5)
        
        
        # Create output images
        alpha = object_mask
        rgba = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = alpha
        
        result = image.copy()
        result[alpha == 0] = [0, 0, 0]
        
        # Convert to RGB for display
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        
        checkered = np.zeros((image.shape[0], image.shape[1], 3), dtype=np.uint8)
        checkered[::20, ::20] = [200, 200, 200]
        checkered[10::20, 10::20] = [200, 200, 200]
        
        alpha_3d = alpha[:,:,np.newaxis] / 255.0
        blended = (image_rgb * alpha_3d + checkered * (1 - alpha_3d)).astype(np.uint8)
        
        return image_rgb, alpha, result_rgb, blended, rgba
        
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        return None