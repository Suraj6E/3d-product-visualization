# enhanced_visualization.py
import os
import uuid
import torch
import numpy as np
from typing import Dict, Optional, Tuple
from models.model_monitoring import ModelMonitor
from models.quality_analysis import QualityAnalyzer
from transformers import pipeline
import cv2
import psutil
from PIL import Image

class Enhanced3DVisualizer:
    def __init__(self, log_dir: str = "logs"):
        """
        Initialize the enhanced 3D visualization system with monitoring and quality analysis
        """
        # Initialize monitoring and quality analysis
        self.monitor = ModelMonitor(log_dir=log_dir)
        self.quality_analyzer = QualityAnalyzer()
        
        # Initialize the depth estimation model
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.depth_model = pipeline("depth-estimation", 
                                  model="depth-anything/Depth-Anything-V2-base-hf", 
                                  device=self.device)

    def process_orthogonal_views(self, front_path: str, back_path: str, 
                               top_path: str, depth_threshold: float = 0.25,
                               sampling_rate: float = 1.0) -> Dict:
        """
        Process multiple views with comprehensive monitoring and quality analysis
        """
        # Generate unique ID for this processing task
        process_id = str(uuid.uuid4())
        self.monitor.start_processing(process_id)

        try:
            # Stage 1: Image Loading and Normalization
            self.monitor.start_stage("normalization")
            image_paths = {
                'front': front_path,
                'back': back_path,
                'top': top_path
            }
            normalized_images, target_size = self._normalize_images(image_paths)
            norm_metrics = self._analyze_normalization_quality(image_paths, normalized_images)
            self.monitor.end_stage("normalization", quality_metrics=norm_metrics)

            # Stage 2: Depth Estimation
            self.monitor.start_stage("depth_estimation")
            depth_results = {}
            depth_metrics = {}
            for view, img in normalized_images.items():
                depth_map, quality = self._estimate_depth(img)
                depth_results[view] = depth_map
                depth_metrics[view] = quality
            self.monitor.end_stage("depth_estimation", quality_metrics=depth_metrics)

            # Stage 3: Mesh Generation
            self.monitor.start_stage("mesh_generation")
            meshes = {}
            mesh_metrics = {}
            for view, img in normalized_images.items():
                mesh, quality = self._generate_mesh(img, depth_results[view], depth_threshold)
                meshes[view] = mesh
                mesh_metrics[view] = quality
            self.monitor.end_stage("mesh_generation", quality_metrics=mesh_metrics)

            # Stage 4: View Combination
            self.monitor.start_stage("view_combination")
            combined_result = self._combine_views(meshes, sampling_rate)
            combination_metrics = self._analyze_combination_quality(combined_result)
            self.monitor.end_stage("view_combination", quality_metrics=combination_metrics)

            # Complete processing and collect final metrics
            final_metrics = self.monitor.end_processing()

            # Return results with metrics
            return {
                'visualization': combined_result,
                'metrics': final_metrics,
                'quality_summary': self._generate_quality_summary(final_metrics)
            }

        except Exception as e:
            self.monitor.logger.error(f"Processing error: {str(e)}")
            raise

    def _normalize_images(self, image_paths: Dict[str, str]) -> Tuple[Dict[str, np.ndarray], int]:
        """
        Enhanced image normalization with quality tracking
        """
        normalized_images = {}
        normalization_metrics = {}
        
        for view_type, path in image_paths.items():
            # Load and process image
            img = cv2.imread(path)
            if img is None:
                raise ValueError(f"Failed to load image: {path}")
                
            # Track memory usage during processing
            memory_before = psutil.Process().memory_info().rss
            
            # Perform normalization
            normalized = self._normalize_single_image(img)
            
            # Track memory usage after processing
            memory_after = psutil.Process().memory_info().rss
            memory_used = memory_after - memory_before
            
            # Store metrics
            normalization_metrics[view_type] = {
                'memory_used': memory_used,
                'original_size': img.shape,
                'normalized_size': normalized.shape
            }
            
            normalized_images[view_type] = normalized
            
        return normalized_images, normalized_images[list(normalized_images.keys())[0]].shape[0]

    def _estimate_depth(self, image: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Enhanced depth estimation with quality metrics
        """
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(image_rgb)
        
        # Track GPU memory before depth estimation
        gpu_mem_before = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        
        # Perform depth estimation
        depth_predictions = self.depth_model(image_pil)
        depth_map = np.array(depth_predictions["depth"])
        
        # Track GPU memory after depth estimation
        gpu_mem_after = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        gpu_mem_used = gpu_mem_after - gpu_mem_before
        
        # Analyze depth quality
        quality_metrics = self.quality_analyzer.analyze_depth_estimation(depth_map)
        quality_metrics['gpu_memory_used'] = gpu_mem_used
        
        return depth_map, quality_metrics

    def _generate_mesh(self, image: np.ndarray, depth_map: np.ndarray,
                      depth_threshold: float) -> Tuple[Dict, Dict]:
        """
        Enhanced mesh generation with quality tracking
        """
        # Track resource usage
        start_memory = psutil.Process().memory_info().rss
        start_gpu = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        
        # Generate mesh
        mesh_data = self._create_mesh_from_depth(image, depth_map, depth_threshold)
        
        # Calculate resource usage
        end_memory = psutil.Process().memory_info().rss
        end_gpu = torch.cuda.memory_allocated() if torch.cuda.is_available() else 0
        
        # Analyze mesh quality
        quality_metrics = self.quality_analyzer.analyze_mesh_quality(
            mesh_data['vertices'],
            mesh_data['faces'],
            mesh_data.get('texture_coords')
        )
        
        # Add resource usage to metrics
        quality_metrics.update({
            'memory_used': end_memory - start_memory,
            'gpu_memory_used': end_gpu - start_gpu
        })
        
        return mesh_data, quality_metrics

    def _generate_quality_summary(self, metrics: Dict) -> Dict:
        """
        Generate a comprehensive quality summary from all collected metrics
        """
        summary = {
            'overall_quality': self._calculate_overall_quality(metrics),
            'performance': {
                'total_processing_time': metrics['total_time'],
                'peak_memory_usage': metrics['peak_memory'],
                'peak_gpu_memory': metrics['peak_gpu_memory']
            },
            'quality_scores': metrics['quality_scores'],
            'stage_performance': {
                stage: {
                    'time': data['processing_time'],
                    'quality': np.mean(list(data['quality_metrics'].values()))
                    if data['quality_metrics'] else 0
                }
                for stage, data in metrics['stages'].items()
            }
        }
        
        return summary

    def _calculate_overall_quality(self, metrics: Dict) -> float:
        """
        Calculate an overall quality score based on all metrics
        """
        quality_weights = {
            'depth_confidence': 0.3,
            'mesh_density': 0.2,
            'texture_quality': 0.2,
            'structural_similarity': 0.15,
            'color_preservation': 0.15
        }
        
        overall_score = 0
        total_weight = 0
        
        for metric, weight in quality_weights.items():
            if metric in metrics['quality_scores']:
                overall_score += metrics['quality_scores'][metric] * weight
                total_weight += weight
        
        return overall_score / total_weight if total_weight > 0 else 0