from models import db, User, DailyRecord
from datetime import date
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User
from flask import abort

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@app.before_first_request
def create_tables():
    db.create_all()

    # إنشاء أدمن مرة واحدة
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/admin")
@login_required
def admin():
    if not current_user.is_admin:
        abort(403)

    users = User.query.all()
    return render_template("admin.html", users=users)
from datetime import date

@app.route("/answer/<question>", methods=["POST"])
@login_required
def answer(question):
    today = date.today()

    existing = DailyRecord.query.filter_by(
        user_id=current_user.id,
        date=today,
        question=question
    ).first()

    if existing:
        return redirect(url_for("dashboard"))

    record = DailyRecord(
        user_id=current_user.id,
        date=today,
        question=question
    )

    current_user.total_points += 5

    db.session.add(record)
    db.session.commit()

    return redirect(url_for("dashboard"))

@app.route("/admin/reset")
@login_required
def reset():
    if not current_user.is_admin:
        abort(403)

    for user in User.query.all():
        user.total_points = 0

    DailyRecord.query.delete()
    db.session.commit()

    return redirect(url_for("admin"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])

        if User.query.filter_by(username=username).first():
            flash("الاسم موجود بالفعل")
            return redirect(url_for("register"))

        user = User(username=username, password_hash=password)
        db.session.add(user)
        db.session.commit()

        flash("تم إنشاء الحساب")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form["username"]).first()

        if user and check_password_hash(user.password_hash, request.form["password"]):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("بيانات الدخول غلط")

    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    today = date.today()

    # كل الأسئلة اللي جاوبها المستخدم النهارده
    answered_questions = DailyRecord.query.filter_by(
        user_id=current_user.id,
        date=today
    ).all()

    # نحولهم لقائمة أسماء
    answered = [record.question for record in answered_questions]

    # قائمة الأسئلة المتاحة
    questions = {
        "zuhr": "صليت الظهر",
        "asr": "صليت العصر",
        "maghrib": "صليت المغرب",
        "tasbeeh": "سبحت 100 مرة",
        "quran": "قرأت قرآن"
    }

    return render_template(
        "dashboard.html",
        questions=questions,
        answered=answered
    )

@app.route("/admin/leaderboard")
@login_required
def admin_leaderboard():
    if not current_user.is_admin:
        abort(403)

    users = User.query.order_by(User.total_points.desc()).all()
    return render_template("leaderboard.html", users=users)
    