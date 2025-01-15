# routes/dashboard.py
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from db.manager import feedback_manager

dashboard = Blueprint('dashboard', __name__)

@dashboard.route('/dashboard')
@login_required
def overview():
    """Main dashboard overview"""
    try:
        # Get analytics data
        analytics = feedback_manager.get_overall_analytics()
        platform_data = feedback_manager.get_platform_distribution()
        performance_data = feedback_manager.get_performance_metrics()
        
        return render_template('dashboard/analytics.html',
                             analytics=analytics,
                             platform_data=platform_data,
                             performance_data=performance_data)
    except Exception as e:
        print(f"Error loading dashboard: {str(e)}")
        return render_template('dashboard/analytics.html',
                             analytics={
                                 'avg_rating': 0,
                                 'total_reviews': 0,
                                 'avg_load_time': 0,
                                 'avg_visual_quality': 0,
                                 'recent_feedback': []
                             },
                             platform_data={'labels': [], 'values': []},
                             performance_data={'dates': [], 'load_times': []})

@dashboard.route('/dashboard/feedback')
@login_required
def feedback_analysis():
    """Detailed feedback analysis view"""
    try:
        feedback_data = {
            'ratings_distribution': feedback_manager.get_ratings_distribution(),
            'trends': feedback_manager.get_feedback_trends(),
            'feedback_list': feedback_manager.get_recent_feedback(limit=10)
        }
        return render_template('dashboard/feedback.html', feedback_data=feedback_data)
    except Exception as e:
        print(f"Error loading feedback analysis: {str(e)}")
        return render_template('dashboard/feedback.html', 
                             feedback_data={
                                 'ratings_distribution': {'labels': [], 'values': []},
                                 'trends': {'dates': [], 'ratings': []},
                                 'feedback_list': []
                             })

@dashboard.route('/api/dashboard/performance')
@login_required
def get_performance_data():
    """API endpoint for performance metrics"""
    try:
        performance_trends = feedback_manager.get_performance_trends()
        return jsonify({'success': True, 'data': performance_trends})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})