#!/usr/bin/env python3
"""
Test script for Research Artifacts API endpoints
Tests flashcards and presentation generation from research workspace
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5001"  # Adjust if needed
API_BASE = f"{BASE_URL}/api"

# Test credentials (adjust as needed)
TEST_USER = {
    "email": "test@example.com",
    "password": "test123"
}

def login():
    """Get JWT token"""
    print("🔐 Logging in...")
    response = requests.post(f"{API_BASE}/auth/login", json=TEST_USER)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return None
    token = response.json().get('access_token')
    print(f"✅ Logged in successfully")
    return token

def create_test_project(token):
    """Create a test research project"""
    print("\n📁 Creating test research project...")
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "title": "Test Research Project",
        "topic": "AI and Machine Learning",
        "description": "Test project for artifacts integration"
    }
    response = requests.post(f"{API_BASE}/research/projects", json=data, headers=headers)
    if response.status_code != 201:
        print(f"❌ Failed to create project: {response.text}")
        return None
    project_id = response.json().get('id')
    print(f"✅ Created project: {project_id}")
    return project_id

def create_test_session(token, project_id):
    """Create a test research session"""
    print("\n📝 Creating test research session...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(f"{API_BASE}/research/projects/{project_id}/sessions", headers=headers)
    if response.status_code != 201:
        print(f"❌ Failed to create session: {response.text}")
        return None
    session_id = response.json().get('id')
    print(f"✅ Created session: {session_id}")
    return session_id

def test_generate_flashcards(token, session_id, file_ids):
    """Test flashcards generation endpoint"""
    print("\n🃏 Testing flashcards generation...")
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "file_ids": file_ids,
        "title": "Test Flashcards",
        "options": {
            "max_cards": 10,
            "difficulty": "medium",
            "include_definitions": True,
            "include_concepts": True,
            "include_facts": True
        }
    }
    response = requests.post(
        f"{API_BASE}/research/sessions/{session_id}/flashcards",
        json=data,
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"❌ Failed to generate flashcards: {response.text}")
        return None
    
    result = response.json()
    print(f"✅ Flashcards generation started:")
    print(f"   Artifact ID: {result['artifact_id']}")
    print(f"   Progress ID: {result['progress_id']}")
    print(f"   Status: {result['status']}")
    return result

def test_list_flashcards(token, session_id):
    """Test list flashcards endpoint"""
    print("\n📋 Testing list flashcards...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/research/sessions/{session_id}/flashcards",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to list flashcards: {response.text}")
        return None
    
    artifacts = response.json()
    print(f"✅ Found {len(artifacts)} flashcard artifacts:")
    for artifact in artifacts:
        print(f"   - {artifact['title']} ({artifact['status']})")
    return artifacts

def test_get_artifact(token, artifact_id):
    """Test get artifact endpoint"""
    print(f"\n🔍 Testing get artifact {artifact_id}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/research/artifacts/{artifact_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get artifact: {response.text}")
        return None
    
    artifact = response.json()
    print(f"✅ Retrieved artifact:")
    print(f"   Type: {artifact['artifact_type']}")
    print(f"   Title: {artifact['title']}")
    print(f"   Status: {artifact['status']}")
    return artifact

def test_get_progress(token, artifact_id):
    """Test get artifact progress endpoint"""
    print(f"\n⏳ Testing get artifact progress...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/research/artifacts/{artifact_id}/progress",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to get progress: {response.text}")
        return None
    
    progress = response.json()
    print(f"✅ Progress info:")
    print(f"   Artifact Status: {progress['artifact_status']}")
    if 'percentage' in progress:
        print(f"   Progress: {progress['percentage']}%")
        print(f"   Status: {progress.get('status', 'N/A')}")
    return progress

def test_generate_presentation(token, session_id):
    """Test presentation generation endpoint"""
    print("\n🎬 Testing presentation generation...")
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "title": "Test Presentation",
        "options": {
            "source_type": "text",
            "text_prompt": "Create a presentation about artificial intelligence and its applications in modern education. Cover machine learning, natural language processing, and personalized learning.",
            "total_slides": 8,
            "theme": "professional_blue"
        }
    }
    response = requests.post(
        f"{API_BASE}/research/sessions/{session_id}/presentations",
        json=data,
        headers=headers
    )
    
    if response.status_code != 201:
        print(f"❌ Failed to generate presentation: {response.text}")
        return None
    
    result = response.json()
    print(f"✅ Presentation generation started:")
    print(f"   Artifact ID: {result['artifact_id']}")
    print(f"   Progress ID: {result['progress_id']}")
    print(f"   Status: {result['status']}")
    return result

def test_list_presentations(token, session_id):
    """Test list presentations endpoint"""
    print("\n📊 Testing list presentations...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE}/research/sessions/{session_id}/presentations",
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Failed to list presentations: {response.text}")
        return None
    
    artifacts = response.json()
    print(f"✅ Found {len(artifacts)} presentation artifacts:")
    for artifact in artifacts:
        print(f"   - {artifact['title']} ({artifact['status']})")
    return artifacts

def main():
    """Run all tests"""
    print("=" * 60)
    print("Research Artifacts API Integration Test")
    print("=" * 60)
    
    # Login
    token = login()
    if not token:
        sys.exit(1)
    
    # Create test project
    project_id = create_test_project(token)
    if not project_id:
        sys.exit(1)
    
    # Create test session
    session_id = create_test_session(token, project_id)
    if not session_id:
        sys.exit(1)
    
    # Note: For flashcards testing, you need actual file IDs
    # Skipping flashcards test if no files available
    print("\n⚠️  Skipping flashcards test (requires uploaded file IDs)")
    print("    To test flashcards, manually provide file IDs in the script")
    
    # Test presentations (works without files)
    presentation_result = test_generate_presentation(token, session_id)
    if presentation_result:
        artifact_id = presentation_result['artifact_id']
        
        # Wait a bit and check progress
        time.sleep(2)
        test_get_progress(token, artifact_id)
        
        # Check artifact details
        test_get_artifact(token, artifact_id)
        
        # List all presentations
        test_list_presentations(token, session_id)
    
    print("\n" + "=" * 60)
    print("✅ Test suite completed!")
    print("=" * 60)

if __name__ == '__main__':
    main()
