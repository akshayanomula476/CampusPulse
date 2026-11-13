
import os
from dotenv import load_dotenv

load_dotenv()

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from supabase import create_client
from config import supabase


# ==========================================
# FLASK CONFIGURATION
# ==========================================

app = Flask(__name__)

app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY is missing from .env")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("FLASK_HTTPS", "false").lower() == "true"
)


# ==========================================
# SUPABASE CONFIGURATION
# ==========================================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase configuration is missing.")


# ==========================================
# USER SUPABASE CLIENT
# ==========================================

def get_user_supabase():

    access_token = session.get("access_token")

    if not access_token:
        raise ValueError("Session expired. Please log in again.")

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.postgrest.auth(access_token)

    return client


# ==========================================
# HOMEPAGE
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================
# STUDENT REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        student_id = request.form.get("student_id", "").strip()
        department = request.form.get("department", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([full_name, email, student_id, department,
                    password, confirm_password]):

            return render_template(
                "register.html",
                message="Please fill in all fields."
            )

        if len(password) < 8:
            return render_template(
                "register.html",
                message="Password must contain at least 8 characters."
            )

        if password != confirm_password:
            return render_template(
                "register.html",
                message="Passwords do not match."
            )

        try:

            response = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "student_id": student_id,
                        "department": department
                    }
                }
            })

            if response.user is None:
                return render_template(
                    "register.html",
                    message="Registration could not be completed."
                )

            return render_template(
                "register.html",
                message="Registration successful! Please check your email if confirmation is required."
            )

        except Exception as e:

            print("Registration error:", str(e))

            return render_template(
                "register.html",
                message="Registration failed. Please check your details."
            )

    return render_template("register.html", message=None)


# ==========================================
# STUDENT LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template(
                "login.html",
                message="Please enter your email and password."
            )

        try:

            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.user and response.session:

                session.clear()

                session["user_id"] = response.user.id
                session["email"] = response.user.email
                session["access_token"] = response.session.access_token
                session["refresh_token"] = response.session.refresh_token

                return redirect(url_for("student_dashboard"))

            return render_template(
                "login.html",
                message="Login failed. Please try again."
            )

        except Exception as e:

            print("Login error:", str(e))

            return render_template(
                "login.html",
                message="Invalid email or password, or email confirmation is required."
            )

    return render_template("login.html", message=None)


# ==========================================
# STUDENT DASHBOARD
# ==========================================

@app.route("/student-dashboard")
def student_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    try:

        user_supabase = get_user_supabase()

        response = user_supabase.table("complaints").select("*").eq(
            "user_id", session["user_id"]
        ).order("created_at", desc=True).execute()

        complaints = response.data or []

        total = len(complaints)

        pending = sum(
            1 for c in complaints
            if (c.get("status") or "Pending").strip().lower() == "pending"
        )

        in_progress = sum(
            1 for c in complaints
            if (c.get("status") or "Pending").strip().lower() == "in progress"
        )

        resolved = sum(
            1 for c in complaints
            if (c.get("status") or "Pending").strip().lower() == "resolved"
        )

        return render_template(
            "student_dashboard.html",
            email=session.get("email"),
            complaints=complaints,
            total=total,
            pending=pending,
            in_progress=in_progress,
            resolved=resolved,
            message=None
        )

    except Exception as e:

        print("Student dashboard error:", str(e))

        return render_template(
            "student_dashboard.html",
            email=session.get("email"),
            complaints=[],
            total=0,
            pending=0,
            in_progress=0,
            resolved=0,
            message="Unable to load complaints. Please log in again."
        )


# ==========================================
# REPORT CAMPUS ISSUE
# ==========================================

@app.route("/report-issue", methods=["GET", "POST"])
def report_issue():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()

        if not all([title, description, location]):
            return render_template(
                "report_issue.html",
                message="Please fill in all required fields."
            )

        try:

            user_supabase = get_user_supabase()

            user_supabase.table("complaints").insert({
                "user_id": session["user_id"],
                "title": title,
                "description": description,
                "location": location,
                "status": "Pending",
                "priority": "Medium"
            }).execute()

            return redirect(url_for("student_dashboard"))

        except Exception as e:

            print("Complaint submission error:", str(e))

            return render_template(
                "report_issue.html",
                message="Complaint submission failed. Please try again."
            )

    return render_template("report_issue.html", message=None)


# ==========================================
# ADMIN AUTHORIZATION
# ==========================================

def is_admin():

    if "user_id" not in session:
        return False

    try:

        user_supabase = get_user_supabase()

        response = user_supabase.table("user_roles").select(
            "role"
        ).eq("user_id", session["user_id"]).execute()

        return any(
            item.get("role") == "admin"
            for item in (response.data or [])
        )

    except Exception as e:

        print("Admin authorization error:", str(e))
        return False


# ==========================================
# ADMIN LOGIN
# ==========================================

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template(
                "admin_login.html",
                message="Please enter email and password."
            )

        try:

            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not response.user or not response.session:
                return render_template(
                    "admin_login.html",
                    message="Invalid login details."
                )

            session.clear()

            session["user_id"] = response.user.id
            session["email"] = response.user.email
            session["access_token"] = response.session.access_token
            session["refresh_token"] = response.session.refresh_token

            if not is_admin():

                session.clear()

                return render_template(
                    "admin_login.html",
                    message="Access denied. Admin account required."
                )

            return redirect(url_for("admin_dashboard"))

        except Exception as e:

            print("Admin login error:", str(e))
            session.clear()

            return render_template(
                "admin_login.html",
                message="Invalid email or password."
            )

    return render_template("admin_login.html", message=None)


# ==========================================
# ADMIN DASHBOARD
# ==========================================

@app.route("/admin-dashboard")
def admin_dashboard():

    if not is_admin():
        return redirect(url_for("admin_login"))

    try:

        user_supabase = get_user_supabase()

        response = user_supabase.table("complaints").select(
            "*"
        ).order("created_at", desc=True).execute()

        complaints = response.data or []

        total = len(complaints)

        pending = sum(
            1 for c in complaints
            if (c.get("status") or "Pending").strip().lower() == "pending"
        )

        in_progress = sum(
            1 for c in complaints
            if (c.get("status") or "Pending").strip().lower() == "in progress"
        )

        resolved = sum(
            1 for c in complaints
            if (c.get("status") or "Pending").strip().lower() == "resolved"
        )

        return render_template(
            "admin_dashboard.html",
            complaints=complaints,
            total=total,
            pending=pending,
            in_progress=in_progress,
            resolved=resolved,
            message=None
        )

    except Exception as e:

        print("Admin dashboard error:", str(e))

        return render_template(
            "admin_dashboard.html",
            complaints=[],
            total=0,
            pending=0,
            in_progress=0,
            resolved=0,
            message="Unable to load complaints. Check database permissions."
        )


# ==========================================
# UPDATE COMPLAINT
# ==========================================

@app.route("/update-complaint", methods=["POST"])
def update_complaint():

    if not is_admin():
        return redirect(url_for("admin_login"))

    complaint_id = request.form.get("complaint_id", "").strip()
    status = request.form.get("status", "").strip()
    priority = request.form.get("priority", "").strip()

    allowed_statuses = ["Pending", "In Progress", "Resolved"]
    allowed_priorities = ["Low", "Medium", "High"]

    if not complaint_id:
        return redirect(url_for("admin_dashboard"))

    if status not in allowed_statuses or priority not in allowed_priorities:
        return redirect(url_for("admin_dashboard"))

    try:

        user_supabase = get_user_supabase()

        print("Updating complaint:", complaint_id)
        print("New status:", status)
        print("New priority:", priority)

        response = user_supabase.table("complaints").update({
            "status": status,
            "priority": priority
        }).eq("id", complaint_id).execute()

        if not response.data:
            print("UPDATE FAILED: No complaint row was updated.")
            return render_template(
                "admin_dashboard.html",
                complaints=[],
                total=0,
                pending=0,
                in_progress=0,
                resolved=0,
                message="Update failed. No complaint was updated. Check Supabase UPDATE permissions."
            )

        print("UPDATE SUCCESS:", response.data)

        return redirect(url_for("admin_dashboard"))

    except Exception as e:

        print("COMPLAINT UPDATE ERROR:", repr(e))

        try:
            user_supabase = get_user_supabase()

            response = user_supabase.table("complaints").select(
                "*"
            ).order("created_at", desc=True).execute()

            complaints = response.data or []

            total = len(complaints)
            pending = sum(1 for c in complaints if c.get("status") == "Pending")
            in_progress = sum(1 for c in complaints if c.get("status") == "In Progress")
            resolved = sum(1 for c in complaints if c.get("status") == "Resolved")

            return render_template(
                "admin_dashboard.html",
                complaints=complaints,
                total=total,
                pending=pending,
                in_progress=in_progress,
                resolved=resolved,
                message="Update failed: " + str(e)
            )

        except Exception as dashboard_error:

            print("Dashboard reload error:", repr(dashboard_error))

            return "Complaint update failed. Check the PowerShell error.", 500


# ==========================================
# ADMIN LOGOUT
# ==========================================

@app.route("/admin-logout")
def admin_logout():

    session.clear()
    return redirect(url_for("admin_login"))


# ==========================================
# STUDENT LOGOUT
# ==========================================

@app.route("/logout", methods=["GET", "POST"])
def logout():

    session.clear()
    return redirect(url_for("login"))


# ==========================================
# ERROR HANDLING
# ==========================================

@app.errorhandler(404)
def page_not_found(error):
    return "Page not found!", 404


@app.errorhandler(500)
def internal_server_error(error):
    return "Internal server error. Please try again.", 500


# ==========================================
# RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(
        debug=os.getenv("FLASK_DEBUG", "false").lower() == "true"
    )
