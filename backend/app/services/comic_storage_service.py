"""
Comic Storage Service

Handles Azure Blob Storage operations for comic panel images.
Downloads DALL-E generated images and uploads them to permanent Azure storage.
"""

import os
import logging
import requests
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from io import BytesIO
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from app.models.comics import ComicCreation
from app.db import db

logger = logging.getLogger(__name__)

# Azure config
CONTAINER_NAME = "scoolish"


def get_blob_service_client():
    """Get Azure Blob Service Client from connection string."""
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set")
    return BlobServiceClient.from_connection_string(conn)


def download_image_from_url(image_url: str, timeout: int = 30) -> Optional[bytes]:
    """
    Download image from DALL-E URL.

    Args:
        image_url: DALL-E image URL (expires after 1 hour)
        timeout: Request timeout in seconds

    Returns:
        Image bytes or None if download fails
    """
    try:
        logger.info(f"Downloading image from URL: {image_url[:100]}...")
        response = requests.get(image_url, timeout=timeout)
        response.raise_for_status()

        logger.info(f"Successfully downloaded image ({len(response.content)} bytes)")
        return response.content

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download image from {image_url}: {str(e)}")
        return None


def upload_comic_panel_to_azure(
    user_id: str,
    comic_id: str,
    panel_number: int,
    image_bytes: bytes
) -> Optional[str]:
    """
    Upload comic panel image to Azure Blob Storage.

    Args:
        user_id: User's ID
        comic_id: Comic creation ID
        panel_number: Panel number (1-indexed)
        image_bytes: Image content as bytes

    Returns:
        Azure blob URL with SAS token or None if upload fails
    """
    try:
        # Construct blob path: {user_id}/comics/{comic_id}/panel_{number}.png
        blob_path = f"{user_id}/comics/{comic_id}/panel_{panel_number}.png"

        logger.info(f"Uploading panel {panel_number} to Azure: {blob_path}")

        # Get blob client
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_path
        )

        # Upload with PNG content type
        content_settings = ContentSettings(content_type="image/png")
        blob_client.upload_blob(
            image_bytes,
            overwrite=True,
            content_settings=content_settings
        )

        # Generate SAS token valid for 10 years (effectively permanent for user access)
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=CONTAINER_NAME,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(days=3650)  # 10 years
        )

        # Construct URL with SAS token
        blob_url_with_sas = f"{blob_client.url}?{sas_token}"
        logger.info(f"Successfully uploaded panel {panel_number} to Azure with SAS token")

        return blob_url_with_sas

    except Exception as e:
        logger.error(f"Failed to upload panel {panel_number} to Azure: {str(e)}")
        return None


def persist_comic_to_azure(
    user_id: str,
    comic_data: Dict[str, Any],
    panels_with_dalle_urls: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Download DALL-E images and upload to Azure, then create database record.

    This is the main function called from the Celery task after comic generation.

    Args:
        user_id: User's ID
        comic_data: Comic metadata (title, total_panels, etc.)
        panels_with_dalle_urls: List of panels with DALL-E image URLs

    Returns:
        Dictionary with comic_id and status
        {
            'success': True/False,
            'comic_id': str,
            'azure_folder_path': str,
            'panels_persisted': int,
            'error': str (if failed)
        }
    """
    comic_id = str(uuid.uuid4())
    azure_folder_path = f"{user_id}/comics/{comic_id}/"

    try:
        logger.info(f"Starting comic persistence for user {user_id}, comic_id {comic_id}")

        persisted_panels = []
        thumbnail_url = None

        # Process each panel
        for panel in panels_with_dalle_urls:
            panel_number = panel.get('panel_number')
            dalle_url = panel.get('image_url')

            if not dalle_url:
                logger.warning(f"Panel {panel_number} has no image URL, skipping")
                continue

            # Download from DALL-E
            image_bytes = download_image_from_url(dalle_url)
            if not image_bytes:
                logger.error(f"Failed to download panel {panel_number}")
                # Still add panel but mark as failed
                persisted_panels.append({
                    **panel,
                    'image_url': None,
                    'azure_upload_failed': True
                })
                continue

            # Upload to Azure
            azure_url = upload_comic_panel_to_azure(
                user_id=user_id,
                comic_id=comic_id,
                panel_number=panel_number,
                image_bytes=image_bytes
            )

            if azure_url:
                # Replace DALL-E URL with Azure URL
                persisted_panel = {
                    **panel,
                    'image_url': azure_url,
                    'dalle_url': dalle_url,  # Keep original for reference
                    'azure_path': f"{azure_folder_path}panel_{panel_number}.png"
                }
                persisted_panels.append(persisted_panel)

                # Set first panel as thumbnail
                if thumbnail_url is None:
                    thumbnail_url = azure_url

                logger.info(f"Successfully persisted panel {panel_number}")
            else:
                logger.error(f"Failed to upload panel {panel_number} to Azure")
                persisted_panels.append({
                    **panel,
                    'image_url': dalle_url,  # Fallback to DALL-E URL (will expire)
                    'azure_upload_failed': True
                })

        # Create database record
        comic_creation = ComicCreation(
            id=comic_id,
            user_id=user_id,
            title=comic_data.get('title', 'Untitled Comic'),
            source_type=comic_data.get('source_type', 'text'),
            source_file_id=comic_data.get('source_file_id'),
            source_text_preview=comic_data.get('source_text_preview'),
            status='active',
            total_panels=len(persisted_panels),
            style=comic_data.get('style', 'vivid'),
            azure_folder_path=azure_folder_path,
            thumbnail_url=thumbnail_url,
            panels_data=persisted_panels,
            comic_metadata={
                'generation_options': comic_data.get('generation_options', {}),
                'source_info': comic_data.get('source_info', {}),
                'ai_metadata': comic_data.get('ai_metadata', {})
            }
        )

        db.session.add(comic_creation)
        db.session.commit()

        logger.info(f"Successfully created comic record {comic_id} with {len(persisted_panels)} panels")

        return {
            'success': True,
            'comic_id': comic_id,
            'azure_folder_path': azure_folder_path,
            'panels_persisted': len(persisted_panels),
            'thumbnail_url': thumbnail_url
        }

    except Exception as e:
        logger.error(f"Failed to persist comic to Azure: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


def delete_comic_from_azure(user_id: str, comic_id: str) -> bool:
    """
    Delete all comic panel images from Azure Blob Storage.

    Args:
        user_id: User's ID
        comic_id: Comic creation ID

    Returns:
        True if successful, False otherwise
    """
    try:
        azure_folder_path = f"{user_id}/comics/{comic_id}/"

        logger.info(f"Deleting comic folder from Azure: {azure_folder_path}")

        # Get container client
        container_client = get_blob_service_client().get_container_client(CONTAINER_NAME)

        # List all blobs in the comic folder
        blobs = container_client.list_blobs(name_starts_with=azure_folder_path)

        deleted_count = 0
        for blob in blobs:
            try:
                container_client.delete_blob(blob.name)
                deleted_count += 1
                logger.info(f"Deleted blob: {blob.name}")
            except Exception as e:
                logger.error(f"Failed to delete blob {blob.name}: {str(e)}")

        logger.info(f"Successfully deleted {deleted_count} blobs from comic {comic_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete comic folder from Azure: {str(e)}")
        return False


def delete_comic_creation(user_id: str, comic_id: str) -> Dict[str, Any]:
    """
    Delete comic creation from database and Azure storage.

    Args:
        user_id: User's ID (for security check)
        comic_id: Comic creation ID

    Returns:
        Dictionary with status
        {
            'success': True/False,
            'message': str,
            'error': str (if failed)
        }
    """
    try:
        # Get comic from database
        comic = ComicCreation.query.filter_by(
            id=comic_id,
            user_id=user_id
        ).first()

        if not comic:
            return {
                'success': False,
                'error': 'Comic not found or access denied'
            }

        # Delete from Azure
        azure_deleted = delete_comic_from_azure(user_id, comic_id)

        # Delete from database
        db.session.delete(comic)
        db.session.commit()

        logger.info(f"Successfully deleted comic {comic_id} from database")

        return {
            'success': True,
            'message': 'Comic deleted successfully',
            'azure_deleted': azure_deleted
        }

    except Exception as e:
        logger.error(f"Failed to delete comic {comic_id}: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }
