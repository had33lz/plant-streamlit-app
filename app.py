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