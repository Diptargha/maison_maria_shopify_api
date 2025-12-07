"""
Product Description Formatter
Converts structured description data from CSV into formatted HTML for Shopify
Based on the master template in product_description_template.md
"""

import re

# Standard delivery details table (same for all products)
DELIVERY_TABLE = """
<h3>Delivery Details</h3>
<p>Delivery times to Europe (including UK) depend on the shipping method selected:</p>
<table>
  <thead>
    <tr>
      <th>Shipping Method</th>
      <th>Shipping Cost</th>
      <th>Estimated Delivery Time</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Ordinary</td>
      <td>£4.00</td>
      <td>7–15 days</td>
    </tr>
    <tr>
      <td>Ordinary Plus</td>
      <td>£5.00</td>
      <td>5–11 days</td>
    </tr>
    <tr>
      <td>Ordinary Fast</td>
      <td>£6.14</td>
      <td>4–9 days</td>
    </tr>
    <tr>
      <td>DHL Express</td>
      <td>£39.56</td>
      <td>3–7 days</td>
    </tr>
  </tbody>
</table>
"""


def parse_description_data(description_text):
    """
    Parse structured description data from CSV format.
    
    Expected format:
    [SHORT_DESC]
    Text here...
    
    [WHY_LOVE]
    Key: Value
    Key: Value
    
    [SIZE_FIT]
    Key: Value
    
    [FABRIC_CARE]
    Key: Value
    
    [WHATS_INCLUDED]
    Text here...
    
    Returns a dictionary with parsed sections.
    """
    if not description_text or not isinstance(description_text, str):
        return {}
    
    sections = {
        'short_desc': '',
        'why_love': [],
        'size_fit': [],
        'fabric_care': [],
        'whats_included': ''
    }
    
    # Split by section markers
    section_pattern = r'\[(SHORT_DESC|WHY_LOVE|SIZE_FIT|FABRIC_CARE|WHATS_INCLUDED)\](.*?)(?=\[|$)'
    matches = re.findall(section_pattern, description_text, re.DOTALL | re.IGNORECASE)
    
    for section_name, content in matches:
        section_name = section_name.upper()
        content = content.strip()
        
        if section_name == 'SHORT_DESC':
            sections['short_desc'] = content
        
        elif section_name == 'WHY_LOVE':
            # Parse key-value pairs
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    sections['why_love'].append({'key': key.strip(), 'value': value.strip()})
        
        elif section_name == 'SIZE_FIT':
            # Parse key-value pairs
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    sections['size_fit'].append({'key': key.strip(), 'value': value.strip()})
        
        elif section_name == 'FABRIC_CARE':
            # Parse key-value pairs
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    sections['fabric_care'].append({'key': key.strip(), 'value': value.strip()})
        
        elif section_name == 'WHATS_INCLUDED':
            sections['whats_included'] = content
    
    return sections


def generate_html_from_template(parsed_data):
    """
    Generate HTML description from parsed data using the master template.
    
    Args:
        parsed_data: Dictionary with sections (short_desc, why_love, size_fit, fabric_care, whats_included)
    
    Returns:
        HTML string formatted for Shopify
    """
    html_parts = []
    
    # Short Description
    if parsed_data.get('short_desc'):
        html_parts.append(f'<p>{parsed_data["short_desc"]}</p>')
        html_parts.append('<hr>')
    
    # Why You'll Love It section
    if parsed_data.get('why_love'):
        html_parts.append('<h3>Why You\'ll Love It:</h3>')
        html_parts.append('<ul>')
        for item in parsed_data['why_love']:
            html_parts.append(f'  <li><strong>{item["key"]}:</strong> {item["value"]}</li>')
        html_parts.append('</ul>')
        html_parts.append('<hr>')
    
    # Size & Fit section
    if parsed_data.get('size_fit'):
        html_parts.append('<h3>Size &amp; Fit:</h3>')
        html_parts.append('<ul>')
        for item in parsed_data['size_fit']:
            html_parts.append(f'  <li><strong>{item["key"]}:</strong> {item["value"]}</li>')
        html_parts.append('</ul>')
        html_parts.append('<hr>')
    
    # Fabric & Care section
    if parsed_data.get('fabric_care'):
        html_parts.append('<h3>Fabric &amp; Care:</h3>')
        html_parts.append('<ul>')
        for item in parsed_data['fabric_care']:
            html_parts.append(f'  <li><strong>{item["key"]}:</strong> {item["value"]}</li>')
        html_parts.append('</ul>')
        html_parts.append('<hr>')
    
    # What's Included section
    if parsed_data.get('whats_included'):
        html_parts.append('<h3>What\'s Included:</h3>')
        html_parts.append(f'<p>{parsed_data["whats_included"]}</p>')
        html_parts.append('<hr>')
    
    # Add standard delivery details
    html_parts.append(DELIVERY_TABLE)
    
    return '\n'.join(html_parts)


def format_description_with_template(description_text):
    """
    Main function to format a description using the template.
    
    Args:
        description_text: Raw structured description from CSV
    
    Returns:
        Formatted HTML ready for Shopify
    """
    # Parse the structured data
    parsed_data = parse_description_data(description_text)
    
    # Generate HTML from template
    html_output = generate_html_from_template(parsed_data)
    
    return html_output


# For testing purposes
if __name__ == "__main__":
    # Test with sample data
    sample_description = """
[SHORT_DESC]
Turn heads in this Elegant Navy Blue Evening Dress, featuring spaghetti straps, a back lace-up closure, high thigh slit, and mermaid silhouette. Perfect for proms, weddings, galas, or formal events, this fitted gown combines sophistication, comfort, and micro-elastic stretch for all-season wear.

[WHY_LOVE]
Style: Spaghetti straps with back lace-up closure and thigh-high slit
Fit: Mermaid / bodycon silhouette for a flattering, figure-hugging look
Season: Suitable for all seasons
Effortless Wear: Micro-elastic fabric for comfort and ease of movement
Occasion Ready: Perfect for proms, weddings, galas, or formal evening events

[SIZE_FIT]
Fit Type: Bodycon / Mermaid Fit
Length: Floor-Length
Sleeve: Sleeveless / Spaghetti Straps
Customer Group: Adult Women
Gender: Women

[FABRIC_CARE]
Fabric: 95% Polyester, 5% Elastane
Feel: Soft, slightly stretchy, and smooth
Care Instructions: Hand wash or professional dry clean

[WHATS_INCLUDED]
1 x Elegant Navy Blue Spaghetti Strap Evening Dress
"""
    
    result = format_description_with_template(sample_description)
    print("=== Generated HTML ===")
    print(result)
    print("\n=== Preview ===")
    print("(Open in browser to see formatted output)")

