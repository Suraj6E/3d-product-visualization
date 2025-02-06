# models.py
from flask_login import UserMixin
from bson.objectid import ObjectId

class User(UserMixin):
    def __init__(self, user_doc):
        self.user_doc = user_doc
        
    def get_id(self):
        return str(self.user_doc.get('_id'))
    
    @property
    def is_active(self):
        return self.user_doc.get('active', True)
    
    @property
    def username(self):
        return self.user_doc.get('username')
    
    @property
    def email(self):
        return self.user_doc.get('email')
    
    @property
    def role(self):
        return self.user_doc.get('role', 'user')
    
    @property
    def created_at(self):
        return self.user_doc.get('created_at')
    
    @property
    def google_id(self):
        return self.user_doc.get('google_id')
    
    @property
    def is_google_user(self):
        return bool(self.google_id)

    def is_admin(self):
        return self.role == 'admin'