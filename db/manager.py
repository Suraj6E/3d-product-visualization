# database.py
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime, timedelta

# Initialize MongoDB connection
client = MongoClient('mongodb+srv://3dvis:.7yt_QtvB6fU68J@3dvisualization.eevq2.mongodb.net/')
db = client['3dvisualization']  # Your database name

class UserManager:
    """
    Handles all user-related database operations.
    This class provides an abstraction layer between your application and MongoDB.
    """
    def __init__(self):
        self.users = db.users
        self.setup_indexes()

    def setup_indexes(self):
        """Creates necessary indexes for the users collection"""
        # Create unique indexes for email and username
        self.users.create_index('email', unique=True)
        self.users.create_index('username', unique=True)

    def create_user(self, username, email, password):
        """
        Creates a new user in the database
        Returns user document if successful, None if user already exists
        """
        try:
            user_doc = {
                'username': username,
                'email': email,
                'password_hash': generate_password_hash(password),
                'created_at': datetime.utcnow(),
                'role': 'user',
                'active': True
            }
            result = self.users.insert_one(user_doc)
            user_doc['_id'] = result.inserted_id
            return user_doc
        except Exception as e:
            print(f"Error creating user: {e}")
            return None

    def get_user_by_email(self, email):
        """Retrieves a user by email"""
        return self.users.find_one({'email': email})

    def get_user_by_id(self, user_id):
        """Retrieves a user by ID"""
        if not isinstance(user_id, ObjectId):
            try:
                user_id = ObjectId(user_id)
            except:
                return None
        return self.users.find_one({'_id': user_id})

    def verify_password(self, user_doc, password):
        """Verifies a user's password"""
        if not user_doc:
            return False
        return check_password_hash(user_doc['password_hash'], password)

class SurveyManager:
    """Handles all survey-related database operations"""
    def __init__(self):
        self.surveys = db.surveys

    def create_survey(self, user_id, survey_data):
        """Creates a new survey submission"""
        survey_doc = {
            'user_id': user_id,
            'submission_date': datetime.utcnow(),
            'ease_of_use': survey_data.get('ease_of_use'),
            'visual_quality': survey_data.get('visual_quality'),
            'loading_speed': survey_data.get('loading_speed'),
            'feature_completeness': survey_data.get('feature_completeness'),
            'comments': survey_data.get('comments')
        }
        return self.surveys.insert_one(survey_doc)


    
    
class ProductFeedbackManager:
    def __init__(self):
        self.feedback = db.product_feedback
        self.setup_indexes()


    def create_feedback(self, user_id, product_id, feedback_data):
        """Creates new product feedback with comprehensive metrics"""
        try:
            feedback_doc = {
                'user_id': ObjectId(user_id),
                'product_id': product_id,
                'rating': feedback_data.get('rating'),
                'comment': feedback_data.get('comment'),
                'timestamp': datetime.utcnow(),
                'metrics': {
                    # Load time and performance metrics
                    'load_time': feedback_data.get('load_time'),
                    'processing_time': feedback_data.get('processing_time'),
                    'visual_quality_score': feedback_data.get('visual_quality_score'),
                    'interaction_time': feedback_data.get('interaction_time'),
                    
                    # System metrics
                    'browser_info': feedback_data.get('browser_info'),
                    'platform': feedback_data.get('platform'),
                    'screen_resolution': feedback_data.get('screen_resolution'),
                    'memory_usage': feedback_data.get('memory_usage'),
                    'cpu_usage': feedback_data.get('cpu_usage'),
                    
                    # Interaction metrics
                    'feature_usage': {
                        'rotation': feedback_data.get('rotation_count', 0),
                        'zoom': feedback_data.get('zoom_count', 0),
                        'pan': feedback_data.get('pan_count', 0)
                    }
                },
                'visualization_type': feedback_data.get('visualization_type', '3D'),
                'processed_views': feedback_data.get('processed_views', []),
                'session_data': {
                    'start_time': feedback_data.get('session_start'),
                    'end_time': feedback_data.get('session_end'),
                    'total_duration': feedback_data.get('session_duration')
                }
            }
            return self.feedback.insert_one(feedback_doc)
        except Exception as e:
            print(f"Error creating feedback: {str(e)}")
            return None

    def get_folder_feedback(self, folder_name):
        """Retrieves all feedback for a specific folder"""
        return list(self.feedback.find({'folder_name': folder_name}).sort('timestamp', -1))
    def get_overall_analytics(self):
        """
        Gets overall analytics across all products.
        Returns aggregated metrics for the entire platform.
        """
        pipeline = [
            {
                '$facet': {
                    'ratings': [
                        {'$group': {
                            '_id': None,
                            'avg_rating': {'$avg': '$rating'},
                            'total_reviews': {'$sum': 1}
                        }}
                    ],
                    'performance': [
                        {'$group': {
                            '_id': None,
                            'avg_load_time': {'$avg': '$metrics.load_time'},
                            'avg_visual_quality': {'$avg': '$metrics.visual_quality_score'}
                        }}
                    ],
                    'recent_activity': [
                        {'$sort': {'timestamp': -1}},
                        {'$limit': 5}
                    ]
                }
            }
        ]
        
        results = list(self.feedback.aggregate(pipeline))
        
        if not results or not results[0]['ratings'] or not results[0]['performance']:
            # Return default values if no data exists
            return {
                'avg_rating': 0,
                'total_reviews': 0,
                'avg_load_time': 0,
                'avg_visual_quality': 0,
                'recent_feedback': []
            }
        
        analytics_data = {
            'avg_rating': results[0]['ratings'][0]['avg_rating'],
            'total_reviews': results[0]['ratings'][0]['total_reviews'],
            'avg_load_time': results[0]['performance'][0]['avg_load_time'],
            'avg_visual_quality': results[0]['performance'][0]['avg_visual_quality'],
            'recent_feedback': results[0]['recent_activity']
        }
        
        return analytics_data
    def get_platform_distribution(self):
        """Gets platform distribution data in a format ready for charts"""
        pipeline = [
            {'$group': {
                '_id': '$metrics.platform',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        
        results = list(self.feedback.aggregate(pipeline))
        
        return {
            'labels': [r['_id'] for r in results],
            'values': [r['count'] for r in results]
        }

    def get_performance_metrics(self):
        """Gets performance metrics over time"""
        pipeline = [
            {'$group': {
                '_id': {
                    '$dateToString': {
                        'format': '%Y-%m-%d',
                        'date': '$timestamp'
                    }
                },
                'avg_load_time': {'$avg': '$metrics.load_time'}
            }},
            {'$sort': {'_id': 1}}
        ]
        
        results = list(self.feedback.aggregate(pipeline))
        
        return {
            'dates': [r['_id'] for r in results],
            'load_times': [r['avg_load_time'] for r in results]
        }
    def get_performance_trends(self):
        """
        Gets performance trends over time.
        Returns daily aggregated metrics for charting.
        """
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'date': {
                            '$dateToString': {
                                'format': '%Y-%m-%d',
                                'date': '$timestamp'
                            }
                        }
                    },
                    'avg_load_time': {'$avg': '$metrics.load_time'},
                    'avg_rating': {'$avg': '$rating'},
                    'avg_visual_quality': {'$avg': '$metrics.visual_quality_score'},
                    'total_reviews': {'$sum': 1}
                }
            },
            {'$sort': {'_id.date': 1}},
            {'$limit': 30}  # Last 30 days of data
        ]
        
        results = list(self.feedback.aggregate(pipeline))
        
        return {
            'dates': [r['_id']['date'] for r in results],
            'metrics': {
                'load_times': [r['avg_load_time'] for r in results],
                'ratings': [r['avg_rating'] for r in results],
                'visual_quality': [r['avg_visual_quality'] for r in results],
                'daily_reviews': [r['total_reviews'] for r in results]
            }
        }

    def setup_indexes(self):
        """Creates necessary indexes for feedback collection"""
        self.feedback.create_index([('user_id', 1), ('product_id', 1)])
        self.feedback.create_index('timestamp')
        self.feedback.create_index('rating')

    def create_feedback(self, user_id, product_id, feedback_data):
        """Creates new product feedback with detailed metrics"""
        feedback_doc = {
            'user_id': ObjectId(user_id),
            'product_id': product_id,
            'rating': feedback_data.get('rating'),
            'comment': feedback_data.get('comment'),
            'timestamp': datetime.utcnow(),
            'metrics': {
                'load_time': feedback_data.get('load_time'),
                'visual_quality_score': feedback_data.get('visual_quality_score'),
                'interaction_time': feedback_data.get('interaction_time'),
                'browser_info': feedback_data.get('browser_info'),
                'platform': feedback_data.get('platform'),
                'screen_resolution': feedback_data.get('screen_resolution')
            },
            'visualization_type': feedback_data.get('visualization_type', '3D'),
            'processed_views': feedback_data.get('processed_views', [])
        }
        return self.feedback.insert_one(feedback_doc)

    def get_product_analytics(self, product_id):
        """Gets aggregated analytics for a product"""
        pipeline = [
            {'$match': {'product_id': product_id}},
            {'$group': {
                '_id': None,
                'avg_rating': {'$avg': '$rating'},
                'total_reviews': {'$sum': 1},
                'avg_load_time': {'$avg': '$metrics.load_time'},
                'avg_visual_quality': {'$avg': '$metrics.visual_quality_score'},
                'platform_distribution': {'$push': '$metrics.platform'}
            }}
        ]
        return list(self.feedback.aggregate(pipeline))

    def get_user_feedback_history(self, user_id):
        """Gets all feedback from a specific user"""
        return list(self.feedback.find({'user_id': ObjectId(user_id)}).sort('timestamp', -1))
    
    def get_performance_trends(self):
        """
        Gets detailed performance trends over time, including load times, 
        visual quality scores, and interaction metrics.
        """
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'date': {
                            '$dateToString': {
                                'format': '%Y-%m-%d',
                                'date': '$timestamp'
                            }
                        }
                    },
                    'avg_load_time': {'$avg': '$metrics.load_time'},
                    'avg_visual_quality': {'$avg': '$metrics.visual_quality_score'},
                    'avg_interaction_time': {'$avg': '$metrics.interaction_time'},
                    'total_interactions': {'$sum': 1}
                }
            },
            {'$sort': {'_id.date': 1}},
            {'$limit': 30}  # Get last 30 days of data
        ]
        
        results = list(self.feedback.aggregate(pipeline))
        
        # If no results, return empty dataset with proper structure
        if not results:
            return {
                'dates': [],
                'metrics': {
                    'load_times': [],
                    'visual_quality': [],
                    'interaction_times': [],
                    'daily_interactions': []
                }
            }
        
        return {
            'dates': [r['_id']['date'] for r in results],
            'metrics': {
                'load_times': [r['avg_load_time'] for r in results],
                'visual_quality': [r['avg_visual_quality'] for r in results],
                'interaction_times': [r['avg_interaction_time'] for r in results],
                'daily_interactions': [r['total_interactions'] for r in results]
            }
        }
    
    # # Add this to your ProductFeedbackManager class
    # def insert_test_data(self):
    #     """
    #     Inserts sample data for testing the dashboard
    #     """
    #     import random
    #     from datetime import datetime, timedelta
        
    #     platforms = ['Windows', 'MacOS', 'Linux', 'iOS', 'Android']
        
    #     # Generate 30 days of test data
    #     for i in range(30):
    #         date = datetime.utcnow() - timedelta(days=i)
            
    #         # Create 5 feedback entries per day
    #         for _ in range(5):
    #             feedback_doc = {
    #                 'user_id': ObjectId(),  # Random ObjectId for testing
    #                 'product_id': 'test_product',
    #                 'rating': random.randint(1, 10),
    #                 'comment': f'Test feedback comment {i}',
    #                 'timestamp': date,
    #                 'metrics': {
    #                     'load_time': random.uniform(100, 2000),  # 100ms to 2000ms
    #                     'visual_quality_score': random.uniform(5, 10),
    #                     'interaction_time': random.uniform(10, 300),  # 10s to 300s
    #                     'browser_info': 'Chrome',
    #                     'platform': random.choice(platforms),
    #                     'screen_resolution': '1920x1080'
    #                 },
    #                 'visualization_type': '3D',
    #                 'processed_views': ['front', 'back', 'top']
    #             }
    #             self.feedback.insert_one(feedback_doc)
    def get_overall_analytics(self):
        """Gets comprehensive analytics for the overview dashboard"""
        try:
            # Basic metrics with trends
            basic_metrics = self._get_basic_metrics()
            activity_data = self._get_activity_data()
            system_health = self._get_system_health()
            recent_activity = self._get_recent_activity()

            return {
                # Basic Metrics
                'total_products': basic_metrics['total_products'],
                'product_growth': basic_metrics['product_growth'],
                'active_users': basic_metrics['active_users'],
                'user_growth': basic_metrics['user_growth'],
                'avg_processing_time': basic_metrics['avg_processing_time'],
                'processing_improvement': basic_metrics['processing_improvement'],
                'satisfaction_score': basic_metrics['satisfaction_score'],
                'satisfaction_change': basic_metrics['satisfaction_change'],

                # Activity Data for Charts
                'activity_data': activity_data,
                'peak_usage_times': self._get_peak_usage_times(),
                'top_platforms': self._get_top_platforms(),
                
                # Performance Data
                'performance_data': self._get_performance_data(),
                'top_product': self._get_top_performing_product(),
                'improvement_areas': self._get_improvement_areas(),

                # Recent Activity
                'recent_activity': recent_activity,

                # System Health
                'storage_usage': system_health['storage_usage'],
                'storage_total': system_health['storage_total'],
                'queue_status': system_health['queue_status'],
                'queue_length': system_health['queue_length'],
                'avg_queue_time': system_health['avg_queue_time'],
                'error_rate': system_health['error_rate'],
                'total_errors': system_health['total_errors']
            }
        except Exception as e:
            print(f"Error getting overall analytics: {str(e)}")
            return self._get_default_analytics()

    def _get_basic_metrics(self):
        """
        Gets basic metrics with trend calculations.
        Returns a dictionary with all necessary metrics, using defaults when data is unavailable.
        """
        try:
            # Get current period metrics
            current_pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': datetime.utcnow() - timedelta(days=30)
                        }
                    }
                },
                {
                    '$facet': {
                        'products': [
                            {'$group': {'_id': '$product_id'}},
                            {'$count': 'count'}
                        ],
                        'users': [
                            {'$group': {'_id': '$user_id'}},
                            {'$count': 'count'}
                        ],
                        'processing_times': [
                            {'$group': {
                                '_id': None,
                                'avg_time': {'$avg': '$metrics.load_time'}
                            }}
                        ],
                        'satisfaction': [
                            {'$group': {
                                '_id': None,
                                'avg_rating': {'$avg': '$rating'}
                            }}
                        ]
                    }
                }
            ]

            current_results = list(self.feedback.aggregate(current_pipeline))
            
            # Extract values with safe defaults
            if current_results and len(current_results) > 0:
                results = current_results[0]
                total_products = results['products'][0]['count'] if results['products'] else 0
                active_users = results['users'][0]['count'] if results['users'] else 0
                avg_processing = results['processing_times'][0]['avg_time'] if results['processing_times'] else 0
                satisfaction = results['satisfaction'][0]['avg_rating'] if results['satisfaction'] else 0
            else:
                total_products = 0
                active_users = 0
                avg_processing = 0
                satisfaction = 0

            # Calculate growth rates by comparing with previous period
            prev_month = datetime.utcnow() - timedelta(days=60)
            this_month = datetime.utcnow() - timedelta(days=30)
            
            product_growth = self._calculate_growth_rate('product_id', prev_month, this_month)
            user_growth = self._calculate_growth_rate('user_id', prev_month, this_month)
            processing_improvement = self._calculate_processing_improvement(prev_month, this_month)
            satisfaction_change = self._calculate_satisfaction_change(prev_month, this_month)

            return {
                'total_products': total_products,
                'product_growth': product_growth,
                'active_users': active_users,
                'user_growth': user_growth,
                'avg_processing_time': avg_processing,
                'processing_improvement': processing_improvement,
                'satisfaction_score': satisfaction,
                'satisfaction_change': satisfaction_change
            }

        except Exception as e:
            print(f"Error calculating basic metrics: {str(e)}")
            # Return safe default values if calculation fails
            return {
                'total_products': 0,
                'product_growth': 0,
                'active_users': 0,
                'user_growth': 0,
                'avg_processing_time': 0,
                'processing_improvement': 0,
                'satisfaction_score': 0,
                'satisfaction_change': 0
            }

    def _calculate_growth_rate(self, field, start_date, end_date):
        """
        Calculates the growth rate for a specific field between two dates.
        Returns percentage growth rate.
        """
        try:
            # Get counts for both periods
            previous_count = self.feedback.count_documents({
                'timestamp': {'$gte': start_date, '$lt': end_date}
            })
            
            current_count = self.feedback.count_documents({
                'timestamp': {'$gte': end_date}
            })

            if previous_count == 0:
                return 0
                
            growth_rate = ((current_count - previous_count) / previous_count) * 100
            return round(growth_rate, 1)
            
        except Exception as e:
            print(f"Error calculating growth rate: {str(e)}")
            return 0

    def _calculate_growth(self, field):
        """Calculates growth percentage for a given field"""
        # Implementation for growth calculation
        return 5  # Placeholder

    def _get_activity_data(self):
        """Gets user activity data for charting"""
        pipeline = [
            {
                '$group': {
                    '_id': {
                        'date': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$timestamp'}}
                    },
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'_id.date': 1}},
            {'$limit': 30}
        ]
        
        results = list(self.feedback.aggregate(pipeline))
        
        return {
            'dates': [r['_id']['date'] for r in results],
            'counts': [r['count'] for r in results]
        }

    def _get_system_health(self):
        """Gets system health metrics"""
        # Implementation for system health metrics
        return {
            'storage_usage': 45,
            'storage_total': 1000,
            'queue_status': 'normal',
            'queue_length': 5,
            'avg_queue_time': 2.3,
            'error_rate': 0.5,
            'total_errors': 12
        }
    
    def _get_default_analytics(self):
        """
        Provides default analytics values when actual data cannot be retrieved.
        This ensures our dashboard doesn't break when data is missing.
        """
        return {
            # Basic Metrics
            'total_products': 0,
            'product_growth': 0,
            'active_users': 0,
            'user_growth': 0,
            'avg_processing_time': 0,
            'processing_improvement': 0,
            'satisfaction_score': 0,
            'satisfaction_change': 0,

            # Activity Data
            'activity_data': {
                'dates': [],
                'counts': []
            },
            'peak_usage_times': 'No data available',
            'top_platforms': 'No data available',
            
            # Performance Data
            'performance_data': {
                'products': [],
                'scores': []
            },
            'top_product': 'No data available',
            'improvement_areas': 'No data available',

            # Recent Activity
            'recent_activity': [],

            # System Health
            'storage_usage': 0,
            'storage_total': 100,
            'queue_status': 'normal',
            'queue_length': 0,
            'avg_queue_time': 0,
            'error_rate': 0,
            'total_errors': 0
        }
    def get_user_interaction_metrics(self):
        """
        Analyzes user interaction patterns and behaviors
        """
        return {
            'interaction_patterns': {
                'avg_session_duration': 0,
                'interaction_frequency': 0,
                'feature_usage': {
                    'model_rotation': 0,
                    'zoom_actions': 0,
                    'measurement_tools': 0
                },
                'completion_rates': 0
            },
            'user_journey': {
                'entry_points': [],
                'drop_off_points': [],
                'conversion_path': []
            }
        }
    
    def get_interaction_analytics(self, days=30):
        """Get user interaction analytics with fallback for missing data"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': start_date,
                            '$lte': end_date
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'avg_session_duration': {'$avg': '$metrics.interaction_time'},
                        'total_interactions': {'$sum': 1},
                        'completed_sessions': {
                            '$sum': {
                                '$cond': [{'$gt': ['$metrics.interaction_time', 0]}, 1, 0]
                            }
                        }
                    }
                }
            ]
            
            results = list(self.feedback.aggregate(pipeline))
            
            if results:
                data = results[0]
                completion_rate = (data['completed_sessions'] / data['total_interactions'] * 100 
                                if data['total_interactions'] > 0 else 0)
                
                return {
                    'session_duration': round(data['avg_session_duration'] or 0, 2),
                    'interaction_frequency': round(data['total_interactions'] / days, 2),
                    'completion_rate': round(completion_rate, 2)
                }
            
            return self._get_default_interaction_metrics()
            
        except Exception as e:
            print(f"Error getting interaction analytics: {str(e)}")
            return self._get_default_interaction_metrics()
    
    def get_resource_usage(self):
        """Get system resource usage metrics"""
        try:
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'avg_cpu_usage': {'$avg': '$metrics.cpu_usage'},
                        'avg_memory_usage': {'$avg': '$metrics.memory_usage'},
                        'processing_times': {'$push': '$metrics.load_time'}
                    }
                }
            ]
            
            results = list(self.feedback.aggregate(pipeline))
            
            if results:
                data = results[0]
                return {
                    'cpu_usage': round(data['avg_cpu_usage'] or 0, 2),
                    'memory_usage': round(data['avg_memory_usage'] or 0, 2),
                    'processing_times': data['processing_times'] or []
                }
            
            return self._get_default_resource_metrics()
            
        except Exception as e:
            print(f"Error getting resource usage: {str(e)}")
            return self._get_default_resource_metrics()

    def get_ecommerce_metrics(self, days=30):
        """Get e-commerce related metrics"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            pipeline = [
                {
                    '$match': {
                        'timestamp': {
                            '$gte': start_date,
                            '$lte': end_date
                        }
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_views': {'$sum': 1},
                        'purchases': {
                            '$sum': {
                                '$cond': [{'$eq': ['$interaction_type', 'purchase']}, 1, 0]
                            }
                        },
                        'avg_time_to_purchase': {'$avg': '$metrics.time_to_purchase'}
                    }
                }
            ]
            
            results = list(self.feedback.aggregate(pipeline))
            
            if results:
                data = results[0]
                conversion_rate = (data['purchases'] / data['total_views'] * 100 
                                if data['total_views'] > 0 else 0)
                
                return {
                    'conversion_rate': round(conversion_rate, 2),
                    'avg_purchase_time': round(data['avg_time_to_purchase'] or 0, 2),
                    'total_views': data['total_views'],
                    'total_purchases': data['purchases']
                }
            
            return self._get_default_ecommerce_metrics()
            
        except Exception as e:
            print(f"Error getting e-commerce metrics: {str(e)}")
            return self._get_default_ecommerce_metrics()

    # Default metric methods
    def _get_default_interaction_metrics(self):
        return {
            'session_duration': 0,
            'interaction_frequency': 0,
            'completion_rate': 0
        }

    def _get_default_resource_metrics(self):
        return {
            'cpu_usage': 0,
            'memory_usage': 0,
            'processing_times': []
        }

    def _get_default_ecommerce_metrics(self):
        return {
            'conversion_rate': 0,
            'avg_purchase_time': 0,
            'total_views': 0,
            'total_purchases': 0
        }
        



# Create global instances of our managers
user_manager = UserManager()
survey_manager = SurveyManager()
feedback_manager = ProductFeedbackManager()