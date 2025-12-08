import requests
import json
import time
import pandas as pd

# === CONFIGURATION ===
# Load credentials from JSON file
try:
    with open('shop_api_credential.json', 'r') as f:
        credentials = json.load(f)
    ACCESS_TOKEN = credentials.get('api_token')
    if not ACCESS_TOKEN:
        print("❌ Error: 'api_token' not found in shop_api_credential.json")
        exit(1)
except FileNotFoundError:
    print("❌ Error: shop_api_credential.json file not found")
    exit(1)
except json.JSONDecodeError as e:
    print(f"❌ Error: Invalid JSON in shop_api_credential.json: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Error loading credentials: {e}")
    exit(1)

SHOP_NAME = "hcuvpw-td"  # Correct shop name
API_VERSION = "2025-01"
CSV_FILE = "products_to_update.csv"  # CSV file with product IDs (when PROCESS_ALL_PRODUCTS=False)

# === SALES CHANNEL TOGGLE FLAGS ===
# Set to True to enable, False to disable for each channel
TOGGLE_ONLINE_STORE = False  # Toggle Online Store channel
TOGGLE_SHOP = False  # Toggle Shop channel
TOGGLE_TIKTOK = True  # Toggle TikTok channel

# === PRODUCT SELECTION MODE ===
PROCESS_ALL_PRODUCTS = True  # If True, process all products; if False, use CSV file

# GraphQL endpoint
GRAPHQL_URL = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/graphql.json"

headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}

# === UTILITIES ===

def get_all_products():
    """Fetch all products from Shopify with pagination."""
    products = []
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/products.json?limit=250"
    
    print(f"🔍 Fetching products from: {url}")

    try:
        while url:
            response = requests.get(url, headers=headers, timeout=30)
            
            # Check for API errors
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response Body: {response.text}")
                if response.status_code == 401:
                    print("⚠️  Authentication failed. Please check your API token.")
                elif response.status_code == 404:
                    print("⚠️  Shop not found. Please check SHOP_NAME.")
                break
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                print(f"❌ Error: Invalid JSON response from API")
                break
            
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
            
            time.sleep(0.5)  # Rate limit: respect API limits

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while fetching products: {e}")
        return []

    return products


def execute_graphql_query(query, variables=None):
    """Execute a GraphQL query/mutation."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    
    try:
        response = requests.post(GRAPHQL_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ GraphQL Error: {response.status_code}")
            print(f"Response: {response.text}")
            if response.status_code == 401:
                print("⚠️  Authentication failed. Please check your API token.")
            return None
        
        try:
            result = response.json()
        except json.JSONDecodeError:
            print(f"❌ Error: Invalid JSON response from GraphQL API")
            return None
        
        if "errors" in result:
            print(f"❌ GraphQL Errors: {result['errors']}")
            return None
        
        return result.get("data")
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error in GraphQL query: {e}")
        return None


def get_publications():
    """Get publication IDs for Online Store, Shop, and TikTok channels via GraphQL."""
    query = """
    query {
        publications(first: 250) {
            edges {
                node {
                    id
                    name
                }
            }
        }
    }
    """
    
    data = execute_graphql_query(query)
    if not data:
        return None
    
    publications = {}
    edges = data.get("publications", {}).get("edges", [])
    
    for edge in edges:
        node = edge.get("node", {})
        name = node.get("name", "").lower()
        pub_id = node.get("id", "")
        
        # Map publication names to our channel identifiers
        if "online store" in name or name == "online store":
            publications["online_store"] = pub_id
        elif "shop" in name and "tik" not in name:  # Shop channel (but not TikTok Shop)
            publications["shop"] = pub_id
        elif "tiktok" in name or "tik tok" in name:
            publications["tiktok"] = pub_id
    
    print("📰 Found publications:")
    if "online_store" in publications:
        print(f"   ✅ Online Store: {publications['online_store']}")
    else:
        print("   ⚠️  Online Store: Not found")
    
    if "shop" in publications:
        print(f"   ✅ Shop: {publications['shop']}")
    else:
        print("   ⚠️  Shop: Not found")
    
    if "tiktok" in publications:
        print(f"   ✅ TikTok: {publications['tiktok']}")
    else:
        print("   ⚠️  TikTok: Not found")
    
    return publications


def check_product_publication_status(product_id, publication_id):
    """
    Check if a product is currently published to a specific publication.
    
    Args:
        product_id: The product ID (numeric)
        publication_id: The publication ID (GID format)
    
    Returns:
        True if published, False if not published, None if error
    """
    # Convert product ID to GraphQL ID format
    product_gid = f"gid://shopify/Product/{product_id}"
    
    query = """
    query($id: ID!) {
        product(id: $id) {
            id
            publishedOnPublication(publicationId: "%s") {
                id
            }
        }
    }
    """ % publication_id
    
    variables = {"id": product_gid}
    
    data = execute_graphql_query(query, variables)
    if not data:
        return None
    
    product_data = data.get("product")
    if not product_data:
        return None
    
    # publishedOnPublication returns the publication ID if published, null if not
    published = product_data.get("publishedOnPublication")
    return published is not None


def determine_toggle_actions(product_ids, publications, channels_to_check):
    """
    Determine whether to publish or unpublish for each channel based on current state.
    
    Args:
        product_ids: List of product IDs to check
        publications: Dictionary with publication IDs (keys: online_store, shop, tiktok)
        channels_to_check: List of channel keys to check (e.g., ['online_store', 'tiktok'])
    
    Returns:
        Dictionary mapping channel keys to actions (True = publish, False = unpublish)
    """
    actions = {}
    
    for channel in channels_to_check:
        if channel not in publications:
            continue
        
        pub_id = publications[channel]
        published_count = 0
        unpublished_count = 0
        error_count = 0
        
        print(f"🔍 Checking current status for {channel.replace('_', ' ').title()} channel...")
        
        for product_id in product_ids:
            status = check_product_publication_status(product_id, pub_id)
            if status is True:
                published_count += 1
            elif status is False:
                unpublished_count += 1
            else:
                error_count += 1
            time.sleep(0.2)  # Rate limiting
        
        total_checked = published_count + unpublished_count
        
        if total_checked == 0:
            # No valid status checks, default to publish
            actions[channel] = True
            print(f"   ⚠️  Could not determine status, defaulting to PUBLISH")
        elif published_count == total_checked:
            # All published → unpublish
            actions[channel] = False
            print(f"   ✅ All products ({total_checked}) are published → will UNPUBLISH")
        elif unpublished_count == total_checked:
            # All unpublished → publish
            actions[channel] = True
            print(f"   ✅ All products ({total_checked}) are unpublished → will PUBLISH")
        else:
            # Mixed state → default to majority or publish if equal
            if published_count >= unpublished_count:
                actions[channel] = False  # More published, so unpublish
                print(f"   ⚠️  Mixed state ({published_count} published, {unpublished_count} unpublished) → will UNPUBLISH (majority)")
            else:
                actions[channel] = True  # More unpublished, so publish
                print(f"   ⚠️  Mixed state ({published_count} published, {unpublished_count} unpublished) → will PUBLISH (majority)")
        
        if error_count > 0:
            print(f"   ⚠️  {error_count} products had errors checking status")
    
    return actions


def toggle_product_sales_channels(product_id, publications, enable_channels):
    """
    Toggle product visibility for specified sales channels.
    
    Args:
        product_id: The product ID (numeric)
        publications: Dictionary with publication IDs (keys: online_store, shop, tiktok)
        enable_channels: Dictionary with boolean values for each channel to enable/disable
    """
    # Validate product_id
    if not product_id or not isinstance(product_id, (int, str)):
        return {"error": "Invalid product ID"}
    
    try:
        product_id = int(product_id)
    except (ValueError, TypeError):
        return {"error": f"Product ID must be numeric, got: {product_id}"}
    
    # Convert product ID to GraphQL ID format (gid://shopify/Product/{id})
    product_gid = f"gid://shopify/Product/{product_id}"
    
    results = {}
    
    # Toggle Online Store
    if TOGGLE_ONLINE_STORE and "online_store" in publications:
        pub_id = publications["online_store"]
        enable = enable_channels.get("online_store", True)
        
        mutation = """
        mutation %s($id: ID!, $input: [PublicationInput!]!) {
            publishable%s(id: $id, input: $input) {
                publishable {
                    ... on Product {
                        id
                        title
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """ % ("publishablePublish" if enable else "publishableUnpublish",
               "Publish" if enable else "Unpublish")
        
        variables = {
            "id": product_gid,
            "input": [{"publicationId": pub_id}]
        }
        
        data = execute_graphql_query(mutation, variables)
        if data:
            operation = "publishablePublish" if enable else "publishableUnpublish"
            result = data.get(operation, {})
            user_errors = result.get("userErrors", [])
            if user_errors:
                results["online_store"] = {"success": False, "errors": user_errors}
            else:
                results["online_store"] = {"success": True}
        else:
            results["online_store"] = {"success": False, "errors": ["Unknown error"]}
        
        time.sleep(0.3)  # Rate limiting
    
    # Toggle Shop
    if TOGGLE_SHOP and "shop" in publications:
        pub_id = publications["shop"]
        enable = enable_channels.get("shop", True)
        
        mutation = """
        mutation %s($id: ID!, $input: [PublicationInput!]!) {
            publishable%s(id: $id, input: $input) {
                publishable {
                    ... on Product {
                        id
                        title
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """ % ("publishablePublish" if enable else "publishableUnpublish",
               "Publish" if enable else "Unpublish")
        
        variables = {
            "id": product_gid,
            "input": [{"publicationId": pub_id}]
        }
        
        data = execute_graphql_query(mutation, variables)
        if data:
            operation = "publishablePublish" if enable else "publishableUnpublish"
            result = data.get(operation, {})
            user_errors = result.get("userErrors", [])
            if user_errors:
                results["shop"] = {"success": False, "errors": user_errors}
            else:
                results["shop"] = {"success": True}
        else:
            results["shop"] = {"success": False, "errors": ["Unknown error"]}
        
        time.sleep(0.3)  # Rate limiting
    
    # Toggle TikTok
    if TOGGLE_TIKTOK and "tiktok" in publications:
        pub_id = publications["tiktok"]
        enable = enable_channels.get("tiktok", True)
        
        mutation = """
        mutation %s($id: ID!, $input: [PublicationInput!]!) {
            publishable%s(id: $id, input: $input) {
                publishable {
                    ... on Product {
                        id
                        title
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """ % ("publishablePublish" if enable else "publishableUnpublish",
               "Publish" if enable else "Unpublish")
        
        variables = {
            "id": product_gid,
            "input": [{"publicationId": pub_id}]
        }
        
        data = execute_graphql_query(mutation, variables)
        if data:
            operation = "publishablePublish" if enable else "publishableUnpublish"
            result = data.get(operation, {})
            user_errors = result.get("userErrors", [])
            if user_errors:
                results["tiktok"] = {"success": False, "errors": user_errors}
            else:
                results["tiktok"] = {"success": True}
        else:
            results["tiktok"] = {"success": False, "errors": ["Unknown error"]}
        
        time.sleep(0.3)  # Rate limiting
    
    return results


def process_products_from_csv(csv_file):
    """Read product IDs from CSV file."""
    try:
        df = pd.read_csv(csv_file)
        
        # Try common column names for product ID
        product_id_col = None
        for col in ['product_id', 'Product ID', 'productId', 'ProductId', 'id', 'ID']:
            if col in df.columns:
                product_id_col = col
                break
        
        if not product_id_col:
            print(f"❌ Could not find product ID column in {csv_file}")
            print(f"   Available columns: {list(df.columns)}")
            return []
        
        product_ids = []
        for _, row in df.iterrows():
            product_id = row.get(product_id_col)
            if not pd.isna(product_id):
                try:
                    product_ids.append(int(product_id))
                except (ValueError, TypeError):
                    print(f"⚠️  Skipping invalid product ID: {product_id}")
        
        print(f"📋 Read {len(product_ids)} product IDs from {csv_file}")
        return product_ids
    
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_file}")
        return []
    except Exception as e:
        print(f"❌ Error reading CSV file: {e}")
        return []


# === MAIN SCRIPT ===

# Display configuration
print("=" * 60)
print("📡 SALES CHANNEL TOGGLE CONFIGURATION:")
print("=" * 60)
print(f"   Online Store: {'✅ ENABLED' if TOGGLE_ONLINE_STORE else '❌ DISABLED'}")
print(f"   Shop: {'✅ ENABLED' if TOGGLE_SHOP else '❌ DISABLED'}")
print(f"   TikTok: {'✅ ENABLED' if TOGGLE_TIKTOK else '❌ DISABLED'}")
print(f"   Mode: {'All Products' if PROCESS_ALL_PRODUCTS else f'CSV File ({CSV_FILE})'}")
print("=" * 60)
print()

# Get publications first
print("🔍 Fetching publication information...")
publications = get_publications()
print()

if not publications or len(publications) == 0:
    print("❌ No publications found. Please check your sales channel setup.")
    print("   Make sure your sales channels (Online Store, Shop, TikTok) are configured in Shopify.")
    exit(1)

# Check if required publications exist for enabled channels
missing_publications = []
if TOGGLE_ONLINE_STORE and "online_store" not in publications:
    missing_publications.append("Online Store")
if TOGGLE_SHOP and "shop" not in publications:
    missing_publications.append("Shop")
if TOGGLE_TIKTOK and "tiktok" not in publications:
    missing_publications.append("TikTok")

if missing_publications:
    print(f"⚠️  Warning: The following channels are enabled but not found: {', '.join(missing_publications)}")
    print("   These channels will be skipped during processing.")
    print()

# Check if any channels are enabled to toggle
channels_to_toggle = []
if TOGGLE_ONLINE_STORE:
    channels_to_toggle.append("Online Store")
if TOGGLE_SHOP:
    channels_to_toggle.append("Shop")
if TOGGLE_TIKTOK:
    channels_to_toggle.append("TikTok")

if not channels_to_toggle:
    print("⚠️  No channels selected for toggling. Please enable at least one channel.")
    exit(1)

print(f"📋 Channels to toggle: {', '.join(channels_to_toggle)}")
print()

# Get products based on mode
product_ids = []

if PROCESS_ALL_PRODUCTS:
    print("🔄 Processing all products in store...")
    products = get_all_products()
    if not products:
        print("❌ No products found or error fetching products. Exiting.")
        exit(1)
    product_ids = [product.get("id") for product in products if product.get("id")]
    if not product_ids:
        print("❌ No valid product IDs found. Exiting.")
        exit(1)
    print(f"📦 Found {len(product_ids)} products to process")
else:
    print(f"📂 Processing products from CSV file: {CSV_FILE}")
    product_ids = process_products_from_csv(CSV_FILE)
    if not product_ids:
        print("❌ No valid product IDs found. Exiting.")
        exit(1)

print()

# Determine toggle actions based on current publication status
# Build list of channels to check based on enabled flags
channels_to_check = []
if TOGGLE_ONLINE_STORE and "online_store" in publications:
    channels_to_check.append("online_store")
if TOGGLE_SHOP and "shop" in publications:
    channels_to_check.append("shop")
if TOGGLE_TIKTOK and "tiktok" in publications:
    channels_to_check.append("tiktok")

# Check current status and determine actions (True = publish, False = unpublish)
print("🔍 Checking current publication status...")
enable_channels = determine_toggle_actions(product_ids, publications, channels_to_check)
print()

# Display determined actions
print("📋 Determined actions based on current status:")
for channel in channels_to_check:
    action = "PUBLISH" if enable_channels.get(channel, True) else "UNPUBLISH"
    channel_name = channel.replace('_', ' ').title()
    print(f"   {channel_name}: {action}")
print()

# Toggle sales channels for each product
success_count = 0
failure_count = 0
results_summary = {
    "online_store": {"success": 0, "failure": 0},
    "shop": {"success": 0, "failure": 0},
    "tiktok": {"success": 0, "failure": 0}
}

print("🚀 Starting sales channel toggle process...")
print("=" * 60)

for i, product_id in enumerate(product_ids, 1):
    try:
        print(f"\n[{i}/{len(product_ids)}] Processing product {product_id}...")
        
        results = toggle_product_sales_channels(product_id, publications, enable_channels)
        
        # Check if there was an error in the function itself
        if "error" in results:
            print(f"   ❌ Error: {results['error']}")
            failure_count += 1
            continue
        
        # Process results
        for channel, result in results.items():
            if result.get("success"):
                print(f"   ✅ {channel.replace('_', ' ').title()}: Success")
                results_summary[channel]["success"] += 1
                success_count += 1
            else:
                errors = result.get("errors", [])
                if errors:
                    # Handle both dict and string error objects
                    error_messages = []
                    for e in errors:
                        if isinstance(e, dict):
                            error_messages.append(e.get("message", str(e)))
                        else:
                            error_messages.append(str(e))
                    error_msg = ", ".join(error_messages)
                else:
                    error_msg = "Unknown error"
                print(f"   ❌ {channel.replace('_', ' ').title()}: Failed - {error_msg}")
                results_summary[channel]["failure"] += 1
                failure_count += 1
        
        # Add delay between products
        time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Process interrupted by user")
        print(f"   Processed {i}/{len(product_ids)} products before interruption")
        break
    except Exception as e:
        print(f"   ❌ Unexpected error processing product {product_id}: {e}")
        failure_count += 1
        continue

print()
print("=" * 60)
print("📊 SUMMARY")
print("=" * 60)
print(f"Total products processed: {len(product_ids)}")
print(f"Total successful operations: {success_count}")
print(f"Total failed operations: {failure_count}")
print()
print("Per-channel summary:")
for channel, stats in results_summary.items():
    if TOGGLE_ONLINE_STORE and channel == "online_store":
        print(f"   {channel.replace('_', ' ').title()}: {stats['success']} success, {stats['failure']} failures")
    if TOGGLE_SHOP and channel == "shop":
        print(f"   {channel.replace('_', ' ').title()}: {stats['success']} success, {stats['failure']} failures")
    if TOGGLE_TIKTOK and channel == "tiktok":
        print(f"   {channel.replace('_', ' ').title()}: {stats['success']} success, {stats['failure']} failures")

print()
print("🎉 Sales channel toggle process completed!")


