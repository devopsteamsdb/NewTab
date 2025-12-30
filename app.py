from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from flasgger import Swagger
import json
import os
import base64
import uuid
import re

app = Flask(__name__)
DATA_FILE = 'data/database/data.json'
UPLOAD_FOLDER = 'data/uploads'

# Swagger Configuration
app.config['SWAGGER'] = {
    'title': 'NewTab Dashboard API',
    'uiversion': 3
}
swagger_config = Swagger.DEFAULT_CONFIG.copy()
swagger_config['specs_route'] = '/swagger/'
swagger = Swagger(app, config=swagger_config)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('data/database', exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"pages": [{"id": "default", "name": "Home"}], "systems": [], "presets": []}
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Migration: old format (list) -> new format (dict)
            if isinstance(data, list):
                return {"pages": [{"id": "default", "name": "Home"}], "systems": data, "presets": []}
            # Ensure presets key exists
            if 'presets' not in data:
                data['presets'] = []
            return data
    except:
        return {"pages": [{"id": "default", "name": "Home"}], "systems": [], "presets": []}

PRESETS_FILE = 'config/presets.json'

def load_presets():
    """Load presets from presets.json file"""
    if not os.path.exists(PRESETS_FILE):
        return []
    try:
        with open(PRESETS_FILE, 'r') as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

@app.route('/')
def index():
    """
    Main dashboard page
    ---
    parameters:
      - name: page
        in: query
        type: string
        required: false
        default: default
        description: The ID of the page to display
    responses:
      200:
        description: Success
    """
    data = load_data()
    page_id = request.args.get('page', 'default')
    pages = data.get('pages', [])
    systems = data.get('systems', [])
    settings = data.get('settings', {})
    if 'search_enabled' not in settings: settings['search_enabled'] = True
    if 'search_base_url' not in settings: 
        settings['search_base_url'] = "https://www.google.com/search?q="
    if 'search_placeholder' not in settings:
        settings['search_placeholder'] = "Google Search"
    if 'search_width' not in settings:
        settings['search_width'] = "300"

    
    # Filter systems by page
    filtered = [s for s in systems if page_id in s.get('pages', ['default'])]
    
    current_page = next((p for p in pages if p['id'] == page_id), {'id': 'default', 'name': 'Home'})
    
    return render_template('index.html', systems=filtered, pages=pages, current_page=current_page, settings=settings)

@app.route('/admin')
def admin():
    """
    Admin configuration page
    ---
    responses:
      200:
        description: Success
    """
    data = load_data()
    settings = data.get('settings', {})
    if 'search_enabled' not in settings: settings['search_enabled'] = True
    if 'search_base_url' not in settings: 
        settings['search_base_url'] = "https://www.google.com/search?q="
    if 'search_placeholder' not in settings:
        settings['search_placeholder'] = "Google Search"
    if 'search_width' not in settings:
        settings['search_width'] = "300"

    presets = sorted(load_presets(), key=lambda x: x['name'].lower())
    return render_template('admin.html', pages=data.get('pages', []), systems=data.get('systems', []), settings=settings, presets=presets)

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    """
    Update global dashboard settings
    ---
    parameters:
      - name: search_enabled
        in: formData
        type: string
        enum: [on, off]
      - name: search_base_url
        in: formData
        type: string
      - name: search_placeholder
        in: formData
        type: string
      - name: search_width
        in: formData
        type: integer
      - name: footer_text
        in: formData
        type: string
    responses:
      302:
        description: Redirects back to admin page
    """
    data = load_data()
    current_settings = data.get('settings', {})
    search_enabled = request.form.get('search_enabled') == 'on'
    search_base_url = request.form.get('search_base_url', '').strip()
    search_placeholder = request.form.get('search_placeholder', '').strip()
    search_width = request.form.get('search_width', '').strip()
    footer_text = request.form.get('footer_text', current_settings.get('footer_text', 'Made with Love by DevOps Team'))
    data['settings'] = {
        'search_enabled': search_enabled,
        'search_base_url': search_base_url,
        'search_placeholder': search_placeholder,
        'search_width': search_width,
        'footer_text': footer_text
    }
    save_data(data)
    return redirect(url_for('admin'))

# ========== PAGE MANAGEMENT ==========
@app.route('/admin/pages/add', methods=['POST'])
def add_page():
    """
    Add a new dashboard page
    ---
    parameters:
      - name: page_name
        in: formData
        type: string
        required: true
        description: The display name of the page
    responses:
      302:
        description: Redirects back to admin page
    """
    data = load_data()
    name = request.form.get('page_name', '').strip()
    if name:
        page_id = slugify(name)
        # Avoid duplicates
        if not any(p['id'] == page_id for p in data['pages']):
            data['pages'].append({'id': page_id, 'name': name})
            save_data(data)
    return redirect(url_for('admin'))

@app.route('/admin/pages/delete/<page_id>', methods=['POST'])
def delete_page(page_id):
    """
    Delete a dashboard page
    ---
    parameters:
      - name: page_id
        in: path
        type: string
        required: true
        description: The ID of the page to delete
    responses:
      302:
        description: Redirects back to admin page
    """
    if page_id == 'default':
        return redirect(url_for('admin'))  # Cannot delete default
    data = load_data()
    data['pages'] = [p for p in data['pages'] if p['id'] != page_id]
    # Remove page from all systems
    for system in data['systems']:
        if page_id in system.get('pages', []):
            system['pages'].remove(page_id)
    save_data(data)
    return redirect(url_for('admin'))

# ========== SYSTEM MANAGEMENT ==========
@app.route('/admin/add', methods=['POST'])
def add_system():
    """
    Add a new system (card) to the dashboard
    ---
    parameters:
      - name: name
        in: formData
        type: string
        required: true
      - name: back_color
        in: formData
        type: string
      - name: front_color
        in: formData
        type: string
      - name: image_mode
        in: formData
        type: string
        enum: [fit, fill]
      - name: image_size
        in: formData
        type: integer
      - name: preset_image
        in: formData
        type: string
      - name: link_text[]
        in: formData
        type: array
        items: {type: string}
      - name: link_url[]
        in: formData
        type: array
        items: {type: string}
      - name: assigned_pages[]
        in: formData
        type: array
        items: {type: string}
    responses:
      302:
        description: Redirects back to admin page
    """
    data = load_data()
    
    name = request.form.get('name')
    back_color = request.form.get('back_color', '#000000')
    image_mode = request.form.get('image_mode', 'fill')
    front_color = request.form.get('front_color', '#11161F')
    image_size = request.form.get('image_size', '80')
    link_texts = request.form.getlist('link_text[]')
    link_urls = request.form.getlist('link_url[]')
    assigned_pages = request.form.getlist('assigned_pages[]')
    
    if not assigned_pages:
        assigned_pages = ['default']
    
    links = [{'text': t, 'url': u} for t, u in zip(link_texts, link_urls) if t and u]
    
    image_filename = 'generic.png'
    
    file = request.files.get('image_file')
    if file and file.filename:
        filename = f"{uuid.uuid4()}_{file.filename}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        image_filename = filename
    
    pasted_data = request.form.get('pasted_image')
    if pasted_data and 'base64,' in pasted_data:
        header, encoded = pasted_data.split(',', 1)
        ext = 'png'
        if 'image/jpeg' in header: ext = 'jpg'
        
        decoded = base64.b64decode(encoded)
        filename = f"{uuid.uuid4()}.{ext}"
        with open(os.path.join(UPLOAD_FOLDER, filename), 'wb') as f:
            f.write(decoded)
        image_filename = filename
    
    # Check for preset image (built-in images in static/presets/)
    preset_image = request.form.get('preset_image')
    if preset_image and image_filename == 'generic.png':
        image_filename = preset_image

    data['systems'].append({
        'name': name,
        'image': image_filename,
        'image_mode': image_mode,
        'image_size': image_size,
        'back_color': back_color,
        'front_color': front_color,
        'links': links,
        'pages': assigned_pages
    })
    
    save_data(data)
    return redirect(url_for('admin'))

@app.route('/admin/update/<int:id>', methods=['POST'])
def update_system(id):
    """
    Update an existing system (card)
    ---
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: The index of the system to update
      - name: name
        in: formData
        type: string
        required: true
      - name: back_color
        in: formData
        type: string
      - name: front_color
        in: formData
        type: string
      - name: image_mode
        in: formData
        type: string
        enum: [fit, fill]
      - name: image_size
        in: formData
        type: integer
      - name: link_text[]
        in: formData
        type: array
        items: {type: string}
      - name: link_url[]
        in: formData
        type: array
        items: {type: string}
      - name: assigned_pages[]
        in: formData
        type: array
        items: {type: string}
    responses:
      302:
        description: Redirects back to admin page
    """
    data = load_data()
    systems = data.get('systems', [])
    
    if 0 <= id < len(systems):
        name = request.form.get('name')
        back_color = request.form.get('back_color', '#000000')
        image_mode = request.form.get('image_mode', 'fill')
        front_color = request.form.get('front_color', '#11161F')
        image_size = request.form.get('image_size', '80')
        link_texts = request.form.getlist('link_text[]')
        link_urls = request.form.getlist('link_url[]')
        assigned_pages = request.form.getlist('assigned_pages[]')
        
        if not assigned_pages:
            assigned_pages = ['default']
        
        links = [{'text': t, 'url': u} for t, u in zip(link_texts, link_urls) if t and u]
        
        current_image = systems[id].get('image', 'generic.png')
        image_filename = current_image
        
        # Check for preset image first (so it can be overridden by upload if both present, though UI prevents this)
        preset_image = request.form.get('preset_image')
        if preset_image:
            image_filename = preset_image
        
        file = request.files.get('image_file')
        if file and file.filename:
            filename = f"{uuid.uuid4()}_{file.filename}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            image_filename = filename
        
        pasted_data = request.form.get('pasted_image')
        if pasted_data and 'base64,' in pasted_data:
            header, encoded = pasted_data.split(',', 1)
            ext = 'png'
            if 'image/jpeg' in header: ext = 'jpg'
            
            decoded = base64.b64decode(encoded)
            filename = f"{uuid.uuid4()}.{ext}"
            with open(os.path.join(UPLOAD_FOLDER, filename), 'wb') as f:
                f.write(decoded)
            image_filename = filename

        system_data = {
            'name': name,
            'image': image_filename,
            'image_mode': image_mode,
            'image_size': image_size,
            'back_color': back_color,
            'front_color': front_color,
            'links': links,
            'pages': assigned_pages
        }
        systems[id] = system_data
        
        save_data(data)
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_system(id):
    """
    Delete a system (card) from the dashboard
    ---
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: The index of the system to delete
    responses:
      302:
        description: Redirects back to admin page
    """
    data = load_data()
    systems = data.get('systems', [])
    if 0 <= id < len(systems):
        systems.pop(id)
        save_data(data)
    return redirect(url_for('admin'))

@app.route('/admin/move/<direction>/<int:id>', methods=['POST'])
def move_system(direction, id):
    """
    Move a system card up or down in the list
    ---
    parameters:
      - name: direction
        in: path
        type: string
        enum: [up, down]
        required: true
      - name: id
        in: path
        type: integer
        required: true
    responses:
      302:
        description: Redirects back to admin page
    """
    data = load_data()
    systems = data.get('systems', [])
    
    if direction == 'up' and id > 0 and id < len(systems):
        systems[id], systems[id-1] = systems[id-1], systems[id]
        save_data(data)
    elif direction == 'down' and id < len(systems) - 1 and id >= 0:
        systems[id], systems[id+1] = systems[id+1], systems[id]
        save_data(data)
        
    return redirect(url_for('admin'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """
    Serve an uploaded image file
    ---
    parameters:
      - name: filename
        in: path
        type: string
        required: true
        description: The filename to serve
    responses:
      200:
        description: The image file
      404:
        description: File not found
    """
    return send_from_directory(UPLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
