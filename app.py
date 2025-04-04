from flask import Flask, render_template, request,jsonify,redirect, url_for
import pytesseract
import cv2
import os
import numpy as np
import requests
import re
from werkzeug.utils import secure_filename
from collections import OrderedDict

pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def preprocess_image(image_path):
    image = cv2.imread(image_path)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    alpha = 1.8  
    beta = 20    
    contrast = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)

    blur = cv2.GaussianBlur(contrast, (3, 3), 0)

    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    kernel = np.ones((2,2), np.uint8)
    processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

    cv2.imwrite("processed_debug.png", processed)

    return processed
   

def extract_text(image_path):
    processed_image = preprocess_image(image_path)
    temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed.png')
    cv2.imwrite(temp_path, processed_image)  
    text = pytesseract.image_to_string(processed_image, config='--psm 11')
    return text.strip()


def split_into_unique_words(text):
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    words = text.split()
    unique_words=list(OrderedDict.fromkeys(words))
    print("\nCleaned Unique Words:\n", unique_words)

    return unique_words


@app.route('/scanner', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'imageInput' not in request.files:
            return redirect(request.url)
        file = request.files['imageInput']
        if file.filename == '':
            return redirect(request.url)
        
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            extracted_text = extract_text(file_path)
            listDisplayed=split_into_unique_words(extracted_text)
            return render_template('scanner.html',result=listDisplayed)
    
    return render_template('scanner.html', result=None)


def get_coordinates(location):
    geocode_url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(location)}&format=json"
    headers = {'User-Agent': 'Mozilla/5.0 (MyPharmacyApp/1.0)'}
    response = requests.get(geocode_url, headers=headers)
    
    if response.status_code == 200 and response.json():
        result = response.json()[0]
        return float(result["lat"]), float(result["lon"])
    return None, None

# Get nearby pharmacies using Overpass API
def fetch_nearby_medical_stores(lat, lon):
    query = f"""
        [out:json];
        node["amenity"="pharmacy"](around:5000,{lat},{lon});
        out;
    """
    url = "https://overpass-api.de/api/interpreter?data=" + requests.utils.quote(query)
    headers = {'User-Agent': 'Mozilla/5.0 (MyPharmacyApp/1.0)'}
    response = requests.get(url, headers=headers)
    
    try:
        data = response.json()
        pharmacies = [{
            "name": elem.get("tags", {}).get("name", "Unnamed Pharmacy"),
            "lat": elem.get("lat"),
            "lon": elem.get("lon")
        } for elem in data.get("elements", [])]
        return pharmacies
    except:
        return []

@app.route('/stores', methods=['GET', 'POST'])
def gettingPharmacy():
    pharmacies = []
    error = None

    if request.method == 'POST':
        location = request.form.get('location')
        if location:
            lat, lon = get_coordinates(location)
            if lat and lon:
                pharmacies = fetch_nearby_medical_stores(lat, lon)
                if not pharmacies:
                    error = "No pharmacies found nearby."
            else:
                error = "Location not found."
        else:
            error = "Please enter a location."

    return render_template('stores.html', pharmacies=pharmacies, error=error)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/scanner")
def scanner_page():
    return render_template("scanner.html")





@app.route("/stores")
def stores_page():
    return render_template("stores.html")


@app.route("/contact")
def contact_page():
    return render_template("contact.html")

if __name__ == '__main__':
    app.run(debug=True)






