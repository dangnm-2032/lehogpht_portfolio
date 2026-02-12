from backends import *

from flask import Flask, render_template, session, redirect, url_for, request, send_from_directory
import os
from werkzeug.utils import secure_filename
import zipfile
import yaml
import shutil

app = Flask(__name__)
app.secret_key = '123'

os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

open(os.path.join(DATA_FOLDER, "projects.yaml"), "a").close()

@app.route('/data/<path:filename>')
def data(filename):
    return send_from_directory(DATA_FOLDER, filename)

@app.route("/")
def home():
    # Load projects
    with open(os.path.join(DATA_FOLDER, "projects.yaml"), "r") as f:
        projects = yaml.safe_load(f)
    
    if not projects:
        projects = {}
    
    # Get all projects
    projects_data = []
    categories = []
    for _, project_id in projects.items():
        data_dir = os.path.join(DATA_FOLDER, project_id)
        meta_file = os.path.join(data_dir, "meta.yaml")
        with open(meta_file, "r") as f:
            meta = yaml.safe_load(f)
            meta['project_id'] = project_id
            projects_data.append(meta)
            categories = categories + meta['whatwedid'].split(', ') if meta['whatwedid'] else categories

    categories = set(categories)       
    
    return render_template("home.html", data=projects_data, categories=categories)

@app.route("/project/<project_id>")
def project(project_id):
    # Load project data
    data_dir = os.path.join(DATA_FOLDER, project_id)
    meta_file = os.path.join(data_dir, "meta.yaml")
    if os.path.exists(meta_file):
        with open(meta_file, "r") as f:
            meta = yaml.safe_load(f)
            meta['project_id'] = project_id
            paragraphs = meta['description'].split("<paragraph>")
            meta['description'] = []
            for para in paragraphs:
                para = para.split('\n')
                heading = para[0]
                content = '\n'.join(para[1:])
                if heading and content:
                    meta['description'].append((heading, content))

            return render_template("project.html", project=meta)
    return "Project not found", 404

# Admin routes
@app.route("/admin")
def admin():
    if not session.get('admin_logged_in'):
        return render_template("admin_login.html")

    # Load projects.yaml
    with open(os.path.join(DATA_FOLDER, "projects.yaml"), "r") as f:
        projects = yaml.safe_load(f)
    
    if not projects:
        projects = {}
    
    projects_data = []
    # Load project name and hero image for each project
    for order, project_id in projects.items():
        data_dir = os.path.join(DATA_FOLDER, project_id)
        meta_file = os.path.join(data_dir, "meta.yaml")
        if os.path.exists(meta_file):
            with open(meta_file, "r") as f:
                meta = yaml.safe_load(f)
                projects_data.append((order, project_id, meta.get("name", ""), os.path.join(project_id, meta.get("hero_image", ""))))

    print(projects_data)
    
    return render_template("admin.html", projects=projects_data)

@app.route("/admin/help")
def admin_help():
    return render_template("admin_help.html")

@app.route("/admin/login", methods=["POST"])
def admin_login():
    username = request.form.get("username")
    password = request.form.get("password")
    if username == "admin" and password == "admin":
        session['admin_logged_in'] = True
        return redirect(url_for("admin"))
    return render_template("admin_login.html", error="Invalid username or password")

@app.route("/admin/logout")
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for("admin"))

@app.route("/admin/project_action", methods=["POST"])
def project_action():
    if not session.get('admin_logged_in'):
        return redirect(url_for("admin"))
    file = request.files['zip_file']

    if not file:
        return redirect(url_for("admin"))

    filename = secure_filename(file.filename)
    file.save(os.path.join(TEMP_FOLDER, filename))

    with zipfile.ZipFile(os.path.join(TEMP_FOLDER, filename), 'r') as z:
        for info in z.infolist():
            # Fix Vietnamese / UTF-8 filenames (common Windows ZIP fix)
            name = info.filename.encode('cp437').decode('utf-8', errors='ignore')
            
            # Prevent zip-slip
            target_path = os.path.abspath(os.path.join(TEMP_FOLDER, name))
            if not target_path.startswith(os.path.abspath(TEMP_FOLDER)):
                raise Exception(f"Unsafe file path detected: {name}")

            # Make sure the folder exists
            os.makedirs(os.path.dirname(target_path), exist_ok=True)

            # Extract file
            if not info.is_dir():
                with open(target_path, 'wb') as f:
                    f.write(z.read(info.filename))


    working_dir = os.path.join(TEMP_FOLDER, filename.replace('.zip', ''))

    # Check if meta.yaml exists
    if not os.path.exists(os.path.join(working_dir, "meta.yaml")):
        return "meta.yaml not found", 400

    # Read meta.yaml
    with open(os.path.join(working_dir, "meta.yaml"), "r") as f:
        meta = yaml.load(f, Loader=yaml.FullLoader)

    validate_key = ['name', 'client', 'year', 'industry', 'whatwedid', 'description', 'hero_image', 'images']
    
    # Validate meta.yaml
    for key in validate_key:
        if key not in meta:
            return f"Invalid meta.yaml: {key} not found", 400
 

    # Validate images
    if not os.path.exists(os.path.join(working_dir, meta['hero_image'])):
        return "hero_image not found", 400

    for files in meta['images']:
        for file in files:
            if not os.path.exists(os.path.join(working_dir, file)):
                return f"image {file} not found", 400
    
    # Create project folder but remove whitespace, special characters
    project_id = slugify_vi(meta['name'])
    project_folder = os.path.join(DATA_FOLDER, project_id)
    if not os.path.exists(project_folder):
        os.makedirs(project_folder)
    
    # Move files to project folder
    for file in os.listdir(working_dir):
        if not file.endswith('.zip'):
            os.rename(os.path.join(working_dir, file), os.path.join(project_folder, file))

    # Delete all contents in temp folder
    if os.path.exists(TEMP_FOLDER):
        # Loop through all items inside
        for filename in os.listdir(TEMP_FOLDER):
            file_path = os.path.join(TEMP_FOLDER, filename)
            
            # Remove files
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)  # delete file or symlink
            
            # Remove directories recursively
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
    
    # Load projects.yaml
    with open(os.path.join(DATA_FOLDER, "projects.yaml"), "r") as f:
        projects = yaml.safe_load(f)
    
    if not projects:
        projects = {}

    # Check if project already exists
    if project_id not in projects.values():
        # Count projects
        try:
            project_count = len(projects)
        except:
            project_count = 0

        # Add project to projects.yaml with count + 1
        projects[project_count + 1] = project_id
        
        # Save projects.yaml
        with open(os.path.join(DATA_FOLDER, "projects.yaml"), "w") as f:
            yaml.dump(projects, f, default_flow_style=False)
    
    return redirect(url_for("admin"))

@app.route("/admin/project_remove/<project_id>")
def project_remove(project_id):
    
    # Load projects.yaml
    with open(os.path.join(DATA_FOLDER, "projects.yaml"), "r") as f:
        projects = yaml.safe_load(f)
    
    if not projects:
        projects = {}
    
    # Remove project from projects.yaml
    for key, value in projects.items():
        if value == project_id:
            del projects[key]
            break

    # Reorder projects
    new_projects = {}
    for i, (key, value) in enumerate(projects.items()):
        new_projects[i + 1] = value
    
    projects = new_projects
    
    # Remove project folder
    project_folder = os.path.join(DATA_FOLDER, project_id)
    if os.path.exists(project_folder):
        shutil.rmtree(project_folder)
    
    # Save projects.yaml
    with open(os.path.join(DATA_FOLDER, "projects.yaml"), "w") as f:
        yaml.dump(projects, f, default_flow_style=False)
    
    return redirect(url_for("admin"))

@app.route("/admin/project_change_order/<project_id>/<int:current_order>", methods=["GET"])
def project_change_order_form(project_id, current_order):
    return render_template("admin_change_order.html", project_id=project_id, current_order=current_order)

@app.route("/admin/project_change_order/<project_id>/<int:current_order>", methods=["POST"])
def project_change_order(project_id, current_order):
    new_order = request.form.get("new_order")
    # Load projects.yaml
    with open(os.path.join(DATA_FOLDER, "projects.yaml"), "r") as f:
        projects = yaml.safe_load(f)
    
    if not projects:
        projects = {}
    
    # Move project to new position
    projects = reorder_dict(projects, project_id, int(new_order))
    
    # Save projects.yaml
    with open(os.path.join(DATA_FOLDER, "projects.yaml"), "w") as f:
        yaml.dump(projects, f, default_flow_style=False)
    
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True)