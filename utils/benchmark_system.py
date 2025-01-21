# benchmark_system.py
import time
import json
import numpy as np
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import torch
from models.enhanced_visualization import Enhanced3DVisualizer
import platform
import psutil
import os

class BenchmarkSystem:
    def __init__(self, output_dir: str = "benchmarks"):
        """
        Initialize the benchmark system
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define benchmark thresholds
        self.performance_thresholds = {
            'processing_time': 30.0,  # seconds
            'memory_usage': 2048.0,   # MB
            'gpu_memory': 4096.0,     # MB
            'quality_score': 0.7      # 0-1 scale
        }
        
        # Initialize results storage
        self.benchmark_results = []

    def run_benchmark(self, visualizer: Enhanced3DVisualizer,
                     test_data: List[Dict[str, str]]) -> Dict:
        """
        Run comprehensive benchmarks on the visualization system
        """
        benchmark_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        benchmark_results = {
            'id': benchmark_id,
            'timestamp': datetime.now().isoformat(),
            'system_info': self._get_system_info(),
            'test_cases': []
        }

        for test_case in test_data:
            # Run single test case
            result = self._run_test_case(visualizer, test_case)
            benchmark_results['test_cases'].append(result)

        # Calculate aggregate metrics
        benchmark_results['summary'] = self._calculate_summary(benchmark_results['test_cases'])
        
        # Save results
        self._save_results(benchmark_results)
        
        return benchmark_results

    def _run_test_case(self, visualizer: Enhanced3DVisualizer,
                      test_case: Dict[str, str]) -> Dict:
        """
        Run a single test case and collect detailed metrics
        """
        start_time = time.time()
        
        try:
            # Process the test case
            result = visualizer.process_orthogonal_views(
                front_path=test_case['front'],
                back_path=test_case['back'],
                top_path=test_case['top']
            )
            
            # Collect test metrics
            test_metrics = {
                'test_id': test_case.get('id', 'unknown'),
                'processing_time': time.time() - start_time,
                'success': True,
                'metrics': result['metrics'],
                'quality_summary': result['quality_summary'],
                'validation_results': self._validate_results(result)
            }

        except Exception as e:
            test_metrics = {
                'test_id': test_case.get('id', 'unknown'),
                'processing_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }

        return test_metrics

    def _validate_results(self, result: Dict) -> Dict:
        """
        Validate test results against performance thresholds
        """
        validation = {
            'passed': True,
            'checks': {}
        }

        # Check processing time
        total_time = result['metrics']['total_time']
        validation['checks']['processing_time'] = {
            'value': total_time,
            'threshold': self.performance_thresholds['processing_time'],
            'passed': total_time <= self.performance_thresholds['processing_time']
        }
        
        # Check memory usage
        peak_memory = result['metrics']['peak_memory']
        validation['checks']['memory_usage'] = {
            'value': peak_memory,
            'threshold': self.performance_thresholds['memory_usage'],
            'passed': peak_memory <= self.performance_thresholds['memory_usage']
        }
        
        # Check GPU memory if available
        if 'peak_gpu_memory' in result['metrics']:
            gpu_memory = result['metrics']['peak_gpu_memory']
            validation['checks']['gpu_memory'] = {
                'value': gpu_memory,
                'threshold': self.performance_thresholds['gpu_memory'],
                'passed': gpu_memory <= self.performance_thresholds['gpu_memory']
            }
        
        # Check quality score
        quality_score = result['quality_summary']['overall_quality']
        validation['checks']['quality_score'] = {
            'value': quality_score,
            'threshold': self.performance_thresholds['quality_score'],
            'passed': quality_score >= self.performance_thresholds['quality_score']
        }

        # Update overall validation status
        validation['passed'] = all(check['passed'] for check in validation['checks'].values())
        
        return validation
# Continuing the BenchmarkSystem class...

    def _calculate_summary(self, test_cases: List[Dict]) -> Dict:
        """
        Calculate comprehensive summary statistics from all test cases.
        This helps us understand the model's performance across different scenarios.
        """
        successful_tests = [test for test in test_cases if test['success']]
        
        if not successful_tests:
            return {
                'total_tests': len(test_cases),
                'successful_tests': 0,
                'success_rate': 0,
                'average_metrics': None
            }

        # Calculate key performance indicators across all successful tests
        performance_metrics = {
            'processing_time': {
                'values': [test['processing_time'] for test in successful_tests],
                'weight': 0.3  # Time efficiency importance
            },
            'quality_score': {
                'values': [test['quality_summary']['overall_quality'] 
                          for test in successful_tests],
                'weight': 0.4  # Quality importance
            },
            'memory_efficiency': {
                'values': [1.0 - (test['metrics']['peak_memory'] / 
                          self.performance_thresholds['memory_usage'])
                          for test in successful_tests],
                'weight': 0.3  # Resource efficiency importance
            }
        }

        # Calculate weighted performance score
        overall_score = sum(
            np.mean(metric['values']) * metric['weight']
            for metric in performance_metrics.values()
        )

        # Generate detailed statistical analysis
        summary = {
            'overall_performance': {
                'score': overall_score,
                'total_tests': len(test_cases),
                'successful_tests': len(successful_tests),
                'success_rate': (len(successful_tests) / len(test_cases) * 100)
            },
            'performance_distributions': {},
            'stage_analysis': self._analyze_processing_stages(successful_tests),
            'quality_analysis': self._analyze_quality_metrics(successful_tests),
            'resource_usage': self._analyze_resource_usage(successful_tests)
        }

        # Calculate detailed distributions for each metric
        for metric_name, metric_data in performance_metrics.items():
            values = metric_data['values']
            summary['performance_distributions'][metric_name] = {
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'mean': float(np.mean(values)),
                'median': float(np.median(values)),
                'std': float(np.std(values)),
                'percentiles': {
                    '25': float(np.percentile(values, 25)),
                    '75': float(np.percentile(values, 75)),
                    '90': float(np.percentile(values, 90))
                }
            }

        return summary

    def _analyze_processing_stages(self, test_cases: List[Dict]) -> Dict:
        """
        Analyze the performance of individual processing stages across all tests.
        This helps identify bottlenecks and optimization opportunities.
        """
        stage_metrics = {}
        
        # Collect metrics for each processing stage
        for test in test_cases:
            for stage, metrics in test['metrics']['stages'].items():
                if stage not in stage_metrics:
                    stage_metrics[stage] = {
                        'times': [],
                        'memory_usage': [],
                        'quality_scores': []
                    }
                
                stage_metrics[stage]['times'].append(metrics['processing_time'])
                stage_metrics[stage]['memory_usage'].append(metrics['memory_used'])
                
                # Calculate average quality score for the stage
                if metrics['quality_metrics']:
                    quality_score = np.mean(list(metrics['quality_metrics'].values()))
                    stage_metrics[stage]['quality_scores'].append(quality_score)

        # Generate statistical analysis for each stage
        stage_analysis = {}
        for stage, metrics in stage_metrics.items():
            stage_analysis[stage] = {
                'time_profile': {
                    'mean': float(np.mean(metrics['times'])),
                    'std': float(np.std(metrics['times'])),
                    'percentage_of_total': float(np.mean(metrics['times']) / 
                                               np.mean([t['processing_time'] 
                                                      for t in test_cases]) * 100)
                },
                'memory_profile': {
                    'mean': float(np.mean(metrics['memory_usage'])),
                    'std': float(np.std(metrics['memory_usage'])),
                    'peak': float(np.max(metrics['memory_usage']))
                },
                'quality_profile': {
                    'mean': float(np.mean(metrics['quality_scores'])) 
                            if metrics['quality_scores'] else None,
                    'std': float(np.std(metrics['quality_scores'])) 
                           if metrics['quality_scores'] else None
                }
            }

        return stage_analysis

    def _analyze_quality_metrics(self, test_cases: List[Dict]) -> Dict:
        """
        Perform detailed analysis of quality metrics across all tests.
        This helps understand the consistency and reliability of our results.
        """
        quality_metrics = {}
        
        # Collect all quality metrics
        for test in test_cases:
            for metric, value in test['quality_summary']['quality_scores'].items():
                if metric not in quality_metrics:
                    quality_metrics[metric] = []
                quality_metrics[metric].append(value)

        # Calculate statistical measures for each quality metric
        quality_analysis = {}
        for metric, values in quality_metrics.items():
            quality_analysis[metric] = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'consistency': float(1.0 - np.std(values) / np.mean(values)),
                'reliability': float(len([v for v in values 
                                       if v >= self.performance_thresholds['quality_score']]) / 
                                   len(values)),
                'distribution': {
                    'min': float(np.min(values)),
                    'max': float(np.max(values)),
                    'percentiles': {
                        '25': float(np.percentile(values, 25)),
                        '50': float(np.percentile(values, 50)),
                        '75': float(np.percentile(values, 75))
                    }
                }
            }

        return quality_analysis

    def _analyze_resource_usage(self, test_cases: List[Dict]) -> Dict:
        """
        Analyze resource utilization patterns across all tests.
        This helps optimize resource allocation and improve efficiency.
        """
        resource_metrics = {
            'memory_usage': [test['metrics']['peak_memory'] for test in test_cases],
            'processing_time': [test['processing_time'] for test in test_cases]
        }

        if any('peak_gpu_memory' in test['metrics'] for test in test_cases):
            resource_metrics['gpu_memory'] = [
                test['metrics'].get('peak_gpu_memory', 0) for test in test_cases
            ]

        # Calculate resource utilization metrics
        resource_analysis = {}
        for resource, values in resource_metrics.items():
            resource_analysis[resource] = {
                'average_usage': float(np.mean(values)),
                'peak_usage': float(np.max(values)),
                'utilization_pattern': {
                    'steady': float(1.0 - np.std(values) / np.mean(values)),
                    'spiky': bool(np.max(values) / np.mean(values) > 2.0)
                },
                'efficiency_score': float(np.mean(values) / 
                                       self.performance_thresholds.get(resource, np.max(values)))
            }

        return resource_analysis

    def _get_system_info(self) -> Dict:
        """
        Collect system information for benchmark context.
        This helps understand the testing environment.
        """
        return {
            'device': 'cuda' if torch.cuda.is_available() else 'cpu',
            'gpu_info': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            'python_version': platform.python_version(),
            'torch_version': torch.__version__,
            'cpu_count': os.cpu_count(),
            'memory_total': psutil.virtual_memory().total / (1024 * 1024)  # MB
        }

    def _save_results(self, results: Dict):
        """
        Save benchmark results to file with proper formatting.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_dir / f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)