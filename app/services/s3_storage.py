"""S3 storage service for file uploads (optional; fallback to local filesystem)."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import boto3
    from botocore.exceptions import ClientError
    HAS_S3 = True
except ImportError:
    HAS_S3 = False


class S3StorageService:
    """Handles file uploads to AWS S3 or local filesystem fallback."""

    def __init__(self, region: str, bucket: str, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """
        Initialize S3 client.
        
        Args:
            region: AWS region
            bucket: S3 bucket name
            access_key: AWS access key (optional; uses IAM role on EC2)
            secret_key: AWS secret key (optional; uses IAM role on EC2)
        """
        self.bucket = bucket
        self.region = region
        self.enabled = HAS_S3 and bool(bucket)
        
        if self.enabled:
            try:
                self.client = boto3.client(
                    "s3",
                    region_name=region,
                    aws_access_key_id=access_key or None,
                    aws_secret_access_key=secret_key or None,
                )
                logger.info(f"S3 storage initialized for bucket '{bucket}' in region '{region}'")
            except Exception as e:
                logger.error(f"Failed to initialize S3 client: {e}")
                self.enabled = False
        else:
            logger.info("S3 storage disabled; using local filesystem fallback")

    def upload_file(self, file_data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> str:
        """
        Upload file to S3.
        
        Args:
            file_data: File contents as bytes
            s3_key: S3 object key (e.g., "user_123/event_456/uploads/photo.jpg")
            content_type: MIME type
            
        Returns:
            S3 key or local path on success
        """
        if not self.enabled:
            # Fallback: not implemented here; caller should use local filesystem
            logger.debug(f"S3 disabled; skipping upload of {s3_key}")
            return None

        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
            logger.info(f"Uploaded to S3: s3://{self.bucket}/{s3_key}")
            return s3_key
        except ClientError as e:
            logger.error(f"S3 upload failed for {s3_key}: {e}")
            raise

    def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3."""
        if not self.enabled:
            return False

        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Deleted from S3: s3://{self.bucket}/{s3_key}")
            return True
        except ClientError as e:
            logger.error(f"S3 delete failed for {s3_key}: {e}")
            return False

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for temporary access (e.g., for downloads).
        
        Args:
            s3_key: S3 object key
            expiration: URL validity in seconds (default 1 hour)
            
        Returns:
            Presigned URL
        """
        if not self.enabled:
            return None

        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            raise

    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists in S3."""
        if not self.enabled:
            return False

        try:
            self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Error checking S3 file existence: {e}")
            raise
