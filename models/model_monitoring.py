# model_monitoring.py
import time
import psutil
import torch
import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class ProcessingStage:
    """Tracks metrics for each processing stage"""
    name: str
    start_time: float = 0.0
    end_time: float = 0.0
    memory_start: float = 0.0
    memory_end: float = 0.0
    gpu_memory_start: float = 0.0
    gpu_memory_end: float = 0.0
    quality_metrics: Dict = field(default_factory=dict)

@dataclass
class ProcessingMetrics:
    """Stores complete processing metrics for an image"""
    image_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_processing_time: float = 0.0
    peak_memory_usage: float = 0.0
    peak_gpu_memory: float = 0.0
    stages: Dict[str, ProcessingStage] = field(default_factory=dict)
    quality_scores: Dict[str, float] = field(default_factory=dict)

class ModelMonitor:
    def __init__(self, log_dir: str = "logs"):
        """Initialize the monitoring system"""
        self.current_metrics = None
        self.log_dir = log_dir
        self.setup_logging()
        
        # Initialize GPU monitoring if available
        self.has_gpu = torch.cuda.is_available()
        if self.has_gpu:
            torch.cuda.reset_peak_memory_stats()

    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f"{self.log_dir}/model_monitoring.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("ModelMonitor")

    def start_processing(self, image_id: str):
        """Start monitoring a new image processing task"""
        self.current_metrics = ProcessingMetrics(
            image_id=image_id,
            start_time=datetime.now()
        )
        self.logger.info(f"Started processing image: {image_id}")

    def start_stage(self, stage_name: str):
        """Start monitoring a processing stage"""
        if not self.current_metrics:
            raise ValueError("No active processing task")
            
        stage = ProcessingStage(
            name=stage_name,
            start_time=time.time(),
            memory_start=psutil.Process().memory_info().rss / 1024 / 1024,  # MB
            gpu_memory_start=torch.cuda.memory_allocated() / 1024 / 1024 if self.has_gpu else 0
        )
        self.current_metrics.stages[stage_name] = stage
        self.logger.info(f"Started stage: {stage_name}")
        return stage

    def end_stage(self, stage_name: str, quality_metrics: Dict = None):
        """End monitoring a processing stage"""
        if not self.current_metrics or stage_name not in self.current_metrics.stages:
            raise ValueError(f"No active stage: {stage_name}")
            
        stage = self.current_metrics.stages[stage_name]
        stage.end_time = time.time()
        stage.memory_end = psutil.Process().memory_info().rss / 1024 / 1024
        stage.gpu_memory_end = torch.cuda.memory_allocated() / 1024 / 1024 if self.has_gpu else 0
        
        if quality_metrics:
            stage.quality_metrics = quality_metrics
            
        processing_time = stage.end_time - stage.start_time
        memory_used = stage.memory_end - stage.memory_start
        gpu_memory_used = stage.gpu_memory_end - stage.gpu_memory_start
        
        self.logger.info(
            f"Completed stage: {stage_name}\n"
            f"Processing time: {processing_time:.2f}s\n"
            f"Memory used: {memory_used:.2f}MB\n"
            f"GPU Memory used: {gpu_memory_used:.2f}MB"
        )

        return {
            'processing_time': processing_time,
            'memory_used': memory_used,
            'gpu_memory_used': gpu_memory_used,
            'quality_metrics': quality_metrics
        }

    def end_processing(self):
        """End monitoring the current processing task"""
        if not self.current_metrics:
            raise ValueError("No active processing task")
            
        self.current_metrics.end_time = datetime.now()
        self.current_metrics.total_processing_time = (
            self.current_metrics.end_time - self.current_metrics.start_time
        ).total_seconds()
        
        # Calculate peak memory usage
        self.current_metrics.peak_memory_usage = max(
            stage.memory_end for stage in self.current_metrics.stages.values()
        )
        
        if self.has_gpu:
            self.current_metrics.peak_gpu_memory = torch.cuda.max_memory_allocated() / 1024 / 1024
            
        self.logger.info(
            f"Completed processing image: {self.current_metrics.image_id}\n"
            f"Total time: {self.current_metrics.total_processing_time:.2f}s\n"
            f"Peak memory: {self.current_metrics.peak_memory_usage:.2f}MB\n"
            f"Peak GPU memory: {self.current_metrics.peak_gpu_memory:.2f}MB"
        )
        
        return self.current_metrics

    def log_quality_metric(self, metric_name: str, value: float):
        """Log a quality metric for the current processing task"""
        if not self.current_metrics:
            raise ValueError("No active processing task")
            
        self.current_metrics.quality_scores[metric_name] = value
        self.logger.info(f"Quality metric - {metric_name}: {value}")

    def get_stage_metrics(self, stage_name: str) -> Optional[Dict]:
        """Get metrics for a specific stage"""
        if not self.current_metrics or stage_name not in self.current_metrics.stages:
            return None
            
        stage = self.current_metrics.stages[stage_name]
        return {
            'processing_time': stage.end_time - stage.start_time,
            'memory_used': stage.memory_end - stage.memory_start,
            'gpu_memory_used': stage.gpu_memory_end - stage.gpu_memory_start,
            'quality_metrics': stage.quality_metrics
        }

    def get_summary_metrics(self) -> Dict:
        """Get summary metrics for the entire processing task"""
        if not self.current_metrics:
            return {}
            
        return {
            'image_id': self.current_metrics.image_id,
            'total_time': self.current_metrics.total_processing_time,
            'peak_memory': self.current_metrics.peak_memory_usage,
            'peak_gpu_memory': self.current_metrics.peak_gpu_memory,
            'quality_scores': self.current_metrics.quality_scores,
            'stages': {
                name: self.get_stage_metrics(name)
                for name in self.current_metrics.stages
            }
        }