"""
Kid Art Storage Service

Handles Azure Blob Storage operations for AI-generated kid artwork.
Includes image compression, SAS token generation, and database persistence.
"""

import os
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from app.db import db
from app.models.kid_art import KidArtCreation

logger = logging.getLogger(__name__)

# Azure configuration
CONTAINER_NAME = "scoolish"


def get_blob_service_client():
    """Get Azure Blob Service Client from connection string."""
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set")
    return BlobServiceClient.from_connection_string(conn)


def compress_image(image_bytes: bytes, max_size_kb: int = 500) -> bytes:
    """
    Compress image to reduce file size while maintaining quality.

    Args:
        image_bytes: Original image bytes
        max_size_kb: Maximum size in KB (default 500KB)

    Returns:
        Compressed image bytes
    """
    try:
        img = Image.open(BytesIO(image_bytes))

        # Convert RGBA to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
                img = background

        # Resize if too large (max 1024x1024 for kids' art)
        if img.width > 1024 or img.height > 1024:
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

        # Progressive quality reduction
        output = BytesIO()
        quality = 85

        while quality > 20:
            output.seek(0)
            output.truncate()
            img.save(output, format='JPEG', optimize=True, quality=quality)

            if output.tell() <= max_size_kb * 1024:
                break

            quality -= 5

        return output.getvalue()

    except Exception as e:
        logger.error(f"Error compressing image: {str(e)}")
        return image_bytes  # Return original if compression fails


def upload_kid_art_image_to_azure(
    user_id: str,
    art_id: str,
    variation_num: int,
    image_bytes: bytes,
    compress: bool = True
) -> Optional[str]:
    """
    Upload kid artwork image to Azure Blob Storage.

    Args:
        user_id: User ID
        art_id: Artwork ID
        variation_num: Variation number (1-4)
        image_bytes: Image bytes
        compress: Whether to compress (default True)

    Returns:
        Image URL with SAS token, or None if failed
    """
    try:
        # Compress if requested
        if compress:
            image_bytes = compress_image(image_bytes)

        # Build blob path
        blob_path = f"{user_id}/kid_art/{art_id}/variation_{variation_num}.jpg"

        logger.info(f"Uploading kid art image to Azure: {blob_path}")

        # Upload to Azure
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_path
        )

        blob_client.upload_blob(image_bytes, overwrite=True)

        # Generate SAS token (10-year expiry)
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=CONTAINER_NAME,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(days=3650)
        )

        blob_url_with_sas = f"{blob_client.url}?{sas_token}"

        logger.info(f"Successfully uploaded kid art image: {blob_path}")
        return blob_url_with_sas

    except Exception as e:
        logger.error(f"Error uploading kid art image to Azure: {str(e)}")
        return None


def create_thumbnail(image_bytes: bytes, size: tuple = (200, 200)) -> bytes:
    """
    Create thumbnail from image.

    Args:
        image_bytes: Original image bytes
        size: Thumbnail size (default 200x200)

    Returns:
        Thumbnail bytes
    """
    try:
        img = Image.open(BytesIO(image_bytes))

        # Convert RGBA to RGB
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode in ('RGBA', 'LA'):
                background.paste(img, mask=img.split()[-1])
                img = background

        # Create thumbnail
        img.thumbnail(size, Image.Resampling.LANCZOS)

        output = BytesIO()
        img.save(output, format='JPEG', quality=75, optimize=True)
        return output.getvalue()

    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        return image_bytes


def save_kid_art_creation(
    user_id: str,
    art_data: Dict[str, Any],
    images_with_dalle_urls: list
) -> Dict[str, Any]:
    """
    Save kid art creation to database and Azure storage.

    Args:
        user_id: User ID
        art_data: Artwork metadata
        images_with_dalle_urls: List of dicts with {variation_num, dalle_url}

    Returns:
        Result dict with success status and artwork ID
    """
    try:
        art_id = str(uuid.uuid4())
        azure_folder = f"{user_id}/kid_art/{art_id}"

        logger.info(f"Saving kid art creation {art_id} for user {user_id}")

        # Process each variation
        processed_images = []

        for img_data in images_with_dalle_urls:
            variation_num = img_data.get('variation_num')
            dalle_url = img_data.get('dalle_url')

            if not dalle_url:
                logger.warning(f"No DALL-E URL for variation {variation_num}")
                continue

            # Download from DALL-E
            import requests
            response = requests.get(dalle_url, timeout=60)
            response.raise_for_status()
            image_bytes = response.content

            # Upload full image
            image_url = upload_kid_art_image_to_azure(
                user_id=user_id,
                art_id=art_id,
                variation_num=variation_num,
                image_bytes=image_bytes,
                compress=True
            )

            # Create and upload thumbnail
            thumbnail_bytes = create_thumbnail(image_bytes)
            thumbnail_url = upload_kid_art_image_to_azure(
                user_id=user_id,
                art_id=art_id,
                variation_num=f"{variation_num}_thumb",
                image_bytes=thumbnail_bytes,
                compress=False
            )

            processed_images.append({
                'variation_num': variation_num,
                'image_url': image_url,
                'thumbnail_url': thumbnail_url
            })

        # Create database record
        kid_art = KidArtCreation(
            id=art_id,
            user_id=user_id,
            title=art_data.get('title', 'My Artwork'),
            prompt_text=art_data.get('prompt_text'),
            age_group=art_data.get('age_group'),
            art_style=art_data.get('art_style'),
            color_palette=art_data.get('color_palette'),
            num_variations=len(processed_images),
            azure_folder_path=azure_folder,
            images=processed_images,
            story_text=art_data.get('story_text'),
            character_name=art_data.get('character_name'),
            collection_name=art_data.get('collection_name'),
            original_prompt=art_data.get('original_prompt'),
            sanitized_prompt=art_data.get('sanitized_prompt'),
            generation_metadata=art_data.get('generation_metadata', {}),
            source_file_id=art_data.get('source_file_id')
        )

        db.session.add(kid_art)
        db.session.commit()

        logger.info(f"Successfully saved kid art creation {art_id}")

        return {
            'success': True,
            'art_id': art_id,
            'images': processed_images,
            'num_variations': len(processed_images)
        }

    except Exception as e:
        logger.error(f"Error saving kid art creation: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


def delete_kid_art(user_id: str, art_id: str) -> Dict[str, Any]:
    """
    Delete kid art creation from database and Azure storage.

    Args:
        user_id: User ID
        art_id: Artwork ID

    Returns:
        Result dict with success status
    """
    try:
        # Get artwork from database
        kid_art = KidArtCreation.query.filter_by(
            id=art_id,
            user_id=user_id
        ).first()

        if not kid_art:
            return {'success': False, 'error': 'Artwork not found'}

        # Delete from Azure
        try:
            blob_service_client = get_blob_service_client()
            container_client = blob_service_client.get_container_client(CONTAINER_NAME)
            blob_list = container_client.list_blobs(name_starts_with=kid_art.azure_folder_path)

            for blob in blob_list:
                blob_client = blob_service_client.get_blob_client(
                    container=CONTAINER_NAME,
                    blob=blob.name
                )
                blob_client.delete_blob()
                logger.info(f"Deleted blob: {blob.name}")

        except Exception as azure_error:
            logger.error(f"Error deleting from Azure: {str(azure_error)}")
            # Continue to delete from database even if Azure delete fails

        # Delete from database
        db.session.delete(kid_art)
        db.session.commit()

        logger.info(f"Successfully deleted kid art {art_id}")

        return {'success': True}

    except Exception as e:
        logger.error(f"Error deleting kid art: {str(e)}")
        db.session.rollback()
        return {'success': False, 'error': str(e)}


def download_image_from_url(url: str) -> Optional[bytes]:
    """
    Download image from URL.

    Args:
        url: Image URL

    Returns:
        Image bytes or None if failed
    """
    try:
        import requests
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}")
        return None
