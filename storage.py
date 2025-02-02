# storage.py
from abc import ABC, abstractmethod
import os
import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename
from flask import current_app, url_for
from functools import lru_cache

class StorageManager(ABC):
    @abstractmethod
    def save_file(self, file, folder_name, filename):
        pass
    
    @abstractmethod
    def get_file_url(self, folder_name, filename):
        pass
    
    @abstractmethod
    def list_files(self, folder_name):
        pass
    
    @abstractmethod
    def file_exists(self, folder_name, filename):
        pass
    @abstractmethod
    def list_folders(self):
        pass

class LocalStorageManager(StorageManager):
    def __init__(self, upload_folder):
        self.upload_folder = upload_folder

    def save_file(self, file, folder_name, filename):
        folder_path = os.path.join(self.upload_folder, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        filepath = os.path.join(folder_path, secure_filename(filename))
        file.save(filepath)
        return filepath

    def get_file_url(self, folder_name, filename):
        return url_for('static', 
                      filename=f'uploads/{folder_name}/{filename}')

    def list_files(self, folder_name):
        folder_path = os.path.join(self.upload_folder, folder_name)
        if not os.path.exists(folder_path):
            return []
        return [f for f in os.listdir(folder_path) 
                if os.path.isfile(os.path.join(folder_path, f))]

    def file_exists(self, folder_name, filename):
        filepath = os.path.join(self.upload_folder, folder_name, filename)
        return os.path.exists(filepath)
    
    def list_folders(self):
        """List all folders in the upload directory"""
        if not os.path.exists(self.upload_folder):
            return []
        return [f for f in os.listdir(self.upload_folder) 
                if os.path.isdir(os.path.join(self.upload_folder, f))]

class S3StorageManager(StorageManager):
    def __init__(self, bucket_name, aws_access_key_id=None, 
                 aws_secret_access_key=None, region=None):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region
        )

    def save_file(self, file, folder_name, filename):
        s3_path = f"{folder_name}/{secure_filename(filename)}"
        try:
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                s3_path,
                ExtraArgs={'ContentType': file.content_type}
            )
            return s3_path
        except ClientError as e:
            current_app.logger.error(f"Error uploading to S3: {str(e)}")
            raise

    def get_file_url(self, folder_name, filename):
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': f"{folder_name}/{filename}"
                },
                ExpiresIn=3600  # URL expires in 1 hour
            )
        except ClientError as e:
            current_app.logger.error(f"Error generating presigned URL: {str(e)}")
            raise

    def list_files(self, folder_name):
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"{folder_name}/"
            )
            files = []
            for obj in response.get('Contents', []):
                filename = os.path.basename(obj['Key'])
                if filename:  # Skip empty filenames (folder objects)
                    files.append(filename)
            return files
        except ClientError as e:
            current_app.logger.error(f"Error listing S3 objects: {str(e)}")
            raise

    def file_exists(self, folder_name, filename):
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=f"{folder_name}/{filename}"
            )
            return True
        except ClientError:
            return False
        
    def list_folders(self):
        """List all folders in the S3 bucket"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Delimiter='/'
            )
            folders = []
            for prefix in response.get('CommonPrefixes', []):
                folder = prefix['Prefix'].rstrip('/')
                if folder:  # Skip empty folder names
                    folders.append(folder)
            return folders
        except ClientError as e:
            current_app.logger.error(f"Error listing S3 folders: {str(e)}")
            raise
    


def create_storage_manager(app):
    """Creates a storage manager instance based on configuration"""
    if app.config.get('FLASK_ENV') == 'production':
        return S3StorageManager(
            bucket_name=app.config['AWS_BUCKET_NAME'],
            aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY'],
            region=app.config['AWS_REGION']
        )
    else:
        # Ensure upload folder exists
        upload_folder = app.config.get('UPLOAD_FOLDER')
        if not upload_folder:
            upload_folder = app.config['BASE_DIR'] / 'static' / 'uploads'
            upload_folder.mkdir(parents=True, exist_ok=True)
            app.config['UPLOAD_FOLDER'] = upload_folder
        return LocalStorageManager(upload_folder)