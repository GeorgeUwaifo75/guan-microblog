# main.py - Modified with Full Admin Hierarchy System
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
from typing import List, Set

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

# Compile regex pattern for banned words (case insensitive)
BANNED_PATTERN = re.compile(r'\b(' + '|'.join(re.escape(word) for word in BANNED_WORDS) + r')\b', re.IGNORECASE)

def contains_banned_words(text: str) -> bool:
    """Check if text contains any banned words"""
    if not text:
        return False
    return bool(BANNED_PATTERN.search(text))

def filter_banned_words(text: str) -> str:
    """Replace banned words with asterisks"""
    if not text:
        return text
    
    def replace_word(match):
        return '*' * len(match.group(0))
    
    return BANNED_PATTERN.sub(replace_word, text)

# ===== PROMOTION SYSTEM =====
class PromotionRequest(BaseModel):
    talo_id: str
    amount: float
    payment_method: str  # 'paystack' or 'paypal'

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

# Create directories
TEMPLATES_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ===== JSONBINBRO API CONFIGURATION =====
API_BASE = 'https://jsonbinbro.onrender.com/api'
BIN_ID = '6a23239439cde2dacaf968e2'
USER_ID = 'george01'
API_KEY = 'XcymJbykd573XqKLEHsZvSBo3hYMDv7uRo5P3PKRYDI'

# Configuration
PAYSTACK_PUBLIC_KEY = 'pk_live_2018244c913523ab0751249b240bc3e3448c3c19'
SUPER_ADMIN_ID = "Adminxx01"
SUPER_ADMIN_PASSWORD = "kijiXmart4140#"

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
                        # Ensure all required collections exist
                        collections = ["users", "talos", "replies", "admins", "likes", 
                                      "dislikes", "retalos", "follows", "blocks", 
                                      "payments", "notifications", "adverts", "premium_requests"]
                        for col in collections:
                            if col not in data_content:
                                data_content[col] = []
                        return data_content
                    else:
                        return {
                            "users": [], "talos": [], "replies": [], "admins": [],
                            "likes": [], "dislikes": [], "retalos": [], "follows": [],
                            "blocks": [], "payments": [], "notifications": [], "adverts": [],
                            "premium_requests": []
                        }
                else:
                    return result
            elif response.status_code == 404:
                logger.warning("Bin not found, creating initial data structure")
                initial_data = {
                    "users": [], "talos": [], "replies": [], "admins": [],
                    "likes": [], "dislikes": [], "retalos": [], "follows": [],
                    "blocks": [], "payments": [], "notifications": [], "adverts": [],
                    "premium_requests": []
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

class CreateReplyRequest(BaseModel):
    content: str
    photo: Optional[Dict[str, str]] = None

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

class PremiumRequest(BaseModel):
    user_id: str
    payment_proof_url: str
    payment_amount: float

# ===== ROUTES =====

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
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
    """Signup page"""
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/api/signup")
async def api_signup(user_data: UserSignup):
    """Signup API endpoint"""
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
    
    return {"message": "User created successfully", "user_id": user_data.user_id}

@app.post("/api/login")
async def api_login(login_data: UserLogin):
    """Login API endpoint"""
    data = await get_jsonbin_data()
    
    # Check for super admin
    if login_data.user_id == SUPER_ADMIN_ID and login_data.password == SUPER_ADMIN_PASSWORD:
        token = generate_token()
        
        # Check if super admin already exists
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
    
    # Check for normal admin
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
    
    # Check for normal user
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
    """User dashboard with personalized feed"""
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
        # Check if it's an admin
        for admin in data.get("admins", []):
            if admin.get("session_token") == session_token:
                return RedirectResponse(url="/admin", status_code=303)
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session_token")
        return response
    
    # Update last active
    user["last_active"] = datetime.now().isoformat()
    await save_jsonbin_data(data)
    
    # Get personalized feed (only posts from followed users + own posts)
    followed_user_ids = set()
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_user_ids.add(follow.get("following_id"))
    followed_user_ids.add(user["user_id"])
    
    # Get talos from followed users
    talos = data.get("talos", [])
    personal_talos = []
    
    for talo in talos:
        if talo["user_id"] in followed_user_ids:
            # Add user info
            for u in data.get("users", []):
                if u["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                    talo["user_photo"] = u.get("profile_photo")
                    break
            talo["reply_count"] = len([r for r in data.get("replies", []) if r.get("parent_talo_id") == talo["id"]])
            personal_talos.append(talo)
    
    # Sort by creation date (newest first) - promoted posts get priority
    def sort_priority(talo):
        promotion_boost = 1000 if talo.get("promoted", False) else 0
        return (datetime.now() - datetime.fromisoformat(talo.get("created_at", datetime.now().isoformat()))).total_seconds() - promotion_boost
    
    personal_talos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Get trending topics (from visible posts only)
    words = []
    for talo in personal_talos:
        words.extend(talo.get("content", "").split())
    word_count = {}
    for word in words:
        if word.startswith("#"):
            word_count[word] = word_count.get(word, 0) + 1
    trending = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # Get active users count (last 24 hours)
    day_ago = (datetime.now() - timedelta(days=1)).isoformat()
    active_users = len([u for u in data.get("users", []) if u.get("last_active", "") > day_ago])
    
    # Get unread notifications count
    notifications = [n for n in data.get("notifications", []) if n.get("user_id") == user["user_id"]]
    unread_notifications = len([n for n in notifications if not n.get("read", False)])
    
    # Get Paystack public key
    paystack_public_key = PAYSTACK_PUBLIC_KEY
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "talos": personal_talos[:50],
        "trending": trending,
        "active_users": active_users,
        "unread_notifications": unread_notifications,
        "paystack_public_key": paystack_public_key
    })


@app.post("/api/admin/check_banned_words")
async def check_banned_words_content(request: Request):
    """Check content for banned words (for admin use)"""
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
    
    body = await request.json()
    content = body.get("content", "")
    
    return {
        "contains_banned_words": contains_banned_words(content),
        "banned_words_found": [w for w in BANNED_WORDS if w.lower() in content.lower()]
    }

@app.get("/api/admin/get_promotion_requests")
async def get_admin_promotion_requests(request: Request):
    """Get pending promotion requests for admin"""
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
    
    pending_promotions = [p for p in data.get("promotions", []) if p.get("status") == "pending_admin"]
    
    # Add user info
    for p in pending_promotions:
        for u in data.get("users", []):
            if u["user_id"] == p["user_id"]:
                p["user_name"] = f"{u['first_name']} {u['last_name']}"
                break
        # Get talo content
        for t in data.get("talos", []):
            if t["id"] == p["talo_id"]:
                p["talo_content"] = t["content"][:100]
                break
    
    return {"promotions": pending_promotions}

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Admin panel with role-based permissions"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/", status_code=303)
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin:
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session_token")
        return response
    
    # Get all users
    users = data.get("users", [])
    
    # Sort users by creation date (newest first)
    users.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Get adverts
    adverts = data.get("adverts", [])
    
    # Get premium requests
    premium_requests = data.get("premium_requests", [])
    
    # Get payments
    payments = data.get("payments", [])
    
    # Calculate statistics
    today = datetime.now().date()
    today_str = datetime.now().isoformat()[:10]
    
    daily_active = len([u for u in users if u.get("last_active", "").startswith(today_str)])
    
    # Get all admins (for super admin)
    admins_list = data.get("admins", [])
    
    # Total posts today
    talos_today = len([t for t in data.get("talos", []) if t.get("created_at", "").startswith(today_str)])
    
    stats = {
        "total_users": len(users),
        "active_users": len([u for u in users if u.get("is_active", True)]),
        "inactive_users": len([u for u in users if not u.get("is_active", True)]),
        "premium_users": len([u for u in users if u.get("is_premium", False)]),
        "daily_active": daily_active,
        "total_talos": len(data.get("talos", [])),
        "talos_today": talos_today,
        "total_replies": len(data.get("replies", [])),
        "total_payments": len(payments),
        "total_payment_amount": sum(p.get("amount", 0) for p in payments)
    }
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "admin": admin,
        "users": users,
        "adverts": adverts,
        "premium_requests": premium_requests,
        "payments": payments,
        "admins": admins_list,
        "stats": stats,
        "is_super_admin": admin.get("role") == "super_admin"
    })

@app.get("/profile/{user_id}", response_class=HTMLResponse)
async def view_profile(request: Request, user_id: str):
    """View another user's profile"""
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
    
    # Find the profile user
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
    
    # Get user's talos
    user_talos = [t for t in data.get("talos", []) if t["user_id"] == user_id]
    
    # Count replies for each talo
    replies = data.get("replies", [])
    for talo in user_talos:
        talo["reply_count"] = len([r for r in replies if r.get("parent_talo_id") == talo["id"]])
    
    # Sort by creation date (newest first)
    user_talos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "current_user": current_user,
        "profile_user": profile_user,
        "talos": user_talos[:50]
    })

@app.get("/post/{talo_id}", response_class=HTMLResponse)
async def view_post(request: Request, talo_id: str):
    """View a single post with its replies"""
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
    
    # Find the main talo
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
    
    # Add user info to main talo
    for u in data.get("users", []):
        if u["user_id"] == talo["user_id"]:
            talo["user_name"] = f"{u['first_name']} {u['last_name']}"
            talo["user_photo"] = u.get("profile_photo")
            break
    
    # Get replies for this talo
    replies = [r for r in data.get("replies", []) if r.get("parent_talo_id") == talo_id]
    
    # Add user info to replies
    for reply in replies:
        for u in data.get("users", []):
            if u["user_id"] == reply["user_id"]:
                reply["user_name"] = f"{u['first_name']} {u['last_name']}"
                reply["user_photo"] = u.get("profile_photo")
                break
    
    # Sort replies by date (oldest first)
    replies.sort(key=lambda x: x.get("created_at", ""))
    
    return templates.TemplateResponse("post.html", {
        "request": request,
        "user": user,
        "talo": talo,
        "replies": replies
    })

@app.post("/api/create_talo")
async def create_talo(request: Request):
    """Create a new talo/post with Firebase photo URLs and banned word filtering"""
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
    
    # Check for banned words
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
    """Create a reply to a talo with Firebase photo URL and banned word filtering"""
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
    
    # Check if parent talo exists
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
    
    # Check for banned words
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
    
    # Update reply count on parent talo
    parent_talo["reply_count"] = len([r for r in data["replies"] if r.get("parent_talo_id") == parent_talo_id])
    
    # Create notification for talo owner
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
    """Like or unlike a talo"""
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
    
    if "likes" not in data:
        data["likes"] = []
    
    # Check if already liked
    like_index = None
    for i, like in enumerate(data["likes"]):
        if like.get("talo_id") == talo_id and like.get("user_id") == user["user_id"]:
            like_index = i
            break
    
    if like_index is not None:
        # Unlike
        data["likes"].pop(like_index)
        for talo in data["talos"]:
            if talo["id"] == talo_id:
                talo["likes"] -= 1
                await save_jsonbin_data(data)
                return {"liked": False, "count": talo["likes"]}
    else:
        # Add like
        data["likes"].append({
            "talo_id": talo_id,
            "user_id": user["user_id"],
            "created_at": datetime.now().isoformat()
        })
        
        for talo in data["talos"]:
            if talo["id"] == talo_id:
                talo["likes"] += 1
                await save_jsonbin_data(data)
                return {"liked": True, "count": talo["likes"]}
    
    await save_jsonbin_data(data)
    return {"liked": False, "count": 0}

@app.post("/api/like_reply/{reply_id}")
async def like_reply(reply_id: str, request: Request):
    """Like or unlike a reply"""
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
    
    if "reply_likes" not in data:
        data["reply_likes"] = []
    
    # Check if already liked
    like_index = None
    for i, like in enumerate(data["reply_likes"]):
        if like.get("reply_id") == reply_id and like.get("user_id") == user["user_id"]:
            like_index = i
            break
    
    if like_index is not None:
        # Unlike
        data["reply_likes"].pop(like_index)
        for reply in data.get("replies", []):
            if reply["id"] == reply_id:
                reply["likes"] = reply.get("likes", 0) - 1
                await save_jsonbin_data(data)
                return {"liked": False, "count": reply["likes"]}
    else:
        # Add like
        data["reply_likes"].append({
            "reply_id": reply_id,
            "user_id": user["user_id"],
            "created_at": datetime.now().isoformat()
        })
        
        for reply in data.get("replies", []):
            if reply["id"] == reply_id:
                reply["likes"] = reply.get("likes", 0) + 1
                await save_jsonbin_data(data)
                return {"liked": True, "count": reply["likes"]}
    
    await save_jsonbin_data(data)
    return {"liked": False, "count": 0}

@app.post("/api/follow/{user_id_to_follow}")
async def follow_user(user_id_to_follow: str, request: Request):
    """Follow or unfollow a user"""
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
    
    # Find target user
    target_user = None
    for u in data.get("users", []):
        if u["user_id"] == user_id_to_follow:
            target_user = u
            break
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "follows" not in data:
        data["follows"] = []
    
    # Check if already following
    follow_index = None
    for i, follow in enumerate(data["follows"]):
        if follow.get("follower_id") == user["user_id"] and follow.get("following_id") == user_id_to_follow:
            follow_index = i
            break
    
    if follow_index is not None:
        # Unfollow
        data["follows"].pop(follow_index)
        user["following_count"] = max(0, user.get("following_count", 0) - 1)
        target_user["followers_count"] = max(0, target_user.get("followers_count", 0) - 1)
        await save_jsonbin_data(data)
        return {"following": False, "followers_count": target_user["followers_count"]}
    else:
        # Follow
        data["follows"].append({
            "follower_id": user["user_id"],
            "following_id": user_id_to_follow,
            "created_at": datetime.now().isoformat()
        })
        user["following_count"] = user.get("following_count", 0) + 1
        target_user["followers_count"] = target_user.get("followers_count", 0) + 1
        await save_jsonbin_data(data)
        return {"following": True, "followers_count": target_user["followers_count"]}

@app.get("/api/get_follow_status/{profile_user_id}")
async def get_follow_status(profile_user_id: str, request: Request):
    """Check if current user follows the profile user"""
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
    """Get list of followers for a user"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    
    # Get current user to verify auth
    current_user = None
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            current_user = u
            break
    
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Find followers
    followers = []
    for follow in data.get("follows", []):
        if follow.get("following_id") == user_id:
            # Get follower info
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
    """Get list of users that a user follows"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    
    # Get current user to verify auth
    current_user = None
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            current_user = u
            break
    
    if not current_user:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Find following
    following = []
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user_id:
            # Get following info
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
    """Update user profile including photo, name, and bio"""
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
    
    # Update name fields
    if "first_name" in form:
        user["first_name"] = form["first_name"]
    if "last_name" in form:
        user["last_name"] = form["last_name"]
    if "bio" in form:
        user["bio"] = form["bio"]
    
    # Handle profile photo URL from Firebase
    if "profile_photo_url" in form:
        user["profile_photo"] = form["profile_photo_url"]
        if "profile_photo_path" in form:
            user["profile_photo_path"] = form["profile_photo_path"]
    
    # Save updated user
    if user_index is not None:
        data["users"][user_index] = user
        await save_jsonbin_data(data)
    
    return {"message": "Profile updated successfully"}

@app.get("/api/search_hashtag/{hashtag}")
async def search_by_hashtag(hashtag: str, request: Request):
    """Search for posts with a specific hashtag"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    
    # Filter talos containing the hashtag
    filtered_talos = []
    for talo in data.get("talos", []):
        content = talo.get("content", "")
        if hashtag.lower() in content.lower():
            # Add user info
            for u in data.get("users", []):
                if u["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                    talo["user_photo"] = u.get("profile_photo")
                    break
            filtered_talos.append(talo)
    
    return {"talos": filtered_talos}

@app.get("/logout")
async def logout():
    """Logout endpoint"""
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_token")
    return response

# ===== ADMIN API ENDPOINTS =====

@app.post("/api/admin/create_admin")
async def create_admin(request: Request, admin_data: CreateAdminRequest):
    """Create a new normal administrator (Super Admin only)"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only super admin can create new admins
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can create new admins")
    
    # Check if admin already exists
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

@app.post("/api/admin/deactivate_admin/{admin_id}")
async def deactivate_admin(admin_id: str, request: Request):
    """Deactivate a normal administrator (Super Admin only)"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only super admin can deactivate admins
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can manage other admins")
    
    # Cannot deactivate self
    if admin_id == admin["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    # Cannot deactivate super admin
    if admin_id == SUPER_ADMIN_ID:
        raise HTTPException(status_code=400, detail="Cannot deactivate Super Administrator")
    
    for a in data.get("admins", []):
        if a["user_id"] == admin_id:
            a["is_active"] = not a.get("is_active", True)
            await save_jsonbin_data(data)
            return {"message": f"Admin {'activated' if a['is_active'] else 'deactivated'}"}
    
    raise HTTPException(status_code=404, detail="Admin not found")

@app.post("/api/admin/delete_admin/{admin_id}")
async def delete_admin(admin_id: str, request: Request):
    """Delete a normal administrator (Super Admin only)"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only super admin can delete admins
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can delete other admins")
    
    # Cannot delete self
    if admin_id == admin["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Cannot delete super admin
    if admin_id == SUPER_ADMIN_ID:
        raise HTTPException(status_code=400, detail="Cannot delete Super Administrator")
    
    admin_index = None
    for i, a in enumerate(data.get("admins", [])):
        if a["user_id"] == admin_id:
            admin_index = i
            break
    
    if admin_index is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    data["admins"].pop(admin_index)
    await save_jsonbin_data(data)
    
    return {"message": f"Admin {admin_id} deleted successfully"}

@app.post("/api/admin/deactivate_user/{user_id}")
async def deactivate_user(user_id: str, request: Request):
    """Admin: Deactivate or activate a user (All admins can do this)"""
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

@app.post("/api/admin/delete_user/{user_id}")
async def delete_user(user_id: str, request: Request):
    """Delete a user (Super Admin only)"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only super admin can delete users
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can delete users")
    
    # Delete user
    user_index = None
    for i, user in enumerate(data.get("users", [])):
        if user["user_id"] == user_id:
            user_index = i
            break
    
    if user_index is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user's talos
    data["talos"] = [t for t in data.get("talos", []) if t["user_id"] != user_id]
    # Delete user's replies
    data["replies"] = [r for r in data.get("replies", []) if r["user_id"] != user_id]
    # Delete user's likes
    data["likes"] = [l for l in data.get("likes", []) if l["user_id"] != user_id]
    # Delete user's follows
    data["follows"] = [f for f in data.get("follows", []) if f["follower_id"] != user_id and f["following_id"] != user_id]
    # Delete user's premium requests
    data["premium_requests"] = [pr for pr in data.get("premium_requests", []) if pr["user_id"] != user_id]
    
    data["users"].pop(user_index)
    await save_jsonbin_data(data)
    
    return {"message": "User deleted successfully"}

@app.post("/api/admin/deactivate_advert/{advert_id}")
async def deactivate_advert(advert_id: str, request: Request):
    """Deactivate or activate an advert (All admins can do this)"""
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
    
    for advert in data.get("adverts", []):
        if advert["id"] == advert_id:
            advert["is_active"] = not advert.get("is_active", True)
            await save_jsonbin_data(data)
            return {"message": f"Advert {'activated' if advert['is_active'] else 'deactivated'}"}
    
    raise HTTPException(status_code=404, detail="Advert not found")

@app.post("/api/admin/delete_advert/{advert_id}")
async def delete_advert(advert_id: str, request: Request):
    """Delete an advert (Super Admin only)"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only super admin can delete adverts
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can delete adverts")
    
    advert_index = None
    for i, advert in enumerate(data.get("adverts", [])):
        if advert["id"] == advert_id:
            advert_index = i
            break
    
    if advert_index is None:
        raise HTTPException(status_code=404, detail="Advert not found")
    
    data["adverts"].pop(advert_index)
    await save_jsonbin_data(data)
    
    return {"message": "Advert deleted successfully"}

@app.post("/api/admin/process_premium_request/{request_id}")
async def process_premium_request(request_id: str, request: Request):
    """Approve or reject premium user request (All admins can do this)"""
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
    
    body = await request.json()
    action = body.get("action")  # "approve" or "reject"
    
    req_index = None
    premium_request = None
    for i, pr in enumerate(data.get("premium_requests", [])):
        if pr["id"] == request_id:
            req_index = i
            premium_request = pr
            break
    
    if req_index is None:
        raise HTTPException(status_code=404, detail="Premium request not found")
    
    if action == "approve":
        # Update user to premium
        for user in data.get("users", []):
            if user["user_id"] == premium_request["user_id"]:
                user["is_premium"] = True
                user["premium_activated_at"] = datetime.now().isoformat()
                user["premium_activated_by"] = admin["user_id"]
                break
        
        # Record payment
        if "payments" not in data:
            data["payments"] = []
        data["payments"].append({
            "id": str(uuid.uuid4()),
            "user_id": premium_request["user_id"],
            "amount": premium_request["amount"],
            "payment_proof_url": premium_request["payment_proof_url"],
            "status": "approved",
            "processed_by": admin["user_id"],
            "processed_at": datetime.now().isoformat(),
            "created_at": premium_request["created_at"]
        })
        
        # Remove request
        data["premium_requests"].pop(req_index)
        await save_jsonbin_data(data)
        
        return {"message": "Premium request approved successfully"}
    
    elif action == "reject":
        # Just remove the request
        data["premium_requests"].pop(req_index)
        await save_jsonbin_data(data)
        return {"message": "Premium request rejected"}
    
    raise HTTPException(status_code=400, detail="Invalid action")

@app.post("/api/admin/request_premium")
async def request_premium(request: Request):
    """User requests premium upgrade with payment proof"""
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
    payment_proof_url = body.get("payment_proof_url")
    amount = body.get("amount")
    
    if not payment_proof_url or not amount:
        raise HTTPException(status_code=400, detail="Payment proof URL and amount required")
    
    premium_request = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "user_name": f"{user['first_name']} {user['last_name']}",
        "amount": amount,
        "payment_proof_url": payment_proof_url,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    if "premium_requests" not in data:
        data["premium_requests"] = []
    data["premium_requests"].append(premium_request)
    await save_jsonbin_data(data)
    
    return {"message": "Premium request submitted successfully"}

@app.get("/api/admin/get_premium_requests")
async def get_premium_requests(request: Request):
    """Get all pending premium requests"""
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
    
    pending_requests = [pr for pr in data.get("premium_requests", []) if pr.get("status") == "pending"]
    
    return {"requests": pending_requests}

@app.get("/api/admin/get_payments")
async def get_payments(request: Request):
    """Get all successful payments"""
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
    
    payments = data.get("payments", [])
    payments.sort(key=lambda x: x.get("processed_at", ""), reverse=True)
    
    return {"payments": payments}

@app.get("/api/admin/get_admins")
async def get_admins(request: Request):
    """Get all administrators (Super Admin only)"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only super admin can view all admins
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can view admin list")
    
    admins = data.get("admins", [])
    # Remove sensitive data
    for a in admins:
        if "password_hash" in a:
            del a["password_hash"]
        if "session_token" in a:
            del a["session_token"]
    
    return {"admins": admins}

@app.get("/api/admin/get_reports")
async def get_reports(request: Request):
    """Get comprehensive platform reports (All admins)"""
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
    
    users = data.get("users", [])
    today = datetime.now().date()
    today_str = datetime.now().isoformat()[:10]
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    month_ago = (datetime.now() - timedelta(days=30)).isoformat()
    
    # User reports
    user_reports = {
        "total_users": len(users),
        "active_users": len([u for u in users if u.get("is_active", True)]),
        "inactive_users": len([u for u in users if not u.get("is_active", True)]),
        "premium_users": len([u for u in users if u.get("is_premium", False)]),
        "male_users": len([u for u in users if u.get("gender") == "Male"]),
        "female_users": len([u for u in users if u.get("gender") == "Female"]),
        "users_last_7_days": len([u for u in users if u.get("created_at", "") > week_ago]),
        "users_last_30_days": len([u for u in users if u.get("created_at", "") > month_ago]),
        "daily_active": len([u for u in users if u.get("last_active", "").startswith(today_str)]),
        "users_by_country": {}
    }
    
    # Group users by country
    for user in users:
        country = user.get("country", "Unknown")
        user_reports["users_by_country"][country] = user_reports["users_by_country"].get(country, 0) + 1
    
    # Post reports
    talos = data.get("talos", [])
    replies = data.get("replies", [])
    
    post_reports = {
        "total_talos": len(talos),
        "total_replies": len(replies),
        "talos_today": len([t for t in talos if t.get("created_at", "").startswith(today_str)]),
        "replies_today": len([r for r in replies if r.get("created_at", "").startswith(today_str)]),
        "talos_last_7_days": len([t for t in talos if t.get("created_at", "") > week_ago]),
        "replies_last_7_days": len([r for r in replies if r.get("created_at", "") > week_ago]),
        "total_likes": len(data.get("likes", [])),
        "total_follows": len(data.get("follows", []))
    }
    
    # Financial reports
    payments = data.get("payments", [])
    financial_reports = {
        "total_payments": len(payments),
        "total_amount": sum(p.get("amount", 0) for p in payments),
        "payments_last_7_days": len([p for p in payments if p.get("processed_at", "") > week_ago]),
        "amount_last_7_days": sum(p.get("amount", 0) for p in payments if p.get("processed_at", "") > week_ago),
        "payments_last_30_days": len([p for p in payments if p.get("processed_at", "") > month_ago]),
        "amount_last_30_days": sum(p.get("amount", 0) for p in payments if p.get("processed_at", "") > month_ago)
    }
    
    return {
        "user_reports": user_reports,
        "post_reports": post_reports,
        "financial_reports": financial_reports,
        "generated_at": datetime.now().isoformat(),
        "admin": {
            "user_id": admin["user_id"],
            "role": admin["role"]
        }
    }


# Add these endpoints to main.py after the existing endpoints

# ===== RETALO AND NOTIFICATION ENDPOINTS =====

@app.get("/api/get_latest_talo_timestamp")
async def get_latest_talo_timestamp(request: Request):
    """Get the timestamp of the latest talo for new post detection"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"latest_timestamp": None}
    
    data = await get_jsonbin_data()
    talos = data.get("talos", [])
    
    if talos:
        # Sort by created_at and get the latest
        latest = max(talos, key=lambda x: x.get("created_at", ""))
        return {"latest_timestamp": latest.get("created_at")}
    
    return {"latest_timestamp": None}

# Replace the existing retalo endpoint in main.py with this enhanced version:

@app.post("/api/retalo")
async def create_retalo(request: Request):
    """Create a retalo/repost - shares original post to followers and notifies original poster"""
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
    original_talo_id = body.get("original_talo_id")
    original_user_id = body.get("original_user_id")
    original_content = body.get("original_content")
    original_photos = body.get("original_photos", [])  # Get original photos
    
    if not original_talo_id:
        raise HTTPException(status_code=400, detail="Original talo ID required")
    
    # Get the original talo details
    original_talo = None
    for talo in data.get("talos", []):
        if talo["id"] == original_talo_id:
            original_talo = talo
            break
    
    if not original_talo:
        raise HTTPException(status_code=404, detail="Original post not found")
    
    # Check if user already retaled this post
    for retalo in data.get("retalos", []):
        if retalo.get("user_id") == user["user_id"] and retalo.get("original_talo_id") == original_talo_id:
            raise HTTPException(status_code=400, detail="You have already reposted this post")
    
    # Create retalo record
    retalo = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "original_talo_id": original_talo_id,
        "original_user_id": original_user_id,
        "original_content": original_content,
        "original_photos": original_talo.get("photos", []),  # Store original photos
        "created_at": datetime.now().isoformat()
    }
    
    if "retalos" not in data:
        data["retalos"] = []
    data["retalos"].append(retalo)
    
    # Update retalo count on original talo
    for talo in data.get("talos", []):
        if talo["id"] == original_talo_id:
            talo["retalos"] = talo.get("retalos", 0) + 1
            break
    
    # Create a visible retalo post in the feed with original content
    retalo_post = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "content": original_content,  # Use original content instead of just a message
        "photos": original_talo.get("photos", []),  # Include original photos
        "likes": 0,
        "dislikes": 0,
        "retalos": 0,
        "reply_count": 0,
        "created_at": datetime.now().isoformat(),
        "is_retalo": True,
        "original_talo_id": original_talo_id,
        "original_user_id": original_user_id,
        "retalo_user_name": f"{user['first_name']} {user['last_name']}",
        "retalo_user_id": user["user_id"]
    }
    
    data["talos"].insert(0, retalo_post)
    user["talos_count"] = user.get("talos_count", 0) + 1
    
    # Create notification for original poster
    if original_user_id != user["user_id"]:
        if "notifications" not in data:
            data["notifications"] = []
        
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": original_user_id,
            "type": "retalo",
            "message": f"@{user['user_id']} reposted your post: {original_content[:50]}...",
            "related_talo_id": original_talo_id,
            "from_user_id": user["user_id"],
            "read": False,
            "created_at": datetime.now().isoformat()
        }
        data["notifications"].append(notification)
    
    # Create notifications for all followers of the user
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
            "type": "retalo",
            "message": f"@{user['user_id']} reposted: {original_content[:50]}...",
            "related_talo_id": original_talo_id,
            "from_user_id": user["user_id"],
            "read": False,
            "created_at": datetime.now().isoformat()
        }
        data["notifications"].append(notification)
    
    await save_jsonbin_data(data)
    
    return {
        "message": "Post reposted successfully!", 
        "retalo_id": retalo["id"],
        "retalo_post": retalo_post
    }

@app.get("/api/get_notifications")
async def get_notifications(request: Request):
    """Get notifications for the current user with unread count"""
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
    
    notifications = [n for n in data.get("notifications", []) if n.get("user_id") == user["user_id"]]
    # Sort by created_at descending
    notifications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    unread_count = len([n for n in notifications if not n.get("read", False)])
    
    return {"notifications": notifications, "unread_count": unread_count}
@app.post("/api/mark_all_notifications_read")
async def mark_all_notifications_read(request: Request):
    """Mark all notifications as read for the current user"""
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
    
    for notification in data.get("notifications", []):
        if notification.get("user_id") == user["user_id"]:
            notification["read"] = True
    
    await save_jsonbin_data(data)
    return {"message": "All notifications marked as read"}

@app.post("/api/mark_notification_read/{notification_id}")
async def mark_notification_read(notification_id: str, request: Request):
    """Mark a notification as read"""
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
    
    for notification in data.get("notifications", []):
        if notification.get("id") == notification_id and notification.get("user_id") == user["user_id"]:
            notification["read"] = True
            await save_jsonbin_data(data)
            return {"message": "Notification marked as read"}
    
    raise HTTPException(status_code=404, detail="Notification not found")

@app.post("/api/mark_all_notifications_read")
async def mark_all_notifications_read(request: Request):
    """Mark all notifications as read for the current user"""
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
    
    for notification in data.get("notifications", []):
        if notification.get("user_id") == user["user_id"]:
            notification["read"] = True
    
    await save_jsonbin_data(data)
    return {"message": "All notifications marked as read"}

# Update the like endpoint to send notifications
@app.post("/api/like/{talo_id}")
async def like_talo_with_notification(talo_id: str, request: Request):
    """Like or unlike a talo with notification"""
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
    
    if "likes" not in data:
        data["likes"] = []
    
    # Find the talo owner
    talo_owner_id = None
    for talo in data["talos"]:
        if talo["id"] == talo_id:
            talo_owner_id = talo["user_id"]
            break
    
    # Check if already liked
    like_index = None
    for i, like in enumerate(data["likes"]):
        if like.get("talo_id") == talo_id and like.get("user_id") == user["user_id"]:
            like_index = i
            break
    
    if like_index is not None:
        # Unlike
        data["likes"].pop(like_index)
        for talo in data["talos"]:
            if talo["id"] == talo_id:
                talo["likes"] -= 1
                await save_jsonbin_data(data)
                return {"liked": False, "count": talo["likes"]}
    else:
        # Add like
        data["likes"].append({
            "talo_id": talo_id,
            "user_id": user["user_id"],
            "created_at": datetime.now().isoformat()
        })
        
        for talo in data["talos"]:
            if talo["id"] == talo_id:
                talo["likes"] += 1
                
                # Create notification for talo owner (if not self-like)
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

# Update follow endpoint to send notifications
@app.post("/api/follow/{user_id_to_follow}")
async def follow_user_with_notification(user_id_to_follow: str, request: Request):
    """Follow or unfollow a user with notification"""
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
    
    # Find target user
    target_user = None
    for u in data.get("users", []):
        if u["user_id"] == user_id_to_follow:
            target_user = u
            break
    
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if "follows" not in data:
        data["follows"] = []
    
    # Check if already following
    follow_index = None
    for i, follow in enumerate(data["follows"]):
        if follow.get("follower_id") == user["user_id"] and follow.get("following_id") == user_id_to_follow:
            follow_index = i
            break
    
    if follow_index is not None:
        # Unfollow
        data["follows"].pop(follow_index)
        user["following_count"] = max(0, user.get("following_count", 0) - 1)
        target_user["followers_count"] = max(0, target_user.get("followers_count", 0) - 1)
        await save_jsonbin_data(data)
        return {"following": False, "followers_count": target_user["followers_count"]}
    else:
        # Follow
        data["follows"].append({
            "follower_id": user["user_id"],
            "following_id": user_id_to_follow,
            "created_at": datetime.now().isoformat()
        })
        user["following_count"] = user.get("following_count", 0) + 1
        target_user["followers_count"] = target_user.get("followers_count", 0) + 1
        
        # Create notification for the user being followed
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

@app.get("/api/feed")
async def get_personalized_feed(request: Request):
    """Get personalized feed based on follows (only show posts from followed users)"""
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
    
    # Get IDs of users this user follows
    followed_user_ids = set()
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_user_ids.add(follow.get("following_id"))
    
    # Also include the user's own posts
    followed_user_ids.add(user["user_id"])
    
    # Get talos from followed users
    talos = data.get("talos", [])
    filtered_talos = []
    
    for talo in talos:
        if talo["user_id"] in followed_user_ids:
            # Add user info
            for u in data.get("users", []):
                if u["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                    talo["user_photo"] = u.get("profile_photo")
                    break
            
            # Get reply count
            talo["reply_count"] = len([r for r in data.get("replies", []) if r.get("parent_talo_id") == talo["id"]])
            filtered_talos.append(talo)
    
    # Sort by creation date (newest first)
    filtered_talos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Get replies for these talos
    replies = data.get("replies", [])
    
    return {
        "talos": filtered_talos[:100],
        "replies": replies
    }

@app.post("/api/promote_post")
async def promote_post(request: Request, promotion: PromotionRequest):
    """Initiate post promotion payment"""
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
    
    # Find the talo
    talo = None
    for t in data.get("talos", []):
        if t["id"] == promotion.talo_id:
            talo = t
            break
    
    if not talo:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if talo["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only promote your own posts")
    
    # Create promotion request record
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
    """Confirm promotion payment (for PayPal - requires admin approval)"""
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
    
    # Find promotion
    promotion = None
    for p in data.get("promotions", []):
        if p["id"] == promotion_id:
            promotion = p
            break
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    if promotion["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Update promotion status to pending_admin (for PayPal)
    promotion["status"] = "pending_admin"
    promotion["payment_confirmed_at"] = datetime.now().isoformat()
    
    # Create admin notification for PayPal payment
    if promotion["payment_method"] == "paypal":
        if "admin_notifications" not in data:
            data["admin_notifications"] = []
        
        admin_notification = {
            "id": str(uuid.uuid4()),
            "type": "promotion_payment",
            "promotion_id": promotion_id,
            "user_id": user["user_id"],
            "amount": promotion["amount"],
            "message": f"User @{user['user_id']} has paid for post promotion (${promotion['amount']}) via PayPal. Please verify and activate.",
            "read": False,
            "created_at": datetime.now().isoformat()
        }
        data["admin_notifications"].append(admin_notification)
    
    await save_jsonbin_data(data)
    
    return {"message": "Payment recorded. Awaiting admin verification for PayPal payments, or promotion activated for Paystack."}

@app.post("/api/admin/activate_promotion/{promotion_id}")
async def activate_promotion(promotion_id: str, request: Request):
    """Admin: Activate a promoted post (for PayPal payments)"""
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
    
    # Find promotion
    promotion = None
    promotion_index = None
    for i, p in enumerate(data.get("promotions", [])):
        if p["id"] == promotion_id:
            promotion = p
            promotion_index = i
            break
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    # Find the talo and mark as promoted
    for talo in data.get("talos", []):
        if talo["id"] == promotion["talo_id"]:
            talo["promoted"] = True
            talo["promotion_level"] = promotion.get("amount", 0) // 100  # $100 = level 1
            talo["promoted_at"] = datetime.now().isoformat()
            talo["promoted_by"] = admin["user_id"]
            break
    
    # Update promotion status
    promotion["status"] = "activated"
    promotion["activated_at"] = datetime.now().isoformat()
    promotion["activated_by"] = admin["user_id"]
    
    data["promotions"][promotion_index] = promotion
    await save_jsonbin_data(data)
    
    # Create notification for user
    if "notifications" not in data:
        data["notifications"] = []
    
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": promotion["user_id"],
        "type": "promotion",
        "message": "Your post promotion has been activated! Your post will get higher visibility.",
        "related_talo_id": promotion["talo_id"],
        "read": False,
        "created_at": datetime.now().isoformat()
    }
    data["notifications"].append(notification)
    await save_jsonbin_data(data)
    
    return {"message": "Promotion activated successfully"}

@app.get("/api/get_admin_promotion_requests")
async def get_admin_promotion_requests(request: Request):
    """Get pending promotion requests for admin"""
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
    
    pending_promotions = [p for p in data.get("promotions", []) if p.get("status") == "pending_admin"]
    
    # Add user info
    for p in pending_promotions:
        for u in data.get("users", []):
            if u["user_id"] == p["user_id"]:
                p["user_name"] = f"{u['first_name']} {u['last_name']}"
                break
    
    return {"promotions": pending_promotions}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
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