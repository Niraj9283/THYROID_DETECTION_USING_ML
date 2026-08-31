"""
ThyroScan — Database Layer
SQLite schema with clean SQL execution, migration, and CRUD helpers.
Compatible with standard relational DB design (ready for PostgreSQL).
"""

import sqlite3
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.environ.get('VERCEL'):
    DB_PATH = '/tmp/thyroscan.db'
else:
    DB_PATH = os.path.join(BASE_DIR, '..', 'data', 'thyroscan.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)



def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'patient',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    """)

    # Patient Profiles Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS patient_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        age INTEGER,
        sex INTEGER,
        height_cm REAL,
        weight_kg REAL,
        bmi REAL,
        medical_notes TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Assessments / Screenings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        assessment_type TEXT DEFAULT 'comprehensive',
        screening_result TEXT NOT NULL,
        risk_level TEXT NOT NULL,
        model_probability REAL NOT NULL,
        class_probabilities TEXT NOT NULL,
        biomarker_analysis TEXT,
        inputs_json TEXT NOT NULL,
        model_version TEXT DEFAULT 'v1.0',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """)

    # Chat Sessions & History Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        citations_json TEXT,
        is_emergency INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()


# Initialize database schema immediately on import
init_db()
