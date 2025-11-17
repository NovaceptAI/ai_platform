"""
3D Model Storage Service

Handles uploading and managing 3D model files in Azure Blob Storage.
Manages file lifecycle, preview images, and database records.
"""

import os
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from io import BytesIO
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from app.db import db
from app.models.three_d_models import ThreeDModelCreation

logger = logging.getLogger(__name__)

# Azure Storage Configuration
CONTAINER_NAME = "scoolish"  # Same container as other services


def get_blob_service_client():
    """Get Azure Blob Service Client from connection string."""
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING is not set")
    return BlobServiceClient.from_connection_string(conn)


def upload_3d_model_file_to_azure(
    user_id: str,
    model_id: str,
    file_format: str,
    file_bytes: bytes
) -> Optional[str]:
    """
    Upload 3D model file to Azure Blob Storage.

    Args:
        user_id: User's ID
        model_id: Model ID
        file_format: File format (glb, obj, stl)
        file_bytes: File content as bytes

    Returns:
        Azure blob URL with SAS token or None if upload fails
    """
    try:
        # Construct blob path
        blob_path = f"{user_id}/3d_models/{model_id}/model.{file_format}"

        logger.info(f"Uploading {file_format.upper()} file to Azure: {blob_path}")

        # Get blob client
        blob_service_client = get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=blob_path
        )

        # Set content type based on format
        content_types = {
            'glb': 'model/gltf-binary',
            'obj': 'model/obj',
            'stl': 'model/stl'
        }
        content_settings = ContentSettings(
            content_type=content_types.get(file_format, 'application/octet-stream')
        )

        # Upload
        blob_client.upload_blob(
            file_bytes,
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

        # Construct full URL with SAS token
        blob_url_with_sas = f"{blob_client.url}?{sas_token}"

        logger.info(f"Successfully uploaded {file_format.upper()} file")
        return blob_url_with_sas

    except Exception as e:
        logger.error(f"Error uploading {file_format} file to Azure: {str(e)}")
        return None


def upload_preview_image_to_azure(
    user_id: str,
    model_id: str,
    angle: str,
    image_bytes: bytes
) -> Optional[str]:
    """
    Upload preview image to Azure Blob Storage.

    Args:
        user_id: User's ID
        model_id: Model ID
        angle: View angle (front, side, top, perspective)
        image_bytes: Image content as bytes

    Returns:
        Azure blob URL with SAS token or None if upload fails
    """
    try:
        # Construct blob path
        blob_path = f"{user_id}/3d_models/{model_id}/previews/{angle}.png"

        logger.info(f"Uploading preview image ({angle}) to Azure: {blob_path}")

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

        # Generate SAS token valid for 10 years
        sas_token = generate_blob_sas(
            account_name=blob_service_client.account_name,
            container_name=CONTAINER_NAME,
            blob_name=blob_path,
            account_key=blob_service_client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(days=3650)
        )

        # Construct full URL with SAS token
        blob_url_with_sas = f"{blob_client.url}?{sas_token}"

        logger.info(f"Successfully uploaded preview image ({angle})")
        return blob_url_with_sas

    except Exception as e:
        logger.error(f"Error uploading preview image to Azure: {str(e)}")
        return None


def save_3d_model_to_azure(
    user_id: str,
    model_data: Dict[str, Any],
    export_files: Dict[str, bytes],
    preview_images: List[Dict[str, Any]],
    mesh_metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Save 3D model files to Azure and create database record.

    Args:
        user_id: User ID
        model_data: Model metadata (title, prompt, style, etc.)
        export_files: Dict of format -> file bytes (glb, obj, stl)
        preview_images: List of preview image dicts with angle and image_bytes
        mesh_metadata: Mesh statistics and properties

    Returns:
        Dict with success status and model_id
    """
    try:
        model_id = str(uuid.uuid4())
        azure_folder = f"{user_id}/3d_models/{model_id}"

        logger.info(f"[3DModelStorage] Saving 3D model {model_id} for user {user_id}")

        # Upload model files to Azure
        model_files = {}
        file_size_total = 0

        for file_format, file_bytes in export_files.items():
            logger.info(f"[3DModelStorage] Uploading {file_format.upper()} file ({len(file_bytes)} bytes)")

            url = upload_3d_model_file_to_azure(
                user_id=user_id,
                model_id=model_id,
                file_format=file_format,
                file_bytes=file_bytes
            )

            if url:
                model_files[f'{file_format}_url'] = url
                file_size_total += len(file_bytes)
                logger.info(f"[3DModelStorage] Uploaded {file_format}: {url[:100]}...")
            else:
                logger.error(f"[3DModelStorage] Failed to upload {file_format} file")

        # Upload preview images to Azure
        preview_images_data = []
        thumbnail_url = None

        for preview in preview_images:
            angle = preview.get('angle', 'unknown')
            image_bytes = preview.get('image_bytes')

            # Skip if no image data (placeholder)
            if not image_bytes:
                logger.warning(f"[3DModelStorage] No image data for {angle}, skipping")
                continue

            logger.info(f"[3DModelStorage] Uploading preview image: {angle}")

            url = upload_preview_image_to_azure(
                user_id=user_id,
                model_id=model_id,
                angle=angle,
                image_bytes=image_bytes
            )

            if url:
                preview_images_data.append({
                    'angle': angle,
                    'url': url
                })

                # Use perspective view as thumbnail, or first image
                if angle == 'perspective' or thumbnail_url is None:
                    thumbnail_url = url

                logger.info(f"[3DModelStorage] Uploaded preview: {angle}")

        # Prepare camera and lighting default settings
        camera_settings = {
            'position': [5, 5, 5],
            'rotation': [0, 45, 0],
            'zoom': 1.0,
            'target': [0, 0, 0]
        }

        lighting_config = {
            'ambient': {'color': '#FFFFFF', 'intensity': 0.5},
            'directional': {'color': '#FFFFFF', 'intensity': 0.8, 'position': [5, 10, 7.5]}
        }

        material_properties = {
            'base_color': '#888888',
            'roughness': 0.5,
            'metalness': 0.0
        }

        # Create database record
        model_record = ThreeDModelCreation(
            id=model_id,
            user_id=user_id,
            title=model_data.get('title', 'My 3D Model'),
            prompt_text=model_data.get('prompt_text', ''),
            category=model_data.get('category'),
            complexity_level=model_data.get('complexity_level', 'simple'),
            style=model_data.get('style', 'realistic'),
            azure_folder_path=azure_folder,
            model_files=model_files,
            preview_images=preview_images_data,
            thumbnail_url=thumbnail_url,
            object_type=model_data.get('object_type'),
            vertex_count=mesh_metadata.get('vertex_count', 0),
            polygon_count=mesh_metadata.get('face_count', 0),
            file_size_bytes=file_size_total,
            camera_settings=camera_settings,
            lighting_config=lighting_config,
            material_properties=material_properties,
            bounding_box=mesh_metadata.get('bounds', {}),
            generation_metadata=model_data.get('generation_metadata', {}),
            status='active',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.session.add(model_record)
        db.session.commit()

        logger.info(f"[3DModelStorage] Successfully saved 3D model {model_id} to database")

        return {
            'success': True,
            'model_id': model_id,
            'thumbnail_url': thumbnail_url,
            'files_uploaded': len(model_files),
            'preview_images_count': len(preview_images_data)
        }

    except Exception as e:
        logger.error(f"[3DModelStorage] Error saving 3D model: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


def delete_3d_model(user_id: str, model_id: str) -> Dict[str, Any]:
    """
    Delete a 3D model and all associated files.

    Args:
        user_id: User ID
        model_id: Model ID

    Returns:
        Dict with success status
    """
    try:
        logger.info(f"[3DModelStorage] Deleting 3D model {model_id} for user {user_id}")

        # Get model from database
        model = ThreeDModelCreation.query.filter_by(
            id=model_id,
            user_id=user_id
        ).first()

        if not model:
            logger.warning(f"[3DModelStorage] Model {model_id} not found for user {user_id}")
            return {
                'success': False,
                'error': 'Model not found or access denied'
            }

        # Delete files from Azure
        try:
            blob_service_client = get_blob_service_client()

            # Delete model files
            for file_format in ['glb', 'obj', 'stl']:
                blob_path = f"{user_id}/3d_models/{model_id}/model.{file_format}"
                try:
                    blob_client = blob_service_client.get_blob_client(
                        container=CONTAINER_NAME,
                        blob=blob_path
                    )
                    blob_client.delete_blob()
                    logger.info(f"[3DModelStorage] Deleted {file_format} file")
                except Exception as e:
                    logger.warning(f"[3DModelStorage] Could not delete {file_format}: {str(e)}")

            # Delete preview images
            if model.preview_images:
                for preview in model.preview_images:
                    angle = preview.get('angle')
                    if angle:
                        blob_path = f"{user_id}/3d_models/{model_id}/previews/{angle}.png"
                        try:
                            blob_client = blob_service_client.get_blob_client(
                                container=CONTAINER_NAME,
                                blob=blob_path
                            )
                            blob_client.delete_blob()
                            logger.info(f"[3DModelStorage] Deleted preview: {angle}")
                        except Exception as e:
                            logger.warning(f"[3DModelStorage] Could not delete preview {angle}: {str(e)}")

        except Exception as azure_error:
            logger.error(f"[3DModelStorage] Error deleting Azure files: {str(azure_error)}")
            # Continue to delete database record even if Azure deletion fails

        # Delete database record
        db.session.delete(model)
        db.session.commit()

        logger.info(f"[3DModelStorage] Successfully deleted 3D model {model_id}")

        return {
            'success': True,
            'model_id': model_id
        }

    except Exception as e:
        logger.error(f"[3DModelStorage] Error deleting 3D model: {str(e)}")
        db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }
