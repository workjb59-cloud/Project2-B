import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError, NoCredentialsError


class OfficeS3Uploader:
    """
    Handles uploading Excel files to AWS S3 with date-based partitioning for offices.
    Files are organized in: s3://bucket/boshamlan-data/offices/year=YYYY/month=MM/day=DD/
    """
    
    def __init__(self, bucket_name='data-collection-dl', aws_access_key_id=None, 
                 aws_secret_access_key=None, region_name='us-east-1'):
        """
        Initialize S3 uploader.
        
        Args:
            bucket_name: Name of the S3 bucket
            aws_access_key_id: AWS access key (optional, can use environment variables)
            aws_secret_access_key: AWS secret key (optional, can use environment variables)
            region_name: AWS region name
        """
        self.bucket_name = bucket_name
        self.base_path = 'boshamlan-data/offices'
        self.region_name = region_name
        
        # Get credentials from parameters or environment variables
        access_key = aws_access_key_id or os.environ.get('AWS_ACCESS_KEY_ID')
        secret_key = aws_secret_access_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
        
        # Initialize S3 client
        try:
            if access_key and secret_key:
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name=region_name
                )
                print(f"S3 client initialized with provided credentials for region '{region_name}'")
            else:
                # Use default credentials chain
                self.s3_client = boto3.client('s3', region_name=region_name)
                print(f"S3 client initialized with default credentials for region '{region_name}'")
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure credentials.")
    
    def upload_excel_file(self, file_path, upload_date=None):
        """
        Upload an Excel file to S3 with date partitioning.
        
        Args:
            file_path: Local path to the Excel file
            upload_date: Date for partitioning (default: today)
            
        Returns:
            S3 URL of the uploaded file
        """
        if upload_date is None:
            upload_date = datetime.now()
        
        # Create S3 key with date partitioning
        year = upload_date.strftime('%Y')
        month = upload_date.strftime('%m')
        day = upload_date.strftime('%d')
        
        file_name = os.path.basename(file_path)
        s3_key = f"{self.base_path}/year={year}/month={month}/day={day}/{file_name}"
        
        try:
            # Upload file
            print(f"Uploading {file_name} to s3://{self.bucket_name}/{s3_key}")
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            
            # Generate S3 URL
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            print(f"Successfully uploaded to {s3_url}")
            
            return s3_url
            
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")
        except ClientError as e:
            raise Exception(f"Failed to upload to S3: {e}")
    
    def upload_multiple_files(self, file_paths, upload_date=None):
        """
        Upload multiple Excel files to S3.
        
        Args:
            file_paths: List of local file paths
            upload_date: Date for partitioning (default: today)
            
        Returns:
            List of S3 URLs
        """
        uploaded_urls = []
        
        for file_path in file_paths:
            try:
                s3_url = self.upload_excel_file(file_path, upload_date)
                uploaded_urls.append(s3_url)
            except Exception as e:
                print(f"Error uploading {file_path}: {e}")
        
        return uploaded_urls
    
    def verify_bucket_exists(self):
        """
        Verify that the S3 bucket exists.
        
        Returns:
            True if bucket exists, False otherwise
        """
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            return True
        except ClientError:
            return False


def main():
    """Test the S3 uploader"""
    uploader = OfficeS3Uploader()
    
    # Verify bucket exists
    if uploader.verify_bucket_exists():
        print(f"Bucket '{uploader.bucket_name}' exists and is accessible")
    else:
        print(f"Warning: Bucket '{uploader.bucket_name}' does not exist or is not accessible")


if __name__ == "__main__":
    main()
