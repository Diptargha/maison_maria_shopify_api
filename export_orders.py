import requests
import json
import csv
import time
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
# Load credentials from JSON file
with open('shop_api_credential.json', 'r') as f:
    credentials = json.load(f)

SHOP_NAME = "hcuvpw-td"  # Shop name
ACCESS_TOKEN = credentials['api_token']  # Load the correct token from credentials file
API_VERSION = "2025-01"  # Using stable API version
EXPORT_CUSTOMER_INFO = True  # Set to True to export customer information, False to skip

headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}


# --- FUNCTION TO GET DELIVERY STATUS ---
def get_delivery_status(order):
    """
    Determine delivery status from order fulfillment tracking data.
    Returns: 'tracking added', 'in transit', 'out for delivery', 'delivered', or 'unfulfilled'
    """
    fulfillments = order.get("fulfillments", [])
    
    if not fulfillments:
        return "unfulfilled"
    
    # Get the most recent fulfillment
    latest_fulfillment = fulfillments[-1]
    
    # Check fulfillment status
    fulfillment_status = latest_fulfillment.get("status", "").lower()
    
    # Check if delivered
    if fulfillment_status == "success":
        # Check if there's a delivered_at timestamp
        delivered_at = latest_fulfillment.get("delivered_at")
        if delivered_at:
            return "delivered"
        # If status is success but no delivered_at, check tracking events
        tracking_events = latest_fulfillment.get("tracking_events", [])
        for event in tracking_events:
            event_status = event.get("status", "").lower()
            if "delivered" in event_status:
                return "delivered"
        # If success but no delivered confirmation, assume delivered
        return "delivered"
    
    # Check tracking number
    tracking_number = latest_fulfillment.get("tracking_number")
    if not tracking_number:
        return "unfulfilled"
    
    # Check tracking events for more detailed status
    tracking_events = latest_fulfillment.get("tracking_events", [])
    if tracking_events:
        # Get the latest tracking event
        latest_event = tracking_events[-1] if tracking_events else {}
        event_status = latest_event.get("status", "").lower()
        event_message = latest_event.get("message", "").lower()
        
        # Check for delivered status
        if "delivered" in event_status or "delivered" in event_message:
            return "delivered"
        # Check for out for delivery
        if "out for delivery" in event_status or "out for delivery" in event_message or "out_for_delivery" in event_status:
            return "out for delivery"
        # Check for in transit
        if "in transit" in event_status or "in transit" in event_message or "in_transit" in event_status:
            return "in transit"
    
    # Check tracking URL for status indicators
    tracking_url = latest_fulfillment.get("tracking_url", "").lower()
    if tracking_url:
        if "delivered" in tracking_url:
            return "delivered"
        elif "out for delivery" in tracking_url or "out_for_delivery" in tracking_url:
            return "out for delivery"
        elif "in transit" in tracking_url or "in_transit" in tracking_url:
            return "in transit"
    
    # If tracking number exists but no specific status found, check fulfillment status
    if fulfillment_status == "pending" or fulfillment_status == "open":
        return "tracking added"
    elif fulfillment_status == "in_transit" or fulfillment_status == "in transit":
        return "in transit"
    
    # Default: if tracking number exists, assume tracking added
    if tracking_number:
        return "tracking added"
    
    return "unfulfilled"


# --- FUNCTION TO FORMAT DATE ---
def format_order_date(date_string):
    """Format Shopify date string to readable format."""
    if not date_string:
        return ""
    try:
        # Shopify dates are in ISO 8601 format (e.g., "2025-01-15T10:30:00-05:00" or "2025-01-15T10:30:00Z")
        if date_string.endswith('Z'):
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(date_string)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        # If parsing fails, return original string
        return date_string


# --- FUNCTION TO GET ALL ORDERS ---
def get_all_orders():
    """Fetch all orders from Shopify with pagination."""
    orders = []
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/orders.json?limit=250&status=any"
    
    print(f"🔍 Attempting to fetch orders from: {url}")
    print(f"🔑 Using token: {ACCESS_TOKEN[:10]}...")

    while url:
        response = requests.get(url, headers=headers)
        
        # Check for API errors
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"Full URL: {url}")
            print(f"Response Body: {response.text}")
            break
        
        data = response.json()
        fetched_count = len(data.get("orders", []))
        orders.extend(data.get("orders", []))
        print(f"✅ Fetched {fetched_count} orders (Total so far: {len(orders)})")

        # Check for pagination
        if "link" in response.headers:
            links = response.headers["link"].split(",")
            next_url = None
            for link in links:
                if 'rel="next"' in link:
                    next_url = link[link.find("<") + 1: link.find(">")]
            url = next_url
        else:
            url = None
        
        time.sleep(0.5)  # Rate limit: respect API limits

    return orders


# --- FUNCTION TO EXTRACT CUSTOMER INFO ---
def get_customer_info(order):
    """Extract customer information from order."""
    customer = order.get("customer", {})
    shipping_address = order.get("shipping_address", {})
    
    customer_name = customer.get("first_name", "") + " " + customer.get("last_name", "")
    customer_name = customer_name.strip() or shipping_address.get("name", "")
    
    customer_email = customer.get("email", "") or order.get("email", "")
    
    customer_phone = shipping_address.get("phone", "") or customer.get("phone", "")
    
    customer_postcode = shipping_address.get("zip", "") or shipping_address.get("postal_code", "")
    
    return {
        "name": customer_name,
        "email": customer_email,
        "phone": customer_phone,
        "postcode": customer_postcode
    }


# --- FUNCTION TO PARSE VARIANT INTO COLOUR AND SIZE ---
def parse_variant(variant_title):
    """
    Parse variant title into colour and size.
    Handles formats like: "Small / Red", "Red / Small", "Small, Red", "Red, Small", etc.
    Returns tuple: (colour, size)
    """
    if not variant_title or variant_title == "Default":
        return ("", "")
    
    variant_title = variant_title.strip()
    
    # Common separators
    separators = [" / ", "/", " , ", ", ", " - ", "-"]
    
    # Try to split by common separators
    for sep in separators:
        if sep in variant_title:
            parts = [p.strip() for p in variant_title.split(sep)]
            if len(parts) == 2:
                # Try to determine which is size and which is colour
                # Common size keywords
                size_keywords = ["xs", "small", "s", "medium", "m", "large", "l", "xl", "xxl", "xxxl", 
                                "one size", "os", "0", "2", "4", "6", "8", "10", "12", "14", "16", "18", "20"]
                
                part1_lower = parts[0].lower()
                part2_lower = parts[1].lower()
                
                # Check if first part is a size
                if any(keyword in part1_lower for keyword in size_keywords):
                    return (parts[1], parts[0])  # (colour, size)
                # Check if second part is a size
                elif any(keyword in part2_lower for keyword in size_keywords):
                    return (parts[0], parts[1])  # (colour, size)
                else:
                    # If can't determine, assume first is colour, second is size
                    return (parts[0], parts[1])
    
    # If no separator found, try to identify if it's a size or colour
    variant_lower = variant_title.lower()
    size_keywords = ["xs", "small", "s", "medium", "m", "large", "l", "xl", "xxl", "xxxl", 
                    "one size", "os", "0", "2", "4", "6", "8", "10", "12", "14", "16", "18", "20"]
    
    if any(keyword in variant_lower for keyword in size_keywords):
        return ("", variant_title)  # It's a size
    else:
        return (variant_title, "")  # Assume it's a colour


# --- FUNCTION TO COMBINE CSV FILES ---
def combine_csv_files(shopify_csv, external_csv, output_csv):
    """
    Combine shopify_orders_export.csv with orders_export_1.csv.
    Matches by Order Name and adds customer columns from external CSV.
    """
    try:
        # Read both CSV files
        print(f"\n📂 Reading {shopify_csv}...")
        df_shopify = pd.read_csv(shopify_csv)
        print(f"   Found {len(df_shopify)} rows")
        
        print(f"📂 Reading {external_csv}...")
        df_external = pd.read_csv(external_csv)
        print(f"   Found {len(df_external)} rows")
        
        # Ensure Order Name column exists in shopify CSV
        if 'Order Name' not in df_shopify.columns:
            print("❌ 'Order Name' column not found in shopify CSV")
            return False
        
        # Check for duplicate column names in shopify dataframe
        if df_shopify.columns.duplicated().any():
            print(f"   ⚠️  Removing duplicate columns from shopify CSV")
            df_shopify = df_shopify.loc[:, ~df_shopify.columns.duplicated()]
        
        # Find the Order Name column in external CSV
        # First try 'Name' column (as specified for orders_export_1.csv)
        order_name_col = None
        if 'Name' in df_external.columns:
            order_name_col = 'Name'
        elif 'name' in df_external.columns:
            order_name_col = 'name'
        else:
            # Try flexible matching as fallback
            for col in df_external.columns:
                if 'name' in col.lower() and 'order' in col.lower():
                    order_name_col = col
                    break
            if not order_name_col:
                print(f"❌ Could not find Order Name column in {external_csv}")
                print(f"   Looking for 'Name' column. Available columns: {list(df_external.columns)}")
                return False
        
        print(f"   Matching on column: '{order_name_col}'")
        
        # Find customer columns in external CSV
        customer_cols = {}
        col_mapping = {
            'shipping name': ['shipping name', 'shipping_name', 'ship_name', 'name'],
            'shipping address1': ['shipping address1', 'shipping_address1', 'shipping address', 'address1', 'address'],
            'shipping zip': ['shipping zip', 'shipping_zip', 'shipping postcode', 'zip', 'postcode'],
            'shipping phone': ['shipping phone', 'shipping_phone', 'phone'],
            'email': ['email', 'customer email', 'customer_email']
        }
        
        for target_col, possible_names in col_mapping.items():
            for col in df_external.columns:
                if col.lower() in [n.lower() for n in possible_names]:
                    customer_cols[target_col] = col
                    break
        
        print(f"   Found customer columns: {customer_cols}")
        
        # Merge dataframes on Order Name
        # Since both CSVs have one row per line item, we merge on Order Name
        print(f"\n🔗 Merging dataframes on Order Name...")
        
        # Prepare external dataframe - select needed columns
        # First, collect all columns we need
        cols_to_select = []
        
        # Handle Order Name column - check if it already exists
        if 'Order Name' in df_external.columns:
            # Use existing 'Order Name' column
            cols_to_select.append('Order Name')
            print(f"   Using existing 'Order Name' column from external CSV")
        else:
            # Use the found order_name_col and rename it
            cols_to_select.append(order_name_col)
        
        # Add customer columns
        cols_to_select.extend(list(customer_cols.values()))
        
        # Remove any duplicates from cols_to_select
        cols_to_select = list(dict.fromkeys(cols_to_select))  # Preserves order, removes duplicates
        
        # Select only the columns we need
        df_external_clean = df_external[cols_to_select].copy()
        
        # Rename the order name column to match shopify CSV (if needed)
        if 'Order Name' not in df_external_clean.columns and order_name_col in df_external_clean.columns:
            df_external_clean = df_external_clean.rename(columns={order_name_col: 'Order Name'})
        
        # Verify 'Order Name' column exists and is unique
        if 'Order Name' not in df_external_clean.columns:
            print(f"❌ 'Order Name' column not found in cleaned external dataframe")
            return False
        
        # Check for duplicate column names in external dataframe
        if df_external_clean.columns.duplicated().any():
            print(f"   ⚠️  Removing duplicate columns from external CSV")
            df_external_clean = df_external_clean.loc[:, ~df_external_clean.columns.duplicated()]
        
        # Rename customer columns to target names
        rename_dict = {source_col: target_col for target_col, source_col in customer_cols.items()}
        df_external_clean = df_external_clean.rename(columns=rename_dict)
        
        # Check for duplicate column names before merge
        shopify_cols = set(df_shopify.columns)
        external_cols = set(df_external_clean.columns)
        overlapping_cols = shopify_cols.intersection(external_cols) - {'Order Name'}
        
        if overlapping_cols:
            print(f"   ⚠️  Found overlapping columns (will be suffixed): {overlapping_cols}")
            # Use suffixes to handle overlapping columns
            df_merged = df_shopify.merge(
                df_external_clean,
                on='Order Name',
                how='left',
                suffixes=('', '_external')
            )
            
            # If there are duplicate columns from merge, keep the external ones
            for col in list(df_merged.columns):
                if col.endswith('_external'):
                    base_col = col.replace('_external', '')
                    if base_col in df_merged.columns:
                        # Keep external version, drop original
                        df_merged[base_col] = df_merged[col]
                    df_merged.drop(columns=[col], inplace=True)
        else:
            # No overlapping columns, simple merge
            df_merged = df_shopify.merge(
                df_external_clean,
                on='Order Name',
                how='left'
            )
        
        # Reorder columns: add customer columns after Order Name and Date
        base_cols = ['Order Name', 'Date']
        customer_cols_list = ['shipping name', 'shipping address1', 'shipping zip', 'shipping phone', 'email']
        
        # Get existing columns
        existing_cols = list(df_merged.columns)
        
        # Remove base and customer cols to get other cols
        other_cols = [col for col in existing_cols if col not in base_cols + customer_cols_list]
        
        # Build final column order: Order Name, Date, Customer columns (only those that exist), then rest
        final_cols = base_cols.copy()
        for cust_col in customer_cols_list:
            if cust_col in existing_cols:
                final_cols.append(cust_col)
        final_cols.extend(other_cols)
        
        # Reorder dataframe
        df_merged = df_merged[final_cols]
        
        # Save combined CSV
        print(f"💾 Saving combined data to {output_csv}...")
        df_merged.to_csv(output_csv, index=False, encoding='utf-8')
        print(f"✅ Combined CSV saved: {len(df_merged)} rows")
        
        return True
        
    except FileNotFoundError as e:
        print(f"❌ File not found: {e}")
        return False
    except Exception as e:
        print(f"❌ Error combining CSV files: {e}")
        import traceback
        traceback.print_exc()
        return False


# --- MAIN SCRIPT ---
print("=" * 60)
print("📦 SHOPIFY ORDERS EXPORT")
print("=" * 60)
print()

if EXPORT_CUSTOMER_INFO:
    print("👤 Customer information: ENABLED (will combine with orders_export_1.csv)")
else:
    print("👤 Customer information: DISABLED")
print()

all_orders = get_all_orders()

print(f"\n📊 Total orders found: {len(all_orders)}")

# Export to CSV
csv_filename = "shopify_orders_export.csv"
with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
    csv_writer = csv.writer(csvfile)
    
    # Write header - customer columns will be added from external CSV if EXPORT_CUSTOMER_INFO is True
    header = ['Order Name', 'Date']
    # Note: Customer columns will be added from orders_export_1.csv if EXPORT_CUSTOMER_INFO is True
    header.extend([
        'Total Cost',
        'Product Name',
        'Colour',
        'Size',
        'Delivery Status'
    ])
    csv_writer.writerow(header)
    
    # Write order data
    row_count = 0
    for order in all_orders:
        order_name = order.get("name", "")  # Order name like #1010
        order_date = format_order_date(order.get("created_at", ""))
        
        # Customer info will be added from external CSV if EXPORT_CUSTOMER_INFO is True
        total_cost = order.get("total_price", "0.00")
        delivery_status = get_delivery_status(order)
        
        # Get line items
        line_items = order.get("line_items", [])
        
        if line_items:
            # One row per line item
            for item in line_items:
                product_name = item.get("name", "")
                variant_title = item.get("variant_title", "") or "Default"
                
                # Parse variant into colour and size
                colour, size = parse_variant(variant_title)
                
                # Build row (customer info will be added from external CSV if EXPORT_CUSTOMER_INFO is True)
                row = [
                    order_name,
                    order_date,
                    total_cost,
                    product_name,
                    colour,
                    size,
                    delivery_status
                ]
                csv_writer.writerow(row)
                row_count += 1
        else:
            # If no line items, write order info only
            row = [
                order_name,
                order_date,
                total_cost,
                "",
                "",
                "",
                delivery_status
            ]
            csv_writer.writerow(row)
            row_count += 1

print(f"✅ Data exported to {csv_filename}")
print(f"📝 Total rows written: {row_count}")

# If EXPORT_CUSTOMER_INFO is True, combine with external CSV
if EXPORT_CUSTOMER_INFO:
    print("\n" + "=" * 60)
    print("🔗 COMBINING WITH EXTERNAL CSV")
    print("=" * 60)
    external_csv = "orders_export_1.csv"
    if combine_csv_files(csv_filename, external_csv, csv_filename):
        print(f"\n✅ Successfully combined customer data from {external_csv}")
    else:
        print(f"\n⚠️  Could not combine CSV files. Continuing with basic export.")

print("\n🎉 Orders export completed successfully!")
