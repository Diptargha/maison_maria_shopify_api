# Template-Based Product Description Guide

## Overview

The template system formats product descriptions into beautiful, structured HTML for Shopify using a master template. This ensures consistent, professional, and SEO-optimized product pages.

## How It Works

1. **CSV Input**: Provide structured data in the CSV file using section markers
2. **Template Processing**: The script parses the structured data and applies the master template
3. **HTML Output**: Generates formatted HTML that's uploaded to Shopify

## CSV Format for Descriptions

In your CSV file (`products_to_update.csv`), structure the `description` column using these section markers:

```
[SHORT_DESC]
Your compelling short description here (≤50 words, keyword-rich)

[WHY_LOVE]
Style: Description of style features
Fit: Description of fit
Season: Suitable seasons
Effortless Wear: Comfort features
Occasion Ready: Suitable occasions

[SIZE_FIT]
Fit Type: e.g., Bodycon / Mermaid Fit
Length: e.g., Floor-Length
Sleeve: e.g., Sleeveless
Customer Group: e.g., Adult Women
Gender: e.g., Women

[FABRIC_CARE]
Fabric: e.g., 95% Polyester, 5% Elastane
Feel: e.g., Soft, slightly stretchy
Care Instructions: e.g., Hand wash or dry clean

[WHATS_INCLUDED]
1 x Product Name and Description
```

## Section Descriptions

### [SHORT_DESC]
- A compelling, keyword-rich introduction (aim for ≤50 words)
- Highlights the main features and appeal
- Should grab attention and encourage reading

### [WHY_LOVE]
- Key selling points as key-value pairs
- Each line should be: `Label: Description`
- Common labels: Style, Fit, Season, Effortless Wear, Occasion Ready

### [SIZE_FIT]
- Size and fit specifications
- Format: `Label: Value`
- Include: Fit Type, Length, Sleeve, Customer Group, Gender

### [FABRIC_CARE]
- Material composition and care instructions
- Format: `Label: Value`
- Include: Fabric, Feel, Care Instructions

### [WHATS_INCLUDED]
- List what comes in the package
- Can be multiple lines if needed

## Delivery Details

**Automatically Added**: A standard delivery information table is automatically appended to all product descriptions with shipping options for Europe/UK.

## Configuration

In `update_product_details.py`, control the template system with:

```python
USE_TEMPLATE = True   # Enable template formatting
USE_TEMPLATE = False  # Disable template formatting (use plain description)
```

## Example

See `products_to_update_sample.csv` for complete examples of properly formatted descriptions.

## Generated Output

The template generates clean HTML with:
- ✨ Proper headings (H3)
- 📋 Bullet lists for features
- 🎨 Horizontal dividers for sections
- 📊 Tables for delivery information
- 🔍 SEO-friendly structure

## Testing

To test the template system without uploading to Shopify:

```bash
python3 description_formatter.py
```

This will show you the HTML output for the sample product.

## Tips for Best Results

1. **Be Consistent**: Use the same section markers for all products
2. **Keep it Concise**: Short, impactful descriptions work best
3. **Use Keywords**: Include relevant search terms naturally
4. **Check Examples**: Refer to `products_to_update_sample.csv` for formatting guidance
5. **Test First**: Always test with a few products before bulk updates

## Troubleshooting

- **Missing Sections**: If a section is empty, it won't appear in the output
- **Format Errors**: Make sure each line in key-value sections has a colon (`:`)
- **Section Names**: Section markers must be in UPPERCASE and enclosed in brackets
- **Line Breaks**: Blank lines between sections are recommended for readability

## Files in the System

- `description_formatter.py` - Template processing engine
- `update_product_details.py` - Main script with USE_TEMPLATE flag
- `product_description_template.md` - Master template reference
- `products_to_update_sample.csv` - Example CSV with proper formatting
- `TEMPLATE_USAGE_GUIDE.md` - This guide

