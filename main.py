from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime
import sqlite3, string, random

app = FastAPI(title="Wetlinks – URL Shortener")
templates = Jinja2Templates(directory="templates")
DB_PATH = "wetlinks.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                long_url TEXT NOT NULL,
                short_code TEXT UNIQUE NOT NULL,
                clicks INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
init_db()

def generate_short_code(length: int = 6) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url

@app.get("/")
def home(request: Request):
    context = {"request": request, "short_url": None, "error": None, "stats": None}
    return templates.TemplateResponse("index.html", context)

@app.post("/shorten")
def shorten_url(request: Request, long_url: str = Form(...), customcode: str = Form(None)):
    long_url = normalize_url(long_url)
    conn = get_db()
    cursor = conn.cursor()
    if customcode:
        exists = cursor.execute("SELECT 1 FROM urls WHERE short_code=?", (customcode,)).fetchone()
        if exists:
            context = {"request": request, "error": "Custom code already in use!", "short_url": None, "stats": None}
            return templates.TemplateResponse("index.html", context)
        short_code = customcode
    else:
        short_code = generate_short_code()
        while cursor.execute("SELECT 1 FROM urls WHERE short_code=?", (short_code,)).fetchone():
            short_code = generate_short_code()
    cursor.execute(
        "INSERT INTO urls (long_url, short_code, created_at) VALUES (?, ?, ?)",
        (long_url, short_code, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    short_url = f"https://wetlinks-url-shortener.onrender.com/{short_code}"
    context = {"request": request, "short_url": short_url, "error": None, "stats": None}
    return templates.TemplateResponse("index.html", context)

@app.get("/{short_code}")
def redirect_url(short_code: str):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT long_url, clicks FROM urls WHERE short_code=?", (short_code,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="URL not found")
    long_url, clicks = row["long_url"], row["clicks"]
    cursor.execute("UPDATE urls SET clicks=? WHERE short_code=?", (clicks + 1, short_code))
    conn.commit()
    conn.close()
    return RedirectResponse(long_url)

@app.get("/stats/{short_code}")
def url_stats(request: Request, short_code: str):
    conn = get_db()
    cursor = conn.cursor()
    row = cursor.execute("SELECT long_url, clicks, created_at FROM urls WHERE short_code=?", (short_code,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="URL not found")
    stats = {"short_code": short_code, "long_url": row["long_url"], "clicks": row["clicks"], "created_at": row["created_at"]}
    context = {"request": request, "short_url": None, "error": None, "stats": stats}
    return templates.TemplateResponse("stats.html", context)
