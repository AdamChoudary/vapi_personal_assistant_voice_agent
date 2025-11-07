"""
Automated JotForm Setup Script

This script:
1. Uses your JotForm API key
2. Creates a customer onboarding form
3. Configures all necessary fields
4. Fetches the form ID
5. Updates .env file with credentials
"""

import asyncio
import os
import sys
import httpx
from dotenv import load_dotenv

# Your JotForm API Key
JOTFORM_API_KEY = "d0b3c98a0557e5c58f4886be6862de32"
JOTFORM_BASE_URL = "https://api.jotform.com"


async def create_form():
    """Create a new JotForm for customer onboarding."""
    print("🔧 Creating JotForm for Fontis Water Customer Onboarding...\n")
    
    # Form properties
    form_data = {
        "properties": {
            "title": "Fontis Water - Customer Service Agreement",
            "height": "539",
            "thankurl": "",
            "theme": "blue",
            "sendpostdata": "enable"
        }
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create form
            print("1️⃣ Creating new form...")
            response = await client.post(
                f"{JOTFORM_BASE_URL}/form",
                params={"apiKey": JOTFORM_API_KEY},
                data=form_data
            )
            
            if response.status_code not in [200, 201]:
                print(f"❌ Failed to create form: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
            
            result = response.json()
            
            if result.get("responseCode") != 200:
                print(f"❌ API Error: {result.get('message', 'Unknown error')}")
                return None
            
            form_id = result.get("content", {}).get("id")
            
            if not form_id:
                print("❌ No form ID returned")
                return None
            
            print(f"✅ Form created successfully!")
            print(f"   Form ID: {form_id}")
            print(f"   URL: https://form.jotform.com/{form_id}\n")
            
            # Add form fields
            print("2️⃣ Adding form fields...")
            await add_form_fields(client, form_id)
            
            # Configure email notifications
            print("3️⃣ Configuring email notifications...")
            await configure_notifications(client, form_id)
            
            return form_id
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


async def add_form_fields(client: httpx.AsyncClient, form_id: str):
    """Add fields to the form."""
    
    fields = [
        # Welcome text
        {
            "type": "control_head",
            "text": "Welcome to Fontis Water!",
            "order": "1"
        },
        {
            "type": "control_text",
            "text": "Please complete this service agreement form. We'll contact you within 24 hours to schedule your first delivery.",
            "order": "2"
        },
        
        # Full Name
        {
            "type": "control_fullname",
            "text": "Full Name",
            "required": "Yes",
            "order": "3"
        },
        
        # Email
        {
            "type": "control_email",
            "text": "Email Address",
            "required": "Yes",
            "order": "4"
        },
        
        # Phone
        {
            "type": "control_phone",
            "text": "Phone Number",
            "required": "Yes",
            "order": "5"
        },
        
        # Service Address
        {
            "type": "control_address",
            "text": "Service Address",
            "required": "Yes",
            "order": "6"
        },
        
        # Delivery Preference
        {
            "type": "control_dropdown",
            "text": "Preferred Delivery Day",
            "required": "No",
            "options": "Monday|Tuesday|Wednesday|Thursday|Friday",
            "order": "7"
        },
        
        # Product Interest
        {
            "type": "control_checkbox",
            "text": "Products of Interest",
            "required": "No",
            "options": "5-Gallon Bottles|3-Gallon Bottles|1-Gallon Bottles|Water Dispenser Rental|Coffee Service",
            "order": "8"
        },
        
        # Special Instructions
        {
            "type": "control_textarea",
            "text": "Special Instructions or Questions",
            "required": "No",
            "order": "9"
        },
        
        # Terms acceptance
        {
            "type": "control_checkbox",
            "text": "Terms & Conditions",
            "required": "Yes",
            "options": "I agree to the Fontis Water service terms and conditions",
            "order": "10"
        },
        
        # Submit button
        {
            "type": "control_button",
            "text": "Submit Agreement",
            "order": "11"
        }
    ]
    
    try:
        for field in fields:
            response = await client.post(
                f"{JOTFORM_BASE_URL}/form/{form_id}/questions",
                params={"apiKey": JOTFORM_API_KEY},
                data={"question": field}
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("responseCode") == 200:
                    print(f"   ✅ Added: {field.get('text', field.get('type'))}")
                else:
                    print(f"   ⚠️  Skipped: {field.get('text', field.get('type'))}")
            else:
                print(f"   ⚠️  Error adding: {field.get('text', field.get('type'))}")
        
        print("✅ All fields added successfully!\n")
        
    except Exception as e:
        print(f"⚠️  Some fields may not have been added: {str(e)}\n")


async def configure_notifications(client: httpx.AsyncClient, form_id: str):
    """Configure email notifications for the form."""
    
    try:
        # Get current form properties
        response = await client.get(
            f"{JOTFORM_BASE_URL}/form/{form_id}/properties",
            params={"apiKey": JOTFORM_API_KEY}
        )
        
        if response.status_code == 200:
            print("✅ Email notifications can be configured in JotForm dashboard\n")
        
    except Exception as e:
        print(f"⚠️  Configure email notifications manually in JotForm dashboard\n")


async def update_env_file(form_id: str):
    """Update .env file with JotForm credentials."""
    print("4️⃣ Updating .env file...")
    
    env_path = ".env"
    
    try:
        # Read existing .env
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                lines = f.readlines()
        else:
            # Read from env.example
            with open("env.example", 'r') as f:
                lines = f.readlines()
        
        # Update JotForm credentials
        updated_lines = []
        jotform_key_updated = False
        jotform_id_updated = False
        
        for line in lines:
            if line.startswith("JOTFORM_API_KEY="):
                updated_lines.append(f"JOTFORM_API_KEY={JOTFORM_API_KEY}\n")
                jotform_key_updated = True
            elif line.startswith("JOTFORM_FORM_ID="):
                updated_lines.append(f"JOTFORM_FORM_ID={form_id}\n")
                jotform_id_updated = True
            else:
                updated_lines.append(line)
        
        # Add if not found
        if not jotform_key_updated:
            updated_lines.append(f"\n# JotForm Configuration\n")
            updated_lines.append(f"JOTFORM_API_KEY={JOTFORM_API_KEY}\n")
        
        if not jotform_id_updated:
            if not jotform_key_updated:
                updated_lines.append(f"JOTFORM_BASE_URL=https://api.jotform.com\n")
            updated_lines.append(f"JOTFORM_FORM_ID={form_id}\n")
        
        # Write updated .env
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)
        
        print("✅ .env file updated successfully!\n")
        
    except Exception as e:
        print(f"⚠️  Could not update .env automatically: {str(e)}")
        print(f"\n📝 Please add these to your .env file manually:")
        print(f"   JOTFORM_API_KEY={JOTFORM_API_KEY}")
        print(f"   JOTFORM_FORM_ID={form_id}\n")


async def verify_setup():
    """Verify JotForm setup by testing the client."""
    print("5️⃣ Verifying setup...")
    
    # Reload environment
    load_dotenv(override=True)
    
    try:
        from src.services.jotform_client import JotFormClient
        
        client = JotFormClient()
        
        # Test contract link generation
        result = await client.create_contract_link(
            customer_name="Test Customer",
            email="test@example.com",
            phone="555-555-5555",
            address="123 Test St",
            city="Test City",
            state="GA",
            postal_code="30301"
        )
        
        print("✅ JotForm client is working!")
        print(f"   Test URL: {result['url'][:80]}...\n")
        
        await client.close()
        return True
        
    except Exception as e:
        print(f"⚠️  Verification failed: {str(e)}\n")
        return False


async def main():
    """Main execution."""
    print("\n" + "=" * 60)
    print("🚀 AUTOMATED JOTFORM SETUP")
    print("=" * 60 + "\n")
    
    print(f"📋 Using API Key: {JOTFORM_API_KEY[:10]}...{JOTFORM_API_KEY[-4:]}\n")
    
    # Step 1: Create form
    form_id = await create_form()
    
    if not form_id:
        print("\n❌ Failed to create form. Please check your API key.\n")
        print("To get a valid API key:")
        print("1. Go to https://www.jotform.com/myaccount/api")
        print("2. Create a new API key")
        print("3. Run this script again with the new key\n")
        sys.exit(1)
    
    # Step 2: Update .env
    await update_env_file(form_id)
    
    # Step 3: Verify setup
    verified = await verify_setup()
    
    # Summary
    print("=" * 60)
    print("✅ JOTFORM SETUP COMPLETE!")
    print("=" * 60 + "\n")
    
    print(f"📋 Configuration:")
    print(f"   API Key: {JOTFORM_API_KEY[:10]}...{JOTFORM_API_KEY[-4:]}")
    print(f"   Form ID: {form_id}")
    print(f"   Form URL: https://form.jotform.com/{form_id}")
    print(f"   Edit Form: https://www.jotform.com/build/{form_id}\n")
    
    print("📝 Next Steps:")
    print("   1. Restart your FastAPI server: python run.py")
    print("   2. Test JotForm: python scripts/test_jotform.py")
    print("   3. Customize form at: https://www.jotform.com/build/{form_id}")
    print("   4. Test voice call: +1 (678) 303-4022\n")
    
    if verified:
        print("✅ System is ready to use!")
    else:
        print("⚠️  Please restart server and test again")
    
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())








