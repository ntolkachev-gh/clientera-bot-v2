#!/usr/bin/env python3
"""
Test script for the updated search_slots function.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from src.integrations.yclients_adapter import get_yclients_adapter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_search_slots():
    """Test the updated search_slots function."""
    adapter = get_yclients_adapter()
    
    # Get tomorrow's date
    tomorrow = datetime.now() + timedelta(days=1)
    test_date = tomorrow.strftime('%Y-%m-%d')
    
    logger.info("Testing search_slots function with updated signature")
    
    try:
        # First, get available doctors
        logger.info("Getting list of doctors...")
        doctors = await adapter.list_doctors()
        
        if not doctors:
            logger.error("No doctors found!")
            return
        
        # Use the first doctor for testing
        test_doctor = doctors[0]
        doctor_id = test_doctor.get('id')
        doctor_name = test_doctor.get('name', 'Unknown')
        
        logger.info(f"Testing with doctor: {doctor_name} (ID: {doctor_id}) on date: {test_date}")
        
        # Test the search_slots function
        slots = await adapter.search_slots(doctor_id=doctor_id, date=test_date)
        
        logger.info(f"Found {len(slots)} slots:")
        for i, slot in enumerate(slots[:5]):  # Show first 5 slots
            logger.info(f"  {i+1}. {slot.get('time')} - {slot.get('doctor')} - Service: {slot.get('service_name', 'N/A')}")
        
        if len(slots) > 5:
            logger.info(f"  ... and {len(slots) - 5} more slots")
        
        # Test with invalid doctor ID
        logger.info("\nTesting with invalid doctor ID...")
        invalid_slots = await adapter.search_slots(doctor_id=99999, date=test_date)
        logger.info(f"Invalid doctor test: found {len(invalid_slots)} slots (should be 0)")
        
        logger.info("\n✅ Test completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_search_slots())
