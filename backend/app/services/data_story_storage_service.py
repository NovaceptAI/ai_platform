# app/services/data_story_storage_service.py
"""
Data Story Storage Service

Handles Azure Blob Storage operations for Data Story Builder:
- Upload CSV/Excel files to Azure
- Upload chart images (PNG)
- Upload PDF/HTML exports
- Generate SAS tokens for downloads
"""

import os
import logging
from io import BytesIO
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobSasPermissions, generate_blob_sas, ContentSettings

logger = logging.getLogger(__name__)

# Azure container name - same as Story to Comics
CONTAINER_NAME = "scoolish"


class DataStoryStorageService:
    """Service for managing Data Story files in Azure Blob Storage."""

    def __init__(self):
        """Initialize Azure Blob Storage client."""
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not set")

        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = CONTAINER_NAME
        self.container_client = self.blob_service_client.get_container_client(CONTAINER_NAME)

        # Extract account name and key for SAS token generation
        self.account_name = self._extract_account_name(connection_string)
        self.account_key = self._extract_account_key(connection_string)

    def _extract_account_name(self, connection_string):
        """Extract account name from connection string."""
        for part in connection_string.split(";"):
            if part.startswith("AccountName="):
                return part.split("=", 1)[1]
        return None

    def _extract_account_key(self, connection_string):
        """Extract account key from connection string."""
        for part in connection_string.split(";"):
            if part.startswith("AccountKey="):
                return part.split("=", 1)[1]
        return None

    def get_folder_path(self, user_id, story_id):
        """
        Generate Azure folder path for a data story.

        Args:
            user_id: User's ID
            story_id: Data story creation ID

        Returns:
            str: Folder path like "{user_id}/data_stories/{story_id}/"
        """
        return f"{user_id}/data_stories/{story_id}/"

    def upload_chart(self, user_id, story_id, chart_id, chart_bytes, file_extension="png"):
        """
        Upload a chart image to Azure.

        Args:
            user_id: User's ID
            story_id: Data story creation ID
            chart_id: Unique chart identifier (e.g., "chart_1")
            chart_bytes: Chart image bytes
            file_extension: Image format (default: png)

        Returns:
            str: Public URL with SAS token
        """
        folder_path = self.get_folder_path(user_id, story_id)
        blob_name = f"{folder_path}charts/{chart_id}.{file_extension}"

        try:
            logger.info(f"Uploading chart to Azure: {blob_name}")

            blob_client = self.container_client.get_blob_client(blob_name)

            # Upload with appropriate content type
            content_settings = ContentSettings(content_type=f"image/{file_extension}")
            blob_client.upload_blob(
                chart_bytes,
                overwrite=True,
                content_settings=content_settings
            )

            # Generate SAS token (10 years)
            sas_url = self._generate_sas_url(blob_name)

            logger.info(f"Chart uploaded successfully: {chart_id}")
            return sas_url

        except Exception as e:
            logger.error(f"Error uploading chart {chart_id}: {str(e)}")
            raise

    def upload_pdf(self, user_id, story_id, pdf_bytes):
        """
        Upload PDF export to Azure.

        Args:
            user_id: User's ID
            story_id: Data story creation ID
            pdf_bytes: PDF file bytes

        Returns:
            str: Public URL with SAS token
        """
        folder_path = self.get_folder_path(user_id, story_id)
        blob_name = f"{folder_path}exports/story.pdf"

        try:
            logger.info(f"Uploading PDF to Azure: {blob_name}")

            blob_client = self.container_client.get_blob_client(blob_name)

            content_settings = ContentSettings(content_type='application/pdf')
            blob_client.upload_blob(
                pdf_bytes,
                overwrite=True,
                content_settings=content_settings
            )

            sas_url = self._generate_sas_url(blob_name)

            logger.info("PDF uploaded successfully")
            return sas_url

        except Exception as e:
            logger.error(f"Error uploading PDF: {str(e)}")
            raise

    def upload_html(self, user_id, story_id, html_content):
        """
        Upload HTML export to Azure.

        Args:
            user_id: User's ID
            story_id: Data story creation ID
            html_content: HTML content as string

        Returns:
            str: Public URL with SAS token
        """
        folder_path = self.get_folder_path(user_id, story_id)
        blob_name = f"{folder_path}exports/story.html"

        try:
            logger.info(f"Uploading HTML to Azure: {blob_name}")

            blob_client = self.container_client.get_blob_client(blob_name)

            # Convert string to bytes
            html_bytes = html_content.encode('utf-8')

            content_settings = ContentSettings(content_type='text/html; charset=utf-8')
            blob_client.upload_blob(
                html_bytes,
                overwrite=True,
                content_settings=content_settings
            )

            sas_url = self._generate_sas_url(blob_name)

            logger.info("HTML uploaded successfully")
            return sas_url

        except Exception as e:
            logger.error(f"Error uploading HTML: {str(e)}")
            raise

    def upload_thumbnail(self, user_id, story_id, thumbnail_bytes):
        """
        Upload thumbnail image to Azure.

        Args:
            user_id: User's ID
            story_id: Data story creation ID
            thumbnail_bytes: Thumbnail image bytes

        Returns:
            str: Public URL with SAS token
        """
        folder_path = self.get_folder_path(user_id, story_id)
        blob_name = f"{folder_path}thumbnail.png"

        try:
            logger.info(f"Uploading thumbnail to Azure: {blob_name}")

            blob_client = self.container_client.get_blob_client(blob_name)

            content_settings = ContentSettings(content_type="image/png")
            blob_client.upload_blob(
                thumbnail_bytes,
                overwrite=True,
                content_settings=content_settings
            )

            sas_url = self._generate_sas_url(blob_name)

            logger.info("Thumbnail uploaded successfully")
            return sas_url

        except Exception as e:
            logger.error(f"Error uploading thumbnail: {str(e)}")
            raise

    def upload_data_file(self, user_id, story_id, file_bytes, filename):
        """
        Upload original data file (CSV/Excel) to Azure for reference.

        Args:
            user_id: User's ID
            story_id: Data story creation ID
            file_bytes: File bytes
            filename: Original filename

        Returns:
            str: Public URL with SAS token
        """
        folder_path = self.get_folder_path(user_id, story_id)
        blob_name = f"{folder_path}data/{filename}"

        try:
            logger.info(f"Uploading data file to Azure: {blob_name}")

            blob_client = self.container_client.get_blob_client(blob_name)

            # Determine content type
            content_type = "application/octet-stream"
            if filename.endswith('.csv'):
                content_type = "text/csv"
            elif filename.endswith(('.xlsx', '.xls')):
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

            content_settings = ContentSettings(content_type=content_type)
            blob_client.upload_blob(
                file_bytes,
                overwrite=True,
                content_settings=content_settings
            )

            sas_url = self._generate_sas_url(blob_name)

            logger.info("Data file uploaded successfully")
            return sas_url

        except Exception as e:
            logger.error(f"Error uploading data file: {str(e)}")
            raise

    def _generate_sas_url(self, blob_name, expiry_years=10):
        """
        Generate a SAS URL for a blob with long-term access.

        Args:
            blob_name: Name of the blob
            expiry_years: Years until SAS token expires (default: 10)

        Returns:
            str: Full URL with SAS token
        """
        try:
            sas_token = generate_blob_sas(
                account_name=self.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(days=365 * expiry_years)
            )

            blob_url = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
            return blob_url

        except Exception as e:
            logger.error(f"Error generating SAS token for {blob_name}: {str(e)}")
            raise

    def delete_story_folder(self, user_id, story_id):
        """
        Delete all files in a data story's folder.

        Args:
            user_id: User's ID
            story_id: Data story creation ID

        Returns:
            int: Number of blobs deleted
        """
        folder_path = self.get_folder_path(user_id, story_id)

        try:
            logger.info(f"Deleting data story folder: {folder_path}")

            # List all blobs with this prefix
            blobs = self.container_client.list_blobs(name_starts_with=folder_path)

            deleted_count = 0
            for blob in blobs:
                blob_client = self.container_client.get_blob_client(blob.name)
                blob_client.delete_blob()
                deleted_count += 1

            logger.info(f"Deleted {deleted_count} blobs from {folder_path}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting story folder {folder_path}: {str(e)}")
            raise
