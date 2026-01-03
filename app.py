import re
import hashlib
from datetime import date
from io import BytesIO

import pandas as pd
import pymysql
import streamlit as st



# CONFIG ------------------


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root",
    "database": "plantlog_db",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

SEASONS = ["Winter", "Spring", "Summer", "Autumn"]
STATUSES = ["Seed", "Sprout", "Growing", "Flowering", "Harvested"]
LOCATIONS = ["Indoor", "Outdoor", "Pot", "Ground"]





# DB --------------------
def get_conn():
    return pymysql.connect(**DB_CONFIG)


def init_db():
    sql = """
    CREATE TABLE IF NOT EXISTS users (
      id INT AUTO_INCREMENT PRIMARY KEY,
      email VARCHAR(120) NOT NULL UNIQUE,
      password_hash CHAR(64) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS plant_logs (
      id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT NOT NULL,
      plant_name VARCHAR(120) NOT NULL,
      planting_date DATE NOT NULL,
      season ENUM('Winter','Spring','Summer','Autumn') NOT NULL,
      status ENUM('Seed','Sprout','Growing','Flowering','Harvested') NOT NULL,
      location ENUM('Indoor','Outdoor','Pot','Ground') NOT NULL,
      notes TEXT,
      photo LONGBLOB NULL,
      photo_mime VARCHAR(40) NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
    conn = get_conn()
    with conn.cursor() as cur:
        for statement in sql.split(";"):
            s = statement.strip()
            if s:
                cur.execute(s)
    conn.close()



    # SECURITY HELPERS
# -----------------------------
def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def is_strong_password(pw: str) -> bool:
    if len(pw) < 8:
        return False
    if not re.search(r"[A-Z]", pw):
        return False
    if not re.search(r"[0-9]", pw):
        return False
    if not re.search(r"[^A-Za-z0-9]", pw):
        return False
    return True


# -----------------------------
# AUTH
# -----------------------------
def register_user(email: str, password: str) -> tuple[bool, str]:
    if not email or "@" not in email:
        return False, "Enter a valid email."
    if not is_strong_password(password):
        return False, "Password must be 8+ chars with uppercase, number, and special character."

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                return False, "Email already exists. Login instead."
            cur.execute(
                "INSERT INTO users(email, password_hash) VALUES(%s, %s)",
                (email, sha256_hash(password)),
            )
        return True, "Account created. You can login now."
    finally:
        conn.close()


def login_user(email: str, password: str) -> tuple[bool, str]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE email=%s", (email,))
            row = cur.fetchone()
            if not row:
                return False, "User not found."
            if row["password_hash"] != sha256_hash(password):
                return False, "Wrong password."
            st.session_state["user_id"] = row["id"]
            st.session_state["user_email"] = email
            return True, "Logged in."
    finally:
        conn.close()


def logout():
    st.session_state.pop("user_id", None)
    st.session_state.pop("user_email", None)


