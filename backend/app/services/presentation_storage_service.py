"""
Presentation Storage Service

Handles Azure Blob Storage operations for PowerPoint presentations.
- Downloads DALL-E images and uploads to Azure
- Creates PowerPoint files using python-pptx
- Compresses images before embedding
- Generates preview images of slides
- Manages presentation lifecycle in database
"""

import os
import logging
import requests
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from io import BytesIO
from PIL import Image
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from app.models.presentations import PresentationCreation
from app.db import db

logger = logging.getLogger(__name__)

# Azure config
CONTAINER_NAME = "scoolish"

# File size limits
MAX_PPTX_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_IMAGE_SIZE = 500 * 1024  # 500 KB per image


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


def compress_image(image_bytes: bytes, max_size_kb: int = 500) -> bytes:
    """
    Compress image to reduce file size for PPTX embedding.

    Args:
        image_bytes: Original image bytes
        max_size_kb: Maximum size in KB

    Returns:
        Compressed image bytes
    """
    try:
        img = Image.open(BytesIO(image_bytes))

        # Convert to RGB if necessary (for PNG with alpha)
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Resize if too large (max 1920x1080 for 16:9)
        max_width = 1920
        max_height = 1080
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

        # Compress with quality adjustment
        output = BytesIO()
        quality = 85

        # Try progressively lower quality until under max_size
        while quality > 20:
            output.seek(0)
            output.truncate()
            img.save(output, format='JPEG', optimize=True, quality=quality)

            if output.tell() <= max_size_kb * 1024:
                break
            quality -= 5

        logger.info(f"Compressed image from {len(image_bytes)} to {output.tell()} bytes (quality={quality})")
        return output.getvalue()

    except Exception as e:
        logger.error(f"Failed to compress image: {str(e)}")
        return image_bytes  # Return original if compression fails


def upload_presentation_image_to_azure(
    user_id: str,
    presentation_id: str,
    slide_number: int,
    image_bytes: bytes,
    compress: bool = True
) -> Optional[str]:
    """
    Upload presentation slide image to Azure Blob Storage.

    Args:
        user_id: User's ID
        presentation_id: Presentation ID
        slide_number: Slide number (1-indexed)
        image_bytes: Image content as bytes
        compress: Whether to compress the image

    Returns:
        Azure blob URL with SAS token or None if upload fails
    """
    try:
        # Compress image if requested
        if compress:
            image_bytes = compress_image(image_bytes)

        # Construct blob path: {user_id}/presentations/{presentation_id}/images/slide_{number}.jpg
        blob_path = f"{user_id}/presentations/{presentation_id}/images/slide_{slide_number}.jpg"

        logger.info(f"Uploading slide {slide_number} image to Azure: {blob_path}")

        # Get blob client
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_path
        )

        # Upload with JPEG content type
        content_settings = ContentSettings(content_type="image/jpeg")
        blob_client.upload_blob(
            image_bytes,
            overwrite=True,
            content_settings=content_settings
        )

        # Generate SAS token valid for 10 years
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=CONTAINER_NAME,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(days=3650)
        )

        # Construct URL with SAS token
        blob_url_with_sas = f"{blob_client.url}?{sas_token}"
        logger.info(f"Successfully uploaded slide {slide_number} image to Azure")

        return blob_url_with_sas

    except Exception as e:
        logger.error(f"Failed to upload slide {slide_number} image to Azure: {str(e)}")
        return None


def upload_pptx_to_azure(
    user_id: str,
    presentation_id: str,
    pptx_bytes: bytes
) -> Optional[str]:
    """
    Upload PowerPoint file to Azure Blob Storage.

    Args:
        user_id: User's ID
        presentation_id: Presentation ID
        pptx_bytes: PowerPoint file as bytes

    Returns:
        Azure blob URL with SAS token or None if upload fails
    """
    try:
        # Check file size
        file_size = len(pptx_bytes)
        if file_size > MAX_PPTX_SIZE:
            logger.error(f"PPTX file too large: {file_size} bytes (max {MAX_PPTX_SIZE})")
            return None

        # Construct blob path: {user_id}/presentations/{presentation_id}/presentation.pptx
        blob_path = f"{user_id}/presentations/{presentation_id}/presentation.pptx"

        logger.info(f"Uploading PPTX to Azure: {blob_path} ({file_size} bytes)")

        # Get blob client
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_path
        )

        # Upload with PPTX content type
        content_settings = ContentSettings(
            content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        blob_client.upload_blob(
            pptx_bytes,
            overwrite=True,
            content_settings=content_settings
        )

        # Generate SAS token valid for 10 years
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=CONTAINER_NAME,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(days=3650)
        )

        # Construct URL with SAS token
        blob_url_with_sas = f"{blob_client.url}?{sas_token}"
        logger.info(f"Successfully uploaded PPTX to Azure")

        return blob_url_with_sas

    except Exception as e:
        logger.error(f"Failed to upload PPTX to Azure: {str(e)}")
        return None


def save_presentation_stage1(
    user_id: str,
    presentation_data: Dict[str, Any],
    slides_data: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Save presentation after Stage 1 (content generation).
    Creates database record without PPTX file.

    Args:
        user_id: User's ID
        presentation_data: Presentation metadata
        slides_data: List of slide objects with content

    Returns:
        Dictionary with presentation_id and status
    """
    presentation_id = str(uuid.uuid4())
    azure_folder_path = f"{user_id}/presentations/{presentation_id}/"

    try:
        logger.info(f"Saving Stage 1 presentation for user {user_id}, presentation_id {presentation_id}")

        # Create database record
        presentation = PresentationCreation(
            id=presentation_id,
            user_id=user_id,
            title=presentation_data.get('title', 'Untitled Presentation'),
            source_type=presentation_data.get('source_type', 'text'),
            source_file_id=presentation_data.get('source_file_id'),
            source_text_preview=presentation_data.get('source_text_preview'),
            status='active',
            total_slides=len(slides_data),
            theme=presentation_data.get('theme', 'professional_blue'),
            image_style=None,  # Set in Stage 2
            azure_folder_path=azure_folder_path,
            pptx_url=None,  # Created in Stage 2
            thumbnail_url=None,
            slides_data=slides_data,
            preview_images=None,
            presentation_metadata={
                'stage': 1,
                'generation_options': presentation_data.get('generation_options', {}),
                'source_info': presentation_data.get('source_info', {}),
                'ai_metadata': presentation_data.get('ai_metadata', {})
            }
        )

        db.session.add(presentation)
        db.session.commit()

        logger.info(f"Successfully saved Stage 1 presentation {presentation_id}")

        return {
            'success': True,
            'presentation_id': presentation_id,
            'stage': 1
        }

    except Exception as e:
        logger.error(f"Failed to save Stage 1 presentation: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


def delete_presentation_from_azure(user_id: str, presentation_id: str) -> bool:
    """
    Delete all presentation files from Azure Blob Storage.

    Args:
        user_id: User's ID
        presentation_id: Presentation ID

    Returns:
        True if successful, False otherwise
    """
    try:
        azure_folder_path = f"{user_id}/presentations/{presentation_id}/"

        logger.info(f"Deleting presentation folder from Azure: {azure_folder_path}")

        # Get container client
        container_client = get_blob_service_client().get_container_client(CONTAINER_NAME)

        # List all blobs in the presentation folder
        blobs = container_client.list_blobs(name_starts_with=azure_folder_path)

        deleted_count = 0
        for blob in blobs:
            try:
                container_client.delete_blob(blob.name)
                deleted_count += 1
                logger.info(f"Deleted blob: {blob.name}")
            except Exception as e:
                logger.error(f"Failed to delete blob {blob.name}: {str(e)}")

        logger.info(f"Successfully deleted {deleted_count} blobs from presentation {presentation_id}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete presentation folder from Azure: {str(e)}")
        return False


def delete_presentation(user_id: str, presentation_id: str) -> Dict[str, Any]:
    """
    Delete presentation from database and Azure storage.

    Args:
        user_id: User's ID (for security check)
        presentation_id: Presentation ID

    Returns:
        Dictionary with status
    """
    try:
        # Get presentation from database
        presentation = PresentationCreation.query.filter_by(
            id=presentation_id,
            user_id=user_id
        ).first()

        if not presentation:
            return {
                'success': False,
                'error': 'Presentation not found or access denied'
            }

        # Delete from Azure
        azure_deleted = delete_presentation_from_azure(user_id, presentation_id)

        # Delete from database
        db.session.delete(presentation)
        db.session.commit()

        logger.info(f"Successfully deleted presentation {presentation_id} from database")

        return {
            'success': True,
            'message': 'Presentation deleted successfully',
            'azure_deleted': azure_deleted
        }

    except Exception as e:
        logger.error(f"Failed to delete presentation {presentation_id}: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }
