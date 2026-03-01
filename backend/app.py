import os
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder="../frontend/dist", static_url_path="")
app.secret_key = secrets.token_hex(32)

CORS(app, supports_credentials=True)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_ALBUMS = os.path.join(BASE_DIR, "frontend", "uploads", "albums")
UPLOAD_PHOTOS = os.path.join(BASE_DIR, "frontend", "uploads", "photos")

os.makedirs(UPLOAD_ALBUMS, exist_ok=True)
os.makedirs(UPLOAD_PHOTOS, exist_ok=True)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{os.path.join(BASE_DIR, 'gallery.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

db = SQLAlchemy(app)

ADMIN_PASSWORD = "st3fan0"
IP_REGISTRATION_LIMIT = 2
IP_REGISTRATION_COOLDOWN = 12

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def optimize_image(input_path, output_path, max_width=1920, quality=85):
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        if img.width > max_width:
            ratio = max_width / img.width
            new_height = int(img.height * ratio)
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        img.save(output_path, "JPEG", quality=quality, optimize=True)


def create_thumbnail(input_path, output_path, width=400):
    with Image.open(input_path) as img:
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        ratio = width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((width, new_height), Image.Resampling.LANCZOS)

        img.save(output_path, "JPEG", quality=80, optimize=True)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)

    return decorated_function


class Album(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), unique=True, nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    cover_image = db.Column(db.String(500))
    short_description = db.Column(db.String(50))
    full_description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    photos = db.relationship(
        "Photo", backref="album", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "slug": self.slug,
            "cover_image": self.cover_image,
            "short_description": self.short_description,
            "full_description": self.full_description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "photo_count": len(self.photos),
        }


class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    album_id = db.Column(db.Integer, db.ForeignKey("album.id"), nullable=False)
    filename = db.Column(db.String(500))
    optimized_filename = db.Column(db.String(500))
    thumbnail_filename = db.Column(db.String(500))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ratings = db.relationship(
        "Rating", backref="photo", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        avg_rating = (
            sum(r.score for r in self.ratings) / len(self.ratings)
            if self.ratings
            else 0
        )
        return {
            "id": self.id,
            "album_id": self.album_id,
            "filename": self.optimized_filename,
            "thumbnail": self.thumbnail_filename,
            "title": self.title,
            "description": self.description,
            "average_rating": round(avg_rating, 1),
            "rating_count": len(self.ratings),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ratings = db.relationship("Rating", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    photo_id = db.Column(db.Integer, db.ForeignKey("photo.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("photo_id", "user_id", name="unique_rating"),)


class IPRegistration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(50), nullable=False)
    last_registration = db.Column(db.DateTime, default=datetime.utcnow)
    accounts_created = db.Column(db.Integer, default=1)


def create_slug(title):
    slug = title.lower()
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
    slug = "-".join(filter(None, slug.split("-")))
    return slug[:200]


@app.route("/uploads/albums/<path:filename>")
def serve_album_cover(filename):
    return send_from_directory(UPLOAD_ALBUMS, filename)


@app.route("/uploads/photos/<path:filename>")
def serve_photo(filename):
    return send_from_directory(UPLOAD_PHOTOS, filename)


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/album/<path:path>")
def album_catchall(path):
    return send_from_directory(app.static_folder, "index.html")


@app.route("/panel")
def panel():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/panel/<path:path>")
def panel_catchall(path):
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    if path.startswith("api/"):
        return jsonify({"error": "Not found"}), 404
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/albums", methods=["GET"])
def get_albums():
    albums = Album.query.order_by(Album.created_at.desc()).all()
    return jsonify([album.to_dict() for album in albums])


@app.route("/api/albums/<slug>", methods=["GET"])
def get_album(slug):
    album = Album.query.filter_by(slug=slug).first()
    if not album:
        return jsonify({"error": "Album not found"}), 404

    photos = (
        Photo.query.filter_by(album_id=album.id).order_by(Photo.created_at.desc()).all()
    )

    return jsonify(
        {"album": album.to_dict(), "photos": [photo.to_dict() for photo in photos]}
    )


@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    if data.get("password") == ADMIN_PASSWORD:
        session["admin_authenticated"] = True
        return jsonify({"success": True})
    return jsonify({"error": "Invalid password"}), 401


@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_authenticated", None)
    return jsonify({"success": True})


@app.route("/api/admin/albums", methods=["POST"])
@admin_required
def create_album():
    data = request.form
    title = data.get("title")
    short_description = data.get("short_description", "")[:50]
    full_description = data.get("full_description") or ""

    if not title:
        return jsonify({"error": "Title is required"}), 400

    slug = create_slug(title)
    original_slug = slug
    counter = 1
    while Album.query.filter_by(slug=slug).first():
        slug = f"{original_slug}-{counter}"
        counter += 1

    cover_image = None
    if "cover" in request.files:
        file = request.files["cover"]
        if file and allowed_file(file.filename):
            filename = f"{slug}_{secrets.token_hex(8)}.{file.filename.rsplit('.', 1)[1].lower()}"
            filepath = os.path.join(UPLOAD_ALBUMS, filename)

            temp_path = os.path.join(UPLOAD_ALBUMS, f"temp_{filename}")
            file.save(temp_path)

            optimize_image(temp_path, filepath)
            os.remove(temp_path)

            cover_image = filename

    album = Album(
        title=title,
        slug=slug,
        cover_image=cover_image,
        short_description=short_description,
        full_description=full_description,
    )

    db.session.add(album)
    db.session.commit()

    return jsonify(album.to_dict())


@app.route("/api/admin/albums/<int:id>", methods=["PUT"])
@admin_required
def update_album(id):
    album = Album.query.get(id)
    if not album:
        return jsonify({"error": "Album not found"}), 404

    data = request.form

    if "title" in data:
        album.title = data["title"]
        new_slug = create_slug(data["title"])
        if new_slug != album.slug:
            original_slug = new_slug
            counter = 1
            while Album.query.filter(Album.slug == new_slug, Album.id != id).first():
                new_slug = f"{original_slug}-{counter}"
                counter += 1
            album.slug = new_slug

    if "short_description" in data:
        album.short_description = data["short_description"][:50]

    if "full_description" in data:
        album.full_description = data["full_description"]

    if "cover" in request.files:
        file = request.files["cover"]
        if file and allowed_file(file.filename):
            if album.cover_image:
                old_path = os.path.join(UPLOAD_ALBUMS, album.cover_image)
                if os.path.exists(old_path):
                    os.remove(old_path)

            filename = f"{album.slug}_{secrets.token_hex(8)}.{file.filename.rsplit('.', 1)[1].lower()}"
            filepath = os.path.join(UPLOAD_ALBUMS, filename)

            temp_path = os.path.join(UPLOAD_ALBUMS, f"temp_{filename}")
            file.save(temp_path)

            optimize_image(temp_path, filepath)
            os.remove(temp_path)

            album.cover_image = filename

    db.session.commit()
    return jsonify(album.to_dict())


@app.route("/api/admin/albums/<int:id>", methods=["DELETE"])
@admin_required
def delete_album(id):
    album = Album.query.get(id)
    if not album:
        return jsonify({"error": "Album not found"}), 404

    for photo in album.photos:
        if photo.optimized_filename:
            photo_path = os.path.join(UPLOAD_PHOTOS, photo.optimized_filename)
            if os.path.exists(photo_path):
                os.remove(photo_path)
        if photo.thumbnail_filename:
            thumb_path = os.path.join(UPLOAD_PHOTOS, photo.thumbnail_filename)
            if os.path.exists(thumb_path):
                os.remove(thumb_path)

    if album.cover_image:
        cover_path = os.path.join(UPLOAD_ALBUMS, album.cover_image)
        if os.path.exists(cover_path):
            os.remove(cover_path)

    db.session.delete(album)
    db.session.commit()

    return jsonify({"success": True})


@app.route("/api/admin/photos", methods=["POST"])
@admin_required
def upload_photo():
    album_id = request.form.get("album_id")
    title = request.form.get("title", "")
    description = request.form.get("description", "")

    if not album_id:
        return jsonify({"error": "Album ID is required"}), 400

    album = Album.query.get(album_id)
    if not album:
        return jsonify({"error": "Album not found"}), 404

    if "photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400

    file = request.files["photo"]
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    original_filename = file.filename
    ext = original_filename.rsplit(".", 1)[1].lower()
    base_filename = secrets.token_hex(12)

    optimized_filename = f"{base_filename}_optimized.jpg"
    thumbnail_filename = f"{base_filename}_thumb.jpg"

    temp_path = os.path.join(UPLOAD_PHOTOS, f"temp_{base_filename}.{ext}")
    file.save(temp_path)

    optimized_path = os.path.join(UPLOAD_PHOTOS, optimized_filename)
    thumbnail_path = os.path.join(UPLOAD_PHOTOS, thumbnail_filename)

    optimize_image(temp_path, optimized_path)
    create_thumbnail(temp_path, thumbnail_path)

    os.remove(temp_path)

    photo = Photo(
        album_id=album_id,
        filename=original_filename,
        optimized_filename=optimized_filename,
        thumbnail_filename=thumbnail_filename,
        title=title if title else None,
        description=description if description else None,
    )

    db.session.add(photo)
    db.session.commit()

    return jsonify(photo.to_dict())


@app.route("/api/admin/photos/<int:id>", methods=["PUT"])
@admin_required
def update_photo(id):
    photo = Photo.query.get(id)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    data = request.form

    if "title" in data:
        photo.title = data["title"] if data["title"] else None
    if "description" in data:
        photo.description = data["description"] if data["description"] else None

    db.session.commit()
    return jsonify(photo.to_dict())


@app.route("/api/admin/photos/<int:id>", methods=["DELETE"])
@admin_required
def delete_photo(id):
    photo = Photo.query.get(id)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    if photo.optimized_filename:
        path = os.path.join(UPLOAD_PHOTOS, photo.optimized_filename)
        if os.path.exists(path):
            os.remove(path)

    if photo.thumbnail_filename:
        thumb_path = os.path.join(UPLOAD_PHOTOS, photo.thumbnail_filename)
        if os.path.exists(thumb_path):
            os.remove(thumb_path)

    db.session.delete(photo)
    db.session.commit()

    return jsonify({"success": True})


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")
    ip_address = request.remote_addr

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400

    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already taken"}), 400

    ip_reg = IPRegistration.query.filter_by(ip_address=ip_address).first()

    if ip_reg:
        if ip_reg.accounts_created >= IP_REGISTRATION_LIMIT:
            cooldown_end = ip_reg.last_registration + timedelta(
                hours=IP_REGISTRATION_COOLDOWN
            )
            if datetime.utcnow() < cooldown_end:
                remaining = (cooldown_end - datetime.utcnow()).total_seconds() / 3600
                return jsonify(
                    {"error": f"IP limit reached. Try again in {remaining:.1f} hours"}
                ), 429

        ip_reg.accounts_created += 1
        ip_reg.last_registration = datetime.utcnow()
    else:
        ip_reg = IPRegistration(ip_address=ip_address, accounts_created=1)
        db.session.add(ip_reg)

    user = User(username=username, ip_address=ip_address)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    token = secrets.token_hex(32)
    session[f"user_{user.id}"] = token

    return jsonify(
        {
            "success": True,
            "user": {"id": user.id, "username": user.username},
            "token": token,
        }
    )


@app.route("/api/login", methods=["POST"])
def user_login():
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    token = secrets.token_hex(32)
    session[f"user_{user.id}"] = token

    return jsonify(
        {
            "success": True,
            "user": {"id": user.id, "username": user.username},
            "token": token,
        }
    )


@app.route("/api/rate", methods=["POST"])
def rate_photo():
    user_id = request.headers.get("X-User-ID")
    token = request.headers.get("X-Token")

    if not user_id or not token:
        return jsonify({"error": "Authentication required"}), 401

    if not session.get(f"user_{user_id}") == token:
        return jsonify({"error": "Invalid session"}), 401

    data = request.get_json()
    photo_id = data.get("photo_id")
    score = data.get("score")

    if not photo_id or not score:
        return jsonify({"error": "Photo ID and score required"}), 400

    if score < 1 or score > 5:
        return jsonify({"error": "Score must be between 1 and 5"}), 400

    photo = Photo.query.get(photo_id)
    if not photo:
        return jsonify({"error": "Photo not found"}), 404

    rating = Rating.query.filter_by(photo_id=photo_id, user_id=user_id).first()

    if rating:
        rating.score = score
    else:
        rating = Rating(photo_id=photo_id, user_id=user_id, score=score)
        db.session.add(rating)

    db.session.commit()

    avg_rating = sum(r.score for r in photo.ratings) / len(photo.ratings)

    return jsonify(
        {
            "success": True,
            "average_rating": round(avg_rating, 1),
            "rating_count": len(photo.ratings),
        }
    )


@app.route("/api/check-auth", methods=["GET"])
def check_auth():
    user_id = request.headers.get("X-User-ID")
    token = request.headers.get("X-Token")

    if user_id and token and session.get(f"user_{user_id}") == token:
        user = User.query.get(user_id)
        if user:
            return jsonify(
                {
                    "authenticated": True,
                    "user": {"id": user.id, "username": user.username},
                }
            )

    return jsonify({"authenticated": False})


@app.route("/api/admin/status", methods=["GET"])
def admin_status():
    return jsonify({"authenticated": session.get("admin_authenticated", False)})


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=21523, debug=True)
