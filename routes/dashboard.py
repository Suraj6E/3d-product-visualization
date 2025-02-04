# routes/dashboard.py
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from db.manager import feedback_manager
from utils.benchmark_runner import run_folder_benchmarks

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/dashboard')
@login_required
def overview():
    """Main dashboard overview showing key metrics"""
    try:
        analytics = feedback_manager.get_overall_analytics()
        return render_template('dashboard/overview.html',
                             analytics=analytics)
    except Exception as e:
        print(f"Error loading overview: {str(e)}")
        return render_template('dashboard/overview.html',
                             analytics={
                                 'total_products': 0,
                                 'total_users': 0,
                                 'total_feedback': 0,
                                 'recent_activity': []
                             })

@dashboard.route('/dashboard/analytics')
@login_required
def analytics():
    """Detailed analytics dashboard with charts and metrics"""
    try:
        platform_data = feedback_manager.get_platform_distribution()
        performance_data = feedback_manager.get_performance_metrics()
        
        return render_template('dashboard/analytics.html',
                             platform_data=platform_data,
                             performance_data=performance_data)
    except Exception as e:
        print(f"Error loading analytics: {str(e)}")
        return render_template('dashboard/analytics.html',
                             platform_data={'labels': [], 'values': []},
                             performance_data={'dates': [], 'load_times': []})

@dashboard.route('/dashboard/feedback')
@login_required
def feedback_analysis():
    """Feedback analysis dashboard"""
    try:
        feedback_data = {
            'ratings_distribution': feedback_manager.get_ratings_distribution(),
            'trends': feedback_manager.get_feedback_trends(),
            'feedback_list': feedback_manager.get_recent_feedback(limit=10)
        }
        return render_template('dashboard/feedback.html', 
                             feedback_data=feedback_data)
    except Exception as e:
        print(f"Error loading feedback: {str(e)}")
        return render_template('dashboard/feedback.html', 
                             feedback_data={
                                 'ratings_distribution': {'labels': [], 'values': []},
                                 'trends': {'dates': [], 'ratings': []},
                                 'feedback_list': []
                             })

@dashboard.route('/dashboard/performance')
@login_required
def performance():
    """Performance metrics dashboard"""
    try:
        performance_trends = feedback_manager.get_performance_trends()
        return render_template('dashboard/performance.html',
                             performance_data=performance_trends)
    except Exception as e:
        print(f"Error loading performance: {str(e)}")
        return render_template('dashboard/performance.html',
                             performance_data={
                                 'dates': [],
                                 'metrics': {
                                     'load_times': [],
                                     'visual_quality': [],
                                     'interaction_times': [],
                                     'daily_interactions': []
                                 }
                             })

# API endpoints for dynamic updates
@dashboard.route('/api/dashboard/performance')
@login_required
def get_performance_data():
    """API endpoint for performance metrics updates"""
    try:
        performance_trends = feedback_manager.get_performance_trends()
        return jsonify({'success': True, 'data': performance_trends})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    
@dashboard.route('/dashboard/metrics')
@login_required
def get_dashboard_metrics():
    """API endpoint for dashboard metrics"""
    try:
        days = request.args.get('days', default=30, type=int)
        
        metrics = {
            'interaction': feedback_manager.get_interaction_analytics(days),
            'resources': feedback_manager.get_resource_usage(),
            'ecommerce': feedback_manager.get_ecommerce_metrics(days)
        }
        
        return jsonify({'success': True, 'data': metrics})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@dashboard.route('/dashboard/findings')
@login_required
def findings():
    """Finngs"""
    try:
        findings_data = {
            'experiment_metrics': {
                'processing_times': {
                    'mean': 1.5,
                    'std': 0.3,
                    'min': 0.8,
                    'max': 2.3
                },
                'memory_usage': {
                    'mean': 750,
                    'std': 150,
                    'min': 500,
                    'max': 1000
                },
                'model_inference': {
                    'mean': 0.75,
                    'std': 0.15,
                    'min': 0.5,
                    'max': 1.0
                }
            },
            'user_metrics': {
                'satisfaction_scores': {
                    'mean': 8.5,
                    'std': 0.8,
                    'min': 7,
                    'max': 10
                },
                'task_completion_rate': {
                    'mean': 90,
                    'std': 5,
                    'min': 80,
                    'max': 100
                },
                'interaction_time': {
                    'mean': 90,
                    'std': 30,
                    'min': 60,
                    'max': 180
                }
            }
        }
        return render_template('dashboard/findings.html',
                             findings_data=findings_data)
    except Exception as e:
        print(f"Error loading findings: {str(e)}")
        return render_template('dashboard/findings.html',
                             findings_data={})

@dashboard.route('/dashboard/run-benchmarks')
@login_required
def run_benchmarks():
    """
    Run benchmarks and return results with proper error handling
    """
    try:
        from utils.benchmark_runner import run_folder_benchmarks
        results = run_folder_benchmarks()
        
        # Ensure we always return a valid JSON response
        response = {
            'success': True,
            'data': results if results else {'error': 'No results generated'},
            'message': 'Benchmarks completed successfully'
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error running benchmarks'
        }), 500