#!/usr/bin/env python3
"""
Configure CORS for Azure Blob Storage to allow frontend to load 3D models.
This script sets up CORS rules to allow GLB/OBJ/STL files to be loaded by the browser.
"""

import os
from azure.storage.blob import BlobServiceClient, CorsRule
from dotenv import load_dotenv

load_dotenv()

def configure_cors():
    """Configure CORS rules for Azure Blob Storage."""

    # Get connection string from environment
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")

    if not connection_string:
        print("❌ Error: AZURE_STORAGE_CONNECTION_STRING not found in environment")
        return False

    try:
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Define CORS rules
        cors_rule = CorsRule(
            allowed_origins=[
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://172.178.120.199:3000",
                "https://scoolish.com",
                "https://www.scoolish.com"
            ],
            allowed_methods=["GET", "HEAD", "OPTIONS"],
            allowed_headers=[
                "x-ms-blob-type",
                "x-ms-blob-content-type",
                "x-ms-version",
                "Content-Type",
                "Accept",
                "Range"
            ],
            exposed_headers=[
                "x-ms-request-id",
                "x-ms-version",
                "Content-Length",
                "Content-Type",
                "Content-Range",
                "Accept-Ranges"
            ],
            max_age_in_seconds=3600
        )

        # Get current service properties
        properties = blob_service_client.get_service_properties()

        # Set CORS rules
        properties['cors'] = [cors_rule]

        # Update service properties
        blob_service_client.set_service_properties(
            cors=[cors_rule]
        )

        print("✅ CORS configuration successfully applied to Azure Blob Storage!")
        print("\n📋 Configured CORS Rules:")
        print(f"   Allowed Origins: {', '.join(cors_rule.allowed_origins)}")
        print(f"   Allowed Methods: {', '.join(cors_rule.allowed_methods)}")
        print(f"   Max Age: {cors_rule.max_age_in_seconds} seconds")

        return True

    except Exception as e:
        print(f"❌ Error configuring CORS: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 Configuring Azure Blob Storage CORS for 3D Model Viewer...")
    print()

    success = configure_cors()

    if success:
        print("\n✨ CORS configuration complete! The frontend can now load 3D models.")
    else:
        print("\n❌ CORS configuration failed. Please check your Azure credentials.")
