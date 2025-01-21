# benchmark_runner.py
import os
from pathlib import Path
from models.enhanced_visualization import Enhanced3DVisualizer
from utils.benchmark_system import BenchmarkSystem

def run_folder_benchmarks(upload_folder="static/uploads"):
    """
    Run benchmarks using existing folders in the uploads directory.
    This function automatically discovers and tests all product folders.
    """
    # Initialize our systems
    visualizer = Enhanced3DVisualizer()
    benchmark = BenchmarkSystem()
    
    # Create test data from existing folders
    test_data = []
    uploads_path = Path(upload_folder)
    
    # Scan through all folders in the uploads directory
    for folder in uploads_path.iterdir():
        if folder.is_dir():
            # Look for front, back, and top view images
            front_image = next(folder.glob("front.*"), None)
            back_image = next(folder.glob("back.*"), None)
            top_image = next(folder.glob("top.*"), None)
            
            # If we have at least one view, add it to test data
            if any([front_image, back_image, top_image]):
                test_case = {
                    'id': folder.name,
                    'front': str(front_image) if front_image else None,
                    'back': str(back_image) if back_image else None,
                    'top': str(top_image) if top_image else None
                }
                test_data.append(test_case)
                print(f"Added test case from folder: {folder.name}")

    if not test_data:
        print("No test cases found in uploads folder!")
        return

    # Run benchmarks
    print(f"\nRunning benchmarks on {len(test_data)} test cases...")
    results = benchmark.run_benchmark(visualizer, test_data)

    # Print detailed analysis
    print("\n=== Benchmark Results ===")
    print(f"\nOverall Performance:")
    print(f"Success Rate: {results['summary']['overall_performance']['success_rate']:.2f}%")
    print(f"Total Tests: {results['summary']['overall_performance']['total_tests']}")
    print(f"Successful Tests: {results['summary']['overall_performance']['successful_tests']}")
    
    print("\nProcessing Stage Analysis:")
    for stage, metrics in results['summary']['stage_analysis'].items():
        print(f"\nStage: {stage}")
        print(f"Average Time: {metrics['time_profile']['mean']:.2f}s")
        print(f"Percentage of Total: {metrics['time_profile']['percentage_of_total']:.2f}%")
        if metrics['quality_profile']['mean']:
            print(f"Quality Score: {metrics['quality_profile']['mean']:.2f}")
    
    print("\nQuality Analysis:")
    for metric, stats in results['summary']['quality_analysis'].items():
        print(f"\n{metric}:")
        print(f"Mean: {stats['mean']:.2f}")
        print(f"Consistency: {stats['consistency']:.2f}")
        print(f"Reliability: {stats['reliability']:.2f}")
    
    print("\nResource Usage:")
    for resource, metrics in results['summary']['resource_usage'].items():
        print(f"\n{resource}:")
        print(f"Average Usage: {metrics['average_usage']:.2f}")
        print(f"Peak Usage: {metrics['peak_usage']:.2f}")
        print(f"Efficiency Score: {metrics['efficiency_score']:.2f}")

    return results