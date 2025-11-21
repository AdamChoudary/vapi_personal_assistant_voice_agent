"""
Test script for declined payment batch processing workflow.

Tests:
- CSV parsing
- Customer matching
- Priority calculation
- Day 0 SMS
- Database tracking
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.fontis_client import FontisClient
from src.services.batch_orchestrator import BatchOrchestrator
from src.services.batch_database import BatchDatabase
from src.services.declined_payment_processor import DeclinedPaymentProcessor

load_dotenv()


async def test_csv_processing():
    """Test CSV processing workflow."""
    print("🧪 Testing Declined Payment Batch Processing\n")
    
    # Initialize services
    fontis = FontisClient()
    orchestrator = BatchOrchestrator(fontis)
    
    # Test CSV path (use sample from docs)
    csv_path = Path("docs/Batch_20000_20250930181935_result (1).csv")
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        print("   Please ensure the CSV file exists in docs/ directory")
        return
    
    print(f"📄 Processing CSV: {csv_path.name}\n")
    
    try:
        # Process batch
        result = await orchestrator.process_batch_csv(csv_path, "20000")
        
        print("✅ Batch Processing Results:")
        print(f"   Total Records: {result['total_records']}")
        print(f"   Declined Count: {result['declined_count']}")
        print(f"   Matched Customers: {result['matched_count']}")
        print(f"   Unmatched Records: {result['unmatched_count']}")
        print(f"   SMS Sent: {result.get('sms_sent', 0)}")
        print(f"   SMS Failed: {result.get('sms_failed', 0)}\n")
        
        if result['matched_customers']:
            print("📋 Matched Customers:")
            for customer in result['matched_customers'][:5]:  # Show first 5
                print(f"   - {customer['name']} (ID: {customer['customer_id']})")
                print(f"     Phone: {customer['phone']}")
                print(f"     Declined: ${customer['declined_amount']:.2f}")
                print(f"     Total Due: ${customer['total_due']:.2f}")
                print(f"     Match Method: {customer['match_method']}\n")
        
        if result['unmatched_records']:
            print(f"⚠️  Unmatched Records ({len(result['unmatched_records'])}):")
            for record in result['unmatched_records'][:3]:  # Show first 3
                print(f"   - {record['name']} ({record['phone']})")
                print(f"     Amount: ${record['amount']:.2f}\n")
        
        print("✅ CSV processing test complete!\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await fontis.close()


async def test_customer_matching():
    """Test customer matching logic."""
    print("🧪 Testing Customer Matching\n")
    
    fontis = FontisClient()
    processor = DeclinedPaymentProcessor(fontis)
    
    # Test with sample declined record
    from src.services.declined_payment_processor import DeclinedPaymentRecord
    
    test_record = DeclinedPaymentRecord({
        "id": "test123",
        "customer_id": "",
        "amount": "44.78",
        "status": "declined",
        "response_code": "202",
        "processor_response_text": "Insufficient funds",
        "billing_first_name": "SANDY",
        "billing_last_name": "McCoy",
        "billing_phone": "4704459854",
        "billing_email": "sandygmccoy@yahoo.com",
        "billing_address_line_1": "55 Henderson St",
        "billing_city": "Marietta",
        "billing_state": "GA",
        "billing_postal_code": "30064",
        "created_at": "2025-09-30 22:21:45"
    })
    
    print(f"🔍 Testing match for: {test_record.full_name}")
    print(f"   Phone: {test_record.billing_phone}")
    print(f"   Email: {test_record.billing_email}")
    print(f"   Address: {test_record.full_address}\n")
    
    try:
        match_result = await processor._match_customer(test_record)
        
        if match_result.matched:
            print("✅ Customer Matched!")
            print(f"   Customer ID: {match_result.customer_id}")
            print(f"   Match Method: {match_result.match_method}")
            print(f"   Confidence: {match_result.confidence}")
            print(f"   Total Due: ${match_result.total_due:.2f}")
        else:
            print("❌ No match found")
            print("   (This is expected if customer doesn't exist in Fontis system)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await fontis.close()


async def test_priority_calculation():
    """Test priority calculation."""
    print("🧪 Testing Priority Calculation\n")
    
    fontis = FontisClient()
    from src.services.priority_calculator import PriorityCalculator
    
    calculator = PriorityCalculator(fontis)
    
    # Test with a customer ID (use one from CSV if available)
    test_customer_id = "cosgt7n0i478ibepeb70"  # From CSV sample
    
    print(f"📊 Calculating priority for customer: {test_customer_id}\n")
    
    try:
        priority_result = await calculator.calculate_priority(
            customer_id=test_customer_id,
            is_repeat_decline=False
        )
        
        print("✅ Priority Calculation Results:")
        print(f"   Priority: {priority_result.priority.value.upper()}")
        print(f"   Account Active: {priority_result.account_active}")
        print(f"   Payment Still Due: {priority_result.payment_still_due}")
        print(f"   Total Due: ${priority_result.total_due or 0:.2f}")
        
        if priority_result.next_delivery_date:
            print(f"   Next Delivery: {priority_result.next_delivery_date.strftime('%Y-%m-%d')}")
            print(f"   Days Until Delivery: {priority_result.days_until_delivery} business days")
        
        print(f"\n   Should Call: {priority_result.should_call()}")
        print(f"   Should SMS: {priority_result.should_sms()}")
        print(f"   Should Email: {priority_result.should_email()}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await fontis.close()


async def test_database():
    """Test database operations."""
    print("🧪 Testing Database Operations\n")
    
    db_path = Path("data/batch_tracking.db")
    db = BatchDatabase(db_path)
    
    # Test batch recording
    db.record_batch_processed(
        batch_id="TEST_001",
        total_records=100,
        declined_count=5,
        matched_count=4,
        sms_sent=4,
        csv_filename="test.csv"
    )
    
    print("✅ Batch recorded in database")
    
    # Test customer decline recording
    db.record_customer_decline(
        customer_id="TEST_CUSTOMER",
        batch_id="TEST_001",
        declined_amount=45.99,
        priority="high"
    )
    
    print("✅ Customer decline recorded")
    
    # Test outreach recording
    db.record_outreach(
        customer_id="TEST_CUSTOMER",
        batch_id="TEST_001",
        outreach_type="sms",
        priority="high",
        sms_id="sms_123",
        success=True
    )
    
    print("✅ Outreach recorded")
    
    # Get active customers
    active = db.get_active_declined_customers()
    print(f"✅ Active declined customers: {len(active)}")
    
    print("\n✅ Database test complete!\n")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Declined Payment Batch Processing - Test Suite")
    print("=" * 60 + "\n")
    
    # Test database first (no external dependencies)
    await test_database()
    
    # Test customer matching (requires Fontis API)
    print("\n" + "=" * 60 + "\n")
    await test_customer_matching()
    
    # Test priority calculation (requires Fontis API)
    print("\n" + "=" * 60 + "\n")
    await test_priority_calculation()
    
    # Test full CSV processing (requires Fontis API + VAPI)
    print("\n" + "=" * 60 + "\n")
    print("⚠️  Full CSV processing test requires:")
    print("   - Fontis API credentials")
    print("   - VAPI API key (for SMS)")
    print("   - CSV file in docs/ directory")
    print("\n   Run manually: await test_csv_processing()\n")


if __name__ == "__main__":
    asyncio.run(main())


