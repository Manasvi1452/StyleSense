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
    skin_tone = result["tone"]

    budget_limit = get_budget_limit(budget)

    # -------------------------
    # Strong & Safe AI Parser
    # -------------------------
    def parse_recommendation(recommendation):

        styling_text = recommendation
        structured_queries = {}

        if "SHOPPING_KEYWORDS" not in recommendation:
            return styling_text, structured_queries

        parts = recommendation.split("SHOPPING_KEYWORDS")
        styling_text = parts[0].strip()
        shopping_section = parts[1]

        lines = shopping_section.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if ":" in line:
                category, value = line.split(":", 1)
            elif "-" in line:
                category, value = line.split("-", 1)
            else:
                continue

            category = category.strip().upper()
            value = value.strip()

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

    products_ethnic = match_products(queries_ethnic, budget_limit, gender)

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

    products_western = match_products(queries_western, budget_limit, gender)

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
