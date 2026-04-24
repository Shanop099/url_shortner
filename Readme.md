# 🔗 URL Shortener (Flask + Redis)

A full-stack URL shortening service built with Flask, Redis, and SQLite. Supports custom URLs, expiry links, QR code generation, rate limiting, and real-time analytics.

---

## 🚀 Features

- 🔗 Shorten long URLs instantly  
- ✏️ Custom short URLs (user-defined codes)  
- ⏱️ Expiry-based links  
- ⚡ Redis caching for fast redirection  
- 🚦 Rate limiting using Redis  
- 📊 Click tracking (real-time analytics)  
- 📱 QR code generation & download  
- 🎨 Glassmorphism UI  

---

## 🧠 Tech Stack

- Backend: Flask (Python)  
- Database: SQLite  
- Cache & Rate Limiting: Redis  
- Frontend: HTML, CSS, JavaScript  
- Deployment: Render  

---

## 📁 Project Structure

url-shortener/
├── app.py  
├── database.py  
├── utils.py  
├── requirements.txt  
├── Procfile  
├── templates/  
│   └── index.html  
└── urls.db  

---

## ⚙️ Setup & Run Locally

1. Clone the repo  
git clone https://github.com/your-username/url-shortener.git  
cd url-shortener  

2. Install dependencies  
pip install -r requirements.txt  

3. Start Redis  
redis-server  

4. Run the app  
python app.py  

5. Open in browser  
http://127.0.0.1:5000/  

---

## 📡 API Endpoints

Create Short URL  
POST /shorten  

Example:
{
  "url": "https://example.com",
  "custom": "mycode",
  "expiry": 10
}

Redirect  
GET /<short_code>  

Stats  
GET /stats/<short_code>  

Example response:
{
  "db_clicks": 2,
  "redis_clicks": 5
}

---

## 🌐 Deployment (Render)

- Create Web Service on Render  
- Add Redis service  
- Set environment variables:

REDIS_URL = <your-redis-url>  
BASE_URL = https://your-app-name.onrender.com/  

---

## 🧪 Example

Input:  https://google.com  
Output: https://your-app.onrender.com/abc123  

---

## 🧠 System Design Highlights

- Cache-aside pattern (Redis + DB)  
- TTL-based rate limiting  
- Unique ID generation with collision handling  
- Graceful fallback when Redis is unavailable  

---

## 📌 Future Improvements

- User authentication  
- Dashboard for managing links  
- Custom domain support  
- Analytics graphs  

---

## 👨‍💻 Author

Ishan Gupta  
IIIT Nagpur  

---

## ⭐ If you like this project

Give it a ⭐ on GitHub!
