# database.py
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from datetime import datetime

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
    """Handles all product feedback-related database operations"""
    def __init__(self):
        self.feedback = db.product_feedback

    def create_feedback(self, user_id, folder_name, feedback_data):
        """Creates new product feedback"""
        feedback_doc = {
            'user_id': user_id,
            'folder_name': folder_name,
            'rating': feedback_data.get('rating'),
            'comment': feedback_data.get('comment'),
            'timestamp': datetime.utcnow(),
            'load_time': feedback_data.get('load_time'),
            'visual_quality_score': feedback_data.get('visual_quality_score'),
            'platform_info': feedback_data.get('platform_info')
        }
        return self.feedback.insert_one(feedback_doc)

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
    

# manager.py additions

class ProductFeedbackManager:
    def __init__(self):
        self.feedback = db.product_feedback
        self.setup_indexes()

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
    
    # Add this to your ProductFeedbackManager class
    def insert_test_data(self):
        """
        Inserts sample data for testing the dashboard
        """
        import random
        from datetime import datetime, timedelta
        
        platforms = ['Windows', 'MacOS', 'Linux', 'iOS', 'Android']
        
        # Generate 30 days of test data
        for i in range(30):
            date = datetime.utcnow() - timedelta(days=i)
            
            # Create 5 feedback entries per day
            for _ in range(5):
                feedback_doc = {
                    'user_id': ObjectId(),  # Random ObjectId for testing
                    'product_id': 'test_product',
                    'rating': random.randint(1, 10),
                    'comment': f'Test feedback comment {i}',
                    'timestamp': date,
                    'metrics': {
                        'load_time': random.uniform(100, 2000),  # 100ms to 2000ms
                        'visual_quality_score': random.uniform(5, 10),
                        'interaction_time': random.uniform(10, 300),  # 10s to 300s
                        'browser_info': 'Chrome',
                        'platform': random.choice(platforms),
                        'screen_resolution': '1920x1080'
                    },
                    'visualization_type': '3D',
                    'processed_views': ['front', 'back', 'top']
                }
                self.feedback.insert_one(feedback_doc)
    


# Create global instances of our managers
user_manager = UserManager()
survey_manager = SurveyManager()
feedback_manager = ProductFeedbackManager()

