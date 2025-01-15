# database.py

from pymongo import MongoClient
from datetime import datetime

class DatabaseConnection:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._instance is not None:
            raise Exception("This class is a singleton!")
        
        # Initialize MongoDB connection
        self.client = MongoClient('mongodb+srv://3dvis:.7yt_QtvB6fU68J@3dvisualization.eevq2.mongodb.net/')
        self.db = self.client['3dvisualization']
        
        # Initialize collections
        self.metrics = self.db.interaction_metrics
        self.performance_metrics = self.db.performance_metrics
        self.monitoring_queue = self.db.monitoring_queue
        
        # Set up indexes
        self._setup_indexes()

    def _setup_indexes(self):
        # Set up indexes for metrics collection
        self.metrics.create_index([('timestamp', -1)])
        self.metrics.create_index([('folder_name', 1)])
        
        # Set up indexes for performance metrics
        self.performance_metrics.create_index([
            ('timestamp', -1),
            ('folder_name', 1)
        ])
        
        # Set up indexes for monitoring queue
        self.monitoring_queue.create_index([
            ('folder_name', 1),
            ('status', 1)
        ])

# Create a global database instance
db = DatabaseConnection.get_instance()