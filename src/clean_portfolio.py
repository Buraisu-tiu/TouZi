from utils.db import db
from google.cloud import firestore
import sys

def clean_portfolio_records():
    """Clean up portfolio records to remove asset_type field and ensure consistent structure."""
    print("Starting portfolio database cleanup...")
    
    try:
        # Get all portfolio items
        portfolio_query = db.collection('portfolios').stream()
        total_records = 0
        updated_records = 0
        
        for item in portfolio_query:
            total_records += 1
            item_data = item.to_dict()
            item_id = item.id
            needs_update = False
            
            # Check for asset_type field and remove it
            if 'asset_type' in item_data:
                print(f"Found asset_type in record {item_id}: {item_data['asset_type']}")
                item_data.pop('asset_type')
                needs_update = True
            
            # Ensure all necessary fields exist
            required_fields = {
                'symbol': '',
                'shares': 0.0,
                'purchase_price': 0.0,
                'last_updated': firestore.SERVER_TIMESTAMP
            }
            
            for field, default_value in required_fields.items():
                if field not in item_data or item_data[field] is None:
                    print(f"Adding missing field {field} to record {item_id}")
                    item_data[field] = default_value
                    needs_update = True
            
            # Update the record if needed
            if needs_update:
                print(f"Updating record {item_id}")
                db.collection('portfolios').document(item_id).set(item_data)
                updated_records += 1
        
        print(f"Portfolio cleanup complete. Processed {total_records} records, updated {updated_records}.")
        return True
    
    except Exception as e:
        print(f"Error cleaning portfolio records: {e}")
        return False

if __name__ == "__main__":
    print("Portfolio Database Cleanup Tool")
    confirmation = input("This will modify your database records. Continue? (y/n): ")
    
    if confirmation.lower() == 'y':
        clean_portfolio_records()
    else:
        print("Operation cancelled.")
