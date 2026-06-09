# main.py - Complete with Search, Trending System, Promotion Icon, and @wa_guan Account

from fastapi import FastAPI, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import hashlib
import secrets
import uuid
import json
import base64
import httpx
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
import os
import re
from collections import defaultdict

# ===== BANNED WORDS CONFIGURATION =====
BANNED_WORDS = {
    'kill', 'bomb', 'have sex', 'porn', 'cum', 'fuck', 'penis', 'dick', 'blow job',
    'ass', 'boob', 'butt', 'bullets', 'guns', 'weapon', 'pussy', 'tits', 'titties',
    'doggy', 'yansh', 'yash', 'prick', 'toto', 'homosexual', 'gay', 'terrorist',
    'lgbt', 'lgbtq+', 'bitch', 'whore', 'slut', 'ugly', 'retard', 'vagina',
    'clitoris', 'seggs', 'prostitute', 'cocaine', 'crack cocaine', 'booty', 'nigga',
    'nigger', 'zionist', 'heroin', 'meth', 'weed', 'marijuana', 'cannabis', 'suicide',
    'suicidal', 'shoot', 'obidiots', 'slave', 'died', 'queer', 'transgender',
    'intersex', 'abortion', 'sexual', 'orgasm', 'nipple', 'onlyfans', 'sex worker',
    'stripper', 'lingerie', 'rape', 'sexual assault', 'pedophile', 'nazi', 'swastika',
    'hitler', 'jews', 'lesbian'
}

BANNED_PATTERN = re.compile(r'\b(' + '|'.join(re.escape(word) for word in BANNED_WORDS) + r')\b', re.IGNORECASE)

def contains_banned_words(text: str) -> bool:
    if not text:
        return False
    return bool(BANNED_PATTERN.search(text))

def filter_banned_words(text: str) -> str:
    if not text:
        return text
    def replace_word(match):
        return '*' * len(match.group(0))
    return BANNED_PATTERN.sub(replace_word, text)

# ===== PROMOTION SYSTEM =====
class PromotionRequest(BaseModel):
    talo_id: str
    amount: float
    payment_method: str

# ===== PAYPAL CONFIGURATION =====
PAYPAL_EMAIL = 'victor_uwafo@yahoo.com'

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GuAn - Microblogging Platform")

# Setup paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ===== JSONBINBRO API CONFIGURATION =====
API_BASE = 'https://jsonbinbro.onrender.com/api'
BIN_ID = '6a1c737827e57e6773a47627'
USER_ID = 'Admin01'
API_KEY = 'admin_97375e28712d7627e7cea67c8c86d60d'

PAYSTACK_PUBLIC_KEY = 'pk_live_2018244c913523ab0751249b240bc3e3448c3c19'
SUPER_ADMIN_ID = "Adminxx01"
SUPER_ADMIN_PASSWORD = "kijiXmart4140#"

# ===== WA_GUAN ACCOUNT CONFIGURATION =====
WA_GUAN_USER_ID = "wa_guan"
WA_GUAN_FIRST_NAME = "Support"
WA_GUAN_LAST_NAME = "GuAn"
WA_GUAN_EMAIL = "support@guan.com"

async def ensure_wa_guan_account():
    """Ensure the @wa_guan support account exists"""
    data = await get_jsonbin_data()
    
    # Check if wa_guan account exists
    wa_guan_exists = False
    for user in data.get("users", []):
        if user.get("user_id") == WA_GUAN_USER_ID:
            wa_guan_exists = True
            break
    
    if not wa_guan_exists:
        new_user = {
            "id": str(uuid.uuid4()),
            "user_id": WA_GUAN_USER_ID,
            "email": WA_GUAN_EMAIL,
            "first_name": WA_GUAN_FIRST_NAME,
            "last_name": WA_GUAN_LAST_NAME,
            "password_hash": hash_password("support123"),
            "gender": "Male",
            "age": 25,
            "country": "Nigeria",
            "profile_photo": None,
            "background_image": None,
            "is_active": True,
            "is_premium": True,
            "user_category": "Support",
            "followers_count": 0,
            "following_count": 0,
            "talos_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "bio": "Official Support Account for GuAn Microblogging Platform"
        }
        data["users"].append(new_user)
        
        # Create welcome post
        welcome_content = "Wa guan. 👋 Welcome to GuAn! Connect with others of like minds by following them and being followed. Stay positive, objective, and truthful with your posts. Together we build a great community! #WelcomeToGuAn #StayPositive"
        
        talo = {
            "id": str(uuid.uuid4()),
            "user_id": WA_GUAN_USER_ID,
            "content": welcome_content,
            "photos": [],
            "likes": 0,
            "dislikes": 0,
            "retalos": 0,
            "reply_count": 0,
            "created_at": datetime.now().isoformat(),
            "promoted": True,
            "promotion_level": 1,
            "is_welcome": True
        }
        
        if "talos" not in data:
            data["talos"] = []
        data["talos"].insert(0, talo)
        
        await save_jsonbin_data(data)
        logger.info(f"Created @{WA_GUAN_USER_ID} support account with welcome post")

async def get_jsonbin_data() -> Dict:
    """Fetch data from jsonbinbro API"""
    try:
        url = f"{API_BASE}/bins/{BIN_ID}?api_key={API_KEY}"
        logger.info(f"Attempting to fetch data from: {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            
            logger.info(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if 'data' in result:
                    data_content = result['data']
                    if isinstance(data_content, dict):
                        collections = ["users", "talos", "replies", "admins", "likes", 
                                      "dislikes", "retalos", "follows", "blocks", 
                                      "payments", "notifications", "adverts", "premium_requests",
                                      "promotions", "word_trends"]
                        for col in collections:
                            if col not in data_content:
                                data_content[col] = []
                        return data_content
                    else:
                        return {
                            "users": [], "talos": [], "replies": [], "admins": [],
                            "likes": [], "dislikes": [], "retalos": [], "follows": [],
                            "blocks": [], "payments": [], "notifications": [], "adverts": [],
                            "premium_requests": [], "promotions": [], "word_trends": []
                        }
                else:
                    return result
            elif response.status_code == 404:
                logger.warning("Bin not found, creating initial data structure")
                initial_data = {
                    "users": [], "talos": [], "replies": [], "admins": [],
                    "likes": [], "dislikes": [], "retalos": [], "follows": [],
                    "blocks": [], "payments": [], "notifications": [], "adverts": [],
                    "premium_requests": [], "promotions": [], "word_trends": []
                }
                await save_jsonbin_data(initial_data)
                return initial_data
            else:
                raise HTTPException(status_code=503, detail=f"API error: Status {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Unable to access API: {str(e)}")

async def save_jsonbin_data(data: Dict) -> bool:
    """Save data to jsonbinbro API"""
    try:
        payload = {
            "data": data,
            "name": "GuAn Microblogging Platform",
            "is_private": False
        }
        
        url = f"{API_BASE}/bins/{BIN_ID}?api_key={API_KEY}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                logger.info("Data saved successfully")
                return True
            else:
                raise HTTPException(status_code=503, detail=f"Failed to save: Status {response.status_code}")
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Unable to save: {str(e)}")

# Helper functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def generate_token():
    return secrets.token_urlsafe(32)

# Models
class UserSignup(BaseModel):
    email: str
    user_id: str
    first_name: str
    last_name: str
    password: str
    gender: str
    age: int
    country: str

class UserLogin(BaseModel):
    user_id: str
    password: str

class CreateTaloRequest(BaseModel):
    content: str
    photos: List[Dict[str, str]] = []

class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    profile_photo_url: Optional[str] = None
    profile_photo_path: Optional[str] = None

class CreateAdminRequest(BaseModel):
    admin_id: str
    password: str
    name: str

# ===== TRENDING WORDS SYSTEM =====
def update_word_trends(talo_content: str, talo_created_at: str, data: Dict):
    """Update trending words tracking"""
    words = re.findall(r'\b\w+\b', talo_content.lower())
    hashtags = [w for w in words if w.startswith('#')]
    
    if "word_trends" not in data:
        data["word_trends"] = []
    
    for word in hashtags + words[:10]:  # Track hashtags and top regular words
        data["word_trends"].append({
            "word": word,
            "timestamp": talo_created_at,
            "is_hashtag": word.startswith('#')
        })

def get_trending_words(data: Dict) -> List[tuple]:
    """Get trending words (appear in >=10% of posts in last 3 hours)"""
    three_hours_ago = (datetime.now() - timedelta(hours=3)).isoformat()
    
    # Get recent posts from last 3 hours
    recent_talos = [t for t in data.get("talos", []) 
                   if t.get("created_at", "") > three_hours_ago]
    
    if not recent_talos:
        return []
    
    total_posts = len(recent_talos)
    threshold = max(1, int(total_posts * 0.1))  # 10% threshold
    
    # Count word frequencies
    word_count = defaultdict(int)
    for talo in recent_talos:
        words = re.findall(r'\b\w+\b', talo.get("content", "").lower())
        # Track unique words per post to avoid skew
        unique_words = set(words)
        for word in unique_words:
            if len(word) > 2:  # Ignore very short words
                word_count[word] += 1
    
    # Filter by threshold and sort
    trending = [(word, count) for word, count in word_count.items() 
                if count >= threshold]
    trending.sort(key=lambda x: x[1], reverse=True)
    
    return trending[:15]  # Return top 15 trending words

# ===== SEARCH SYSTEM =====
async def search_posts_and_users(search_query: str, data: Dict) -> Dict:
    """Search for posts and users based on query"""
    query_lower = search_query.lower().strip()
    
    # Search in posts
    matched_posts = []
    for talo in data.get("talos", []):
        content_lower = talo.get("content", "").lower()
        if query_lower in content_lower:
            # Add user info
            for user in data.get("users", []):
                if user["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{user['first_name']} {user['last_name']}"
                    talo["user_photo"] = user.get("profile_photo")
                    break
            talo["reply_count"] = len([r for r in data.get("replies", []) 
                                       if r.get("parent_talo_id") == talo["id"]])
            matched_posts.append(talo)
    
    # Search in users (by user_id or name)
    matched_users = []
    for user in data.get("users", []):
        user_id_lower = user.get("user_id", "").lower()
        name_lower = f"{user.get('first_name', '')} {user.get('last_name', '')}".lower()
        if query_lower in user_id_lower or query_lower in name_lower:
            matched_users.append({
                "user_id": user["user_id"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "profile_photo": user.get("profile_photo"),
                "followers_count": user.get("followers_count", 0)
            })
    
    # Sort posts by date (newest first)
    matched_posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "posts": matched_posts[:50],
        "users": matched_users[:20],
        "total_posts": len(matched_posts),
        "total_users": len(matched_users)
    }

# ===== ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    session_token = request.cookies.get("session_token")
    user = None
    
    if session_token:
        try:
            data = await get_jsonbin_data()
            for u in data.get("users", []):
                if u.get("session_token") == session_token:
                    user = u
                    break
        except HTTPException:
            pass
    
    return templates.TemplateResponse("index.html", {"request": request, "user": user})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/api/signup")
async def api_signup(user_data: UserSignup):
    data = await get_jsonbin_data()
    
    if user_data.age < 18:
        raise HTTPException(status_code=400, detail="You must be 18 or older")
    
    for user in data.get("users", []):
        if user["user_id"] == user_data.user_id:
            raise HTTPException(status_code=400, detail="User ID already exists")
        if user["email"] == user_data.email:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    new_user = {
        "id": str(uuid.uuid4()),
        "user_id": user_data.user_id,
        "email": user_data.email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "password_hash": hash_password(user_data.password),
        "gender": user_data.gender,
        "age": user_data.age,
        "country": user_data.country,
        "profile_photo": None,
        "background_image": None,
        "is_active": True,
        "is_premium": False,
        "user_category": "Normal",
        "followers_count": 0,
        "following_count": 0,
        "talos_count": 0,
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat()
    }
    
    if "users" not in data:
        data["users"] = []
    data["users"].append(new_user)
    await save_jsonbin_data(data)
    
    # Auto-follow wa_guan for new users
    for user in data.get("users", []):
        if user["user_id"] == WA_GUAN_USER_ID:
            if "follows" not in data:
                data["follows"] = []
            data["follows"].append({
                "follower_id": user_data.user_id,
                "following_id": WA_GUAN_USER_ID,
                "created_at": datetime.now().isoformat()
            })
            user["followers_count"] = user.get("followers_count", 0) + 1
            await save_jsonbin_data(data)
            break
    
    return {"message": "User created successfully", "user_id": user_data.user_id}

@app.post("/api/login")
async def api_login(login_data: UserLogin):
    data = await get_jsonbin_data()
    
    # Ensure wa_guan account exists
    await ensure_wa_guan_account()
    data = await get_jsonbin_data()  # Refresh data
    
    if login_data.user_id == SUPER_ADMIN_ID and login_data.password == SUPER_ADMIN_PASSWORD:
        token = generate_token()
        
        super_admin_exists = False
        for admin in data.get("admins", []):
            if admin.get("user_id") == SUPER_ADMIN_ID:
                super_admin_exists = True
                admin["session_token"] = token
                admin["last_login"] = datetime.now().isoformat()
                break
        
        if not super_admin_exists:
            if "admins" not in data:
                data["admins"] = []
            data["admins"].append({
                "user_id": SUPER_ADMIN_ID,
                "name": "Super Administrator",
                "role": "super_admin",
                "session_token": token,
                "created_at": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat()
            })
        
        await save_jsonbin_data(data)
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="session_token", value=token, httponly=True)
        return response
    
    for admin in data.get("admins", []):
        if admin["user_id"] == login_data.user_id and verify_password(login_data.password, admin.get("password_hash", "")):
            if not admin.get("is_active", True):
                raise HTTPException(status_code=403, detail="Admin account deactivated")
            token = generate_token()
            admin["session_token"] = token
            admin["last_login"] = datetime.now().isoformat()
            await save_jsonbin_data(data)
            response = RedirectResponse(url="/admin", status_code=303)
            response.set_cookie(key="session_token", value=token, httponly=True)
            return response
    
    for user in data.get("users", []):
        if user["user_id"] == login_data.user_id and verify_password(login_data.password, user["password_hash"]):
            if not user.get("is_active"):
                raise HTTPException(status_code=403, detail="Account deactivated")
            token = generate_token()
            user["session_token"] = token
            user["last_active"] = datetime.now().isoformat()
            await save_jsonbin_data(data)
            response = RedirectResponse(url="/dashboard", status_code=303)
            response.set_cookie(key="session_token", value=token, httponly=True)
            return response
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/", status_code=303)
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        for admin in data.get("admins", []):
            if admin.get("session_token") == session_token:
                return RedirectResponse(url="/admin", status_code=303)
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session_token")
        return response
    
    user["last_active"] = datetime.now().isoformat()
    await save_jsonbin_data(data)
    
    # Get personalized feed (posts from followed users + own posts)
    followed_user_ids = set()
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_user_ids.add(follow.get("following_id"))
    followed_user_ids.add(user["user_id"])
    
    talos = data.get("talos", [])
    personal_talos = []
    
    for talo in talos:
        if talo["user_id"] in followed_user_ids or talo.get("promoted", False):
            for u in data.get("users", []):
                if u["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                    talo["user_photo"] = u.get("profile_photo")
                    break
            talo["reply_count"] = len([r for r in data.get("replies", []) if r.get("parent_talo_id") == talo["id"]])
            personal_talos.append(talo)
    
    # Sort with promoted posts first, then by date
    def sort_priority(talo):
        promotion_boost = 1000000 if talo.get("promoted", False) else 0
        created_at = datetime.fromisoformat(talo.get("created_at", datetime.now().isoformat()))
        return (created_at.timestamp() + promotion_boost)
    
    personal_talos.sort(key=sort_priority, reverse=True)
    
    # Get trending words (from all posts, not just followed)
    trending = get_trending_words(data)
    
    active_users = len([u for u in data.get("users", []) if u.get("last_active", "") > (datetime.now() - timedelta(days=1)).isoformat()])
    
    notifications = [n for n in data.get("notifications", []) if n.get("user_id") == user["user_id"]]
    unread_notifications = len([n for n in notifications if not n.get("read", False)])
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "talos": personal_talos[:50],
        "trending": trending,
        "active_users": active_users,
        "unread_notifications": unread_notifications,
        "paystack_public_key": PAYSTACK_PUBLIC_KEY
    })

# ===== SEARCH ENDPOINT =====
@app.get("/api/search")
async def search_global(request: Request, q: str = ""):
    """Global search for posts and users"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not q or len(q.strip()) < 2:
        return {"posts": [], "users": [], "total_posts": 0, "total_users": 0}
    
    data = await get_jsonbin_data()
    
    # Check if searching for @username
    if q.startswith('@'):
        search_term = q[1:].lower()
        # Search for user
        matched_users = []
        for user in data.get("users", []):
            if search_term in user.get("user_id", "").lower():
                matched_users.append({
                    "user_id": user["user_id"],
                    "first_name": user["first_name"],
                    "last_name": user["last_name"],
                    "profile_photo": user.get("profile_photo"),
                    "followers_count": user.get("followers_count", 0)
                })
        
        # Get posts from that user
        matched_posts = []
        for talo in data.get("talos", []):
            if talo["user_id"].lower() == search_term:
                for user in data.get("users", []):
                    if user["user_id"] == talo["user_id"]:
                        talo["user_name"] = f"{user['first_name']} {user['last_name']}"
                        talo["user_photo"] = user.get("profile_photo")
                        break
                talo["reply_count"] = len([r for r in data.get("replies", []) if r.get("parent_talo_id") == talo["id"]])
                matched_posts.append(talo)
        
        matched_posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return {
            "posts": matched_posts[:50],
            "users": matched_users[:20],
            "total_posts": len(matched_posts),
            "total_users": len(matched_users)
        }
    else:
        # Regular text search
        return await search_posts_and_users(q, data)

@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    """Search results page"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/", status_code=303)
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session_token")
        return response
    
    search_results = await search_posts_and_users(q, data) if q else {"posts": [], "users": [], "total_posts": 0, "total_users": 0}
    
    return templates.TemplateResponse("search.html", {
        "request": request,
        "user": user,
        "search_query": q,
        "results": search_results
    })

@app.get("/profile/{user_id}", response_class=HTMLResponse)
async def view_profile(request: Request, user_id: str):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/", status_code=303)
    
    data = await get_jsonbin_data()
    current_user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            current_user = u
            break
    
    if not current_user:
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session_token")
        return response
    
    profile_user = None
    for u in data.get("users", []):
        if u["user_id"] == user_id:
            profile_user = u
            break
    
    if not profile_user:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "User not found"
        })
    
    user_talos = [t for t in data.get("talos", []) if t["user_id"] == user_id]
    replies = data.get("replies", [])
    for talo in user_talos:
        talo["reply_count"] = len([r for r in replies if r.get("parent_talo_id") == talo["id"]])
    
    user_talos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "current_user": current_user,
        "profile_user": profile_user,
        "talos": user_talos[:50]
    })

@app.get("/post/{talo_id}", response_class=HTMLResponse)
async def view_post(request: Request, talo_id: str):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/", status_code=303)
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session_token")
        return response
    
    talo = None
    for t in data.get("talos", []):
        if t["id"] == talo_id:
            talo = t
            break
    
    if not talo:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Post not found"
        })
    
    for u in data.get("users", []):
        if u["user_id"] == talo["user_id"]:
            talo["user_name"] = f"{u['first_name']} {u['last_name']}"
            talo["user_photo"] = u.get("profile_photo")
            break
    
    replies = [r for r in data.get("replies", []) if r.get("parent_talo_id") == talo_id]
    
    for reply in replies:
        for u in data.get("users", []):
            if u["user_id"] == reply["user_id"]:
                reply["user_name"] = f"{u['first_name']} {u['last_name']}"
                reply["user_photo"] = u.get("profile_photo")
                break
    
    replies.sort(key=lambda x: x.get("created_at", ""))
    
    return templates.TemplateResponse("post.html", {
        "request": request,
        "user": user,
        "talo": talo,
        "replies": replies
    })

@app.post("/api/create_talo")
async def create_talo(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    body = await request.json()
    content = body.get("content", "")
    photos = body.get("photos", [])
    
    if contains_banned_words(content):
        raise HTTPException(status_code=400, detail="Your post contains inappropriate language. Please review and try again.")
    
    if len(content) > 250:
        raise HTTPException(status_code=400, detail="Talo cannot exceed 250 characters")
    
    talo = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "content": content,
        "photos": photos,
        "likes": 0,
        "dislikes": 0,
        "retalos": 0,
        "reply_count": 0,
        "created_at": datetime.now().isoformat(),
        "promoted": False,
        "promotion_level": 0
    }
    
    if "talos" not in data:
        data["talos"] = []
    data["talos"].insert(0, talo)
    user["talos_count"] = user.get("talos_count", 0) + 1
    
    # Update word trends for trending system
    update_word_trends(content, talo["created_at"], data)
    
    await save_jsonbin_data(data)
    
    # Create notifications for followers
    followers = []
    for follow in data.get("follows", []):
        if follow.get("following_id") == user["user_id"]:
            followers.append(follow.get("follower_id"))
    
    for follower_id in followers:
        if "notifications" not in data:
            data["notifications"] = []
        
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": follower_id,
            "type": "new_post",
            "message": f"@{user['user_id']} posted a new talo: {content[:50]}...",
            "related_talo_id": talo["id"],
            "from_user_id": user["user_id"],
            "read": False,
            "created_at": datetime.now().isoformat()
        }
        data["notifications"].append(notification)
    
    await save_jsonbin_data(data)
    
    return {"message": "Talo created successfully", "talo_id": talo["id"]}

@app.post("/api/create_reply/{parent_talo_id}")
async def create_reply(request: Request, parent_talo_id: str):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    parent_talo = None
    talo_owner_id = None
    for t in data.get("talos", []):
        if t["id"] == parent_talo_id:
            parent_talo = t
            talo_owner_id = t["user_id"]
            break
    
    if not parent_talo:
        raise HTTPException(status_code=404, detail="Parent post not found")
    
    body = await request.json()
    content = body.get("content", "")
    photo = body.get("photo")
    
    if contains_banned_words(content):
        raise HTTPException(status_code=400, detail="Your reply contains inappropriate language. Please review and try again.")
    
    if not content or len(content) > 250:
        raise HTTPException(status_code=400, detail="Reply must be between 1 and 250 characters")
    
    reply = {
        "id": str(uuid.uuid4()),
        "parent_talo_id": parent_talo_id,
        "user_id": user["user_id"],
        "content": content,
        "photos": [photo] if photo else [],
        "likes": 0,
        "created_at": datetime.now().isoformat()
    }
    
    if "replies" not in data:
        data["replies"] = []
    data["replies"].append(reply)
    
    parent_talo["reply_count"] = len([r for r in data["replies"] if r.get("parent_talo_id") == parent_talo_id])
    
    if talo_owner_id != user["user_id"]:
        if "notifications" not in data:
            data["notifications"] = []
        
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": talo_owner_id,
            "type": "reply",
            "message": f"@{user['user_id']} replied to your post: {content[:50]}...",
            "related_talo_id": parent_talo_id,
            "reply_id": reply["id"],
            "from_user_id": user["user_id"],
            "read": False,
            "created_at": datetime.now().isoformat()
        }
        data["notifications"].append(notification)
    
    await save_jsonbin_data(data)
    
    return {"message": "Reply created successfully", "reply_id": reply["id"]}

@app.post("/api/like/{talo_id}")
async def like_talo(talo_id: str, request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    talo_owner_id = None
    for talo in data["talos"]:
        if talo["id"] == talo_id:
            talo_owner_id = talo["user_id"]
            break
    
    if "likes" not in data:
        data["likes"] = []
    
    like_index = None
    for i, like in enumerate(data["likes"]):
        if like.get("talo_id") == talo_id and like.get("user_id") == user["user_id"]:
            like_index = i
            break
    
    if like_index is not None:
        data["likes"].pop(like_index)
        for talo in data["talos"]:
            if talo["id"] == talo_id:
                talo["likes"] -= 1
                await save_jsonbin_data(data)
                return {"liked": False, "count": talo["likes"]}
    else:
        data["likes"].append({
            "talo_id": talo_id,
            "user_id": user["user_id"],
            "created_at": datetime.now().isoformat()
        })
        
        for talo in data["talos"]:
            if talo["id"] == talo_id:
                talo["likes"] += 1
                
                if talo_owner_id and talo_owner_id != user["user_id"]:
                    if "notifications" not in data:
                        data["notifications"] = []
                    
                    notification = {
                        "id": str(uuid.uuid4()),
                        "user_id": talo_owner_id,
                        "type": "like",
                        "message": f"@{user['user_id']} liked your talo",
                        "related_talo_id": talo_id,
                        "from_user_id": user["user_id"],
                        "read": False,
                        "created_at": datetime.now().isoformat()
                    }
                    data["notifications"].append(notification)
                
                await save_jsonbin_data(data)
                return {"liked": True, "count": talo["likes"]}
    
    await save_jsonbin_data(data)
    return {"liked": False, "count": 0}

@app.post("/api/follow/{user_id_to_follow}")
async def follow_user(user_id_to_follow: str, request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if user["user_id"] == user_id_to_follow:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    target_user = None
    for u in data.get("users", []):
        if u["user_id"] == user_id_to_follow:
            target_user = u
            break
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "follows" not in data:
        data["follows"] = []
    
    follow_index = None
    for i, follow in enumerate(data["follows"]):
        if follow.get("follower_id") == user["user_id"] and follow.get("following_id") == user_id_to_follow:
            follow_index = i
            break
    
    if follow_index is not None:
        data["follows"].pop(follow_index)
        user["following_count"] = max(0, user.get("following_count", 0) - 1)
        target_user["followers_count"] = max(0, target_user.get("followers_count", 0) - 1)
        await save_jsonbin_data(data)
        return {"following": False, "followers_count": target_user["followers_count"]}
    else:
        data["follows"].append({
            "follower_id": user["user_id"],
            "following_id": user_id_to_follow,
            "created_at": datetime.now().isoformat()
        })
        user["following_count"] = user.get("following_count", 0) + 1
        target_user["followers_count"] = target_user.get("followers_count", 0) + 1
        
        if "notifications" not in data:
            data["notifications"] = []
        
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": user_id_to_follow,
            "type": "follow",
            "message": f"@{user['user_id']} started following you",
            "from_user_id": user["user_id"],
            "read": False,
            "created_at": datetime.now().isoformat()
        }
        data["notifications"].append(notification)
        
        await save_jsonbin_data(data)
        return {"following": True, "followers_count": target_user["followers_count"]}

@app.get("/api/get_follow_status/{profile_user_id}")
async def get_follow_status(profile_user_id: str, request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"following": False}
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        return {"following": False}
    
    if "follows" not in data:
        return {"following": False}
    
    for follow in data["follows"]:
        if follow.get("follower_id") == user["user_id"] and follow.get("following_id") == profile_user_id:
            return {"following": True}
    
    return {"following": False}

@app.get("/api/get_followers/{user_id}")
async def get_followers(user_id: str, request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    
    current_user = None
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            current_user = u
            break
    
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
    
    followers = []
    for follow in data.get("follows", []):
        if follow.get("following_id") == user_id:
            for u in data.get("users", []):
                if u["user_id"] == follow["follower_id"]:
                    followers.append({
                        "user_id": u["user_id"],
                        "name": f"{u['first_name']} {u['last_name']}",
                        "profile_photo": u.get("profile_photo")
                    })
                    break
    
    return {"followers": followers}

@app.get("/api/get_following/{user_id}")
async def get_following(user_id: str, request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    
    current_user = None
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            current_user = u
            break
    
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
    
    following = []
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user_id:
            for u in data.get("users", []):
                if u["user_id"] == follow["following_id"]:
                    following.append({
                        "user_id": u["user_id"],
                        "name": f"{u['first_name']} {u['last_name']}",
                        "profile_photo": u.get("profile_photo")
                    })
                    break
    
    return {"following": following}

@app.post("/api/update_profile")
async def update_profile(request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    user = None
    user_index = None
    
    for i, u in enumerate(data.get("users", [])):
        if u.get("session_token") == session_token:
            user = u
            user_index = i
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    form = await request.form()
    
    if "first_name" in form:
        user["first_name"] = form["first_name"]
    if "last_name" in form:
        user["last_name"] = form["last_name"]
    if "bio" in form:
        user["bio"] = form["bio"]
    
    if "profile_photo_url" in form:
        user["profile_photo"] = form["profile_photo_url"]
        if "profile_photo_path" in form:
            user["profile_photo_path"] = form["profile_photo_path"]
    
    if user_index is not None:
        data["users"][user_index] = user
        await save_jsonbin_data(data)
    
    return {"message": "Profile updated successfully"}

@app.get("/api/trending")
async def get_trending(request: Request):
    """Get trending words/hashtags"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    trending = get_trending_words(data)
    
    return {"trending": [{"word": word, "count": count} for word, count in trending]}

@app.post("/api/promote_post")
async def promote_post(request: Request, promotion: PromotionRequest):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    talo = None
    for t in data.get("talos", []):
        if t["id"] == promotion.talo_id:
            talo = t
            break
    
    if not talo:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if talo["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only promote your own posts")
    
    promotion_id = str(uuid.uuid4())
    promotion_record = {
        "id": promotion_id,
        "talo_id": promotion.talo_id,
        "user_id": user["user_id"],
        "amount": promotion.amount,
        "payment_method": promotion.payment_method,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    if "promotions" not in data:
        data["promotions"] = []
    data["promotions"].append(promotion_record)
    await save_jsonbin_data(data)
    
    return {
        "promotion_id": promotion_id,
        "message": "Promotion request created. Complete payment to activate."
    }

@app.post("/api/confirm_promotion_payment/{promotion_id}")
async def confirm_promotion_payment(promotion_id: str, request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    promotion = None
    for p in data.get("promotions", []):
        if p["id"] == promotion_id:
            promotion = p
            break
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    if promotion["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    promotion["status"] = "activated"
    promotion["payment_confirmed_at"] = datetime.now().isoformat()
    
    # Mark talo as promoted
    for talo in data.get("talos", []):
        if talo["id"] == promotion["talo_id"]:
            talo["promoted"] = True
            talo["promotion_level"] = promotion.get("amount", 0) // 100
            talo["promoted_at"] = datetime.now().isoformat()
            break
    
    await save_jsonbin_data(data)
    
    return {"message": "Promotion activated successfully!"}

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_token")
    return response

# ===== ADMIN API ENDPOINTS =====

@app.post("/api/admin/create_admin")
async def create_admin(request: Request, admin_data: CreateAdminRequest):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can create new admins")
    
    for a in data.get("admins", []):
        if a.get("user_id") == admin_data.admin_id:
            raise HTTPException(status_code=400, detail="Admin ID already exists")
    
    new_admin = {
        "user_id": admin_data.admin_id,
        "password_hash": hash_password(admin_data.password),
        "name": admin_data.name,
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "created_by": admin["user_id"],
        "last_login": None
    }
    
    if "admins" not in data:
        data["admins"] = []
    data["admins"].append(new_admin)
    await save_jsonbin_data(data)
    
    return {"message": f"Administrator {admin_data.admin_id} created successfully"}

@app.post("/api/admin/deactivate_user/{user_id}")
async def deactivate_user(user_id: str, request: Request):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    for user in data.get("users", []):
        if user["user_id"] == user_id:
            user["is_active"] = not user.get("is_active", True)
            await save_jsonbin_data(data)
            return {"message": f"User {'activated' if user['is_active'] else 'deactivated'}"}
    
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/health")
async def health_check():
    try:
        data = await get_jsonbin_data()
        return {
            "status": "healthy",
            "api": "jsonbinbro",
            "connected": True,
            "stats": {
                "users": len(data.get("users", [])),
                "talos": len(data.get("talos", [])),
                "replies": len(data.get("replies", []))
            }
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.on_event("startup")
async def startup_event():
    """Initialize wa_guan account on startup"""
    await ensure_wa_guan_account()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("=" * 60)
    print("🐏 GuAn Microblogging Platform")
    print("=" * 60)
    print(f"Server starting at http://{host}:{port}")
    print(f"Super Admin: {SUPER_ADMIN_ID}")
    print(f"Super Admin Password: {SUPER_ADMIN_PASSWORD}")
    print("=" * 60)
    uvicorn.run(app, host=host, port=port)