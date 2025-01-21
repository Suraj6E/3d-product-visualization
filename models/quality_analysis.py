# quality_analysis.py
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim
from typing import Dict, Tuple, Optional

class QualityAnalyzer:
    """Handles quality analysis for 3D visualization processing"""
    
    def __init__(self):
        self.quality_thresholds = {
            'depth_confidence': 0.7,
            'feature_matching': 0.6,
            'mesh_density': 0.5,
            'texture_quality': 0.8,
            'color_preservation': 0.75
        }

    def analyze_normalization(self, original_image: np.ndarray, 
                            normalized_image: np.ndarray) -> Dict[str, float]:
        """Analyze the quality of image normalization"""
        # Convert images to same size for comparison
        if original_image.shape != normalized_image.shape:
            original_image = cv2.resize(original_image, 
                                      (normalized_image.shape[1], normalized_image.shape[0]))
        
        # Calculate structural similarity
        similarity_score, _ = ssim(original_image, normalized_image, 
                                 multichannel=True, full=True)
        
        # Calculate color distribution preservation
        original_hist = cv2.calcHist([original_image], [0, 1, 2], None, 
                                   [8, 8, 8], [0, 256, 0, 256, 0, 256])
        normalized_hist = cv2.calcHist([normalized_image], [0, 1, 2], None,
                                     [8, 8, 8], [0, 256, 0, 256, 0, 256])
        
        color_correlation = cv2.compareHist(original_hist, normalized_hist,
                                          cv2.HISTCMP_CORREL)
        
        return {
            'structural_similarity': float(similarity_score),
            'color_preservation': float(color_correlation),
            'aspect_ratio_error': self._calculate_aspect_ratio_error(
                original_image.shape, normalized_image.shape
            )
        }

    def analyze_depth_estimation(self, depth_map: np.ndarray) -> Dict[str, float]:
        """Analyze the quality of depth estimation"""
        # Calculate depth map statistics
        depth_mean = np.mean(depth_map)
        depth_std = np.std(depth_map)
        depth_coverage = np.count_nonzero(depth_map) / depth_map.size
        
        # Calculate depth continuity
        depth_gradients = np.gradient(depth_map)
        depth_continuity = 1.0 - (np.mean(np.abs(depth_gradients)) / np.max(depth_map))
        
        return {
            'depth_confidence': float(depth_coverage),
            'depth_continuity': float(depth_continuity),
            'depth_variation': float(depth_std / depth_mean if depth_mean > 0 else 0)
        }

    def analyze_mesh_quality(self, vertices: np.ndarray, faces: np.ndarray,
                           texture_coords: Optional[np.ndarray] = None) -> Dict[str, float]:
        """Analyze the quality of the generated mesh"""
        # Calculate mesh density
        surface_area = self._calculate_mesh_surface_area(vertices, faces)
        vertex_density = len(vertices) / surface_area if surface_area > 0 else 0
        
        # Calculate mesh regularity
        edge_lengths = self._calculate_edge_lengths(vertices, faces)
        length_uniformity = 1.0 - (np.std(edge_lengths) / np.mean(edge_lengths)
                                 if len(edge_lengths) > 0 else 0)
        
        # Analyze texture mapping if available
        texture_coverage = 0.0
        if texture_coords is not None:
            texture_coverage = self._analyze_texture_coverage(texture_coords)
        
        return {
            'mesh_density': float(vertex_density),
            'mesh_regularity': float(length_uniformity),
            'texture_coverage': float(texture_coverage)
        }

    def validate_results(self, metrics: Dict[str, float]) -> Tuple[bool, Dict[str, str]]:
        """Validate quality metrics against thresholds"""
        validation_results = {}
        passed_all = True
        
        for metric, value in metrics.items():
            if metric in self.quality_thresholds:
                threshold = self.quality_thresholds[metric]
                passed = value >= threshold
                passed_all = passed_all and passed
                validation_results[metric] = 'passed' if passed else 'failed'
        
        return passed_all, validation_results

    def _calculate_aspect_ratio_error(self, original_shape: Tuple[int, ...],
                                    normalized_shape: Tuple[int, ...]) -> float:
        """Calculate error in aspect ratio preservation"""
        original_ratio = original_shape[1] / original_shape[0]
        normalized_ratio = normalized_shape[1] / normalized_shape[0]
        return abs(original_ratio - normalized_ratio) / original_ratio

    def _calculate_mesh_surface_area(self, vertices: np.ndarray,
                                   faces: np.ndarray) -> float:
        """Calculate total surface area of the mesh"""
        total_area = 0.0
        for face in faces:
            # Calculate area of each triangular face
            v1, v2, v3 = vertices[face]
            area = np.linalg.norm(np.cross(v2 - v1, v3 - v1)) / 2
            total_area += area
        return total_area

    def _calculate_edge_lengths(self, vertices: np.ndarray,
                              faces: np.ndarray) -> np.ndarray:
        """Calculate lengths of all mesh edges"""
        edges = set()
        for face in faces:
            # Add all edges from face
            for i in range(3):
                edge = tuple(sorted([face[i], face[(i + 1) % 3]]))
                edges.add(edge)
        
        lengths = []
        for v1_idx, v2_idx in edges:
            length = np.linalg.norm(vertices[v1_idx] - vertices[v2_idx])
            lengths.append(length)
        
        return np.array(lengths)

    def _analyze_texture_coverage(self, texture_coords: np.ndarray) -> float:
        """Analyze the coverage and quality of texture mapping"""
        # Calculate percentage of texture space utilized
        min_u, max_u = np.min(texture_coords[:, 0]), np.max(texture_coords[:, 0])
        min_v, max_v = np.min(texture_coords[:, 1]), np.max(texture_coords[:, 1])
        
        texture_area = (max_u - min_u) * (max_v - min_v)
        return min(1.0, texture_area)