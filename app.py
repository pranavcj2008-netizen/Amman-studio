from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os, datetime, json

app = Flask(__name__)
app.secret_key = "amman_studio_secret_2024"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///amman_studio.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join("static", "images")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

db = SQLAlchemy(app)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# ─── Models ───────────────────────────────────────────────
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(200), default="default.jpg")
    featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"))
    service = db.relationship("Service", backref="bookings")
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending")
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"))
    service = db.relationship("Service", backref="reviews")
    approved = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# ─── Helpers ──────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

# ─── Frontend Routes ──────────────────────────────────────
@app.route("/")
def index():
    featured = Service.query.filter_by(featured=True).limit(6).all()
    reviews = Review.query.filter_by(approved=True).order_by(Review.created_at.desc()).limit(6).all()
    return render_template("index.html", featured=featured, reviews=reviews)

@app.route("/services")
def services():
    category = request.args.get("category", "all")
    if category == "all":
        all_services = Service.query.all()
    else:
        all_services = Service.query.filter_by(category=category).all()
    categories = db.session.query(Service.category).distinct().all()
    categories = [c[0] for c in categories]
    return render_template("services.html", services=all_services, categories=categories, active=category)

@app.route("/service/<int:id>")
def service_detail(id):
    svc = Service.query.get_or_404(id)
    reviews = Review.query.filter_by(service_id=id, approved=True).all()
    return render_template("service_detail.html", service=svc, reviews=reviews)

@app.route("/help")
def help_center():
    return render_template("help.html")

@app.route("/booking", methods=["GET", "POST"])
def booking():
    services = Service.query.all()
    if request.method == "POST":
        b = Booking(
            name=request.form["name"],
            email=request.form["email"],
            phone=request.form["phone"],
            service_id=request.form["service_id"],
            message=request.form.get("message", "")
        )
        db.session.add(b)
        db.session.commit()
        return jsonify({"success": True, "message": "Booking confirmed! We'll contact you soon."})
    return render_template("booking.html", services=services)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        c = Contact(
            name=request.form["name"],
            email=request.form["email"],
            subject=request.form.get("subject", ""),
            message=request.form["message"]
        )
        db.session.add(c)
        db.session.commit()
        return jsonify({"success": True, "message": "Message sent! We'll reply within 24 hours."})
    return render_template("contact.html")

@app.route("/review", methods=["POST"])
def add_review():
    r = Review(
        name=request.form["name"],
        rating=int(request.form["rating"]),
        comment=request.form["comment"],
        service_id=request.form.get("service_id")
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({"success": True, "message": "Thank you for your review!"})

# ─── API ──────────────────────────────────────────────────
@app.route("/api/services")
def api_services():
    services = Service.query.all()
    return jsonify([{
        "id": s.id, "name": s.name, "description": s.description,
        "price": s.price, "category": s.category, "image": s.image, "featured": s.featured
    } for s in services])

# ─── Admin Routes ─────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin = Admin.query.filter_by(username=request.form["username"]).first()
        if admin and check_password_hash(admin.password, request.form["password"]):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("admin/login.html", error="Invalid credentials")
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    stats = {
        "services": Service.query.count(),
        "bookings": Booking.query.count(),
        "contacts": Contact.query.count(),
        "reviews": Review.query.count(),
        "pending": Booking.query.filter_by(status="pending").count()
    }
    recent_bookings = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, recent_bookings=recent_bookings)

@app.route("/admin/services", methods=["GET", "POST"])
@admin_required
def admin_services():
    if request.method == "POST":
        image_filename = "default.jpg"
        if "image" in request.files:
            file = request.files["image"]
            if file and allowed_file(file.filename):
                image_filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], image_filename))
        s = Service(
            name=request.form["name"],
            description=request.form["description"],
            price=float(request.form["price"]),
            category=request.form["category"],
            image=image_filename,
            featured="featured" in request.form
        )
        db.session.add(s)
        db.session.commit()
        return redirect(url_for("admin_services"))
    services = Service.query.all()
    return render_template("admin/services.html", services=services)

@app.route("/admin/services/delete/<int:id>")
@admin_required
def delete_service(id):
    s = Service.query.get_or_404(id)
    db.session.delete(s)
    db.session.commit()
    return redirect(url_for("admin_services"))

@app.route("/admin/services/edit/<int:id>", methods=["GET", "POST"])
@admin_required
def edit_service(id):
    s = Service.query.get_or_404(id)
    if request.method == "POST":
        s.name = request.form.get("name", s.name)
        s.price = float(request.form.get("price", s.price))
        s.description = request.form.get("description", s.description)
        s.category = request.form.get("category", s.category)
        s.featured = request.form.get("featured") == "on"
        db.session.commit()
        return redirect(url_for("admin_services"))
    return redirect(url_for("admin_services"))

@app.route("/admin/services/update-price/<int:id>", methods=["POST"])
@admin_required
def update_price(id):
    s = Service.query.get_or_404(id)
    s.price = float(request.form.get("price", s.price))
    db.session.commit()
    return jsonify({"success": True, "price": s.price})

@app.route("/admin/bookings")
@admin_required
def admin_bookings():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template("admin/bookings.html", bookings=bookings)

@app.route("/admin/bookings/status/<int:id>/<status>")
@admin_required
def update_booking_status(id, status):
    b = Booking.query.get_or_404(id)
    b.status = status
    db.session.commit()
    return redirect(url_for("admin_bookings"))

@app.route("/admin/contacts")
@admin_required
def admin_contacts():
    contacts = Contact.query.order_by(Contact.created_at.desc()).all()
    return render_template("admin/contacts.html", contacts=contacts)

@app.route("/admin/reviews")
@admin_required
def admin_reviews():
    reviews = Review.query.order_by(Review.created_at.desc()).all()
    return render_template("admin/reviews.html", reviews=reviews)

# ─── Init ─────────────────────────────────────────────────
def init_db():
    with app.app_context():
        db.create_all()
        if not Admin.query.first():
            db.session.add(Admin(username="admin", password=generate_password_hash("amman2024")))
        if not Service.query.first():
            sample_services = [
                Service(name="Photography Session", description="Professional photography for events, portraits, and products.", price=2500, category="Photography", featured=True),
                Service(name="Video Editing", description="High quality video editing with effects, transitions and color grading.", price=1500, category="Video", featured=True),
                Service(name="Logo Design", description="Creative and unique logo design for your brand.", price=999, category="Design", featured=True),
                Service(name="Website Design", description="Modern, responsive website design and development.", price=5000, category="Web", featured=True),
                Service(name="Social Media Post", description="Eye-catching social media graphics and content.", price=500, category="Design", featured=False),
                Service(name="Wedding Photography", description="Complete wedding photography and videography package.", price=15000, category="Photography", featured=True),
            ]
            db.session.add_all(sample_services)
        db.session.commit()

if __name__ == "__main__":
    os.makedirs(os.path.join("static", "images"), exist_ok=True)
    init_db()
    print("\nAmman Studio is running!")
    print("  Website  -> http://localhost:5000")
    print("  Admin    -> http://localhost:5000/admin/login")
    print("  Login    -> admin / amman2024\n")
    app.run(debug=True, port=5000)
