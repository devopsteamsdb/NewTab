from flask import Flask, render_template, request, redirect, url_for
import json
import os
import base64
import uuid
import re

app = Flask(__name__)
DATA_FILE = 'data.json'
UPLOAD_FOLDER = 'static/img'

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"pages": [{"id": "default", "name": "Home"}], "systems": []}
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            # Migration: old format (list) -> new format (dict)
            if isinstance(data, list):
                return {"pages": [{"id": "default", "name": "Home"}], "systems": data}
            return data
    except:
        return {"pages": [{"id": "default", "name": "Home"}], "systems": []}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

@app.route('/')
def index():
    data = load_data()
    page_id = request.args.get('page', 'default')
    pages = data.get('pages', [])
    systems = data.get('systems', [])
    settings = data.get('settings', {'search_enabled': True, 'search_base_url': ''})
    
    # Filter systems by page
    filtered = [s for s in systems if page_id in s.get('pages', ['default'])]
    
    current_page = next((p for p in pages if p['id'] == page_id), {'id': 'default', 'name': 'Home'})
    
    return render_template('index.html', systems=filtered, pages=pages, current_page=current_page, settings=settings)

@app.route('/admin')
def admin():
    data = load_data()
    settings = data.get('settings', {'search_enabled': True, 'search_base_url': ''})
    return render_template('admin.html', pages=data.get('pages', []), systems=data.get('systems', []), settings=settings)

@app.route('/admin/settings', methods=['POST'])
def update_settings():
    data = load_data()
    current_settings = data.get('settings', {})
    search_enabled = request.form.get('search_enabled') == 'on'
    search_base_url = request.form.get('search_base_url', '')
    footer_text = request.form.get('footer_text', current_settings.get('footer_text', 'Made with Love by DevOps Team'))
    data['settings'] = {
        'search_enabled': search_enabled,
        'search_base_url': search_base_url,
        'footer_text': footer_text
    }
    save_data(data)
    return redirect(url_for('admin'))

# ========== PAGE MANAGEMENT ==========
@app.route('/admin/pages/add', methods=['POST'])
def add_page():
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

        systems[id] = {
            'name': name,
            'image': image_filename,
            'image_mode': image_mode,
            'image_size': image_size,
            'back_color': back_color,
            'front_color': front_color,
            'links': links,
            'pages': assigned_pages
        }
        
        save_data(data)
    return redirect(url_for('admin'))

@app.route('/admin/delete/<int:id>', methods=['POST'])
def delete_system(id):
    data = load_data()
    systems = data.get('systems', [])
    if 0 <= id < len(systems):
        systems.pop(id)
        save_data(data)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
