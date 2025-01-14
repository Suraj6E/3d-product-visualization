# models.py
from flask_login import UserMixin
from bson.objectid import ObjectId

class User(UserMixin):
    """
    User class that works with Flask-Login and MongoDB
    This class adapts MongoDB documents to work with Flask-Login's expected interface
    """
    
    def __init__(self, user_doc):
        self.user_doc = user_doc
        
    def get_id(self):
        """Required by Flask-Login, returns the user's ID as a string"""
        return str(self.user_doc.get('_id'))
    
    @property
    def is_active(self):
        """Required by Flask-Login, checks if the user account is active"""
        return self.user_doc.get('active', True)
    
    @property
    def username(self):
        """Returns the user's username"""
        return self.user_doc.get('username')
    
    @property
    def email(self):
        """Returns the user's email"""
        return self.user_doc.get('email')
    
    @property
    def role(self):
        """Returns the user's role"""
        return self.user_doc.get('role', 'user')
    
    @property
    def created_at(self):
        """Returns when the user account was created"""
        return self.user_doc.get('created_at')

    def is_admin(self):
        """Checks if the user has admin privileges"""
        return self.role == 'admin'