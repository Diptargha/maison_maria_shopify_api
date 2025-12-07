import requests
import json
import csv
import time

# --- CONFIGURATION ---
# Load credentials from JSON file
with open('shop_api_credential.json', 'r') as f:
    credentials = json.load(f)

SHOP_NAME = "hcuvpw-td"  # Replace with your store name
ACCESS_TOKEN = credentials['api_token']  # Load the correct token from credentials file
API_VERSION = "2025-01"  # Using stable API version
FETCH_LOCATIONS = False  # Set to True to fetch inventory location IDs (slower but more detailed)


# --- FUNCTION TO GET INVENTORY LOCATIONS ---
def get_inventory_locations(inventory_item_id):
    """Fetch inventory locations for a given inventory item ID."""
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/inventory_levels.json?inventory_item_ids={inventory_item_id}"
    
    response = requests.get(url, headers={
        "X-Shopify-Access-Token": ACCESS_TOKEN,
        "Content-Type": "application/json"
    })
    
    if response.status_code == 200:
        data = response.json()
        locations = data.get("inventory_levels", [])
        # Return comma-separated location IDs
        location_ids = [str(loc.get("location_id", "")) for loc in locations]
        return ", ".join(location_ids) if location_ids else ""
    else:
        return ""


# --- FUNCTION TO GET PRODUCTS ---
def get_all_products():
    products = []
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/products.json?limit=250"
    
    print(f"🔍 Attempting to fetch from: {url}")
    print(f"🔑 Using token: {ACCESS_TOKEN[:10]}...")

    while url:
        response = requests.get(url, headers={
            "X-Shopify-Access-Token": ACCESS_TOKEN,
            "Content-Type": "application/json"
        })
        
        # Check for API errors
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code}")
            print(f"Full URL: {url}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            break
        
        data = response.json()
        fetched_count = len(data.get("products", []))
        products.extend(data.get("products", []))
        print(f"✅ Fetched {fetched_count} products (Total so far: {len(products)})")

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

    return products


# --- MAIN SCRIPT ---
all_products = get_all_products()

print(f"\n📊 Total products found: {len(all_products)}")

if FETCH_LOCATIONS:
    print("🗺️  Location fetching: ENABLED (this will take longer)")
else:
    print("🗺️  Location fetching: DISABLED (set FETCH_LOCATIONS=True to enable)")

# Export to CSV
csv_filename = "shopify_products_export.csv"
with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
    csv_writer = csv.writer(csvfile)
    
    # Write header
    csv_writer.writerow(['Product ID', 'Product Title', 'Variant ID', 'Variant Title', 'Variant SKU', 'Variant Price', 'Location IDs'])
    
    # Write product and variant data
    row_count = 0
    for product in all_products:
        product_id = product['id']
        product_title = product['title']
        
        # If product has variants, write each variant
        variants = product.get("variants", [])
        if variants:
            # Fetch location IDs only once per product (from first variant) if enabled
            location_ids = ""
            if FETCH_LOCATIONS:
                first_variant = variants[0]
                inventory_item_id = first_variant.get('inventory_item_id', '')
                if inventory_item_id:
                    location_ids = get_inventory_locations(inventory_item_id)
                    print(f"🗺️  Fetched locations for product {product_id}: {location_ids}")
                    time.sleep(0.3)  # Rate limit: ~3 requests per second
            
            # Write all variants with the same location IDs
            for variant in variants:
                csv_writer.writerow([
                    product_id,
                    product_title,
                    variant['id'],
                    variant['title'],
                    variant.get('sku', ''),
                    variant.get('price', ''),
                    location_ids
                ])
                row_count += 1
        else:
            # If no variants, write product info only
            csv_writer.writerow([product_id, product_title, '', '', '', '', ''])
            row_count += 1

print(f"✅ Data exported to {csv_filename}")
print(f"📝 Total rows written: {row_count}")
