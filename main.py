from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import string, random
from datetime import datetime

# FastAPI app & templates

app = FastAPI(title="Wetlinks")
templates = Jinja2Templates(directory="templates")


# SQLite database setup

conn = sqlite3.connect("wetlinks.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    long_url TEXT NOT NULL,
    short_code TEXT UNIQUE NOT NULL,
    clicks INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
)
""")
conn.commit()


# Helper function

def generate_short_code(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Routes
@app.get("/")
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/shorten")
def shorten_url(request: Request, long_url: str = Form(...), customcode: str = Form(None)):
    short_code = customcode if customcode else generate_short_code()

    while cursor.execute("SELECT * FROM urls WHERE short_code=?", (short_code,)).fetchone():
        short_code = generate_short_code()

    cursor.execute(
        "INSERT INTO urls (long_url, short_code, created_at) VALUES (?, ?, ?)",
        (long_url, short_code, datetime.utcnow().isoformat())
    )
    conn.commit()

    return templates.TemplateResponse("index.html", {"request": request, "short_url": f"https://wetlinks-url-shortener.onrender.com/{short_code}"})


@app.get("/{short_code}")
def redirect_url(short_code: str):
    row = cursor.execute("SELECT long_url, clicks FROM urls WHERE short_code=?", (short_code,)).fetchone()
    if row:
        long_url, clicks = row
        cursor.execute("UPDATE urls SET clicks=? WHERE short_code=?", (clicks + 1, short_code))
        conn.commit()
        return RedirectResponse(long_url)
    else:
        raise HTTPException(status_code=404, detail="URL NOT FOUND")

@app.get("/stats/{short_code}")
def url_stats(request: Request, short_code: str):
    row = cursor.execute("SELECT long_url, clicks, created_at FROM urls WHERE short_code=?", (short_code,)).fetchone()
    if row:
        long_url, clicks, created_at = row
        return templates.TemplateResponse("index.html", {"request": request, "stats": {"long_url": long_url, "clicks": clicks, "created_at": created_at}})
    else:
        raise HTTPException(status_code=404, detail="URL not found")
