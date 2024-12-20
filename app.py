import os
import base64
import hashlib
import zipfile
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet

app = Flask(__name__)

app.secret_key = 'your_secret_key_here'

# Configuration
#app.config["UPLOAD_FOLDER"] = "uploads/"
#app.config["PROCESSED_FOLDER"] = "processed/"
#os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
#os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)

## app.config["UPLOAD_FOLDER"] = "uploads/"
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads/")
app.config["PROCESSED_FOLDER"] = os.path.join(os.getcwd(), "processed/")
# app.config["PROCESSED_FOLDER"] = "processed/"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["PROCESSED_FOLDER"], exist_ok=True)


# Utility functions
def zip_folder(folder_path, output_path):
    """Compress a folder into a zip file."""
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, start=folder_path)
                zipf.write(file_path, arcname)

def unzip_folder(zip_path, extract_to):
    """Extract a zip file into a folder."""
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(extract_to)

def encrypt_file(file_path, key):
    """Encrypt a file using Fernet."""
    with open(file_path, 'rb') as f:
        data = f.read()
    encrypted_data = Fernet(key).encrypt(data)
    with open(file_path, 'wb') as f:
        f.write(encrypted_data)

def decrypt_file(file_path, key):
    """Decrypt a file using Fernet."""
    with open(file_path, 'rb') as f:
        data = f.read()
    decrypted_data = Fernet(key).decrypt(data)
    with open(file_path, 'wb') as f:
        f.write(decrypted_data)

@app.route("/")
def index():
    """Render the main page."""
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    """Handle file encryption and decryption."""
    task = request.form.get("task")
    key_text = request.form.get("key")
    file = request.files.get("file")
    
    # Derive the key
    key = hashlib.sha256(key_text.encode()).digest()[:32]
    fernet_key = base64.urlsafe_b64encode(key)

    try:
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)

            if task == "encrypt_file":
                encrypt_file(file_path, fernet_key)
            elif task == "decrypt_file":
                decrypt_file(file_path, fernet_key)
            
            return send_file(file_path, as_attachment=True)
        return jsonify({"error": "No file provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/process-folder", methods=["POST"])
def process_folder():
    """Handle folder encryption and decryption directly."""
    task = request.form.get("task2")
    key_text = request.form.get("key2")
    files = request.files.getlist("folder")

    # Derive the key
    key = hashlib.sha256(key_text.encode()).digest()[:32]
    fernet_key = base64.urlsafe_b64encode(key)

    try:
        if files:
            folder_path = os.path.join(app.config["UPLOAD_FOLDER"], "uploaded_folder")
            os.makedirs(folder_path, exist_ok=True)

            # Save uploaded files into a folder
            for file in files:
                relative_path = file.filename  # The relative path (from client)
                target_path = os.path.join(folder_path, relative_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                file.save(target_path)

            # Process files in the folder
            for root, _, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    encrypt_file(file_path, fernet_key)

            # Provide processed folder for download
            output_zip = os.path.join(app.config["PROCESSED_FOLDER"], "processed_folder.zip")
            zip_folder(folder_path, output_zip)

            return send_file(output_zip, as_attachment=True)

        return jsonify({"error": "No files provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/decrypt-zip-folder", methods=["POST"])
def decrypt_zip_folder():
    """Handle decryption of an uploaded zip folder."""
    key_text = request.form.get("key_zip")
    zip_file = request.files.get("zip_folder")

    # Derive the key
    key = hashlib.sha256(key_text.encode()).digest()[:32]
    fernet_key = base64.urlsafe_b64encode(key)

    try:
        if zip_file:
            # Save uploaded zip file
            zip_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(zip_file.filename))
            zip_file.save(zip_path)

            # Extract the zip file
            extract_path = os.path.join(app.config["UPLOAD_FOLDER"], "extracted_folder")
            os.makedirs(extract_path, exist_ok=True)
            unzip_folder(zip_path, extract_path)

            # Process extracted folder
            for root, _, filenames in os.walk(extract_path):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    if filename != "description.txt":  # Skip description.txt during decryption
                        decrypt_file(file_path, fernet_key)

            # Repack the decrypted folder into a new zip
            output_zip = os.path.join(app.config["PROCESSED_FOLDER"], "decrypted_folder.zip")
            zip_folder(extract_path, output_zip)

            return send_file(output_zip, as_attachment=True)

        return jsonify({"error": "No zip file provided"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/submit', methods=['POST'])
def submit_form():
    if request.method == 'POST':
        # Retrieve form data
        name = request.form['name']
        email = request.form['email']
        subject = request.form['subject']
        message = request.form['message']
        
        # Debug: Print form data to console
        print(f"Name: {name}")
        print(f"Email: {email}")
        print(f"Subject: {subject}")
        print(f"Message: {message}")
        
        # Simulate a success response
        flash("Your message has been sent. Thank you!")
        return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)
