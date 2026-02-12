from werkzeug.utils import secure_filename
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from skin_analysis import detect_skin_tone
from prompt_builder import build_prompt
from ai_engine import generate_recommendation
from shopping_service import match_products

import os
import re
from urllib.parse import quote_plus

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


# ----------------- USER MODEL -----------------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def get_budget_limit(budget):
    if budget == "Low":
        return 2000
    elif budget == "Medium":
        return 6000
    else:
        return 20000


def fallback_queries(style_mode, gender, occasion):
    g = (gender or "").strip().lower()
    o = (occasion or "").strip().lower()

    if style_mode == "Ethnic":
        if o == "wedding":
            clothing = "designer lehenga" if g == "female" else "sherwani set"
        else:
            clothing = "kurta set" if g == "female" else "kurta pajama set"

        footwear = "ethnic jutti" if g == "female" else "mojari shoes"
        jewellery = "jhumka earrings" if g == "female" else "analog watch"
    else:
        if o == "office":
            clothing = "formal blazer with trousers"
        elif o == "party":
            clothing = "party dress" if g == "female" else "casual blazer"
        else:
            clothing = "smart casual outfit"

        footwear = "heels" if g == "female" else "sneakers"
        jewellery = "minimal jewellery" if g == "female" else "watch"

    return {
        "CLOTHING": clothing,
        "FOOTWEAR": footwear,
        "JEWELLERY": jewellery
    }


def fill_missing_products(products, queries, budget_limit, gender):
    gender_term = "women" if (gender or "").strip().lower() == "female" else "men"
    image_by_category = {
        "CLOTHING": "/static/product_images/shirt.webp",
        "FOOTWEAR": "/static/product_images/heels.webp",
        "JEWELLERY": "/static/product_images/blazer.jpg.webp",
    }

    suggestions_by_category = {
        "CLOTHING": ["Kurta Set", "Co-ord Set", "Printed Shirt"],
        "FOOTWEAR": ["Classic Sneakers", "Ethnic Juttis", "Block Heels"],
        "JEWELLERY": ["Minimal Earrings", "Statement Necklace", "Bracelet Set"],
    }

    for category in ["CLOTHING", "FOOTWEAR", "JEWELLERY"]:
        if products.get(category):
            continue

        query = (queries.get(category) or category.title()).strip()
        suggestions = []
        for item_name in suggestions_by_category[category]:
            search = f"{query} {item_name} {gender_term} under {budget_limit} INR"
            link = "https://www.google.com/search?tbm=shop&q=" + quote_plus(search)
            suggestions.append({
                "name": item_name,
                "brand": "StyleSense Pick",
                "price": f"Under INR {budget_limit}",
                "image": image_by_category[category],
                "link": link,
            })

        products[category] = suggestions

    return products


# ----------------- ROUTES -----------------

@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials")

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=current_user.username)


@app.route("/analyze", methods=["POST"])
@login_required
def analyze():

    import base64
    from datetime import datetime

    upload_folder = os.path.join("static", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    captured_image = request.form.get("captured_image")
    uploaded_file = request.files.get("uploaded_image")

    # CASE 1: Webcam capture
    if captured_image:
        header, encoded = captured_image.split(",", 1)
        image_data = base64.b64decode(encoded)

        filename = f"capture_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        upload_path = os.path.join(upload_folder, filename)

        with open(upload_path, "wb") as f:
            f.write(image_data)

    # CASE 2: File upload
    elif uploaded_file and uploaded_file.filename != "":
        filename = secure_filename(uploaded_file.filename)
        upload_path = os.path.join(upload_folder, filename)
        uploaded_file.save(upload_path)

    # CASE 3: Nothing provided
    else:
        return "Please capture or upload an image."


    # -------------------------
    # Get Form Values
    # -------------------------
    gender = request.form.get("gender")
    occasion = request.form.get("occasion")
    mood = request.form.get("mood")
    weather = request.form.get("weather")
    budget = request.form.get("budget")

    # -------------------------
    # Detect Skin Tone
    # -------------------------
    result = detect_skin_tone(upload_path)
    if isinstance(result, str):
        result = {"tone": "Unknown", "rgb": (0, 0, 0), "note": result}
    skin_tone = result["tone"]

    budget_limit = get_budget_limit(budget)

    # -------------------------
    # Strong & Safe AI Parser
    # -------------------------
    def parse_recommendation(recommendation):

        styling_text = (recommendation or "").strip()
        structured_queries = {}

        if not recommendation:
            return styling_text, structured_queries

        marker = re.search(r"shopping[\s_-]*keywords\s*:?", recommendation, flags=re.IGNORECASE)
        if not marker:
            return styling_text, structured_queries

        styling_text = recommendation[:marker.start()].strip() or styling_text
        shopping_section = recommendation[marker.end():]

        lines = shopping_section.split("\n")
        category_map = {
            "CLOTHING": "CLOTHING",
            "CLOTHES": "CLOTHING",
            "OUTFIT": "CLOTHING",
            "FOOTWEAR": "FOOTWEAR",
            "SHOES": "FOOTWEAR",
            "JEWELLERY": "JEWELLERY",
            "JEWELRY": "JEWELLERY",
            "ACCESSORY": "ACCESSORY",
            "ACCESSORIES": "ACCESSORY",
        }

        for line in lines:
            line = line.strip().lstrip("-*").strip()
            if not line:
                continue

            if ":" in line:
                category, value = line.split(":", 1)
            elif "-" in line:
                category, value = line.split("-", 1)
            else:
                continue

            raw_category = category.strip().upper().replace(" ", "").replace("_", "")
            value = value.strip().strip('"').strip("'")
            category = category_map.get(raw_category, category_map.get(raw_category.rstrip("S"), ""))

            if category and value:
                structured_queries[category] = value

        return styling_text, structured_queries

    # -------------------------
    # Generate Ethnic
    # -------------------------
    prompt_ethnic = build_prompt(
        skin_tone,
        gender,
        occasion,
        mood,
        weather,
        budget,
        "Ethnic"
    )

    recommendation_ethnic = generate_recommendation(prompt_ethnic)
    styling_ethnic, queries_ethnic = parse_recommendation(recommendation_ethnic)
    defaults_ethnic = fallback_queries("Ethnic", gender, occasion)
    for key, default_value in defaults_ethnic.items():
        queries_ethnic.setdefault(key, default_value)

    products_ethnic = match_products(queries_ethnic, budget_limit, gender)
    products_ethnic = fill_missing_products(products_ethnic, queries_ethnic, budget_limit, gender)

    # -------------------------
    # Generate Western
    # -------------------------
    prompt_western = build_prompt(
        skin_tone,
        gender,
        occasion,
        mood,
        weather,
        budget,
        "Western"
    )

    recommendation_western = generate_recommendation(prompt_western)
    styling_western, queries_western = parse_recommendation(recommendation_western)
    defaults_western = fallback_queries("Western", gender, occasion)
    for key, default_value in defaults_western.items():
        queries_western.setdefault(key, default_value)

    products_western = match_products(queries_western, budget_limit, gender)
    products_western = fill_missing_products(products_western, queries_western, budget_limit, gender)

    # -------------------------
    # Render Results
    # -------------------------
    return render_template(
        "results.html",
        result=result,
        image=filename,
        styling_ethnic=styling_ethnic,
        styling_western=styling_western,
        products_ethnic=products_ethnic,
        products_western=products_western
    )


    recommendation_ethnic = generate_recommendation(prompt_ethnic)
    styling_ethnic, queries_ethnic = parse_recommendation(recommendation_ethnic)

    print("ETHNIC QUERIES:", queries_ethnic)  # Debug

    products_ethnic = match_products(queries_ethnic, budget_limit, gender)
    print("ETHNIC PRODUCTS:", products_ethnic)
    


    # -------------------------
    # Generate Western
    # -------------------------
    prompt_western = build_prompt(
        skin_tone,
        gender,
        occasion,
        mood,
        weather,
        budget,
        "Western"
    )

    recommendation_western = generate_recommendation(prompt_western)
    styling_western, queries_western = parse_recommendation(recommendation_western)

    print("WESTERN QUERIES:", queries_western)  # Debug

    products_western = match_products(queries_western, budget_limit, gender)
    print("WESTERN PRODUCTS:", products_western)

    return render_template(
        "results.html",
        result=result,
        image=filename,
        styling_ethnic=styling_ethnic,
        styling_western=styling_western,
        products_ethnic=products_ethnic,
        products_western=products_western
    )


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
