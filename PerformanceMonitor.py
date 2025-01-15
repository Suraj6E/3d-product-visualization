class PerformanceMonitor:
    """
    Handles detailed performance monitoring and analysis for the 3D visualization system.
    This class provides comprehensive tracking of system performance, resource usage,
    and user interaction patterns.
    """
    def __init__(self):
        self.performance_metrics = db.performance_metrics
        self.setup_indexes()

    def setup_indexes(self):
        """Creates necessary indexes for efficient querying of performance data"""
        self.performance_metrics.create_index([
            ('timestamp', -1),
            ('metric_type', 1)
        ])
        self.performance_metrics.create_index([
            ('folder_name', 1),
            ('timestamp', -1)
        ])

    def record_render_performance(self, folder_name, metrics):
        """
        Records detailed rendering performance metrics
        
        Parameters:
        - folder_name: Name of the product folder
        - metrics: Dictionary containing performance data like frame rate, 
                  render time, and memory usage
        """
        performance_doc = {
            'folder_name': folder_name,
            'timestamp': datetime.utcnow(),
            'metric_type': 'render',
            'frame_rate': metrics.get('frame_rate'),
            'render_time': metrics.get('render_time'),
            'memory_usage': metrics.get('memory_usage'),
            'gpu_usage': metrics.get('gpu_usage'),
            'model_complexity': metrics.get('model_complexity')
        }
        return self.performance_metrics.insert_one(performance_doc)

    def analyze_performance_trends(self, folder_name=None, days=30):
        """
        Analyzes performance trends over time to identify optimizations
        
        Parameters:
        - folder_name: Optional folder name to filter analysis
        - days: Number of days to analyze
        
        Returns:
        - Dictionary containing trend analysis and recommendations
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        match_query = {'timestamp': {'$gte': start_date}}
        
        if folder_name:
            match_query['folder_name'] = folder_name

        pipeline = [
            {'$match': match_query},
            {'$group': {
                '_id': {
                    'folder': '$folder_name',
                    'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}}
                },
                'avg_frame_rate': {'$avg': '$frame_rate'},
                'avg_render_time': {'$avg': '$render_time'},
                'avg_memory_usage': {'$avg': '$memory_usage'},
                'avg_gpu_usage': {'$avg': '$gpu_usage'}
            }},
            {'$sort': {'_id.date': 1}}
        ]

        results = list(self.performance_metrics.aggregate(pipeline))
        
        # Analyze trends and generate recommendations
        recommendations = self._generate_optimization_recommendations(results)
        
        return {
            'trends': results,
            'recommendations': recommendations
        }

    def _generate_optimization_recommendations(self, performance_data):
        """
        Generates optimization recommendations based on performance trends
        
        Parameters:
        - performance_data: List of performance metrics over time
        
        Returns:
        - List of recommendations for performance optimization
        """
        recommendations = []
        
        # Analyze frame rate trends
        frame_rates = [d['avg_frame_rate'] for d in performance_data if d['avg_frame_rate']]
        if frame_rates:
            avg_frame_rate = sum(frame_rates) / len(frame_rates)
            if avg_frame_rate < 30:
                recommendations.append({
                    'type': 'frame_rate',
                    'severity': 'high',
                    'message': 'Consider reducing model complexity or implementing level-of-detail systems',
                    'metric': avg_frame_rate
                })

        # Analyze memory usage trends
        memory_usage = [d['avg_memory_usage'] for d in performance_data if d['avg_memory_usage']]
        if memory_usage:
            avg_memory = sum(memory_usage) / len(memory_usage)
            if avg_memory > 500:  # 500MB threshold
                recommendations.append({
                    'type': 'memory',
                    'severity': 'medium',
                    'message': 'Implement progressive loading or geometry compression',
                    'metric': avg_memory
                })

        # Analyze render time trends
        render_times = [d['avg_render_time'] for d in performance_data if d['avg_render_time']]
        if render_times:
            avg_render_time = sum(render_times) / len(render_times)
            if avg_render_time > 100:  # 100ms threshold
                recommendations.append({
                    'type': 'render_time',
                    'severity': 'high',
                    'message': 'Consider implementing render optimization techniques',
                    'metric': avg_render_time
                })

        return recommendations

    def get_optimization_score(self, folder_name):
        """
        Calculates an overall optimization score for a product visualization
        
        Parameters:
        - folder_name: Name of the product folder
        
        Returns:
        - Score from 0-100 indicating optimization level
        """
        recent_metrics = self.performance_metrics.find({
            'folder_name': folder_name,
            'timestamp': {
                '$gte': datetime.utcnow() - timedelta(days=7)
            }
        }).limit(100)

        metrics = list(recent_metrics)
        if not metrics:
            return None

        # Calculate subscores
        frame_rate_score = self._calculate_frame_rate_score(metrics)
        memory_score = self._calculate_memory_score(metrics)
        render_time_score = self._calculate_render_time_score(metrics)

        # Weight the scores (adjust weights based on importance)
        total_score = (
            frame_rate_score * 0.4 +
            memory_score * 0.3 +
            render_time_score * 0.3
        )

        return round(total_score, 2)

    def _calculate_frame_rate_score(self, metrics):
        """Calculate score based on frame rate performance"""
        frame_rates = [m['frame_rate'] for m in metrics if 'frame_rate' in m]
        if not frame_rates:
            return 0
        avg_frame_rate = sum(frame_rates) / len(frame_rates)
        return min(100, (avg_frame_rate / 60) * 100)  # 60 FPS = 100 score

    def _calculate_memory_score(self, metrics):
        """Calculate score based on memory usage"""
        memory_usage = [m['memory_usage'] for m in metrics if 'memory_usage' in m]
        if not memory_usage:
            return 0
        avg_memory = sum(memory_usage) / len(memory_usage)
        return max(0, 100 - (avg_memory / 10))  # Lower memory usage = higher score

    def _calculate_render_time_score(self, metrics):
        """Calculate score based on render time performance"""
        render_times = [m['render_time'] for m in metrics if 'render_time' in m]
        if not render_times:
            return 0
        avg_render_time = sum(render_times) / len(render_times)
        return max(0, 100 - (avg_render_time / 2))  # Lower render time = higher score

# Create an instance of the performance monitor
performance_monitor = PerformanceMonitor()