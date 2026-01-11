"""
Digital Ocean Spaces client utilities.

Provides S3-compatible operations for reading and writing JSON files
to the file-the-coop bucket. Used for storing and managing site data.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from api.core.config import settings

logger = logging.getLogger(__name__)


class SpacesClient:
    """
    Client for Digital Ocean Spaces (S3-compatible storage).

    Handles reading and writing JSON files to the Spaces bucket.
    All JSON operations include proper error handling and logging.
    """

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: Optional[str] = None,
        bucket: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        """
        Initialize the Spaces client.

        Args:
            access_key: DO Spaces access key (defaults to env var)
            secret_key: DO Spaces secret key (defaults to env var)
            region: DO Spaces region (defaults to env var or nyc3)
            bucket: Bucket name (defaults to env var or file-the-coop)
            endpoint: Spaces endpoint URL (defaults to env var)
        """
        self.access_key = access_key or settings.SPACES_ACCESS_KEY
        self.secret_key = secret_key or settings.SPACES_SECRET_KEY
        self.region = region or settings.SPACES_REGION
        self.bucket = bucket or settings.SPACES_BUCKET
        self.endpoint = endpoint or settings.SPACES_ENDPOINT

        self._client: Optional[boto3.client] = None

    @property
    def client(self) -> boto3.client:
        """
        Lazy-initialized boto3 S3 client.

        Returns:
            boto3 S3 client configured for Digital Ocean Spaces

        Raises:
            ValueError: If credentials are not configured
        """
        if self._client is None:
            if not self.access_key or not self.secret_key:
                raise ValueError(
                    "Spaces credentials not configured. "
                    "Set DIGITALOCEAN_SPACES_ACCESS_KEY and DIGITALOCEAN_SPACES_SECRET_KEY"
                )

            self._client = boto3.client(
                "s3",
                region_name=self.region,
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
            )

        return self._client

    def read_json(self, key: str) -> Dict[str, Any]:
        """
        Read a JSON file from Spaces.

        Args:
            key: The object key (file path) in the bucket

        Returns:
            Parsed JSON data as a dictionary

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file is not valid JSON
            ClientError: For other S3/Spaces errors
        """
        try:
            logger.info(f"Reading JSON from Spaces: {key}")
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            data = json.loads(content)
            logger.info(f"Successfully read JSON from {key}")
            return data

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "NoSuchKey":
                logger.error(f"File not found in Spaces: {key}")
                raise FileNotFoundError(f"File not found: {key}")
            logger.error(f"Error reading from Spaces: {e}")
            raise

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {key}: {e}")
            raise ValueError(f"Invalid JSON in {key}: {e}")

    def write_json(
        self,
        key: str,
        data: Dict[str, Any],
        content_type: str = "application/json",
        acl: str = "private",
    ) -> bool:
        """
        Write a JSON file to Spaces.

        Args:
            key: The object key (file path) in the bucket
            data: Dictionary to serialize as JSON
            content_type: MIME type (defaults to application/json)
            acl: Access control (private, public-read, etc.)

        Returns:
            True if successful

        Raises:
            ClientError: For S3/Spaces errors
        """
        try:
            logger.info(f"Writing JSON to Spaces: {key}")
            content = json.dumps(data, indent=2, ensure_ascii=False)

            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType=content_type,
                ACL=acl,
            )

            logger.info(f"Successfully wrote JSON to {key}")
            return True

        except ClientError as e:
            logger.error(f"Error writing to Spaces: {e}")
            raise

    def delete_file(self, key: str) -> bool:
        """
        Delete a file from Spaces.

        Args:
            key: The object key (file path) to delete

        Returns:
            True if successful (also returns True if file didn't exist)

        Raises:
            ClientError: For S3/Spaces errors
        """
        try:
            logger.info(f"Deleting from Spaces: {key}")
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Successfully deleted {key}")
            return True

        except ClientError as e:
            logger.error(f"Error deleting from Spaces: {e}")
            raise

    def list_files(self, prefix: str = "", suffix: str = "") -> List[str]:
        """
        List files in the bucket with optional prefix/suffix filtering.

        Args:
            prefix: Only return keys starting with this prefix
            suffix: Only return keys ending with this suffix

        Returns:
            List of object keys matching the filters

        Raises:
            ClientError: For S3/Spaces errors
        """
        try:
            logger.info(f"Listing files in Spaces (prefix={prefix}, suffix={suffix})")
            keys = []

            paginator = self.client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=self.bucket, Prefix=prefix)

            for page in page_iterator:
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if not suffix or key.endswith(suffix):
                        keys.append(key)

            logger.info(f"Found {len(keys)} files")
            return keys

        except ClientError as e:
            logger.error(f"Error listing files in Spaces: {e}")
            raise

    def file_exists(self, key: str) -> bool:
        """
        Check if a file exists in Spaces.

        Args:
            key: The object key to check

        Returns:
            True if the file exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """
        Copy a file within the bucket.

        Args:
            source_key: Source object key
            dest_key: Destination object key

        Returns:
            True if successful

        Raises:
            ClientError: For S3/Spaces errors
        """
        try:
            logger.info(f"Copying {source_key} to {dest_key}")
            copy_source = {"Bucket": self.bucket, "Key": source_key}
            self.client.copy_object(
                Bucket=self.bucket, CopySource=copy_source, Key=dest_key
            )
            logger.info(f"Successfully copied to {dest_key}")
            return True

        except ClientError as e:
            logger.error(f"Error copying file in Spaces: {e}")
            raise


# Convenience functions for common operations
# These use a module-level client instance

_default_client: Optional[SpacesClient] = None


def get_spaces_client() -> SpacesClient:
    """
    Get the default Spaces client instance.

    Creates a new client if one doesn't exist.

    Returns:
        SpacesClient instance
    """
    global _default_client
    if _default_client is None:
        _default_client = SpacesClient()
    return _default_client


def read_site_json(filename: str) -> Dict[str, Any]:
    """
    Read a site JSON file from Spaces.

    Convenience function for reading site data files.

    Args:
        filename: JSON filename (e.g., "events.json", "makers.json")

    Returns:
        Parsed JSON data
    """
    key = f"json/{filename}" if not filename.startswith("json/") else filename
    return get_spaces_client().read_json(key)


def write_site_json(filename: str, data: Dict[str, Any]) -> bool:
    """
    Write a site JSON file to Spaces.

    Convenience function for writing site data files.

    Args:
        filename: JSON filename (e.g., "events.json", "makers.json")
        data: Data to write

    Returns:
        True if successful
    """
    key = f"json/{filename}" if not filename.startswith("json/") else filename
    return get_spaces_client().write_json(key, data)


def list_site_json_files() -> List[str]:
    """
    List all JSON files in the json/ directory.

    Returns:
        List of JSON filenames
    """
    files = get_spaces_client().list_files(prefix="json/", suffix=".json")
    return [f.replace("json/", "") for f in files]
