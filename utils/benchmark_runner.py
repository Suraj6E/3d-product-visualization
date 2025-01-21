# benchmark_runner.py
import os
from pathlib import Path
from models.enhanced_visualization import Enhanced3DVisualizer
from utils.benchmark_system import BenchmarkSystem
from typing import Dict, List
import datetime
import json

def run_folder_benchmarks(upload_folder="static/uploads") -> Dict:
    """
    Run benchmarks using existing folders in the uploads directory.
    Returns a properly structured result even if some tests fail.
    """
    visualizer = Enhanced3DVisualizer()
    benchmark = BenchmarkSystem()
    
    # Create test data from existing folders
    test_data = []
    uploads_path = Path(upload_folder)
    
    print("\nScanning for test cases...")
    for folder in uploads_path.iterdir():
        if folder.is_dir():
            front_image = next(folder.glob("front.*"), None)
            back_image = next(folder.glob("back.*"), None)
            top_image = next(folder.glob("top.*"), None)
            
            if any([front_image, back_image, top_image]):
                test_case = {
                    'id': folder.name,
                    'front': str(front_image) if front_image else None,
                    'back': str(back_image) if back_image else None,
                    'top': str(top_image) if top_image else None
                }
                test_data.append(test_case)
                print(f"Found test case: {folder.name}")

    if not test_data:
        return {
            'success': False,
            'error': 'No test cases found',
            'summary': get_empty_summary()
        }

    print(f"\nRunning benchmarks on {len(test_data)} test cases...")
    try:
        results = benchmark.run_benchmark(visualizer, test_data)
        success_rate = calculate_success_rate(results)
        
        print("\n=== Benchmark Results ===")
        print(f"\nOverall Performance:")
        print(f"Success Rate: {success_rate:.2f}%")
        
        if 'stage_analysis' in results.get('summary', {}):
            print("\nProcessing Stage Analysis:")
            for stage, metrics in results['summary']['stage_analysis'].items():
                print(f"\nStage: {stage}")
                print(f"Average Time: {metrics['time_profile'].get('mean', 0):.2f}s")
                if metrics.get('quality_profile', {}).get('mean'):
                    print(f"Quality Score: {metrics['quality_profile']['mean']:.2f}")
        
        return results
        
    except Exception as e:
        print(f"\nError running benchmarks: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'summary': get_empty_summary()
        }

def get_empty_summary():
    """
    Create an empty summary structure for when processing fails
    """
    return {
        'overall_performance': {
            'success_rate': 0,
            'total_tests': 0,
            'successful_tests': 0
        },
        'stage_analysis': {},
        'quality_analysis': {},
        'resource_usage': {}
    }

def calculate_success_rate(results: Dict) -> float:
    """
    Safely calculate success rate from results
    """
    if not results or 'summary' not in results:
        return 0.0
    
    summary = results['summary']
    total = summary.get('total_tests', 0)
    successful = summary.get('successful_tests', 0)
    
    return (successful / total * 100) if total > 0 else 0.0

# Save benchmark results to file
def save_benchmark_results(results: Dict, output_dir: str = "benchmarks"):
    """
    Save benchmark results to a JSON file
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"benchmark_results_{timestamp}.json")
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nBenchmark results saved to: {filename}")