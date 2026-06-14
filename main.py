# main.py - With Working Search and Original Trending System

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

# Add these imports at the top
from functools import lru_cache
import time
from contextlib import asynccontextmanager

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


# Simple memory cache for API data
class APICache:
    def __init__(self, ttl_seconds=30):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            del self.cache[key]
        return None
    
    def set(self, key, data):
        self.cache[key] = (data, time.time())
    
    def clear(self):
        self.cache.clear()

api_cache = APICache(ttl_seconds=30)  # Cache for 30 seconds


class PersistentAPICache:
    """File-based cache that persists across server restarts"""
    def __init__(self, cache_file="api_cache.json", ttl_seconds=300):  # 5 minute TTL
        self.cache_file = cache_file
        self.ttl = ttl_seconds
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    self.cache = data.get('data', {})
                    self.timestamp = data.get('timestamp', 0)
            else:
                self.cache = {}
                self.timestamp = 0
        except Exception as e:
            logger.error(f"Error loading persistent cache: {e}")
            self.cache = {}
            self.timestamp = 0
    
    def _save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'data': self.cache,
                    'timestamp': self.timestamp
                }, f)
        except Exception as e:
            logger.error(f"Error saving persistent cache: {e}")
    
    def get(self, key):
        """Get cached data if not expired"""
        if self.cache and time.time() - self.timestamp < self.ttl:
            return self.cache.get(key)
        return None
    
    def set(self, key, data):
        """Set cached data"""
        self.cache = {key: data}
        self.timestamp = time.time()
        self._save_cache()
    
    def clear(self):
        """Clear cache"""
        self.cache = {}
        self.timestamp = 0
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

# Replace api_cache with persistent cache
api_cache = PersistentAPICache(ttl_seconds=300)  # 5 minute cache

# ===== WA_GUAN ACCOUNT CONFIGURATION =====
WA_GUAN_USER_ID = "wa_guan"
WA_GUAN_FIRST_NAME = "Support"
WA_GUAN_LAST_NAME = "GuAn"
WA_GUAN_EMAIL = "support@guan.com"

async def ensure_wa_guan_account():
    """Ensure the @wa_guan support account exists with welcome post"""
    try:
        data = await get_jsonbin_data()
        
        # Check if wa_guan account already exists
        wa_guan_exists = False
        wa_guan_user = None
        for user in data.get("users", []):
            if user.get("user_id") == WA_GUAN_USER_ID:
                wa_guan_exists = True
                wa_guan_user = user
                break
        
        # Create wa_guan account if it doesn't exist
        if not wa_guan_exists:
            logger.info("Creating @wa_guan support account...")
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
                "bio": "Official Support Account for GuAn Microblogging Platform. Follow for updates and guidelines!"
            }
            
            if "users" not in data:
                data["users"] = []
            data["users"].append(new_user)
            logger.info(f"Created @{WA_GUAN_USER_ID} support account")
            
            # Create welcome post for wa_guan
            welcome_content = """Wa guan. 👋 Welcome to GuAn!

We're excited to have you here! 

🌟 **Tips for a Great Experience:**
1. **Connect with like minds** - Follow users who share your interests and engage with their content
2. **Be authentic** - Share your thoughts, ideas, and experiences truthfully
3. **Stay positive** - Spread encouragement and build meaningful connections
4. **Post responsibly** - Share content that adds value to our community

Remember: Freedom of expression is a right, but please don't hurt others with yours. Let's build a supportive community together! 

Get started by following interesting accounts and sharing your first talo. 

#WelcomeToGuAn #StayPositive #BeAuthentic #CommunityFirst"""
            
            welcome_talo = {
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
            data["talos"].insert(0, welcome_talo)
            logger.info("Created welcome post for @wa_guan")
            
            await save_jsonbin_data(data)
            logger.info("@wa_guan account setup completed successfully")
        else:
            logger.info("@wa_guan account already exists")
            
            # Check if welcome post exists, create if not
            has_welcome_post = False
            for talo in data.get("talos", []):
                if talo.get("user_id") == WA_GUAN_USER_ID and talo.get("is_welcome"):
                    has_welcome_post = True
                    break
            
            if not has_welcome_post:
                welcome_content = """Wa guan. 👋 Welcome to GuAn!

We're excited to have you here! 

🌟 **Tips for a Great Experience:**
1. **Connect with like minds** - Follow users who share your interests and engage with their content
2. **Be authentic** - Share your thoughts, ideas, and experiences truthfully
3. **Stay positive** - Spread encouragement and build meaningful connections
4. **Post responsibly** - Share content that adds value to our community

Remember: Freedom of expression is a right, but please don't hurt others with yours. Let's build a supportive community together! 

Get started by following interesting accounts and sharing your first talo. 

#WelcomeToGuAn #StayPositive #BeAuthentic #CommunityFirst"""
                
                welcome_talo = {
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
                data["talos"].insert(0, welcome_talo)
                await save_jsonbin_data(data)
                logger.info("Created missing welcome post for @wa_guan")
                
    except Exception as e:
        logger.error(f"Error in ensure_wa_guan_account: {str(e)}")
        # Don't raise the exception - allow the app to start anyway
        # The account will be created on next API call if needed
        logger.warning("Could not verify/create wa_guan account. Will retry on next request.")

# Also update the get_jsonbin_data function to be more resilient
async def get_jsonbin_data(force_refresh=False) -> Dict:
    """Fetch data from jsonbinbro API with improved retry logic"""
    
    # Check cache first
    if not force_refresh:
        cached_data = api_cache.get("jsonbin_data")
        if cached_data:
            logger.info("Returning cached API data")
            return cached_data
    
    max_retries = 3
    retry_delay = 2  # Increased from 1 second
    
    for attempt in range(max_retries):
        try:
            url = f"{API_BASE}/bins/{BIN_ID}?api_key={API_KEY}"
            
            # Increased timeout to 15 seconds
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if 'data' in result:
                        data_content = result['data']
                        if isinstance(data_content, dict):
                            collections = ["users", "talos", "replies", "admins", "likes", 
                                          "dislikes", "retalos", "follows", "blocks", 
                                          "payments", "notifications", "adverts", "premium_requests",
                                          "promotions"]
                            for col in collections:
                                if col not in data_content:
                                    data_content[col] = []
                            # Cache the successful response
                            api_cache.set("jsonbin_data", data_content)
                            return data_content
                        else:
                            default_data = {
                                "users": [], "talos": [], "replies": [], "admins": [],
                                "likes": [], "dislikes": [], "retalos": [], "follows": [],
                                "blocks": [], "payments": [], "notifications": [], "adverts": [],
                                "premium_requests": [], "promotions": []
                            }
                            api_cache.set("jsonbin_data", default_data)
                            return default_data
                    else:
                        api_cache.set("jsonbin_data", result)
                        return result
                        
                elif response.status_code == 404:
                    logger.warning("Bin not found, creating initial data structure")
                    initial_data = {
                        "users": [], "talos": [], "replies": [], "admins": [],
                        "likes": [], "dislikes": [], "retalos": [], "follows": [],
                        "blocks": [], "payments": [], "notifications": [], "adverts": [],
                        "premium_requests": [], "promotions": []
                    }
                    await save_jsonbin_data(initial_data)
                    api_cache.set("jsonbin_data", initial_data)
                    return initial_data
                else:
                    if attempt < max_retries - 1:
                        logger.warning(f"API returned {response.status_code}, retrying...")
                        await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    # Return cached data if available
                    cached = api_cache.get("jsonbin_data")
                    if cached:
                        logger.warning("Using cached data due to API error")
                        return cached
                    raise HTTPException(status_code=503, detail=f"API error: Status {response.status_code}")
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout error (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            # Return cached data if available
            cached = api_cache.get("jsonbin_data")
            if cached:
                logger.warning("Using cached data due to timeout")
                return cached
            raise HTTPException(status_code=503, detail="API is currently slow. Please try again in a moment.")
            
        except Exception as e:
            logger.error(f"Error fetching data (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            # Return cached data if available
            cached = api_cache.get("jsonbin_data")
            if cached:
                logger.warning("Using cached data due to error")
                return cached
            raise HTTPException(status_code=503, detail=f"Unable to access API: {str(e)}")
    
    # Fallback to cached data
    cached = api_cache.get("jsonbin_data")
    if cached:
        logger.warning("Using cached data as final fallback")
        return cached
    raise HTTPException(status_code=503, detail="Unable to access API after multiple attempts")

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

# Add this helper function to organize replies hierarchically:
def organize_replies_hierarchically(replies):
    reply_dict = {}
    top_level_replies = []
    
    # First, index all replies by ID
    for reply in replies:
        reply["child_replies"] = []
        reply["child_reply_count"] = 0
        reply_dict[reply["id"]] = reply
    
    # Then organize them
    for reply in replies:
        parent_id = reply.get("parent_reply_id")
        if parent_id and parent_id in reply_dict:
            reply_dict[parent_id]["child_replies"].append(reply)
            reply_dict[parent_id]["child_reply_count"] = len(reply_dict[parent_id]["child_replies"])
        elif not parent_id:  # Top-level reply (direct to post)
            top_level_replies.append(reply)
    
    # Sort each level by created_at (oldest first for replies)
    top_level_replies.sort(key=lambda x: x.get("created_at", ""))
    for reply in reply_dict.values():
        reply["child_replies"].sort(key=lambda x: x.get("created_at", ""))
    
    return top_level_replies

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


class CreateAdminRequest(BaseModel):
    admin_id: str
    password: str
    name: str

class ToggleAdminStatusRequest(BaseModel):
    admin_id: str
    is_active: bool

# ===== SEARCH SYSTEM =====
async def search_all_posts(search_query: str, data: Dict) -> List[Dict]:
    """Search through all posts in the database"""
    query_lower = search_query.lower().strip()
    
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
    
    # Also search for @username specifically
    if query_lower.startswith('@'):
        username = query_lower[1:]
        for user in data.get("users", []):
            if username in user.get("user_id", "").lower():
                # Get all posts from this user
                for talo in data.get("talos", []):
                    if talo["user_id"].lower() == username and talo not in matched_posts:
                        for u in data.get("users", []):
                            if u["user_id"] == talo["user_id"]:
                                talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                                talo["user_photo"] = u.get("profile_photo")
                                break
                        talo["reply_count"] = len([r for r in data.get("replies", []) 
                                                   if r.get("parent_talo_id") == talo["id"]])
                        matched_posts.append(talo)
    
    # Sort by date (newest first)
    matched_posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return matched_posts

async def search_users(search_query: str, data: Dict) -> List[Dict]:
    """Search for users by user_id or name"""
    query_lower = search_query.lower().strip()
    
    # Remove @ prefix if present
    if query_lower.startswith('@'):
        query_lower = query_lower[1:]
    
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
                "followers_count": user.get("followers_count", 0),
                "bio": user.get("bio", "")
            })
    
    return matched_users

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
    try:
        data = await get_jsonbin_data()
    except HTTPException as e:
        # If API fails, try one more time with force refresh
        logger.warning("First API attempt failed, retrying...")
        await asyncio.sleep(1)
        try:
            data = await get_jsonbin_data(force_refresh=True)
        except HTTPException:
            # Return user-friendly error
            raise HTTPException(status_code=503, detail="Service is starting up. Please wait 10 seconds and try again.")
    
    await ensure_wa_guan_account()
    data = await get_jsonbin_data()
    
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
    
    followed_user_ids = set()
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_user_ids.add(follow.get("following_id"))
    followed_user_ids.add(user["user_id"])
    
    talos = data.get("talos", [])
    
    # Get all promoted posts
    all_promoted_talos = []
    regular_talos = []
    
    for talo in talos:
        # Add user info to each talo
        for u in data.get("users", []):
            if u["user_id"] == talo["user_id"]:
                talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                talo["user_photo"] = u.get("profile_photo")
                break
        talo["reply_count"] = len([r for r in data.get("replies", []) if r.get("parent_talo_id") == talo["id"]])
        
        if talo.get("promoted", False):
            all_promoted_talos.append(talo)
        else:
            # For regular posts, only show from followed users
            if followed_user_ids and talo["user_id"] in followed_user_ids:
                regular_talos.append(talo)
            elif not followed_user_ids or len(followed_user_ids) <= 1:  # Only self
                regular_talos.append(talo)
    
    # Sort regular posts by date (newest first)
    regular_talos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # ===== PROBABILISTIC PROMOTED POSTS (25% chance to show each) =====
    import random
    selected_promoted_talos = []
    
    if all_promoted_talos:
        # Sort promoted posts by promotion level (higher level first)
        all_promoted_talos.sort(key=lambda x: (x.get("promotion_level", 0), x.get("created_at", "")), reverse=True)
        
        # Each promoted post has a 25% chance of being shown
        for promoted_talo in all_promoted_talos:
            # 25% probability (1 in 4 chance)
            if random.random() < 0.25:  # 25% chance
                selected_promoted_talos.append(promoted_talo)
        
        # Also ensure at least one promoted post is shown if any exist (optional)
        # Uncomment the line below if you want at least 1 promoted post guaranteed
        # if not selected_promoted_talos and all_promoted_talos:
        #     selected_promoted_talos.append(all_promoted_talos[0])
    
    # Combine: Selected promoted posts first, then regular posts
    personal_talos = selected_promoted_talos + regular_talos

    # Ensure all posts are sorted by created_at descending (newest first)
    # This is already done but let's reinforce
    personal_talos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    # Store which promoted posts were shown in session for consistency? (optional)
    # This ensures the same promoted posts appear until next refresh
    
    # Global trending - based on ALL posts in the platform
    all_talos = data.get("talos", [])
    global_words = []
    for talo in all_talos:
        content = talo.get("content", "")
        for word in content.split():
            if word.startswith("#") and len(word) > 1:
                global_words.append(word)
    word_count = {}
    for word in global_words:
        word_count[word] = word_count.get(word, 0) + 1
    trending = sorted(word_count.items(), key=lambda x: x[1], reverse=True)[:10]
    
    active_users = len([u for u in data.get("users", []) if u.get("last_active", "") > (datetime.now() - timedelta(days=1)).isoformat()])
    
    notifications = [n for n in data.get("notifications", []) if n.get("user_id") == user["user_id"]]
    unread_notifications = len([n for n in notifications if not n.get("read", False)])
    
    # Pass the probability info to the template for display
    promoted_shown_count = len(selected_promoted_talos)
    promoted_total_count = len(all_promoted_talos)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "talos": personal_talos[:100],
        "trending": trending,
        "active_users": active_users,
        "unread_notifications": unread_notifications,
        "paystack_public_key": PAYSTACK_PUBLIC_KEY,
        "promoted_shown_count": promoted_shown_count,
        "promoted_total_count": promoted_total_count
    })

@app.get("/api/get_promoted_posts")
async def get_promoted_posts(request: Request):
    """Get all promoted posts for global visibility"""
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
    
    promoted_posts = []
    for talo in data.get("talos", []):
        if talo.get("promoted", False):
            # Add user info
            for u in data.get("users", []):
                if u["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                    talo["user_photo"] = u.get("profile_photo")
                    break
            talo["reply_count"] = len([r for r in data.get("replies", []) if r.get("parent_talo_id") == talo["id"]])
            promoted_posts.append(talo)
    
    # Sort by promotion level (higher first) and then by date
    promoted_posts.sort(key=lambda x: (x.get("promotion_level", 0), x.get("created_at", "")), reverse=True)
    
    return {"promoted_posts": promoted_posts}

# ===== SEARCH ENDPOINTS =====
@app.get("/api/search")
async def search_global(request: Request, q: str = ""):
    """Global search for posts and users"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not q or len(q.strip()) < 1:
        return {"posts": [], "users": [], "total_posts": 0, "total_users": 0}
    
    data = await get_jsonbin_data()
    
    # Search posts
    matched_posts = await search_all_posts(q, data)
    
    # Search users
    matched_users = await search_users(q, data)
    
    return {
        "posts": matched_posts[:100],
        "users": matched_users[:20],
        "total_posts": len(matched_posts),
        "total_users": len(matched_users),
        "search_query": q
    }

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
    
    search_results = {"posts": [], "users": [], "total_posts": 0, "total_users": 0}
    if q:
        search_results["posts"] = await search_all_posts(q, data)
        search_results["users"] = await search_users(q, data)
        search_results["total_posts"] = len(search_results["posts"])
        search_results["total_users"] = len(search_results["users"])
    
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
    
    #replies = [r for r in data.get("replies", []) if r.get("parent_talo_id") == talo_id]
     all_replies = [r for r in data.get("replies", []) if r.get("parent_talo_id") == talo_id]
     replies = organize_replies_hierarchically(all_replies)
    
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
    await save_jsonbin_data(data)
    
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
    password_changed = False
    
    # Update profile information
    if "first_name" in form:
        user["first_name"] = form["first_name"]
    if "last_name" in form:
        user["last_name"] = form["last_name"]
    if "bio" in form:
        user["bio"] = form["bio"]
    
    # Update profile photo if provided
    if "profile_photo_url" in form:
        user["profile_photo"] = form["profile_photo_url"]
        if "profile_photo_path" in form:
            user["profile_photo_path"] = form["profile_photo_path"]
    
    # Handle password change
    current_password = form.get("current_password")
    new_password = form.get("new_password")
    
    if current_password and new_password:
        # Verify current password
        if verify_password(current_password, user["password_hash"]):
            # Update to new password
            user["password_hash"] = hash_password(new_password)
            password_changed = True
            logger.info(f"Password changed for user: {user['user_id']}")
        else:
            raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Save changes
    if user_index is not None:
        data["users"][user_index] = user
        await save_jsonbin_data(data)
    
    return {
        "message": "Profile updated successfully" + (" Password changed. Please log in again." if password_changed else ""),
        "password_changed": password_changed
    }


@app.get("/api/search_hashtag/{hashtag}")
async def search_by_hashtag(hashtag: str, request: Request):
    """Search for posts with a specific hashtag"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    
    filtered_talos = []
    for talo in data.get("talos", []):
        content = talo.get("content", "")
        if hashtag.lower() in content.lower():
            for u in data.get("users", []):
                if u["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                    talo["user_photo"] = u.get("profile_photo")
                    break
            filtered_talos.append(talo)
    
    return {"talos": filtered_talos}

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("session_token")
    return response

@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Admin dashboard panel"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return RedirectResponse(url="/", status_code=303)
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        # Clear invalid session
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie("session_token")
        return response
    
    # Get statistics for dashboard
    users = data.get("users", [])
    talos = data.get("talos", [])
    payments = data.get("payments", [])
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    
    stats = {
        "total_users": len(users),
        "active_users": len([u for u in users if u.get("is_active", True)]),
        "daily_active": len([u for u in users if u.get("last_active", "") > today_start]),
        "premium_users": len([u for u in users if u.get("is_premium", False)]),
        "total_talos": len(talos),
        "talos_today": len([t for t in talos if t.get("created_at", "") > today_start]),
        "total_payment_amount": sum([p.get("amount", 0) for p in payments if p.get("status") == "approved"]),
        "total_payments": len([p for p in payments if p.get("status") == "approved"])
    }
    
    # Get all users for the user management table
    user_list = []
    for u in users:
        user_list.append({
            "user_id": u.get("user_id"),
            "first_name": u.get("first_name"),
            "last_name": u.get("last_name"),
            "email": u.get("email"),
            "age": u.get("age"),
            "gender": u.get("gender"),
            "country": u.get("country"),
            "is_active": u.get("is_active", True),
            "is_premium": u.get("is_premium", False),
            "talos_count": u.get("talos_count", 0),
            "created_at": u.get("created_at", ""),
            "last_active": u.get("last_active", "")
        })
    
    # Get all admins (for Super Admin view)
    admins = []
    for a in data.get("admins", []):
        admins.append({
            "user_id": a.get("user_id"),
            "name": a.get("name"),
            "role": a.get("role", "admin"),
            "is_active": a.get("is_active", True),
            "created_at": a.get("created_at", ""),
            "created_by": a.get("created_by", "System"),
            "last_login": a.get("last_login", "")
        })
    
    # Get premium requests
    premium_requests = []
    for pr in data.get("premium_requests", []):
        user_name = "Unknown"
        for u in users:
            if u.get("user_id") == pr.get("user_id"):
                user_name = f"{u.get('first_name', '')} {u.get('last_name', '')}"
                break
        premium_requests.append({
            "id": pr.get("id"),
            "user_id": pr.get("user_id"),
            "user_name": user_name,
            "amount": pr.get("amount", 0),
            "payment_proof_url": pr.get("payment_proof_url", ""),
            "payment_method": pr.get("payment_method", "unknown"),
            "created_at": pr.get("created_at", "")
        })
    
    # Get payment history
    payment_list = []
    for p in payments:
        payment_list.append({
            "id": p.get("id"),
            "user_id": p.get("user_id"),
            "amount": p.get("amount", 0),
            "payment_proof_url": p.get("payment_proof_url", ""),
            "payment_method": p.get("payment_method", "unknown"),
            "status": p.get("status", "pending"),
            "processed_by": p.get("processed_by", ""),
            "created_at": p.get("created_at", ""),
            "processed_at": p.get("processed_at", "")
        })
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "admin": admin,
        "is_super_admin": admin.get("role") == "super_admin",
        "stats": stats,
        "users": user_list,
        "admins": admins,
        "premium_requests": premium_requests,
        "payments": payment_list
    })


# ===== ADMIN API ENDPOINTS =====

@app.post("/api/admin/create_admin")
async def create_admin(request: Request, admin_data: CreateAdminRequest):
    """Super Admin only - Create a new administrator"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only Super Admin can create new admins
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can create new administrators")
    
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

@app.post("/api/admin/deactivate_admin")
async def deactivate_admin(request: Request, admin_data: ToggleAdminStatusRequest):
    """Super Admin only - Activate/Deactivate an administrator"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    current_admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            current_admin = a
            break
    
    # Only Super Admin can manage admins
    if not current_admin or current_admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can manage administrators")
    
    # Cannot deactivate self
    if admin_data.admin_id == current_admin["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot modify your own admin status")
    
    for admin in data.get("admins", []):
        if admin["user_id"] == admin_data.admin_id:
            # Cannot modify Super Admin
            if admin.get("role") == "super_admin":
                raise HTTPException(status_code=403, detail="Cannot modify Super Administrator")
            admin["is_active"] = admin_data.is_active
            await save_jsonbin_data(data)
            return {"message": f"Administrator {'activated' if admin_data.is_active else 'deactivated'}"}
    
    raise HTTPException(status_code=404, detail="Administrator not found")

@app.post("/api/admin/delete_admin/{admin_id}")
async def delete_admin(admin_id: str, request: Request):
    """Super Admin only - Permanently delete an administrator"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    current_admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            current_admin = a
            break
    
    # Only Super Admin can delete admins
    if not current_admin or current_admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can delete administrators")
    
    # Cannot delete self
    if admin_id == current_admin["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    for i, admin in enumerate(data.get("admins", [])):
        if admin["user_id"] == admin_id:
            # Cannot delete Super Admin
            if admin.get("role") == "super_admin":
                raise HTTPException(status_code=403, detail="Cannot delete Super Administrator")
            data["admins"].pop(i)
            await save_jsonbin_data(data)
            return {"message": f"Administrator {admin_id} deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Administrator not found")


@app.post("/api/admin/deactivate_user/{user_id}")
async def deactivate_user(user_id: str, request: Request):
    """Admin+ - Activate/Deactivate a user"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    for user in data.get("users", []):
        if user["user_id"] == user_id:
            user["is_active"] = not user.get("is_active", True)
            await save_jsonbin_data(data)
            return {"message": f"User {'activated' if user['is_active'] else 'deactivated'}"}
    
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/admin/delete_user/{user_id}")
async def delete_user(user_id: str, request: Request):
    """Super Admin only - Permanently delete a user and all their data"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only Super Admin can delete users
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can delete users")
    
    # Find and delete user
    user_index = None
    for i, user in enumerate(data.get("users", [])):
        if user["user_id"] == user_id:
            user_index = i
            break
    
    if user_index is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete user's talos
    data["talos"] = [t for t in data.get("talos", []) if t.get("user_id") != user_id]
    
    # Delete user's replies
    data["replies"] = [r for r in data.get("replies", []) if r.get("user_id") != user_id]
    
    # Delete user's likes
    data["likes"] = [l for l in data.get("likes", []) if l.get("user_id") != user_id]
    
    # Delete user's follows
    data["follows"] = [f for f in data.get("follows", []) if f.get("follower_id") != user_id and f.get("following_id") != user_id]
    
    # Delete user's notifications
    data["notifications"] = [n for n in data.get("notifications", []) if n.get("user_id") != user_id and n.get("from_user_id") != user_id]
    
    # Delete user's payments
    data["payments"] = [p for p in data.get("payments", []) if p.get("user_id") != user_id]
    
    # Delete user's premium requests
    data["premium_requests"] = [pr for pr in data.get("premium_requests", []) if pr.get("user_id") != user_id]
    
    # Delete the user
    data["users"].pop(user_index)
    
    await save_jsonbin_data(data)
    return {"message": f"User {user_id} and all associated data deleted successfully"}

@app.post("/api/admin/activate_promotion/{promotion_id}")
async def activate_promotion(promotion_id: str, request: Request):
    """Admin+ - Activate a post promotion"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    promotion = None
    for p in data.get("promotions", []):
        if p["id"] == promotion_id:
            promotion = p
            break
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    promotion["status"] = "activated"
    promotion["activated_by"] = admin["user_id"]
    promotion["activated_at"] = datetime.now().isoformat()
    
    # Mark the talo as promoted
    for talo in data.get("talos", []):
        if talo["id"] == promotion["talo_id"]:
            talo["promoted"] = True
            talo["promotion_level"] = promotion.get("amount", 0) // 100
            talo["promoted_at"] = datetime.now().isoformat()
            talo["promoted_by"] = admin["user_id"]
            break
    
    await save_jsonbin_data(data)
    return {"message": "Promotion activated successfully"}

@app.post("/api/admin/deactivate_promotion/{promotion_id}")
async def deactivate_promotion(promotion_id: str, request: Request):
    """Admin+ - Deactivate a promoted post"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    promotion = None
    for p in data.get("promotions", []):
        if p["id"] == promotion_id:
            promotion = p
            break
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    promotion["status"] = "deactivated"
    promotion["deactivated_by"] = admin["user_id"]
    promotion["deactivated_at"] = datetime.now().isoformat()
    
    # Remove promotion from talo
    for talo in data.get("talos", []):
        if talo["id"] == promotion["talo_id"]:
            talo["promoted"] = False
            talo["promotion_level"] = 0
            break
    
    await save_jsonbin_data(data)
    return {"message": "Promotion deactivated successfully"}

@app.delete("/api/admin/delete_promotion/{promotion_id}")
async def delete_promotion(promotion_id: str, request: Request):
    """Super Admin only - Permanently delete a promotion request"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    # Only Super Admin can delete promotions
    if not admin or admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can delete promotions")
    
    for i, promotion in enumerate(data.get("promotions", [])):
        if promotion["id"] == promotion_id:
            # Remove promotion flag from talo if present
            for talo in data.get("talos", []):
                if talo["id"] == promotion["talo_id"]:
                    talo["promoted"] = False
                    talo["promotion_level"] = 0
                    break
            data["promotions"].pop(i)
            await save_jsonbin_data(data)
            return {"message": "Promotion deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Promotion not found")

@app.get("/api/admin/get_promotion_requests")
async def get_promotion_requests(request: Request):
    """Admin+ - Get all promotion requests"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    promotions = []
    for p in data.get("promotions", []):
        # Find user info
        user_name = "Unknown"
        talo_content = ""
        for user in data.get("users", []):
            if user["user_id"] == p["user_id"]:
                user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                break
        for talo in data.get("talos", []):
            if talo["id"] == p["talo_id"]:
                talo_content = talo.get("content", "")[:100]
                break
        promotions.append({
            "id": p["id"],
            "user_id": p["user_id"],
            "user_name": user_name,
            "talo_id": p["talo_id"],
            "talo_content": talo_content,
            "amount": p.get("amount", 0),
            "payment_method": p.get("payment_method", "unknown"),
            "status": p.get("status", "pending"),
            "created_at": p.get("created_at", "")
        })
    
    return {"promotions": promotions}

@app.post("/api/admin/process_premium_request/{request_id}")
async def process_premium_request(request_id: str, request: Request):
    """Admin+ - Approve or reject premium upgrade request"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    body = await request.json()
    action = body.get("action")
    
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    premium_request = None
    request_index = None
    for i, pr in enumerate(data.get("premium_requests", [])):
        if pr.get("id") == request_id:
            premium_request = pr
            request_index = i
            break
    
    if not premium_request:
        raise HTTPException(status_code=404, detail="Premium request not found")
    
    if action == "approve":
        # Update user to premium
        for user in data.get("users", []):
            if user["user_id"] == premium_request["user_id"]:
                user["is_premium"] = True
                user["premium_activated_at"] = datetime.now().isoformat()
                user["premium_activated_by"] = admin["user_id"]
                break
        
        # Add to payments
        if "payments" not in data:
            data["payments"] = []
        data["payments"].append({
            "id": str(uuid.uuid4()),
            "user_id": premium_request["user_id"],
            "amount": premium_request["amount"],
            "payment_proof_url": premium_request.get("payment_proof_url", ""),
            "payment_method": premium_request.get("payment_method", "unknown"),
            "status": "approved",
            "processed_by": admin["user_id"],
            "created_at": premium_request.get("created_at", datetime.now().isoformat()),
            "processed_at": datetime.now().isoformat()
        })
        
        # Send notification to user
        if "notifications" not in data:
            data["notifications"] = []
        data["notifications"].append({
            "id": str(uuid.uuid4()),
            "user_id": premium_request["user_id"],
            "type": "premium_approved",
            "message": f"Your premium upgrade request has been approved! You now have premium status.",
            "read": False,
            "created_at": datetime.now().isoformat()
        })
    
    # Remove the request
    data["premium_requests"].pop(request_index)
    
    await save_jsonbin_data(data)
    return {"message": f"Premium request {action}d successfully"}

@app.get("/api/admin/get_reports")
async def get_admin_reports(request: Request):
    """Admin+ - Get platform statistics and reports"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = data.get("users", [])
    talos = data.get("talos", [])
    replies = data.get("replies", [])
    payments = data.get("payments", [])
    
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()
    
    # User Reports
    active_users = len([u for u in users if u.get("is_active", True)])
    inactive_users = len([u for u in users if not u.get("is_active", True)])
    premium_users = len([u for u in users if u.get("is_premium", False)])
    male_users = len([u for u in users if u.get("gender") == "Male"])
    female_users = len([u for u in users if u.get("gender") == "Female"])
    daily_active = len([u for u in users if u.get("last_active", "") > today_start])
    users_last_7_days = len([u for u in users if u.get("created_at", "") > week_ago])
    users_last_30_days = len([u for u in users if u.get("created_at", "") > month_ago])
    
    # Users by country
    users_by_country = {}
    for u in users:
        country = u.get("country", "Unknown")
        users_by_country[country] = users_by_country.get(country, 0) + 1
    
    # Post Reports
    total_talos = len(talos)
    total_replies = len(replies)
    talos_today = len([t for t in talos if t.get("created_at", "") > today_start])
    replies_today = len([r for r in replies if r.get("created_at", "") > today_start])
    talos_last_7_days = len([t for t in talos if t.get("created_at", "") > week_ago])
    replies_last_7_days = len([r for r in replies if r.get("created_at", "") > week_ago])
    total_likes = len(data.get("likes", []))
    total_follows = len(data.get("follows", []))
    
    # Financial Reports
    total_amount = sum([p.get("amount", 0) for p in payments if p.get("status") == "approved"])
    total_payments = len([p for p in payments if p.get("status") == "approved"])
    amount_last_7_days = sum([p.get("amount", 0) for p in payments if p.get("created_at", "") > week_ago and p.get("status") == "approved"])
    payments_last_7_days = len([p for p in payments if p.get("created_at", "") > week_ago and p.get("status") == "approved"])
    amount_last_30_days = sum([p.get("amount", 0) for p in payments if p.get("created_at", "") > month_ago and p.get("status") == "approved"])
    payments_last_30_days = len([p for p in payments if p.get("created_at", "") > month_ago and p.get("status") == "approved"])
    
    # User list with details for admin view
    user_list = []
    for u in users:
        user_list.append({
            "user_id": u.get("user_id"),
            "first_name": u.get("first_name"),
            "last_name": u.get("last_name"),
            "email": u.get("email"),
            "age": u.get("age"),
            "gender": u.get("gender"),
            "country": u.get("country"),
            "is_active": u.get("is_active", True),
            "is_premium": u.get("is_premium", False),
            "talos_count": u.get("talos_count", 0),
            "created_at": u.get("created_at", ""),
            "last_active": u.get("last_active", "")
        })
    
    return {
        "user_reports": {
            "total_users": len(users),
            "active_users": active_users,
            "inactive_users": inactive_users,
            "premium_users": premium_users,
            "male_users": male_users,
            "female_users": female_users,
            "daily_active": daily_active,
            "users_last_7_days": users_last_7_days,
            "users_last_30_days": users_last_30_days,
            "users_by_country": users_by_country
        },
        "post_reports": {
            "total_talos": total_talos,
            "total_replies": total_replies,
            "talos_today": talos_today,
            "replies_today": replies_today,
            "talos_last_7_days": talos_last_7_days,
            "replies_last_7_days": replies_last_7_days,
            "total_likes": total_likes,
            "total_follows": total_follows
        },
        "financial_reports": {
            "total_amount": total_amount,
            "total_payments": total_payments,
            "amount_last_7_days": amount_last_7_days,
            "payments_last_7_days": payments_last_7_days,
            "amount_last_30_days": amount_last_30_days,
            "payments_last_30_days": payments_last_30_days
        },
        "users": user_list,
        "generated_at": now.isoformat()
    }


@app.get("/api/admin/get_users")
async def get_admin_users(request: Request):
    """Admin+ - Get all users with their details"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = []
    for u in data.get("users", []):
        users.append({
            "user_id": u.get("user_id"),
            "first_name": u.get("first_name"),
            "last_name": u.get("last_name"),
            "email": u.get("email"),
            "age": u.get("age"),
            "gender": u.get("gender"),
            "country": u.get("country"),
            "is_active": u.get("is_active", True),
            "is_premium": u.get("is_premium", False),
            "talos_count": u.get("talos_count", 0),
            "followers_count": u.get("followers_count", 0),
            "following_count": u.get("following_count", 0),
            "created_at": u.get("created_at", ""),
            "last_active": u.get("last_active", "")
        })
    
    return {"users": users}


@app.get("/api/admin/get_admins")
async def get_admin_list(request: Request):
    """Super Admin only - Get all administrators"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    current_admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            current_admin = a
            break
    
    if not current_admin or current_admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Super Admin access required")
    
    admins = []
    for a in data.get("admins", []):
        admins.append({
            "user_id": a.get("user_id"),
            "name": a.get("name"),
            "role": a.get("role", "admin"),
            "is_active": a.get("is_active", True),
            "created_at": a.get("created_at", ""),
            "created_by": a.get("created_by", "System"),
            "last_login": a.get("last_login", "")
        })
    
    return {"admins": admins}

@app.get("/api/admin/get_payments")
async def get_admin_payments(request: Request):
    """Admin+ - Get all successful payments"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    payments = []
    for p in data.get("payments", []):
        payments.append({
            "id": p.get("id"),
            "user_id": p.get("user_id"),
            "amount": p.get("amount", 0),
            "payment_proof_url": p.get("payment_proof_url", ""),
            "payment_method": p.get("payment_method", "unknown"),
            "status": p.get("status", "pending"),
            "processed_by": p.get("processed_by", ""),
            "created_at": p.get("created_at", ""),
            "processed_at": p.get("processed_at", "")
        })
    
    return {"payments": payments}

@app.get("/api/admin/get_premium_requests")
async def get_premium_requests(request: Request):
    """Admin+ - Get all pending premium upgrade requests"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    data = await get_jsonbin_data()
    admin = None
    
    for a in data.get("admins", []):
        if a.get("session_token") == session_token:
            admin = a
            break
    
    if not admin or not admin.get("is_active", True):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    premium_requests = []
    for pr in data.get("premium_requests", []):
        # Get user name
        user_name = "Unknown"
        for u in data.get("users", []):
            if u.get("user_id") == pr.get("user_id"):
                user_name = f"{u.get('first_name', '')} {u.get('last_name', '')}"
                break
        
        premium_requests.append({
            "id": pr.get("id"),
            "user_id": pr.get("user_id"),
            "user_name": user_name,
            "amount": pr.get("amount", 0),
            "payment_proof_url": pr.get("payment_proof_url", ""),
            "payment_method": pr.get("payment_method", "unknown"),
            "created_at": pr.get("created_at", "")
        })
    
    return {"premium_requests": premium_requests}


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
    
    for talo in data.get("talos", []):
        if talo["id"] == promotion["talo_id"]:
            talo["promoted"] = True
            talo["promotion_level"] = promotion.get("amount", 0) // 100
            talo["promoted_at"] = datetime.now().isoformat()
            break
    
    await save_jsonbin_data(data)
    
    return {"message": "Promotion activated successfully!"}


@app.get("/api/get_followed_users")
async def get_followed_users(request: Request):
    """Get list of users that the current user follows"""
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
    
    followed_users = []
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_users.append(follow.get("following_id"))
    
    return {"followed_users": followed_users}

@app.get("/api/check_new_posts_from_followed")
async def check_new_posts_from_followed(request: Request):
    """Check if there are new posts from followed users"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"has_new_posts": False, "count": 0}
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        return {"has_new_posts": False, "count": 0}
    
    last_seen = request.headers.get("X-Last-Seen", "")
    
    # Get followed users
    followed_users = set()
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_users.add(follow.get("following_id"))
    
    # Count new posts from followed users
    new_posts_count = 0
    for talo in data.get("talos", []):
        if talo["user_id"] in followed_users:
            if not last_seen or talo.get("created_at", "") > last_seen:
                new_posts_count += 1
    
    return {"has_new_posts": new_posts_count > 0, "count": new_posts_count}

@app.post("/api/mark_posts_viewed")
async def mark_posts_viewed(request: Request):
    """Mark all posts as viewed by the current user"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    body = await request.json()
    timestamp = body.get("timestamp", datetime.now().isoformat())
    
    data = await get_jsonbin_data()
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            u["last_posts_viewed"] = timestamp
            await save_jsonbin_data(data)
            break
    
    return {"success": True}


# ===== ACTIVITY NOTIFICATIONS ENDPOINTS (Likes, Replies, Follows) =====

@app.get("/api/get_activity_notifications")
async def get_activity_notifications(request: Request):
    """Get activity notifications for the current user (likes, replies, follows)"""
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
    
    # Get notifications for this user, exclude 'new_post' type (those are handled separately)
    notifications = []
    for notif in data.get("notifications", []):
        if notif.get("user_id") == user["user_id"] and notif.get("type") != "new_post":
            notifications.append(notif)
    
    # Sort by most recent first
    notifications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {"notifications": notifications[:100]}


@app.delete("/api/delete_activity_notification/{notification_id}")
async def delete_activity_notification(notification_id: str, request: Request):
    """Delete a specific activity notification"""
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
    
    notifications = data.get("notifications", [])
    for i, notif in enumerate(notifications):
        if notif.get("id") == notification_id and notif.get("user_id") == user["user_id"]:
            notifications.pop(i)
            await save_jsonbin_data(data)
            return {"success": True}
    
    raise HTTPException(status_code=404, detail="Notification not found")


@app.patch("/api/mark_notification_read/{notification_id}")
async def mark_notification_read(notification_id: str, request: Request):
    """Mark a specific activity notification as read (without deleting it)"""
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

    notifications = data.get("notifications", [])
    for notif in notifications:
        if notif.get("id") == notification_id and notif.get("user_id") == user["user_id"]:
            if not notif.get("read", False):
                notif["read"] = True
                await save_jsonbin_data(data)
            return {"success": True}

    raise HTTPException(status_code=404, detail="Notification not found")

@app.delete("/api/clear_all_activity_notifications")
async def clear_all_activity_notifications(request: Request):
    """Clear all activity notifications for the current user"""
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
    
    notifications = data.get("notifications", [])
    # Keep 'new_post' notifications for the unviewed posts counter, remove activity ones
    data["notifications"] = [n for n in notifications if n.get("user_id") != user["user_id"] or n.get("type") == "new_post"]
    await save_jsonbin_data(data)
    
    return {"success": True}

@app.get("/api/check_new_notifications")
async def check_new_notifications(request: Request):
    """Check for new notifications since last check"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"has_new": False, "count": 0}
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        return {"has_new": False, "count": 0}
    
    last_checked = request.headers.get("X-Last-Checked", "")
    
    # Get followed users for filtering
    followed_users = set()
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_users.add(follow.get("following_id"))
    
    # Count new notifications ONLY from followed users
    new_count = 0
    for notif in data.get("notifications", []):
        if notif.get("user_id") == user["user_id"] and not notif.get("read", False):
            from_user_id = notif.get("from_user_id")
            # Only count if from followed user (or if it's a follow notification about the user themselves)
            if notif.get("type") == "follow" and from_user_id:
                # Follow notifications are always shown (someone followed you)
                if not last_checked or notif.get("created_at", "") > last_checked:
                    new_count += 1
            elif from_user_id in followed_users:
                if not last_checked or notif.get("created_at", "") > last_checked:
                    new_count += 1
    
    return {"has_new": new_count > 0, "count": new_count}

# Update the notification creation in like, follow, and reply endpoints to only notify followed users
# Modify the create_reply endpoint:

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
    
    # Only send notification if talo owner follows the replier
    if talo_owner_id != user["user_id"]:
        # Check if talo owner follows the replier
        follows_replier = False
        for follow in data.get("follows", []):
            if follow.get("follower_id") == talo_owner_id and follow.get("following_id") == user["user_id"]:
                follows_replier = True
                break
        
        if follows_replier:
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

# Similarly update like_talo endpoint:

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
                
                # Only send notification if talo owner follows the liker
                if talo_owner_id and talo_owner_id != user["user_id"]:
                    follows_liker = False
                    for follow in data.get("follows", []):
                        if follow.get("follower_id") == talo_owner_id and follow.get("following_id") == user["user_id"]:
                            follows_liker = True
                            break
                    
                    if follows_liker:
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

# Add endpoint to get latest talo timestamp
@app.get("/api/get_latest_talo_timestamp")
async def get_latest_talo_timestamp(request: Request):
    """Get the timestamp of the latest talo from followed users"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"latest_timestamp": None}
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        return {"latest_timestamp": None}
    
    # Get followed users
    followed_users = set()
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_users.add(follow.get("following_id"))
    
    # Find latest post from followed users
    latest_timestamp = None
    for talo in data.get("talos", []):
        if talo["user_id"] in followed_users:
            if not latest_timestamp or talo.get("created_at", "") > latest_timestamp:
                latest_timestamp = talo.get("created_at")
    
    return {"latest_timestamp": latest_timestamp}


@app.get("/api/get_unviewed_posts_count")
async def get_unviewed_posts_count(request: Request):
    """Get count of unviewed posts from followed users (NOT activity notifications)"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return {"count": 0}
    
    data = await get_jsonbin_data()
    user = None
    
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            user = u
            break
    
    if not user:
        return {"count": 0}
    
    last_viewed = request.headers.get("X-Last-Viewed", "")
    if not last_viewed:
        last_viewed = user.get("last_posts_viewed", "")
    
    # Get followed users
    followed_users = set()
    for follow in data.get("follows", []):
        if follow.get("follower_id") == user["user_id"]:
            followed_users.add(follow.get("following_id"))
    
    # Count ONLY posts from followed users that are newer than last viewed
    # Exclude the user's own posts
    new_posts_count = 0
    for talo in data.get("talos", []):
        if talo["user_id"] in followed_users and talo["user_id"] != user["user_id"]:
            if not last_viewed or talo.get("created_at", "") > last_viewed:
                new_posts_count += 1
    
    return {"count": new_posts_count}

@app.post("/api/refresh_cache")
async def refresh_cache(request: Request):
    """Force refresh the API cache"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Clear cache and force refresh
    api_cache.clear()
    await get_jsonbin_data(force_refresh=True)
    return {"success": True}

# Add this endpoint to main.py (after the like_talo endpoint)

@app.post("/api/retalo")
async def create_retalo(request: Request):
    """Create a retalo/repost of an existing post"""
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
    original_content = body.get("original_content", "")
    original_photos = body.get("original_photos", [])
    
    # Find the original talo
    original_talo = None
    for talo in data.get("talos", []):
        if talo["id"] == original_talo_id:
            original_talo = talo
            break
    
    if not original_talo:
        raise HTTPException(status_code=404, detail="Original post not found")
    
    # Check if user already retaled this post
    for talo in data.get("talos", []):
        if talo.get("is_retalo") and talo.get("user_id") == user["user_id"] and talo.get("original_talo_id") == original_talo_id:
            raise HTTPException(status_code=400, detail="You have already reposted this")
    
    # Create retalo content (original content with repost prefix)
    retalo_content = f"🔄 Reposted from @{original_user_id}\n\n{original_content}"
    
    # Filter banned words
    if contains_banned_words(retalo_content):
        raise HTTPException(status_code=400, detail="The original post contains inappropriate language and cannot be reposted")
    
    # Create the retalo
    retalo = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "content": retalo_content,
        "photos": original_photos,  # Copy original photos
        "likes": 0,
        "dislikes": 0,
        "retalos": 0,
        "reply_count": 0,
        "created_at": datetime.now().isoformat(),
        "promoted": False,
        "promotion_level": 0,
        "is_retalo": True,
        "original_talo_id": original_talo_id,
        "original_user_id": original_user_id
    }
    
    if "talos" not in data:
        data["talos"] = []
    data["talos"].insert(0, retalo)
    
    # Increment retalo count on original post
    for talo in data["talos"]:
        if talo["id"] == original_talo_id:
            talo["retalos"] = talo.get("retalos", 0) + 1
            break
    
    # Update user's talos count
    user["talos_count"] = user.get("talos_count", 0) + 1
    
    # Send notification to original poster (only if they follow the retaler)
    if original_user_id != user["user_id"]:
        follows_retaler = False
        for follow in data.get("follows", []):
            if follow.get("follower_id") == original_user_id and follow.get("following_id") == user["user_id"]:
                follows_retaler = True
                break
        
        if follows_retaler:
            if "notifications" not in data:
                data["notifications"] = []
            
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": original_user_id,
                "type": "retalo",
                "message": f"@{user['user_id']} reposted your talo",
                "related_talo_id": retalo["id"],
                "original_talo_id": original_talo_id,
                "from_user_id": user["user_id"],
                "read": False,
                "created_at": datetime.now().isoformat()
            }
            data["notifications"].append(notification)
    
    await save_jsonbin_data(data)
    
    return {"message": "Post reposted successfully", "retalo_id": retalo["id"], "retalo_count": original_talo["retalos"] + 1}

@app.delete("/api/delete_talo/{talo_id}")
async def delete_talo(talo_id: str, request: Request):
    """Delete a post - only the author can delete their own post"""
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
    talo_index = None
    talo = None
    for i, t in enumerate(data.get("talos", [])):
        if t["id"] == talo_id:
            talo_index = i
            talo = t
            break
    
    if not talo:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check if user is the author
    if talo["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own posts")
    
    # Delete all replies to this post
    data["replies"] = [r for r in data.get("replies", []) if r.get("parent_talo_id") != talo_id]
    
    # Delete all likes on this post
    data["likes"] = [l for l in data.get("likes", []) if l.get("talo_id") != talo_id]
    
    # Delete all dislikes on this post
    if "dislikes" in data:
        data["dislikes"] = [d for d in data.get("dislikes", []) if d.get("talo_id") != talo_id]
    
    # Delete notifications related to this post
    data["notifications"] = [n for n in data.get("notifications", []) if n.get("related_talo_id") != talo_id and n.get("original_talo_id") != talo_id]
    
    # Remove the post
    data["talos"].pop(talo_index)
    
    # Update user's talos count
    user["talos_count"] = max(0, user.get("talos_count", 0) - 1)
    
    await save_jsonbin_data(data)
    
    return {"message": "Post deleted successfully"}


# Add this endpoint to main.py to check for banned words
@app.post("/api/check_banned_words")
async def check_banned_words(request: Request):
    """Check if content contains banned words"""
    try:
        body = await request.json()
        content = body.get("content", "")
        contains = contains_banned_words(content)
        return {"contains_banned": contains}
    except Exception as e:
        return {"contains_banned": False, "error": str(e)}

@app.post("/api/like_reply/{reply_id}")
async def like_reply(reply_id: str, request: Request):
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
    
    like_index = None
    for i, like in enumerate(data["reply_likes"]):
        if like.get("reply_id") == reply_id and like.get("user_id") == user["user_id"]:
            like_index = i
            break
    
    # Find the reply to update like count
    reply = None
    for r in data.get("replies", []):
        if r["id"] == reply_id:
            reply = r
            break
    
    if not reply:
        raise HTTPException(status_code=404, detail="Reply not found")
    
    if like_index is not None:
        data["reply_likes"].pop(like_index)
        reply["likes"] = max(0, reply.get("likes", 0) - 1)
        await save_jsonbin_data(data)
        return {"liked": False, "count": reply["likes"]}
    else:
        data["reply_likes"].append({
            "reply_id": reply_id,
            "user_id": user["user_id"],
            "created_at": datetime.now().isoformat()
        })
        reply["likes"] = reply.get("likes", 0) + 1
        
        # Send notification to reply owner if they follow the liker
        reply_owner_id = reply.get("user_id")
        if reply_owner_id and reply_owner_id != user["user_id"]:
            follows_liker = False
            for follow in data.get("follows", []):
                if follow.get("follower_id") == reply_owner_id and follow.get("following_id") == user["user_id"]:
                    follows_liker = True
                    break
            
            if follows_liker:
                if "notifications" not in data:
                    data["notifications"] = []
                data["notifications"].append({
                    "id": str(uuid.uuid4()),
                    "user_id": reply_owner_id,
                    "type": "reply_like",
                    "message": f"@{user['user_id']} liked your reply",
                    "reply_id": reply_id,
                    "from_user_id": user["user_id"],
                    "read": False,
                    "created_at": datetime.now().isoformat()
                })
        
        await save_jsonbin_data(data)
        return {"liked": True, "count": reply["likes"]}


# Endpoint to create a nested reply (reply to a reply)
@app.post("/api/create_nested_reply/{parent_reply_id}")
async def create_nested_reply(parent_reply_id: str, request: Request):
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
    talo_id = body.get("talo_id")
    parent_user_id = body.get("parent_user_id")
    
    if contains_banned_words(content):
        raise HTTPException(status_code=400, detail="Your reply contains inappropriate language. Please review and try again.")
    
    if not content or len(content) > 250:
        raise HTTPException(status_code=400, detail="Reply must be between 1 and 250 characters")
    
    # Find the parent reply
    parent_reply = None
    for r in data.get("replies", []):
        if r["id"] == parent_reply_id:
            parent_reply = r
            break
    
    if not parent_reply:
        raise HTTPException(status_code=404, detail="Parent reply not found")
    
    # Create the nested reply
    nested_reply = {
        "id": str(uuid.uuid4()),
        "parent_reply_id": parent_reply_id,
        "parent_talo_id": talo_id,
        "user_id": user["user_id"],
        "content": content,
        "photos": [],
        "likes": 0,
        "created_at": datetime.now().isoformat()
    }
    
    if "replies" not in data:
        data["replies"] = []
    data["replies"].append(nested_reply)
    
    # Update parent reply's child count (optional, can be calculated on the fly)
    parent_reply["child_reply_count"] = parent_reply.get("child_reply_count", 0) + 1
    
    # Send notification to parent reply owner if they follow the replier
    if parent_user_id and parent_user_id != user["user_id"]:
        follows_replier = False
        for follow in data.get("follows", []):
            if follow.get("follower_id") == parent_user_id and follow.get("following_id") == user["user_id"]:
                follows_replier = True
                break
        
        if follows_replier:
            if "notifications" not in data:
                data["notifications"] = []
            
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": parent_user_id,
                "type": "reply_to_reply",
                "message": f"@{user['user_id']} replied to your comment: {content[:50]}...",
                "related_reply_id": parent_reply_id,
                "nested_reply_id": nested_reply["id"],
                "from_user_id": user["user_id"],
                "read": False,
                "created_at": datetime.now().isoformat()
            }
            data["notifications"].append(notification)
    
    await save_jsonbin_data(data)
    
    return {"message": "Reply posted successfully", "reply_id": nested_reply["id"]}


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Render"""
    try:
        # Try to get cached data first
        cached = api_cache.get("jsonbin_data")
        if cached:
            return {
                "status": "healthy",
                "api": "jsonbinbro (cached)",
                "connected": True,
                "cached": True,
                "stats": {
                    "users": len(cached.get("users", [])),
                    "talos": len(cached.get("talos", [])),
                    "replies": len(cached.get("replies", []))
                }
            }
        
        # Try fresh data
        data = await get_jsonbin_data()
        return {
            "status": "healthy",
            "api": "jsonbinbro",
            "connected": True,
            "cached": False,
            "stats": {
                "users": len(data.get("users", [])),
                "talos": len(data.get("talos", [])),
                "replies": len(data.get("replies", []))
            }
        }
    except Exception as e:
        return {"status": "starting", "error": str(e)}

@app.on_event("startup")
async def startup_event():
    """Startup with pre-loading of data"""
    logger.info("Starting GuAn Microblogging Platform...")
    
    # Pre-load data into cache on startup
    for attempt in range(3):
        try:
            logger.info(f"Attempting to pre-load API data (attempt {attempt + 1}/3)...")
            data = await get_jsonbin_data(force_refresh=True)
            if data:
                logger.info(f"Successfully pre-loaded data: {len(data.get('users', []))} users, {len(data.get('talos', []))} talos")
                break
        except Exception as e:
            logger.error(f"Pre-load attempt {attempt + 1} failed: {str(e)}")
            if attempt < 2:
                await asyncio.sleep(5)
    
    # Try to ensure wa_guan account exists, but don't block startup
    for attempt in range(3):
        try:
            await ensure_wa_guan_account()
            logger.info("Startup completed successfully")
            break
        except Exception as e:
            logger.error(f"Startup attempt {attempt + 1} failed: {str(e)}")
            if attempt < 2:
                logger.info(f"Retrying in 5 seconds...")
                await asyncio.sleep(5)
            else:
                logger.warning("Could not verify/create wa_guan account on startup. Account will be created on first API call if needed.")

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