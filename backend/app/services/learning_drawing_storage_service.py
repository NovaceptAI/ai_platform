"""
Learning Drawing Storage Service

Handles Azure Blob Storage operations for learning drawings.
"""

import os
import logging
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions

logger = logging.getLogger(__name__)


def get_blob_service_client():
    """Get Azure Blob Service Client."""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING not found in environment")
    return BlobServiceClient.from_connection_string(connection_string)


def upload_drawing_to_azure(user_id: str, drawing_id: str, image_bytes: bytes) -> str:
    """
    Upload drawing image to Azure Blob Storage.

    Args:
        user_id: User ID
        drawing_id: Drawing ID
        image_bytes: PNG image bytes

    Returns:
        URL with SAS token
    """
    try:
        blob_service_client = get_blob_service_client()
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "scoolish")

        # Path: user_id/learning_drawings/drawing_id/drawing.png
        blob_path = f"{user_id}/learning_drawings/{drawing_id}/drawing.png"

        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_path
        )

        # Upload with PNG content type
        content_settings = ContentSettings(content_type='image/png')
        blob_client.upload_blob(
            image_bytes,
            overwrite=True,
            content_settings=content_settings
        )

        # Generate SAS token (valid for 10 years)
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=container_name,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(days=3650)
        )

        blob_url_with_sas = f"{blob_client.url}?{sas_token}"

        logger.info(f"[DrawingStorage] Uploaded drawing to Azure: {blob_path}")
        return blob_url_with_sas

    except Exception as e:
        logger.error(f"[DrawingStorage] Error uploading drawing: {str(e)}")
        raise


def delete_drawing_from_azure(drawing_url: str) -> bool:
    """
    Delete drawing from Azure Blob Storage.

    Args:
        drawing_url: Full URL with SAS token

    Returns:
        True if deleted successfully
    """
    try:
        # Extract blob path from URL
        blob_service_client = get_blob_service_client()
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "scoolish")

        # Parse blob path from URL
        # URL format: https://{account}.blob.core.windows.net/{container}/{blob_path}?{sas}
        url_parts = drawing_url.split('/')
        if len(url_parts) < 5:
            logger.warning(f"[DrawingStorage] Invalid URL format: {drawing_url}")
            return False

        # Extract blob path (everything after container name, before ?)
        blob_path = '/'.join(url_parts[4:]).split('?')[0]

        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_path
        )

        blob_client.delete_blob()
        logger.info(f"[DrawingStorage] Deleted drawing from Azure: {blob_path}")
        return True

    except Exception as e:
        logger.error(f"[DrawingStorage] Error deleting drawing: {str(e)}")
        return False


def get_drawing_metadata(drawing_url: str) -> dict:
    """
    Get metadata for a drawing from Azure.

    Args:
        drawing_url: Full URL with SAS token

    Returns:
        Metadata dictionary
    """
    try:
        blob_service_client = get_blob_service_client()
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "scoolish")

        # Extract blob path
        url_parts = drawing_url.split('/')
        blob_path = '/'.join(url_parts[4:]).split('?')[0]

        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_path
        )

        properties = blob_client.get_blob_properties()

        return {
            'size': properties.size,
            'created': properties.creation_time,
            'modified': properties.last_modified,
            'content_type': properties.content_settings.content_type
        }

    except Exception as e:
        logger.error(f"[DrawingStorage] Error getting metadata: {str(e)}")
        return {}
