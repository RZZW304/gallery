from flask import Flask, render_template, send_from_directory, abort
import os

app = Flask(__name__)

PHOTO_DIR = "photos"

# lista albumów
def list_albums():
    return [d for d in os.listdir(PHOTO_DIR) if os.path.isdir(os.path.join(PHOTO_DIR, d))]

# lista zdjęć w albumie
def list_photos(album):
    album_path = os.path.join(PHOTO_DIR, album)
    if not os.path.exists(album_path):
        return []
    return sorted([f for f in os.listdir(album_path) if f.lower().endswith((".jpg",".jpeg",".png",".gif",".webp"))])

@app.route("/")
def index():
    albums = list_albums()
    return render_template("index.html", albums=albums)

@app.route("/album/<album_name>")
def album(album_name):
    photos = list_photos(album_name)
    if not photos:
        abort(404)
    return render_template("album.html", album=album_name, photos=photos)

@app.route("/photos/<album>/<filename>")
def photos(album, filename):
    return send_from_directory(os.path.join(PHOTO_DIR, album), filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)