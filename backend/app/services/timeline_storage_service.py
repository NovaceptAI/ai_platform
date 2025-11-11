"""
Timeline Storage Service

Handles Azure Blob Storage operations for timeline documents and exports.
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


def upload_timeline_document(user_id: str, timeline_id: str, document_bytes: bytes, filename: str) -> str:
    """
    Upload timeline source document to Azure Blob Storage.

    Args:
        user_id: User ID
        timeline_id: Timeline ID
        document_bytes: Document bytes
        filename: Original filename

    Returns:
        URL with SAS token
    """
    try:
        blob_service_client = get_blob_service_client()
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "scoolish")

        # Determine content type
        content_type = "application/octet-stream"
        if filename.endswith('.pdf'):
            content_type = "application/pdf"
        elif filename.endswith('.txt'):
            content_type = "text/plain"
        elif filename.endswith('.docx'):
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith('.doc'):
            content_type = "application/msword"

        # Path: user_id/timelines/timeline_id/document_filename
        blob_path = f"{user_id}/timelines/{timeline_id}/{filename}"

        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_path
        )

        # Upload with appropriate content type
        content_settings = ContentSettings(content_type=content_type)
        blob_client.upload_blob(
            document_bytes,
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

        logger.info(f"[TimelineStorage] Uploaded document to Azure: {blob_path}")
        return blob_url_with_sas

    except Exception as e:
        logger.error(f"[TimelineStorage] Error uploading document: {str(e)}")
        raise


def export_timeline_json(user_id: str, timeline_id: str, timeline_data: dict) -> str:
    """
    Export timeline as JSON to Azure Blob Storage.

    Args:
        user_id: User ID
        timeline_id: Timeline ID
        timeline_data: Timeline data dictionary

    Returns:
        URL with SAS token
    """
    try:
        import json

        blob_service_client = get_blob_service_client()
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "scoolish")

        # Path: user_id/timelines/timeline_id/export.json
        blob_path = f"{user_id}/timelines/{timeline_id}/export.json"

        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_path
        )

        # Convert to JSON bytes
        json_bytes = json.dumps(timeline_data, indent=2).encode('utf-8')

        # Upload with JSON content type
        content_settings = ContentSettings(content_type='application/json')
        blob_client.upload_blob(
            json_bytes,
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

        logger.info(f"[TimelineStorage] Exported timeline JSON to Azure: {blob_path}")
        return blob_url_with_sas

    except Exception as e:
        logger.error(f"[TimelineStorage] Error exporting timeline JSON: {str(e)}")
        raise


def delete_timeline_from_azure(azure_folder_path: str) -> bool:
    """
    Delete timeline folder from Azure Blob Storage.

    Args:
        azure_folder_path: Folder path in Azure (e.g., user_id/timelines/timeline_id/)

    Returns:
        True if deleted successfully
    """
    try:
        blob_service_client = get_blob_service_client()
        container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "scoolish")

        container_client = blob_service_client.get_container_client(container_name)
        blob_list = container_client.list_blobs(name_starts_with=azure_folder_path)

        deleted_count = 0
        for blob in blob_list:
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob.name
            )
            blob_client.delete_blob()
            deleted_count += 1
            logger.info(f"[TimelineStorage] Deleted blob: {blob.name}")

        logger.info(f"[TimelineStorage] Deleted {deleted_count} blobs from {azure_folder_path}")
        return True

    except Exception as e:
        logger.error(f"[TimelineStorage] Error deleting timeline from Azure: {str(e)}")
        return False
