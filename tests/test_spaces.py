"""
Pytest tests for the Digital Ocean Spaces client utilities.

Tests use mocking to avoid requiring actual Spaces credentials.
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch
from botocore.exceptions import ClientError

from api.services.spaces import (
    SpacesClient,
    get_spaces_client,
    read_site_json,
    write_site_json,
    list_site_json_files,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_boto3_client():
    """Create a mock boto3 S3 client."""
    mock_client = MagicMock()
    return mock_client


@pytest.fixture
def spaces_client(mock_boto3_client):
    """Create a SpacesClient with mocked boto3 client."""
    client = SpacesClient(
        access_key="test_key",
        secret_key="test_secret",
        region="nyc3",
        bucket="test-bucket",
    )
    client._client = mock_boto3_client
    return client


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {
        "events": [
            {"name": "Test Event", "date": "2025-01-15"},
        ],
        "hero": "https://example.com/hero.jpg"
    }


# =============================================================================
# SpacesClient Initialization Tests
# =============================================================================

class TestSpacesClientInit:
    """Tests for SpacesClient initialization."""

    def test_init_with_credentials(self):
        """Test client initializes with provided credentials."""
        client = SpacesClient(
            access_key="my_key",
            secret_key="my_secret",
            region="sfo3",
            bucket="my-bucket",
        )
        assert client.access_key == "my_key"
        assert client.secret_key == "my_secret"
        assert client.region == "sfo3"
        assert client.bucket == "my-bucket"

    def test_client_property_raises_without_credentials(self):
        """Test accessing client property raises error without credentials."""
        client = SpacesClient(access_key=None, secret_key=None)
        with pytest.raises(ValueError, match="Spaces credentials not configured"):
            _ = client.client

    @patch("api.services.spaces.boto3")
    def test_client_property_creates_boto3_client(self, mock_boto3):
        """Test client property creates boto3 S3 client."""
        mock_boto3.client.return_value = MagicMock()
        client = SpacesClient(
            access_key="test",
            secret_key="test",
            region="nyc3",
            endpoint="https://nyc3.digitaloceanspaces.com",
        )

        _ = client.client

        mock_boto3.client.assert_called_once_with(
            "s3",
            region_name="nyc3",
            endpoint_url="https://nyc3.digitaloceanspaces.com",
            aws_access_key_id="test",
            aws_secret_access_key="test",
        )


# =============================================================================
# Read JSON Tests
# =============================================================================

class TestReadJson:
    """Tests for reading JSON from Spaces."""

    def test_read_json_success(self, spaces_client, mock_boto3_client, sample_json_data):
        """Test successfully reading JSON file."""
        # Mock the S3 response
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(sample_json_data).encode("utf-8")
        mock_boto3_client.get_object.return_value = {"Body": mock_body}

        result = spaces_client.read_json("json/events.json")

        assert result == sample_json_data
        mock_boto3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="json/events.json"
        )

    def test_read_json_file_not_found(self, spaces_client, mock_boto3_client):
        """Test reading non-existent file raises FileNotFoundError."""
        error_response = {"Error": {"Code": "NoSuchKey"}}
        mock_boto3_client.get_object.side_effect = ClientError(
            error_response, "GetObject"
        )

        with pytest.raises(FileNotFoundError, match="File not found"):
            spaces_client.read_json("json/nonexistent.json")

    def test_read_json_invalid_json(self, spaces_client, mock_boto3_client):
        """Test reading invalid JSON raises ValueError."""
        mock_body = MagicMock()
        mock_body.read.return_value = b"not valid json"
        mock_boto3_client.get_object.return_value = {"Body": mock_body}

        with pytest.raises(ValueError, match="Invalid JSON"):
            spaces_client.read_json("json/invalid.json")


# =============================================================================
# Write JSON Tests
# =============================================================================

class TestWriteJson:
    """Tests for writing JSON to Spaces."""

    def test_write_json_success(self, spaces_client, mock_boto3_client, sample_json_data):
        """Test successfully writing JSON file."""
        result = spaces_client.write_json("json/events.json", sample_json_data)

        assert result is True
        mock_boto3_client.put_object.assert_called_once()
        call_kwargs = mock_boto3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "json/events.json"
        assert call_kwargs["ContentType"] == "application/json"

    def test_write_json_custom_acl(self, spaces_client, mock_boto3_client, sample_json_data):
        """Test writing JSON with custom ACL."""
        spaces_client.write_json("json/events.json", sample_json_data, acl="public-read")

        call_kwargs = mock_boto3_client.put_object.call_args[1]
        assert call_kwargs["ACL"] == "public-read"

    def test_write_json_client_error(self, spaces_client, mock_boto3_client, sample_json_data):
        """Test write operation raises on client error."""
        error_response = {"Error": {"Code": "AccessDenied"}}
        mock_boto3_client.put_object.side_effect = ClientError(
            error_response, "PutObject"
        )

        with pytest.raises(ClientError):
            spaces_client.write_json("json/events.json", sample_json_data)


# =============================================================================
# Delete File Tests
# =============================================================================

class TestDeleteFile:
    """Tests for deleting files from Spaces."""

    def test_delete_file_success(self, spaces_client, mock_boto3_client):
        """Test successfully deleting a file."""
        result = spaces_client.delete_file("json/old.json")

        assert result is True
        mock_boto3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="json/old.json"
        )


# =============================================================================
# List Files Tests
# =============================================================================

class TestListFiles:
    """Tests for listing files in Spaces."""

    def test_list_files_success(self, spaces_client, mock_boto3_client):
        """Test listing files returns correct keys."""
        # Mock paginator
        mock_paginator = MagicMock()
        mock_boto3_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "json/events.json"},
                    {"Key": "json/makers.json"},
                    {"Key": "json/home.json"},
                ]
            }
        ]

        result = spaces_client.list_files(prefix="json/")

        assert len(result) == 3
        assert "json/events.json" in result

    def test_list_files_with_suffix_filter(self, spaces_client, mock_boto3_client):
        """Test listing files with suffix filter."""
        mock_paginator = MagicMock()
        mock_boto3_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "json/events.json"},
                    {"Key": "json/backup.txt"},
                ]
            }
        ]

        result = spaces_client.list_files(prefix="json/", suffix=".json")

        assert len(result) == 1
        assert "json/events.json" in result

    def test_list_files_empty(self, spaces_client, mock_boto3_client):
        """Test listing files in empty directory."""
        mock_paginator = MagicMock()
        mock_boto3_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"Contents": []}]

        result = spaces_client.list_files(prefix="empty/")

        assert result == []


# =============================================================================
# File Exists Tests
# =============================================================================

class TestFileExists:
    """Tests for checking file existence."""

    def test_file_exists_true(self, spaces_client, mock_boto3_client):
        """Test file_exists returns True for existing file."""
        mock_boto3_client.head_object.return_value = {}

        result = spaces_client.file_exists("json/events.json")

        assert result is True

    def test_file_exists_false(self, spaces_client, mock_boto3_client):
        """Test file_exists returns False for non-existent file."""
        error_response = {"Error": {"Code": "404"}}
        mock_boto3_client.head_object.side_effect = ClientError(
            error_response, "HeadObject"
        )

        result = spaces_client.file_exists("json/nonexistent.json")

        assert result is False


# =============================================================================
# Copy File Tests
# =============================================================================

class TestCopyFile:
    """Tests for copying files in Spaces."""

    def test_copy_file_success(self, spaces_client, mock_boto3_client):
        """Test successfully copying a file."""
        result = spaces_client.copy_file("json/events.json", "json/events_backup.json")

        assert result is True
        mock_boto3_client.copy_object.assert_called_once()
        call_kwargs = mock_boto3_client.copy_object.call_args[1]
        assert call_kwargs["Key"] == "json/events_backup.json"
        assert call_kwargs["CopySource"]["Key"] == "json/events.json"


# =============================================================================
# Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @patch("api.services.spaces._default_client", None)
    @patch("api.services.spaces.SpacesClient")
    def test_get_spaces_client_creates_instance(self, MockSpacesClient):
        """Test get_spaces_client creates a new instance."""
        MockSpacesClient.return_value = MagicMock()

        client = get_spaces_client()

        MockSpacesClient.assert_called_once()
        assert client is not None

    @patch("api.services.spaces.get_spaces_client")
    def test_read_site_json_adds_prefix(self, mock_get_client):
        """Test read_site_json adds json/ prefix."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.read_json.return_value = {"test": "data"}

        read_site_json("events.json")

        mock_client.read_json.assert_called_once_with("json/events.json")

    @patch("api.services.spaces.get_spaces_client")
    def test_write_site_json_adds_prefix(self, mock_get_client):
        """Test write_site_json adds json/ prefix."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        write_site_json("events.json", {"test": "data"})

        mock_client.write_json.assert_called_once_with("json/events.json", {"test": "data"})

    @patch("api.services.spaces.get_spaces_client")
    def test_list_site_json_files(self, mock_get_client):
        """Test list_site_json_files returns filenames without prefix."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_files.return_value = [
            "json/events.json",
            "json/makers.json",
        ]

        result = list_site_json_files()

        assert result == ["events.json", "makers.json"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
