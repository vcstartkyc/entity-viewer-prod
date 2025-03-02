from flask import Flask, render_template, jsonify, request, redirect, url_for, g, Response
from pathlib import Path
import json
from flask_cors import CORS
import re
from unidecode import unidecode
from datetime import datetime
from flask_babel import Babel, _, lazy_gettext as _l
import pycountry
import requests

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['BABEL_DEFAULT_LOCALE'] = 'en'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'it', 'mt', 'fr', 'de', 'sl', 'hr', 'nl', 'es', 'pt']
babel = Babel(app)

# Configuration
DATA_DIR = Path(__file__).parent / 'data'

# Language names for the UI
LANGUAGES = {
    'en': 'English',
    'it': 'Italiano',
    'mt': 'Malti',
    'fr': 'Français',
    'de': 'Deutsch',
    'sl': 'Slovenščina',
    'hr': 'Hrvatski',
    'nl': 'Nederlands',
    'es': 'Español',
    'pt': 'Português'
}

# Generate country codes from pycountry
COUNTRY_CODES = {country.alpha_2: country.name for country in pycountry.countries}

# Add common alternative names and codes
COUNTRY_ALTERNATIVES = {
    'UK': 'GB',  # United Kingdom
    'USA': 'US',  # United States
    'UAE': 'AE',  # United Arab Emirates
    'Russia': 'RU',
    'Taiwan': 'TW',
    'Iran': 'IR',
    'North Korea': 'KP',
    'South Korea': 'KR',
    'Syria': 'SY',
    'Venezuela': 'VE',
}

def get_country_code(name_or_code):
    """Get standardized country code from name or code"""
    # Check if it's already a valid alpha-2 code
    if name_or_code.upper() in COUNTRY_CODES:
        return name_or_code.upper()
    
    # Check alternatives
    if name_or_code.upper() in COUNTRY_ALTERNATIVES:
        return COUNTRY_ALTERNATIVES[name_or_code.upper()]
    
    # Try to find by name
    try:
        country = pycountry.countries.search_fuzzy(name_or_code)
        if country:
            return country[0].alpha_2
    except LookupError:
        pass
    
    return None

def get_locale():
    # Try to get locale from URL parameter
    locale = request.args.get('lang')
    if locale and locale in app.config['BABEL_SUPPORTED_LOCALES']:
        return locale
    
    # Try to get locale from user preferences
    if not locale:
        locale = request.accept_languages.best_match(app.config['BABEL_SUPPORTED_LOCALES'])
    
    # Default to English
    return locale or 'en'

babel.init_app(app, locale_selector=get_locale)

def slugify(text):
    """Convert text to URL-safe slug"""
    # Convert to ASCII
    text = unidecode(text)
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and special chars with hyphens
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    # Strip leading/trailing hyphens
    return text.strip('-')

def format_date(date_obj=None):
    """Format date for display"""
    if date_obj is None:
        date_obj = datetime.now()
    return date_obj.strftime("%B %d, %Y")

def process_address(address):
    """Process address dictionary to return only populated fields"""
    if isinstance(address, str):
        return {'formatted': address}
        
    processed = {}
    
    # Remove MongoDB ObjectId
    if '_id' in address:
        del address['_id']
    
    # Add populated fields
    for field in ['address1', 'address2', 'address3', 'address4']:
        if address.get(field):
            processed['address'] = address[field]
            break
            
    if address.get('city'):
        processed['city'] = address['city']
        
    if address.get('county'):
        processed['county'] = address['county']
        
    if address.get('country'):
        country_code = get_country_code(address['country'])
        if country_code:
            processed['country'] = {
                'code': country_code,
                'name': COUNTRY_CODES.get(country_code, country_code)
            }
        
    if address.get('postcode'):
        processed['postcode'] = address['postcode']
        
    return processed

def process_note(note):
    """Process note text to extract and format vessel flag states and other country references"""
    if not isinstance(note, dict) or 'text' not in note:
        return None
        
    text = note['text']
    # Split by pipe and process each part
    if '|' in text:
        parts = text.split('|')
        processed_parts = []
        i = 0
        while i < len(parts):
            part = parts[i].strip()
            # Skip empty parts
            if not part:
                i += 1
                continue
                
            # Check if next part exists and could be a country
            if i + 1 < len(parts):
                next_part = parts[i + 1].strip()
                # Try to find country code
                country_code = get_country_code(next_part)
                if country_code:
                    # Format the text and add country info
                    processed_parts.append(f"{part} {COUNTRY_CODES[country_code]}")
                    i += 2  # Skip the country part
                    return {
                        'text': ' '.join(processed_parts),
                        'country': {
                            'code': country_code,
                            'name': COUNTRY_CODES[country_code]
                        }
                    }
                else:
                    # If next part is not a country, join with a dash
                    if next_part:
                        processed_parts.append(f"{part} - {next_part}")
                        i += 2
                    else:
                        processed_parts.append(part)
                        i += 1
            else:
                processed_parts.append(part)
                i += 1
                
        return {'text': ' '.join(processed_parts)}
    
    return {'text': text}

def process_document(doc):
    """Process document data to extract all relevant information"""
    if not isinstance(doc, dict):
        return None
        
    processed = {
        'reference': doc.get('reference'),
        'categories': doc.get('categories', []),
        'url': doc.get('url'),
        'originalUrl': doc.get('originalUrl'),
        'pdf': doc.get('pdf'),
        'datePosted': doc.get('datePosted', {}).get('$date'),
        'dateCollected': doc.get('dateCollected', {}).get('$date'),
    }
    
    # Process extra data if available
    extra_data = doc.get('extraData', {})
    if extra_data:
        processed.update({
            'title': extra_data.get('title'),
            'summary': extra_data.get('summary'),
            'copyrighted': extra_data.get('copyrighted', False)
        })
    
    # Convert dates to readable format
    for date_field in ['datePosted', 'dateCollected']:
        if processed.get(date_field):
            try:
                date_str = processed[date_field]
                if isinstance(date_str, str):
                    # Handle both ISO format and millisecond timestamps
                    if date_str.endswith('Z'):
                        date_str = date_str[:-1]  # Remove 'Z' suffix
                    date_obj = datetime.fromisoformat(date_str)
                    processed[date_field] = date_obj.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                pass
    
    return processed

def load_data():
    """Load and process the JSON data"""
    csv_path = DATA_DIR / 'entities.csv'
    print(f"Loading data from {csv_path}")
    if not csv_path.exists():
        print("File not found:", csv_path)
        return []
    
    try:
        entities = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, start=1):
                try:
                    # Skip empty lines
                    line = line.strip().strip('"')  # Remove quotes
                    if not line:
                        continue
                        
                    # Parse JSON data
                    data = json.loads(line)
                    raw_data = data.get('raw', {})
                    
                    # Extract and normalize datasets
                    datasets = []
                    raw_datasets = raw_data.get('datasets', [])
                    for ds in raw_datasets:
                        if ds == 'INS':
                            datasets.append('insolvency')
                        elif ds == 'RRE':
                            datasets.append('adverse_media')
                        elif ds == 'SAN':
                            datasets.append('sanctions')
                        elif ds == 'POI':
                            datasets.append('pep')
                        elif ds == 'REL':
                            datasets.append('disqualified')
                    
                    # Process addresses
                    addresses = []
                    for addr in raw_data.get('addresses', []):
                        if isinstance(addr, dict):
                            addr_text = []
                            if addr.get('address'):
                                addr_text.append(addr['address'])
                            if addr.get('city'):
                                addr_text.append(addr['city'])
                            if addr.get('county'):
                                addr_text.append(addr['county'])
                            if addr.get('postcode'):
                                addr_text.append(addr['postcode'])
                            if addr.get('country'):
                                addr_text.append(addr['country'])
                            
                            if addr_text:
                                country_code = None
                                country = addr.get('country', '')
                                if country:
                                    # Try to get country code
                                    try:
                                        country_obj = pycountry.countries.get(name=country)
                                        if country_obj:
                                            country_code = country_obj.alpha_2.lower()
                                    except:
                                        pass
                                        
                                addresses.append({
                                    'text': ', '.join(addr_text),
                                    'country': country_code if country_code else country.lower()
                                })
                    
                    # Create entity object
                    entity = {
                        'name': data.get('name', ''),
                        'reference': data.get('reference', ''),
                        'fullname': data.get('fullname', ''),
                        'datasets': datasets,
                        'risk_level': 'HIGH' if 'sanctions' in datasets else ('MEDIUM' if 'pep' in datasets else 'LOW'),
                        'aliases': [a.get('name', '') for a in data.get('aliases', []) if isinstance(a, dict) and a.get('name')],
                        'notes': [{'text': n.get('text', '')} for n in data.get('notes', []) if isinstance(n, dict) and n.get('text')],
                        'documents': [],
                        'addresses': addresses,
                        'businesses': [{
                            'name': b.get('name'),
                            'position': b.get('position'),
                            'reference': b.get('reference')
                        } for b in data.get('businesses', []) if isinstance(b, dict) and b.get('name')],
                        'insolvent': data.get('insolvent', False),
                        'media': data.get('media', False),
                        'financialRegulator': data.get('financialRegulator', False)
                    }
                    
                    # Process documents
                    for doc in data.get('documents', []):
                        if isinstance(doc, dict):
                            doc_url = doc.get('url', '')
                            if doc_url:
                                # Handle sensitive URLs
                                if doc_url.startswith(('https://www.acurisriskintelligence.com/', 'https://secure.c6-intelligence.com/')):
                                    doc_url = f"https://localhost:5000/proxy/document/{doc.get('reference')}"
                                
                            doc_data = {
                                'reference': doc.get('reference'),
                                'title': doc.get('extraData', {}).get('title'),
                                'summary': doc.get('extraData', {}).get('summary'),
                                'url': doc_url,
                                'categories': doc.get('categories', [])
                            }
                            if any(doc_data.values()):
                                entity['documents'].append(doc_data)
                    
                    # Add slug
                    entity['slug'] = slugify(entity['name'])
                    
                    # Only add if we have required fields
                    if entity['name']:
                        entities.append(entity)
                        if len(entities) % 100 == 0:
                            print(f"Processed {len(entities)} entities...")
                        
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON on line {line_num}: {e}")
                    print(f"Line content: {line[:100]}...")
                    continue
                except Exception as e:
                    print(f"Error processing entity on line {line_num}: {e}")
                    continue
                    
        print(f"Successfully loaded {len(entities)} entities")
        if entities:
            print("First entity:", entities[0]['name'])
            print("First entity slug:", entities[0]['slug'])
            print("First entity notes:", entities[0].get('notes'))
            if entities[0].get('addresses'):
                print("First entity addresses:", entities[0]['addresses'])
        return entities
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return []

@app.route('/')
def index():
    """Main page showing all entities"""
    entities = load_data()
    print(f"Index: Loaded {len(entities)} entities")
    if entities:
        print("First entity:", entities[0]['name'])
    return render_template('index.html', languages=LANGUAGES)

@app.route('/api/entities')
def get_entities():
    """API endpoint to get filtered entities"""
    try:
        entities = load_data()
        print(f"API: Loaded {len(entities)} entities")
        
        if not entities:
            print("No entities found!")
            return jsonify({"entities": [], "message": "No entities found in database"})
            
        # Apply filters if provided
        query = request.args.get('q', '').lower()
        dataset = request.args.get('dataset')
        
        filtered = entities
        
        if query:
            filtered = [e for e in filtered if 
                       query in e['name'].lower() or 
                       query in (e.get('fullname', '')).lower() or 
                       query in (e.get('reference', '')).lower() or
                       any(query in alias.lower() for alias in e.get('aliases', []))]
            print(f"After query filter '{query}': {len(filtered)} entities")
        
        if dataset and dataset != 'all':
            filtered = [e for e in filtered if dataset in e.get('datasets', [])]
            print(f"After dataset filter '{dataset}': {len(filtered)} entities")
            
        # Add slug to each entity
        for entity in filtered:
            entity['slug'] = slugify(entity['name'])
            
        if not filtered:
            print("No entities after filtering")
            return jsonify({"entities": [], "message": "No entities found matching your criteria"})
            
        print(f"Returning {len(filtered)} entities")
        if filtered:
            print("First filtered entity:", filtered[0]['name'])
            print("First filtered entity slug:", filtered[0]['slug'])
            
        return jsonify({"entities": filtered})
        
    except Exception as e:
        print(f"Error in get_entities: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/entity/<name_slug>')
def entity_detail(name_slug):
    """Detail page for a specific entity using name slug"""
    try:
        entities = load_data()
        print(f"Looking for entity with slug '{name_slug}' among {len(entities)} entities")
        
        # First try exact match
        entity = next((e for e in entities if slugify(e['name']) == name_slug), None)
        
        if not entity:
            # Try case-insensitive match
            entity = next((e for e in entities if slugify(e['name']).lower() == name_slug.lower()), None)
        
        if not entity:
            print(f"Entity not found with slug '{name_slug}'")
            print("Available slugs:", [slugify(e['name']) for e in entities[:5]])
            return _("Entity not found"), 404
        
        print(f"Found entity: {entity['name']}")
        
        # Add current date for SEO and content freshness
        current_date = format_date()
        
        return render_template('entity_detail.html', 
                            entity=entity,
                            current_date=current_date,
                            languages=LANGUAGES)
                            
    except Exception as e:
        print(f"Error in entity_detail: {e}")
        return str(e), 500

@app.route('/sitemap')
def sitemap():
    """Generate HTML sitemap"""
    entities = load_data()
    
    # Add slug to each entity
    for entity in entities:
        entity['slug'] = slugify(entity['name'])
    
    # Sort entities by name
    entities.sort(key=lambda x: x['name'].lower())
    
    # Group entities by first letter
    grouped_entities = {}
    for entity in entities:
        first_letter = entity['name'][0].upper()
        if first_letter not in grouped_entities:
            grouped_entities[first_letter] = []
        grouped_entities[first_letter].append(entity)
    
    # Sort letters
    letters = sorted(grouped_entities.keys())
    
    return render_template('sitemap.html',
                         letters=letters,
                         grouped_entities=grouped_entities,
                         languages=LANGUAGES)

@app.route('/sitemap.xml')
def sitemap_xml():
    """Generate XML sitemap for search engines"""
    entities = load_data()
    base_url = request.url_root.rstrip('/')
    
    # Add homepage and sitemap
    pages = [
        {'loc': base_url, 'changefreq': 'daily', 'priority': 1.0},
        {'loc': f"{base_url}/sitemap", 'changefreq': 'daily', 'priority': 0.8}
    ]
    
    # Add all entity pages
    for entity in entities:
        slug = slugify(entity['name'])
        pages.append({
            'loc': f"{base_url}/entity/{slug}",
            'changefreq': 'daily',
            'priority': 0.6
        })
    
    return render_template('sitemap.xml',
                         pages=pages,
                         base_url=base_url), 200, {'Content-Type': 'application/xml'}

@app.route('/proxy/document/<reference>')
def proxy_document(reference):
    """Proxy document requests to hide the original URL"""
    try:
        entities = load_data()
        
        # Find the document by reference
        for entity in entities:
            for doc in entity.get('documents', []):
                if doc.get('reference') == reference:
                    # Get the original URL
                    url = doc.get('url', '')
                    if not url:
                        return _("Document not found"), 404
                        
                    # Make request to get document content
                    response = requests.get(url, stream=True)
                    if response.status_code != 200:
                        return _("Failed to fetch document"), response.status_code
                        
                    # Determine content type, defaulting to PDF for common PDF URLs
                    content_type = response.headers.get('Content-Type', '')
                    if '.pdf' in url.lower() and 'html' not in content_type.lower():
                        content_type = 'application/pdf'
                        
                    # Return content with appropriate headers
                    headers = {
                        'Content-Type': content_type,
                        'Content-Disposition': 'inline',
                        'Content-Security-Policy': "frame-ancestors 'self'",
                        'X-Frame-Options': 'SAMEORIGIN'
                    }
                    return Response(response.content, headers=headers)
                    
        return _("Document not found"), 404
        
    except Exception as e:
        print(f"Error proxying document: {e}")
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True)
