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

# Create global instances of our managers
user_manager = UserManager()
survey_manager = SurveyManager()
feedback_manager = ProductFeedbackManager()