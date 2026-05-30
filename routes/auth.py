from flask import Blueprint, request, jsonify, session
from functools import wraps
from database.db import db
from database.models import User, Patient, Doctor
from supabase_cloud import get_supabase
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth_api", __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized. Please log in first."}), 401
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Unauthorized. Please log in first."}), 401
            if session.get("role") not in allowed_roles:
                return jsonify({"error": "Forbidden. Insufficient permissions."}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route("/api/auth/signup", methods=["POST"])
def signup():
    """
    Register a new user (PATIENT, DOCTOR, or ADMIN).
    Payload: { "email": "x@y.com", "password": "...", "role": "PATIENT", "name": "..." }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "PATIENT").upper()
    # Enforce capital first letters for every starting word in Name field
    name = data.get("name", "New User").strip().title()

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    if role not in ["PATIENT", "DOCTOR", "ADMIN"]:
        return jsonify({"error": "Invalid role."}), 400

    # 1. Check if user already exists locally
    existing = User.query.filter_by(email=email).first()
    if existing:
        return jsonify({"error": "User with this email already exists."}), 400

    # 2. Try Supabase Auth first (if active)
    supabase = get_supabase()
    supabase_uid = None
    if supabase:
        try:
            sb_resp = supabase.auth.sign_up({"email": email, "password": password})
            if sb_resp and sb_resp.user:
                supabase_uid = sb_resp.user.id
                logger.info(f"Supabase Auth registered user: {email} (UID: {supabase_uid})")
        except Exception as e:
            logger.error(f"Supabase Auth registration failed: {e}")

    # 3. Create local user
    try:
        user = User(email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()  # get user.id

        # 4. Create profile
        if role == "PATIENT":
            # Generate patient_id like P001, P002...
            patient_count = Patient.query.count()
            p_id = f"P{patient_count + 1:03d}"
            
            # Enforce capital first letters for every starting word in Gender field
            gender = data.get("gender", "Other").strip().title()
            
            patient = Patient(
                patient_id=p_id,
                name=name,
                user_id=user.id,
                age=data.get("age", 35),
                gender=gender
            )
            db.session.add(patient)
            logger.info(f"Created Patient profile: {p_id}")
        elif role == "DOCTOR":
            # Enforce capital first letters for specialty
            specialty = data.get("specialty", "General Medicine").strip().title()
            
            doctor = Doctor(
                name=name,
                user_id=user.id,
                specialty=specialty
            )
            db.session.add(doctor)
            logger.info(f"Created Doctor profile: {name}")

        db.session.commit()

        return jsonify({
            "success": True,
            "message": "User registered successfully.",
            "user": user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Database error during signup: {e}")
        return jsonify({"error": "Internal server error occurred."}), 500


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """
    Log in a user.
    Payload: { "email": "x@y.com", "password": "..." }
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    # 1. Retrieve user locally
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    # 2. Authenticate with Supabase if active
    supabase = get_supabase()
    if supabase:
        try:
            supabase.auth.sign_in_with_password({"email": email, "password": password})
            logger.info(f"Supabase Auth login succeeded for {email}")
        except Exception as e:
            logger.warning(f"Supabase login bypassed or failed: {e}")

    # 3. Store session
    session["user_id"] = user.id
    session["role"] = user.role
    session["email"] = user.email

    patient_id = None
    if user.role == "PATIENT" and user.patient_profile:
        patient_id = user.patient_profile.patient_id
        session["patient_id"] = patient_id
    elif user.role == "DOCTOR" and user.doctor_profile:
        session["doctor_id"] = user.doctor_profile.id

    resp = {
        "success": True,
        "user": user.to_dict()
    }
    if patient_id:
        resp["patient_id"] = patient_id

    return jsonify(resp)


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """Log out current user."""
    # 1. Supabase Signout if active
    supabase = get_supabase()
    if supabase:
        try:
            supabase.auth.sign_out()
        except Exception as e:
            logger.warning(f"Supabase sign_out exception: {e}")

    # 2. Clear Flask Session
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully."})


@auth_bp.route("/api/auth/session", methods=["GET"])
def get_session():
    """Return active session user profile if authenticated."""
    if "user_id" not in session:
        return jsonify({"authenticated": False}), 200

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"authenticated": False}), 200

    res = {
        "authenticated": True,
        "user": user.to_dict(),
    }

    if user.role == "PATIENT" and user.patient_profile:
        res["patient"] = user.patient_profile.to_dict()
    elif user.role == "DOCTOR" and user.doctor_profile:
        res["doctor"] = user.doctor_profile.to_dict()

    return jsonify(res)
