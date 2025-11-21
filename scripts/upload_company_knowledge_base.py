"""
Upload Company documentation to Vapi Knowledge Base.

This script uploads the Company markdown files (overview.md and products-and-services.md)
to Vapi's Knowledge Base so the assistant can reference detailed information.

Usage:
    python scripts/upload_company_knowledge_base.py
"""

import asyncio
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "214d510a-23eb-415a-acc6-591e2ac697bc")
VAPI_BASE_URL = "https://api.vapi.ai"

COMPANY_FILES = [
    "ai-training-main/Company/overview.md",
    "ai-training-main/Company/products-and-services.md",
]


async def upload_file_to_knowledge_base(
    client: httpx.AsyncClient, file_path: Path, assistant_id: str
) -> dict[str, any] | None:
    """
    Upload a markdown file to Vapi Knowledge Base.
    
    Note: Vapi Knowledge Base API may require different endpoints.
    This is a template - adjust based on actual Vapi API documentation.
    """
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        # Vapi Knowledge Base upload endpoint (verify in Vapi docs)
        # Common pattern: POST /assistant/{assistantId}/knowledge-base/files
        response = await client.post(
            f"{VAPI_BASE_URL}/assistant/{assistant_id}/knowledge-base/files",
            files={
                "file": (file_path.name, file_content, "text/markdown"),
            },
            data={
                "name": file_path.stem,  # filename without extension
                "description": f"Fontis Water {file_path.stem.replace('-', ' ').title()}",
            },
            timeout=60.0,
        )
        
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        else:
            print(f"   ⚠️  Upload failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return None
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            print(f"   ⚠️  Knowledge Base endpoint not found - may need to enable Knowledge Base feature")
        elif e.response.status_code == 401:
            print(f"   ⚠️  Authentication failed - check VAPI_API_KEY")
        else:
            print(f"   ⚠️  HTTP Error: {e.response.status_code}")
        return None
    except Exception as e:
        print(f"   ❌ Error uploading {file_path.name}: {str(e)}")
        return None


async def main() -> int:
    """Main execution."""
    if not VAPI_API_KEY:
        print("❌ Missing VAPI_API_KEY environment variable")
        return 1
    
    print("=" * 80)
    print("📚 UPLOADING COMPANY DOCUMENTATION TO VAPI KNOWLEDGE BASE")
    print("=" * 80)
    print(f"Assistant ID: {ASSISTANT_ID}")
    print()
    
    # Check files exist
    project_root = Path(__file__).parent.parent
    files_to_upload = []
    
    for file_rel_path in COMPANY_FILES:
        file_path = project_root / file_rel_path
        if file_path.exists():
            files_to_upload.append(file_path)
            print(f"✓ Found: {file_rel_path}")
        else:
            print(f"✗ Missing: {file_rel_path}")
    
    if not files_to_upload:
        print("\n❌ No Company files found to upload")
        return 1
    
    print(f"\n📤 Uploading {len(files_to_upload)} file(s) to Knowledge Base...")
    print()
    
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        uploaded = []
        failed = []
        
        for file_path in files_to_upload:
            print(f"📄 Uploading {file_path.name}...")
            result = await upload_file_to_knowledge_base(client, file_path, ASSISTANT_ID)
            
            if result:
                uploaded.append(file_path.name)
                print(f"   ✅ Uploaded successfully")
            else:
                failed.append(file_path.name)
                print(f"   ❌ Upload failed")
            print()
    
    print("=" * 80)
    if uploaded:
        print(f"✅ Successfully uploaded {len(uploaded)} file(s):")
        for name in uploaded:
            print(f"   • {name}")
    
    if failed:
        print(f"\n⚠️  Failed to upload {len(failed)} file(s):")
        for name in failed:
            print(f"   • {name}")
        print("\n💡 ALTERNATIVE: Manual Upload via Vapi Dashboard")
        print("   1. Go to https://dashboard.vapi.ai")
        print(f"   2. Select your assistant (ID: {ASSISTANT_ID})")
        print("   3. Navigate to 'Knowledge Base' or 'Files' section")
        print("   4. Upload the Company markdown files manually")
        print("   5. The assistant will automatically reference them during calls")
    
    print()
    print("📋 NOTE: If Knowledge Base API is not available, use the system prompt approach.")
    print("   The Company data is already integrated into the system prompt via")
    print("   scripts/setup_new_assistant_complete.py")
    print()
    
    return 0 if not failed else 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))

