import pandas as pd
import requests
import time
import os
import json
from urllib.parse import urlparse
from PIL import Image
from io import BytesIO
from description_formatter import format_description_with_template

# === CONFIGURATION ===
# Load credentials from JSON file
with open('shop_api_credential.json', 'r') as f:
    credentials = json.load(f)

SHOP_NAME = "hcuvpw-td"  # Correct shop name
ACCESS_TOKEN = credentials['api_token']
API_VERSION = "2025-01"
CSV_FILE = "products_to_update.csv"  # Updated CSV filename

# === FIELD UPDATE FLAGS ===
# Set to True to update specific fields, False to skip them
UPDATE_TITLE = True  # Update product titles
UPDATE_DESCRIPTION = True  # Update product descriptions
UPDATE_TAGS = True  # Update product tags
UPDATE_PRICE = False  # Update variant prices
UPDATE_IMAGES = False  # Update product images from links

# === ADDITIONAL OPTIONS ===
USE_TEMPLATE = True  # Set to True to use template formatting for descriptions, False for plain text
TEMP_DIR = "temp_images"
MAX_WIDTH = 1200  # pixels
JPEG_QUALITY = 85  # compression (1–100)

headers = {
    "X-Shopify-Access-Token": ACCESS_TOKEN
}

# === UTILITIES ===

def make_direct_drive_link(drive_url):
    """Convert a Google Drive share link to a direct download link."""
    try:
        file_id = drive_url.split("/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    except IndexError:
        print(f"⚠️ Invalid Google Drive link: {drive_url}")
        return None


def download_image(drive_url):
    """Download image from Google Drive and return path."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    direct_url = make_direct_drive_link(drive_url)
    if not direct_url:
        return None

    filename = os.path.join(TEMP_DIR, os.path.basename(urlparse(drive_url).path) + ".jpg")
    response = requests.get(direct_url, stream=True)

    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        img = optimize_image(img)
        img.save(filename, "JPEG", optimize=True, quality=JPEG_QUALITY)
        print(f"🖼️ Downloaded and optimized: {filename}")
        return filename
    else:
        print(f"❌ Failed to download {drive_url}")
        return None


def optimize_image(img):
    """Resize and compress the image to optimize for web."""
    if img.mode != "RGB":
        img = img.convert("RGB")

    width, height = img.size
    if width > MAX_WIDTH:
        new_height = int(height * (MAX_WIDTH / width))
        img = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
        print(f"📏 Resized image to {MAX_WIDTH}px width")

    return img


def upload_image_to_shopify(product_id, image_path):
    """Upload local image to Shopify and attach to product."""
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/products/{product_id}/images.json"
    with open(image_path, "rb") as f:
        files = {"image[attachment]": f.read()}
        response = requests.post(url, headers=headers, files=files)

    if response.status_code == 201:
        print(f"✅ Uploaded {os.path.basename(image_path)} to product {product_id}")
        return response.json().get("image", {}).get("src")
    else:
        print(f"❌ Failed to upload {image_path}: {response.text}")
        return None


def update_product(product_id, title=None, description=None, tags=None, image_links=None):
    """Update product info and images based on enabled flags."""
    images_uploaded = []
    
    # Only process images if UPDATE_IMAGES is True
    if UPDATE_IMAGES and image_links:
        for link in str(image_links).split(","):
            link = link.strip()
            if link:
                local_path = download_image(link)
                if local_path:
                    img_src = upload_image_to_shopify(product_id, local_path)
                    if img_src:
                        images_uploaded.append({"src": img_src})
                    os.remove(local_path)

    # Format description using template if USE_TEMPLATE is True and UPDATE_DESCRIPTION is enabled
    if UPDATE_DESCRIPTION and USE_TEMPLATE and description:
        description = format_description_with_template(description)
        print(f"📝 Formatted description using template for product {product_id}")

    data = {"product": {"id": product_id}}
    
    # Only add fields that are enabled for update
    if UPDATE_TITLE and title:
        data["product"]["title"] = title
    if UPDATE_DESCRIPTION and description:
        data["product"]["body_html"] = description
    if UPDATE_TAGS and tags:
        data["product"]["tags"] = tags
    if UPDATE_IMAGES and images_uploaded:
        data["product"]["images"] = images_uploaded

    # Only make API call if there's something to update beyond the ID
    if len(data["product"]) > 1:
        url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/products/{product_id}.json"
        response = requests.put(url, json=data, headers={"Content-Type": "application/json", **headers})

        if response.status_code == 200:
            print(f"✅ Product {product_id} updated successfully.\n")
        else:
            print(f"❌ Failed to update product {product_id}: {response.text}\n")
    else:
        print(f"⏭️  Skipped product {product_id} (no fields enabled for update)\n")


def update_variant_price(variant_id, price):
    """Update variant price."""
    data = {"variant": {"id": variant_id, "price": price}}
    url = f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/variants/{variant_id}.json"
    response = requests.put(url, json=data, headers={"Content-Type": "application/json", **headers})
    if response.status_code == 200:
        print(f"💲 Updated variant {variant_id} price to {price}")
    else:
        print(f"❌ Failed to update variant {variant_id}: {response.text}")


# === MAIN SCRIPT ===

# Display configuration
print("=" * 60)
print("📋 UPDATE CONFIGURATION:")
print(f"   Title: {'✅ ENABLED' if UPDATE_TITLE else '❌ DISABLED'}")
print(f"   Description: {'✅ ENABLED' if UPDATE_DESCRIPTION else '❌ DISABLED'}")
if UPDATE_DESCRIPTION:
    print(f"      - Template formatting: {'✅ ENABLED' if USE_TEMPLATE else '❌ DISABLED'}")
print(f"   Tags: {'✅ ENABLED' if UPDATE_TAGS else '❌ DISABLED'}")
print(f"   Price: {'✅ ENABLED' if UPDATE_PRICE else '❌ DISABLED'}")
print(f"   Images: {'✅ ENABLED' if UPDATE_IMAGES else '❌ DISABLED'}")
print("=" * 60)
print()

df = pd.read_csv(CSV_FILE)

for _, row in df.iterrows():
    product_id = row.get("product_id")
    variant_id = row.get("variant_id")
    title = row.get("title")
    description = row.get("description")
    tags = row.get("tags")
    price = row.get("price")
    image_links = row.get("image_links")

    if not pd.isna(product_id):
        # Only pass image_links if UPDATE_IMAGES is True
        imgs = image_links if UPDATE_IMAGES else None
        update_product(product_id, title, description, tags, imgs)

    # Only update price if UPDATE_PRICE is enabled
    if UPDATE_PRICE and not pd.isna(variant_id) and not pd.isna(price):
        update_variant_price(variant_id, price)

    time.sleep(0.8)  # respect API rate limits

print("\n🎉 All products updated successfully!")
