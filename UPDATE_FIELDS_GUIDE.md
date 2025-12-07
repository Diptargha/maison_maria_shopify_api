# Selective Field Update Guide

## Overview

The `update_product_details.py` script now supports selective field updates. You can choose exactly which fields to update for all products in your CSV, leaving other fields untouched.

## Configuration Flags

At the top of `update_product_details.py` (lines 21-27), you'll find these flags:

```python
# === FIELD UPDATE FLAGS ===
# Set to True to update specific fields, False to skip them
UPDATE_TITLE = True          # Update product titles
UPDATE_DESCRIPTION = True    # Update product descriptions
UPDATE_TAGS = True          # Update product tags
UPDATE_PRICE = True         # Update variant prices
UPDATE_IMAGES = False       # Update product images from links
```

## Common Use Cases

### Example 1: Update Only Titles

To update ONLY product titles and leave everything else unchanged:

```python
UPDATE_TITLE = True          # ✅ Update titles
UPDATE_DESCRIPTION = False   # ❌ Skip descriptions
UPDATE_TAGS = False         # ❌ Skip tags
UPDATE_PRICE = False        # ❌ Skip prices
UPDATE_IMAGES = False       # ❌ Skip images
```

**Result:** Only the `title` column from your CSV will be updated in Shopify.

---

### Example 2: Update Only Descriptions

To update ONLY product descriptions:

```python
UPDATE_TITLE = False         # ❌ Skip titles
UPDATE_DESCRIPTION = True    # ✅ Update descriptions
UPDATE_TAGS = False         # ❌ Skip tags
UPDATE_PRICE = False        # ❌ Skip prices
UPDATE_IMAGES = False       # ❌ Skip images
```

**Result:** Only the `description` column from your CSV will be updated. If `USE_TEMPLATE = True`, descriptions will be formatted using the template.

---

### Example 3: Update Only Prices

To update ONLY variant prices:

```python
UPDATE_TITLE = False         # ❌ Skip titles
UPDATE_DESCRIPTION = False   # ❌ Skip descriptions
UPDATE_TAGS = False         # ❌ Skip tags
UPDATE_PRICE = True          # ✅ Update prices
UPDATE_IMAGES = False       # ❌ Skip images
```

**Result:** Only the `price` column from your CSV will be updated for variants.

---

### Example 4: Update Titles and Tags Only

To update titles and tags together:

```python
UPDATE_TITLE = True          # ✅ Update titles
UPDATE_DESCRIPTION = False   # ❌ Skip descriptions
UPDATE_TAGS = True          # ✅ Update tags
UPDATE_PRICE = False        # ❌ Skip prices
UPDATE_IMAGES = False       # ❌ Skip images
```

**Result:** Both `title` and `tags` columns will be updated, everything else stays the same.

---

### Example 5: Update Everything Except Images

To update all text fields but skip images:

```python
UPDATE_TITLE = True          # ✅ Update titles
UPDATE_DESCRIPTION = True    # ✅ Update descriptions
UPDATE_TAGS = True          # ✅ Update tags
UPDATE_PRICE = True         # ✅ Update prices
UPDATE_IMAGES = False       # ❌ Skip images
```

**Result:** All fields except images are updated. This is faster since it doesn't download/upload images.

---

### Example 6: Update Everything Including Images

To perform a complete update:

```python
UPDATE_TITLE = True          # ✅ Update titles
UPDATE_DESCRIPTION = True    # ✅ Update descriptions
UPDATE_TAGS = True          # ✅ Update tags
UPDATE_PRICE = True         # ✅ Update prices
UPDATE_IMAGES = True        # ✅ Update images
```

**Result:** Full update including downloading images from Google Drive and uploading to Shopify.

---

## How It Works

1. **Configuration Display**: When you run the script, it shows which fields are enabled:

```
============================================================
📋 UPDATE CONFIGURATION:
   Title: ✅ ENABLED
   Description: ❌ DISABLED
   Tags: ❌ DISABLED
   Price: ❌ DISABLED
   Images: ❌ DISABLED
============================================================
```

2. **Smart API Calls**: The script only makes API calls for fields that are enabled. If no fields are enabled, it skips the product entirely.

3. **CSV Structure**: Your CSV should still contain all columns, but only enabled fields will be read and updated:

```csv
product_id,variant_id,title,description,tags,price,image_links
8123456789,,New Title,Description text,tag1,89.99,
```

## Tips

✅ **Best Practice**: Only enable the fields you need to update. This:
- Reduces API calls
- Speeds up execution
- Minimizes risk of accidentally changing fields you don't want to modify

✅ **Test First**: Start with a small CSV file to test your configuration before running on all products.

✅ **Empty Columns**: If a column is empty in your CSV and the field is enabled, that field won't be updated (it checks for None/NaN values).

✅ **Descriptions with Template**: If `UPDATE_DESCRIPTION = True` and `USE_TEMPLATE = True`, descriptions will be formatted. To update descriptions without template formatting, set `USE_TEMPLATE = False`.

## Safety Features

- ⏭️ If all update flags are `False`, products are skipped with a message
- 🔒 Unchanged fields in Shopify remain untouched
- ⚠️ Error messages show if updates fail
- ✅ Success messages confirm what was updated

## Questions?

Refer to:
- `TEMPLATE_USAGE_GUIDE.md` - For description template formatting
- `products_to_update_sample.csv` - For CSV format examples

