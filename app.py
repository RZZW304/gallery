from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

PHOTO_DIR = "photos"

def list_photos():
    files = []
    for file in os.listdir(PHOTO_DIR):
        if file.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            files.append(file)
    files.sort(reverse=True)
    return files


@app.route("/")
def index():
    photos = list_photos()
    return render_template("index.html", photos=photos)


@app.route("/photos/<path:filename>")
def photos(filename):
    return send_from_directory(PHOTO_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)