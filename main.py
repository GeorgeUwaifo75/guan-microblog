# main.py - With Working Search and Original Trending System
# Push notifications removed to fix mobile display issues

from fastapi import FastAPI, HTTPException, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import hashlib
import secrets
import uuid

from pywebpush import webpush, WebPushException

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


VAPID_PRIVATE_KEY = "7ySoI9ylX4CeQE7t8i6TjoHM9s0sj5lRsgDrx8TfAlM"
VAPID_PUBLIC_KEY = "BHD-KUGePj5TuQwWfK85ImeAi7ncRiq-oEgTmSPPke_eoDDyndcPHEf7nhMJpIfT3KCrRiZK6Z6g0gbMq9-C4bQ"
VAPID_CLAIMS = {
    "sub": "mailto:geocorpsys@gmail.com"   # replace with your email
}

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
    days: int
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

api_cache = APICache(ttl_seconds=30)

class PersistentAPICache:
    """File-based cache that persists across server restarts"""
    def __init__(self, cache_file="api_cache.json", ttl_seconds=300):
        self.cache_file = cache_file
        self.ttl = ttl_seconds
        self._load_cache()
    
    def _load_cache(self):
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
        try:
            with open(self.cache_file, 'w') as f:
                json.dump({
                    'data': self.cache,
                    'timestamp': self.timestamp
                }, f)
        except Exception as e:
            logger.error(f"Error saving persistent cache: {e}")
    
    def get(self, key):
        if self.cache and time.time() - self.timestamp < self.ttl:
            return self.cache.get(key)
        return None
    
    def set(self, key, data):
        self.cache = {key: data}
        self.timestamp = time.time()
        self._save_cache()
    
    def clear(self):
        self.cache = {}
        self.timestamp = 0
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

# Replace api_cache with persistent cache
api_cache = PersistentAPICache(ttl_seconds=300)

# ===== WA_GUAN ACCOUNT CONFIGURATION =====
WA_GUAN_USER_ID = "wa_guan"
WA_GUAN_FIRST_NAME = "Support"
WA_GUAN_LAST_NAME = "GuAn"
WA_GUAN_EMAIL = "support@guan.com"

async def ensure_wa_guan_account():
    """Ensure the @wa_guan support account exists with welcome post"""
    try:
        data = await get_jsonbin_data()
        
        wa_guan_exists = False
        wa_guan_user = None
        for user in data.get("users", []):
            if user.get("user_id") == WA_GUAN_USER_ID:
                wa_guan_exists = True
                wa_guan_user = user
                break
        
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
        logger.warning("Could not verify/create wa_guan account. Will retry on next request.")





async def get_jsonbin_data(force_refresh=False, fast_mode=False) -> Dict:
    """Fetch data with optional fast mode for login (fewer retries)."""
    if not force_refresh:
        cached_data = api_cache.get("jsonbin_data")
        if cached_data:
            return cached_data

    max_retries = 2 if fast_mode else 3   # fewer retries for login
    retry_delay = 1 if fast_mode else 2   # shorter delay
    
    
    for attempt in range(max_retries):
        try:
            for attempt in range(max_retries):
                try:
                    url = f"{API_BASE}/bins/{BIN_ID}?api_key={API_KEY}"
                    
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
                                await asyncio.sleep(retry_delay * (attempt + 1))
                                continue
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
                    cached = api_cache.get("jsonbin_data")
                    if cached:
                        logger.warning("Using cached data due to error")
                        return cached
                    raise HTTPException(status_code=503, detail=f"Unable to access API: {str(e)}")
            
            cached = api_cache.get("jsonbin_data")
            if cached:
                logger.warning("Using cached data as final fallback")
                return cached
            raise HTTPException(status_code=503, detail="Unable to access API after multiple attempts")
        
        except Exception:
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            # fallback to cached data or raise
    # ...

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
                # ✅ CRITICAL FIX: Update the cache immediately with the new data
                # This ensures that the session token and other changes are reflected
                # in subsequent requests without forcing a full API fetch.
                api_cache.set("jsonbin_data", data)
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

# ========== WALLET / TaC (Talo Coin) SYSTEM ==========
# Milestone thresholds (in TaC) that trigger a one-time congratulatory
# celebration on the frontend the first time a user's balance reaches them.
TAC_MILESTONES = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 1]

# Minimum character count a talo/post must have to earn any TaC at all.
TAC_MIN_TALO_CHARS = 150

TAC_PER_TALO_REGULAR = 0.0001
TAC_PER_TALO_PREMIUM = 0.001
TAC_PER_REPLY_REGULAR = 0.00005
TAC_PER_REPLY_PREMIUM = 0.0005

# Lifetime supply cap: once this many TaC have ever been minted (awarded for
# talos/replies), no more can be created in any form - this is a hard,
# permanent ceiling on total creation, not a live "coins in circulation"
# count. Deleting a post burns its TaC back out of that user's wallet, but
# does NOT free up more room to mint - otherwise a delete/recreate cycle
# could be used to mint far beyond the cap. Peer-to-peer transfers
# (@sendtac) move already-minted TaC between wallets and never count
# against this cap either, since no new TaC is created by a transfer.
TAC_MAX_SUPPLY = 30000.0

def get_tac_total_minted(data: dict) -> float:
    return round(data.get("tac_total_minted", 0.0), 6)

def get_tac_remaining_supply(data: dict) -> float:
    return round(max(0.0, TAC_MAX_SUPPLY - get_tac_total_minted(data)), 6)

def award_tac(data: dict, user: dict, amount: float):
    """Mints up to `amount` new TaC into a user's wallet (in place),
    respecting the global TAC_MAX_SUPPLY lifetime cap. If the cap has
    already been reached, nothing is awarded; if `amount` would push the
    cumulative minted total past the cap, only the remaining headroom is
    awarded. Returns (new_balance, newly_crossed_milestones, actually_awarded).
    Rounded to 6 decimal places to avoid floating point drift from the very
    small per-action amounts."""
    if amount <= 0:
        return round(user.get("wallet_balance", 0.0), 6), [], 0.0

    remaining_supply = get_tac_remaining_supply(data)
    if remaining_supply <= 0:
        # Lifetime TaC supply cap has been reached - no further additions.
        return round(user.get("wallet_balance", 0.0), 6), [], 0.0

    actual_amount = round(min(amount, remaining_supply), 6)
    if actual_amount <= 0:
        return round(user.get("wallet_balance", 0.0), 6), [], 0.0

    old_balance = round(user.get("wallet_balance", 0.0), 6)
    new_balance = round(old_balance + actual_amount, 6)
    user["wallet_balance"] = new_balance

    data["tac_total_minted"] = round(get_tac_total_minted(data) + actual_amount, 6)

    already_reached = user.setdefault("wallet_milestones", [])
    newly_crossed = []
    for milestone in TAC_MILESTONES:
        if new_balance >= milestone and milestone not in already_reached:
            already_reached.append(milestone)
            newly_crossed.append(milestone)

    return new_balance, newly_crossed, actual_amount

def credit_wallet_transfer(user: dict, amount: float):
    """Credits `amount` TaC to a user's wallet as part of a peer-to-peer
    @sendtac transfer. This only moves TaC that has already been minted
    from one wallet to another, so it does NOT count against
    TAC_MAX_SUPPLY. Returns (new_balance, newly_crossed_milestones)."""
    if amount <= 0:
        return round(user.get("wallet_balance", 0.0), 6), []

    old_balance = round(user.get("wallet_balance", 0.0), 6)
    new_balance = round(old_balance + amount, 6)
    user["wallet_balance"] = new_balance

    already_reached = user.setdefault("wallet_milestones", [])
    newly_crossed = []
    for milestone in TAC_MILESTONES:
        if new_balance >= milestone and milestone not in already_reached:
            already_reached.append(milestone)
            newly_crossed.append(milestone)

    return new_balance, newly_crossed

def deduct_tac(user: dict, amount: float):
    """Debits `amount` TaC from a user's wallet (in place). Floors at 0 so a
    balance never goes negative - e.g. if a user already sent away TaC via
    @sendtac before deleting the post that originally earned it. Milestones
    already reached are treated as permanent achievements and are not
    revoked on a later deduction. Note: this intentionally does NOT reduce
    tac_total_minted - see TAC_MAX_SUPPLY comment above. Returns the new
    balance."""
    if amount <= 0:
        return round(user.get("wallet_balance", 0.0), 6)

    old_balance = round(user.get("wallet_balance", 0.0), 6)
    new_balance = round(max(0.0, old_balance - amount), 6)
    user["wallet_balance"] = new_balance
    return new_balance

def organize_replies_hierarchically(replies):
    """Organize replies into a hierarchical tree structure"""
    reply_dict = {}
    top_level_replies = []
    
    for reply in replies:
        reply["child_replies"] = []
        reply["child_reply_count"] = 0
        reply_dict[reply["id"]] = reply
    
    for reply in replies:
        parent_id = reply.get("parent_reply_id")
        if parent_id and parent_id in reply_dict:
            reply_dict[parent_id]["child_replies"].append(reply)
            reply_dict[parent_id]["child_reply_count"] = len(reply_dict[parent_id]["child_replies"])
        elif not parent_id:
            top_level_replies.append(reply)
    
    top_level_replies.sort(key=lambda x: x.get("created_at", ""))
    
    def sort_children_recursively(reply_list):
        for reply in reply_list:
            reply["child_replies"].sort(key=lambda x: x.get("created_at", ""))
            sort_children_recursively(reply["child_replies"])
    
    sort_children_recursively(top_level_replies)
    
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

class SendTacRequest(BaseModel):
    recipient_id: str
    amount: float

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
            for user in data.get("users", []):
                if user["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{user['first_name']} {user['last_name']}"
                    talo["user_photo"] = user.get("profile_photo")
                    break
            talo["reply_count"] = len([r for r in data.get("replies", []) 
                                       if r.get("parent_talo_id") == talo["id"]])
            matched_posts.append(talo)
    
    if query_lower.startswith('@'):
        username = query_lower[1:]
        for user in data.get("users", []):
            if username in user.get("user_id", "").lower():
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
    
    matched_posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return matched_posts

async def search_users(search_query: str, data: Dict) -> List[Dict]:
    """Search for users by user_id or name"""
    query_lower = search_query.lower().strip()
    
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
        "must_change_password": False,
        "user_category": "Normal",
        "followers_count": 0,
        "following_count": 0,
        "talos_count": 0,
        "first_login_done": False,
        "wallet_balance": 0.0,
        "wallet_milestones": [],
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat()
    }
    
    if "users" not in data:
        data["users"] = []
    data["users"].append(new_user)
    await save_jsonbin_data(data)
    
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
    # 1. Force a fresh fetch of the latest data for every login attempt.
    # We intentionally bypass the shared cache here (force_refresh=True):
    # that cache can hold data for up to 5 minutes, and login must never
    # authenticate against stale residue - e.g. a password that was just
    # changed, an account that was just deactivated, or a session token
    # left over from a different login. fast_mode still keeps retries/
    # timeouts short so this stays quick.
    data = await get_jsonbin_data(force_refresh=True, fast_mode=True)
    
    # 2. Ensure wa_guan exists (async, non-blocking)
    if not any(u.get('user_id') == WA_GUAN_USER_ID for u in data.get('users', [])):
        asyncio.create_task(ensure_wa_guan_account())   # fire and forget

    # 3. Authenticate user/admin (same logic as before)
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
        response = JSONResponse(content={"success": True, "redirect": "/admin"})
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
            response = JSONResponse(content={"success": True, "redirect": "/admin"})
            response.set_cookie(key="session_token", value=token, httponly=True)
            return response
    
    for user in data.get("users", []):
        if user["user_id"] == login_data.user_id and verify_password(login_data.password, user["password_hash"]):
            if not user.get("is_active"):
                raise HTTPException(status_code=403, detail="Account deactivated")
            token = generate_token()
            # Existing users created before this feature shipped won't have a
            # "first_login_done" field at all, so relying on that alone would
            # default to False and wrongly celebrate on their very next login.
            # We also check whether "session_token" was already on the record:
            # that key is only ever added the first time someone logs in, so
            # any account that has logged in before (old or new) already has
            # it. Only an account with neither field counts as a genuine
            # first-ever login.
            has_logged_in_before = "session_token" in user
            is_first_login = (not user.get("first_login_done", False)) and (not has_logged_in_before)
            user["session_token"] = token
            user["last_active"] = datetime.now().isoformat()
            user["first_login_done"] = True
    
            # 4. After successful auth, update session_token and save
            await save_jsonbin_data(data)   # this will save the updated token

            # 5. Return a lightweight JSON response with the cookie set.
            # IMPORTANT: We intentionally do NOT return a RedirectResponse here.
            # fetch() follows redirects automatically, which meant the login
            # request itself was forced to also download and render the full
            # /dashboard page before resolving - a slow, heavy response that
            # could time out and make a correct login appear to fail, requiring
            # the user to retry. Returning JSON keeps the login request small
            # and fast; the frontend performs a single, separate navigation to
            # /dashboard afterward.
            response = JSONResponse(content={"success": True, "redirect": "/dashboard", "first_login": is_first_login})
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
    
    all_promoted_talos = []
    regular_talos = []
    
    for talo in talos:
        for u in data.get("users", []):
            if u["user_id"] == talo["user_id"]:
                talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                talo["user_photo"] = u.get("profile_photo")
                break
        talo["reply_count"] = len([r for r in data.get("replies", []) if r.get("parent_talo_id") == talo["id"]])
        
        if talo.get("promoted", False):
            all_promoted_talos.append(talo)
        else:
            if followed_user_ids and talo["user_id"] in followed_user_ids:
                regular_talos.append(talo)
            elif not followed_user_ids or len(followed_user_ids) <= 1:
                regular_talos.append(talo)
    
    regular_talos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    import random
    selected_promoted_talos = []
    
    if all_promoted_talos:
        all_promoted_talos.sort(key=lambda x: (x.get("promotion_level", 0), x.get("created_at", "")), reverse=True)
        
        for promoted_talo in all_promoted_talos:
            if random.random() < 0.25:
                selected_promoted_talos.append(promoted_talo)
    
    personal_talos = selected_promoted_talos + regular_talos
    personal_talos.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
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
        "promoted_total_count": promoted_total_count,
        "user_email": user.get("email", ""),
        "vapid_public_key": VAPID_PUBLIC_KEY
    })

@app.get("/api/get_promoted_posts")
async def get_promoted_posts(request: Request):
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
            for u in data.get("users", []):
                if u["user_id"] == talo["user_id"]:
                    talo["user_name"] = f"{u['first_name']} {u['last_name']}"
                    talo["user_photo"] = u.get("profile_photo")
                    break
            talo["reply_count"] = len([r for r in data.get("replies", []) if r.get("parent_talo_id") == talo["id"]])
            promoted_posts.append(talo)
    
    promoted_posts.sort(key=lambda x: (x.get("promotion_level", 0), x.get("created_at", "")), reverse=True)
    
    return {"promoted_posts": promoted_posts}

# ===== SEARCH ENDPOINTS =====
@app.get("/api/search")
async def search_global(request: Request, q: str = ""):
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not q or len(q.strip()) < 1:
        return {"posts": [], "users": [], "total_posts": 0, "total_users": 0}
    
    data = await get_jsonbin_data()
    
    matched_posts = await search_all_posts(q, data)
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
        "talos": user_talos[:50],
        "paystack_public_key": PAYSTACK_PUBLIC_KEY,
        "user_email": current_user.get("email", ""),
        "vapid_public_key": VAPID_PUBLIC_KEY
    })

@app.get("/post/{talo_id}", response_class=HTMLResponse)
async def view_post(request: Request, talo_id: str, reply_id: str = None):
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
    
    # Increment view count
    talo["views"] = talo.get("views", 0) + 1
    await save_jsonbin_data(data)   # save the updated data
    
    for u in data.get("users", []):
        if u["user_id"] == talo["user_id"]:
            talo["user_name"] = f"{u['first_name']} {u['last_name']}"
            talo["user_photo"] = u.get("profile_photo")
            break
    
    all_replies = []
    for r in data.get("replies", []):
        if r.get("parent_talo_id") == talo_id:
            for u in data.get("users", []):
                if u["user_id"] == r["user_id"]:
                    r["user_name"] = f"{u['first_name']} {u['last_name']}"
                    r["user_photo"] = u.get("profile_photo")
                    break
            all_replies.append(r)
    
    replies = organize_replies_hierarchically(all_replies)
    
    return templates.TemplateResponse("post.html", {
        "request": request,
        "user": user,
        "talo": talo,
        "replies": replies,
        "highlight_reply_id": reply_id,
        "vapid_public_key": VAPID_PUBLIC_KEY
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
    
    # ----- NEW: Character limit based on premium status -----
    max_len = 500 if user.get("is_premium", False) else 250
    if len(content) > max_len:
        raise HTTPException(status_code=400, detail=f"Talo cannot exceed {max_len} characters")
    # --------------------------------------------------------
    
    talo = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "content": content,
        "photos": photos,
        "likes": 0,
        "dislikes": 0,
        "retalos": 0,
        "reply_count": 0,
        "views": 0,                     # <--- add this line
        "created_at": datetime.now().isoformat(),
        "promoted": False,
        "promotion_level": 0
    }
    
    # Was this the user's very first talo? Used by the frontend to trigger a
    # one-time "first post" celebration.
    is_first_talo = user.get("talos_count", 0) == 0

    # ----- Wallet: award TaC for qualifying posts (subject to the 30,000
    # TaC lifetime supply cap - see award_tac) -----
    tac_eligible = 0.0
    if len(content) >= TAC_MIN_TALO_CHARS:
        tac_eligible = TAC_PER_TALO_PREMIUM if user.get("is_premium", False) else TAC_PER_TALO_REGULAR
    wallet_balance, milestones_reached, tac_earned = award_tac(data, user, tac_eligible)
    supply_capped = tac_eligible > 0 and tac_earned < tac_eligible

    # Record exactly how much TaC this specific talo earned its author, so
    # that if it's later deleted we can reverse precisely this amount -
    # recomputing at delete-time would be wrong if the user's premium status
    # changes in between (or if the supply cap only allowed a partial award).
    talo["tac_earned"] = tac_earned

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
    
    return {
        "message": "Talo created successfully",
        "talo_id": talo["id"],
        "first_talo": is_first_talo,
        "tac_earned": tac_earned,
        "wallet_balance": wallet_balance,
        "milestones_reached": milestones_reached,
        "tac_supply_capped": supply_capped
    }

"""  
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
      follows_replier = False
      for follow in data.get("follows", []):
          if follow.get("follower_id") == talo_owner_id and follow.get("following_id") == user["user_id"]:
              follows_replier = True
              break
      
      if follows_replier:
          if "notifications" not in data:
              data["notifications"] = []
          
          # Create a clickable link in the notification
          notification = {
              "id": str(uuid.uuid4()),
              "user_id": talo_owner_id,
              "type": "reply",
              "message": f"@{user['user_id']} replied to your post",
              "related_talo_id": parent_talo_id,  # This is the post ID
              "reply_id": reply["id"],  # This is the reply ID
              "from_user_id": user["user_id"],
              "read": False,
              "created_at": datetime.now().isoformat()
          }
          data["notifications"].append(notification)

    await save_jsonbin_data(data)
    
    return {"message": "Reply created successfully", "reply_id": reply["id"]}
"""

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
                
                # Example for like_talo (inside the else block after adding like)
                await send_push_notification(
                    talo_owner_id,
                    f"@{user['user_id']} liked your talo",
                    f"💎 {talo.get('content', '')[:50]}...",
                    icon=user.get("profile_photo"),
                    data={"url": f"/post/{talo_id}"}
                )
                
                return {"liked": True, "count": talo["likes"]}
    
    
    
    await save_jsonbin_data(data)
    return {"liked": False, "count": 0}

@app.post("/api/dislike/{talo_id}")
async def dislike_talo(talo_id: str, request: Request):
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
    
    # Ensure dislikes collection exists
    if "dislikes" not in data:
        data["dislikes"] = []
    
    # Check if user already disliked this talo
    dislike_index = None
    for i, d in enumerate(data["dislikes"]):
        if d.get("talo_id") == talo_id and d.get("user_id") == user["user_id"]:
            dislike_index = i
            break
    
    # Find the talo
    talo = None
    for t in data["talos"]:
        if t["id"] == talo_id:
            talo = t
            break
    if not talo:
        raise HTTPException(status_code=404, detail="Talo not found")
    
    if dislike_index is not None:
        # Remove dislike (toggle off)
        data["dislikes"].pop(dislike_index)
        talo["dislikes"] = max(0, talo.get("dislikes", 0) - 1)
        await save_jsonbin_data(data)
        return {"disliked": False, "count": talo["dislikes"]}
    else:
        # Add dislike (toggle on)
        data["dislikes"].append({
            "talo_id": talo_id,
            "user_id": user["user_id"],
            "created_at": datetime.now().isoformat()
        })
        talo["dislikes"] = talo.get("dislikes", 0) + 1
        await save_jsonbin_data(data)
        return {"disliked": True, "count": talo["dislikes"]}

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
        
        await send_push_notification(
            user_id_to_follow,
            f"@{user['user_id']} started following you",
            f"👥 New follower!",
            icon=user.get("profile_photo"),
            data={"url": f"/profile/{user['user_id']}"}
        )
        
        return {"following": True, "followers_count": target_user["followers_count"]}



from fastapi.responses import FileResponse

@app.get("/sw.js")
async def service_worker():
    sw_path = STATIC_DIR / "sw.js"
    if not sw_path.exists():
        raise HTTPException(status_code=404, detail="Service worker not found")
    return FileResponse(sw_path, media_type="application/javascript")

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
            user["must_change_password"] = False
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
        "total_payments": len([p for p in payments if p.get("status") == "approved"]),
        "tac_total_minted": get_tac_total_minted(data),
        "tac_remaining_supply": get_tac_remaining_supply(data),
        "tac_supply_cap": TAC_MAX_SUPPLY
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
            "must_change_password": u.get("must_change_password", False),
            "talos_count": u.get("talos_count", 0),
            "wallet_balance": round(u.get("wallet_balance", 0.0), 6),
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

DEFAULT_RESET_PASSWORD = "0000"

@app.post("/api/admin/reset_user_password/{user_id}")
async def reset_user_password(user_id: str, request: Request):
    """Super Admin only - Reset a user's password to the default temporary
    password when there's an account issue (locked out, compromised, etc).
    The account is flagged so the user is required to set a new password
    the next time they log in, and any existing session is invalidated so
    the reset takes effect immediately."""
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

    if admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can reset user passwords")

    for user in data.get("users", []):
        if user["user_id"] == user_id:
            user["password_hash"] = hash_password(DEFAULT_RESET_PASSWORD)
            user["must_change_password"] = True
            # Invalidate any active session so the old login can't keep being
            # used, and so the user is forced through the login screen with
            # the new temporary password.
            user["session_token"] = None
            await save_jsonbin_data(data)
            logger.info(f"Password reset by super admin {admin['user_id']} for user {user_id}")
            return {
                "message": f"Password for @{user_id} has been reset to the default temporary password. "
                           f"They'll be required to set a new password the next time they log in."
            }

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

    if not admin:
        raise HTTPException(status_code=401, detail="Admin not found")

    if admin.get("role") != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Administrator can delete users")

    # Protect the support account
    if user_id == WA_GUAN_USER_ID:
        raise HTTPException(status_code=403, detail="The support account cannot be deleted")

    # Find user to delete
    user_index = None
    for i, user in enumerate(data.get("users", [])):
        if user["user_id"] == user_id:
            user_index = i
            break

    if user_index is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Remove all associated data
    data["talos"] = [t for t in data.get("talos", []) if t.get("user_id") != user_id]
    data["replies"] = [r for r in data.get("replies", []) if r.get("user_id") != user_id]
    data["likes"] = [l for l in data.get("likes", []) if l.get("user_id") != user_id]
    data["dislikes"] = [d for d in data.get("dislikes", []) if d.get("user_id") != user_id]
    data["follows"] = [f for f in data.get("follows", []) if f.get("follower_id") != user_id and f.get("following_id") != user_id]
    data["notifications"] = [n for n in data.get("notifications", []) if n.get("user_id") != user_id and n.get("from_user_id") != user_id]
    data["payments"] = [p for p in data.get("payments", []) if p.get("user_id") != user_id]
    data["premium_requests"] = [pr for pr in data.get("premium_requests", []) if pr.get("user_id") != user_id]
    data["promotions"] = [p for p in data.get("promotions", []) if p.get("user_id") != user_id]

    # Finally, remove the user
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
    
    # Validate amount matches the days
    expected_amounts = {3: 600, 7: 1100, 30: 3000}
    if promotion.amount != expected_amounts.get(promotion.days, 0):
        raise HTTPException(status_code=400, detail="Invalid amount for selected duration")
    
    promotion_id = str(uuid.uuid4())
    promotion_record = {
        "id": promotion_id,
        "talo_id": promotion.talo_id,
        "user_id": user["user_id"],
        "user_email": user.get("email", ""),
        "amount": promotion.amount,
        "days": promotion.days,
        "payment_method": promotion.payment_method,
        "status": "pending_payment",  # pending_payment, payment_verified, activated, expired
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=promotion.days)).isoformat()
    }
    
    if "promotions" not in data:
        data["promotions"] = []
    data["promotions"].append(promotion_record)
    await save_jsonbin_data(data)
    
    return {
        "promotion_id": promotion_id,
        "amount": promotion.amount,
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
    
    body = await request.json()
    transaction_ref = body.get("transaction_ref")
    payment_status = body.get("status")
    
    promotion = None
    promotion_index = None
    for i, p in enumerate(data.get("promotions", [])):
        if p["id"] == promotion_id:
            promotion = p
            promotion_index = i
            break
    
    if not promotion:
        raise HTTPException(status_code=404, detail="Promotion not found")
    
    if promotion["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    # Verify payment with Paystack (optional but recommended)
    if payment_status == "success":
        # Mark promotion as payment verified but pending admin activation
        promotion["status"] = "payment_verified"
        promotion["transaction_ref"] = transaction_ref
        promotion["payment_confirmed_at"] = datetime.now().isoformat()
        
        # Add to payments record
        if "payments" not in data:
            data["payments"] = []
        data["payments"].append({
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "amount": promotion["amount"],
            "days": promotion["days"],
            "payment_method": "paystack",
            "transaction_ref": transaction_ref,
            "status": "completed",
            "promotion_id": promotion_id,
            "created_at": datetime.now().isoformat()
        })
        
        # Auto-activate promotion (or set for admin approval)
        promotion["status"] = "activated"
        
        # Mark the talo as promoted
        for talo in data.get("talos", []):
            if talo["id"] == promotion["talo_id"]:
                talo["promoted"] = True
                talo["promotion_level"] = promotion["days"] // 3  # Level based on days
                talo["promoted_at"] = datetime.now().isoformat()
                talo["promotion_expires_at"] = promotion["expires_at"]
                break
        
        # Send notification to user
        if "notifications" not in data:
            data["notifications"] = []
        data["notifications"].append({
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "type": "promotion_activated",
            "message": f"Your {promotion['days']}-day promotion has been activated! Your post will be featured.",
            "related_talo_id": promotion["talo_id"],
            "read": False,
            "created_at": datetime.now().isoformat()
        })
        
        await save_jsonbin_data(data)
        
        return {"message": "Promotion activated successfully!"}
    else:
        promotion["status"] = "payment_failed"
        await save_jsonbin_data(data)
        raise HTTPException(status_code=400, detail="Payment verification failed")


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
    
    # ----- Wallet: award TaC for the reply (subject to the 30,000 TaC
    # lifetime supply cap - see award_tac) -----
    reply_tac_eligible = TAC_PER_REPLY_PREMIUM if user.get("is_premium", False) else TAC_PER_REPLY_REGULAR
    wallet_balance, milestones_reached, reply_tac = award_tac(data, user, reply_tac_eligible)
    supply_capped = reply_tac < reply_tac_eligible

    # Recorded so that a future "delete reply" feature can reverse exactly
    # this amount (there is no reply-deletion endpoint yet).
    reply["tac_earned"] = reply_tac
    
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
    # Example for like_talo (inside the else block after adding like)
    await send_push_notification(
        talo_owner_id,
        f"@{user['user_id']} Replied your talo",
        "You got a 💬 to your post.",
        icon=user.get("profile_photo"),
        data={"url": f"/post/{parent_talo_id}"}
    )
    return {
        "message": "Reply created successfully",
        "reply_id": reply["id"],
        "tac_earned": reply_tac,
        "wallet_balance": wallet_balance,
        "milestones_reached": milestones_reached,
        "tac_supply_capped": supply_capped
    }


def format_tac_str(value: float) -> str:
    """Formats a TaC amount trimmed of trailing zeros, mirroring the
    frontend's formatTac() so notification/messages read consistently."""
    s = f"{value:.6f}".rstrip('0').rstrip('.')
    return s if s else "0"

@app.post("/api/send_tac")
async def send_tac(payload: SendTacRequest, request: Request):
    """Transfers TaC from the logged-in user's wallet to another user's
    wallet. Powers the '@sendtac' command - both the guided modal flow
    (typing '@sendtac' alone) and the one-line directive
    '@sendtac @beneficiary amount'."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = await get_jsonbin_data()
    sender = None
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            sender = u
            break

    if not sender:
        raise HTTPException(status_code=401, detail="User not found")

    recipient_id = (payload.recipient_id or "").strip().lstrip("@")
    if not recipient_id:
        raise HTTPException(status_code=400, detail="Please provide a valid beneficiary account ID.")

    if recipient_id.lower() == sender["user_id"].lower():
        raise HTTPException(status_code=400, detail="You cannot send TaC to yourself.")

    amount = round(payload.amount, 6) if payload.amount is not None else 0.0
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Please enter a valid amount greater than zero.")

    sender_balance = round(sender.get("wallet_balance", 0.0), 6)
    if amount > sender_balance:
        raise HTTPException(status_code=400, detail="You cannot send more TaC than you currently have.")

    recipient = None
    for u in data.get("users", []):
        if u.get("user_id", "").lower() == recipient_id.lower():
            recipient = u
            break

    if not recipient:
        raise HTTPException(status_code=404, detail=f"No GuAn account found with the ID @{recipient_id}.")

    if not recipient.get("is_active", True):
        raise HTTPException(status_code=400, detail="This account is currently deactivated and cannot receive TaC.")

    # Move the funds: deduct from sender, credit the recipient. This is a
    # transfer of already-minted TaC, so it uses credit_wallet_transfer()
    # rather than award_tac() and does not touch the 30,000 TaC supply cap.
    new_sender_balance = deduct_tac(sender, amount)
    new_recipient_balance, recipient_milestones_reached = credit_wallet_transfer(recipient, amount)

    # Alert the recipient that they received TaC from a specific sender.
    if "notifications" not in data:
        data["notifications"] = []
    data["notifications"].append({
        "id": str(uuid.uuid4()),
        "user_id": recipient["user_id"],
        "type": "tac_received",
        "message": f"@{sender['user_id']} sent you {format_tac_str(amount)} TaC!",
        "from_user_id": sender["user_id"],
        "amount": amount,
        "read": False,
        "created_at": datetime.now().isoformat()
    })

    await save_jsonbin_data(data)

    # Best-effort push notification to the recipient, matching the pattern
    # used elsewhere (likes, replies, etc.) - failures here shouldn't block
    # a transfer that already succeeded.
    try:
        await send_push_notification(
            recipient["user_id"],
            f"@{sender['user_id']} sent you TaC 🪙",
            f"You received {format_tac_str(amount)} TaC!",
            icon=sender.get("profile_photo"),
            data={"url": "/dashboard"}
        )
    except Exception:
        pass

    return {
        "message": "TaC sent successfully",
        "amount": amount,
        "recipient_id": recipient["user_id"],
        "sender_balance": new_sender_balance
    }


@app.get("/api/wallet_balance")
async def get_wallet_balance(request: Request):
    """Returns the logged-in user's current TaC wallet balance.
    Powers the '@mytac' command and any on-demand wallet refresh."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = await get_jsonbin_data()
    for u in data.get("users", []):
        if u.get("session_token") == session_token:
            return {"wallet_balance": round(u.get("wallet_balance", 0.0), 6)}

    raise HTTPException(status_code=401, detail="User not found")


@app.get("/api/tac_supply")
async def get_tac_supply(request: Request):
    """Returns the global TaC lifetime supply status: how much has ever
    been minted, how much room is left under the 30,000 cap, and whether
    the cap has been reached. Requires login, but is not tied to any one
    user's own wallet."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = await get_jsonbin_data()
    is_authenticated = any(u.get("session_token") == session_token for u in data.get("users", []))
    if not is_authenticated:
        raise HTTPException(status_code=401, detail="User not found")

    total_minted = get_tac_total_minted(data)
    remaining = get_tac_remaining_supply(data)
    return {
        "total_supply_cap": TAC_MAX_SUPPLY,
        "total_minted": total_minted,
        "remaining_supply": remaining,
        "supply_exhausted": remaining <= 0
    }


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
    
    # Re-talo or re-post
    await send_push_notification(
        original_user_id,
        f"@{user['user_id']} reposted your talo",
        f"💬 {talo.get('content', '')[:50]}...",
        icon=user.get("profile_photo"),
        data={"url": f"/post/{original_user_id}"}
    )
    
    
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
    
    # Reverse any TaC this post originally earned its author, since the
    # content that qualified it for the reward no longer exists.
    tac_to_reverse = talo.get("tac_earned", 0.0)
    new_wallet_balance = deduct_tac(user, tac_to_reverse) if tac_to_reverse else round(user.get("wallet_balance", 0.0), 6)
    
    # Remove the post
    data["talos"].pop(talo_index)
    
    # Update user's talos count
    user["talos_count"] = max(0, user.get("talos_count", 0) - 1)
    
    await save_jsonbin_data(data)
    
    return {"message": "Post deleted successfully", "tac_reversed": tac_to_reverse, "wallet_balance": new_wallet_balance}


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
    
    # Create the nested reply - CRITICAL: Set parent_talo_id to the main post ID
    nested_reply = {
        "id": str(uuid.uuid4()),
        "parent_reply_id": parent_reply_id,
        "parent_talo_id": talo_id,  # This links to the main post
        "user_id": user["user_id"],
        "content": content,
        "photos": [],
        "likes": 0,
        "created_at": datetime.now().isoformat()
    }
    
    if "replies" not in data:
        data["replies"] = []
    data["replies"].append(nested_reply)
    
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
                "message": f"@{user['user_id']} replied to your comment",
                "related_talo_id": talo_id,
                "parent_reply_id": parent_reply_id,
                "reply_id": nested_reply["id"],
                "from_user_id": user["user_id"],
                "read": False,
                "created_at": datetime.now().isoformat()
            }
            data["notifications"].append(notification)
    
    await save_jsonbin_data(data)
    
    return {"message": "Reply posted successfully", "reply_id": nested_reply["id"]}


# Add this endpoint to main.py

@app.post("/api/confirm_premium_payment")
async def confirm_premium_payment(request: Request):
    """Confirm premium payment and upgrade user"""
    body = await request.json()
    transaction_ref = body.get("transaction_ref")
    user_id = body.get("user_id")
    status = body.get("status")
    
    if status != "success":
        raise HTTPException(status_code=400, detail="Payment was not successful")
    
    data = await get_jsonbin_data()
    
    # Find the user
    user = None
    user_index = None
    for i, u in enumerate(data.get("users", [])):
        if u["user_id"] == user_id:
            user = u
            user_index = i
            break
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already premium
    if user.get("is_premium", False):
        return {"message": "User is already premium"}
    
    # Upgrade user to premium
    user["is_premium"] = True
    user["premium_activated_at"] = datetime.now().isoformat()
    user["premium_payment_ref"] = transaction_ref
    
    if user_index is not None:
        data["users"][user_index] = user
    
    # Record the payment
    if "payments" not in data:
        data["payments"] = []
    data["payments"].append({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "amount": 7800,
        "payment_method": "paystack",
        "transaction_ref": transaction_ref,
        "status": "approved",
        "type": "premium_upgrade",
        "created_at": datetime.now().isoformat(),
        "processed_at": datetime.now().isoformat()
    })
    
    # Send notification to user
    if "notifications" not in data:
        data["notifications"] = []
    data["notifications"].append({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "premium_upgraded",
        "message": "🎉 Congratulations! You are now a premium user. Enjoy enhanced visibility!",
        "read": False,
        "created_at": datetime.now().isoformat()
    })
    
    await save_jsonbin_data(data)
    
    return {"message": "Premium upgrade successful", "is_premium": True}


@app.post("/api/register_push_subscription")
async def register_push_subscription(request: Request):
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
    subscription = body.get("subscription")
    if not subscription or not subscription.get("endpoint"):
        raise HTTPException(status_code=400, detail="Invalid subscription")

    # Ensure subscriptions list exists for this user
    if "push_subscriptions" not in data:
        data["push_subscriptions"] = []

    # Remove any existing subscription with the same endpoint (avoid duplicates)
    data["push_subscriptions"] = [
        s for s in data["push_subscriptions"]
        if not (s.get("user_id") == user["user_id"] and s.get("endpoint") == subscription["endpoint"])
    ]

    # Save the new subscription
    data["push_subscriptions"].append({
        "user_id": user["user_id"],
        "endpoint": subscription["endpoint"],
        "keys": subscription.get("keys", {}),
        "created_at": datetime.now().isoformat()
    })

    await save_jsonbin_data(data)
    return {"success": True}

@app.delete("/api/delete_push_subscription")
async def delete_push_subscription(request: Request):
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
    endpoint = body.get("endpoint")
    if not endpoint:
        raise HTTPException(status_code=400, detail="Endpoint missing")

    data["push_subscriptions"] = [
        s for s in data.get("push_subscriptions", [])
        if not (s.get("user_id") == user["user_id"] and s.get("endpoint") == endpoint)
    ]
    await save_jsonbin_data(data)
    return {"success": True}

@app.get("/offline", response_class=HTMLResponse)
async def offline_page(request: Request):
    return templates.TemplateResponse("offline.html", {"request": request})


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
            """Startup with pre-loading of data and background tasks"""
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
            
            # Start the promotion expiry background task
            asyncio.create_task(promotion_expiry_loop())
            logger.info("Promotion expiry checker started")


async def send_push_notification(user_id: str, title: str, body: str, icon: str = None, data: dict = None):
    """Send a push notification to all subscriptions of a user."""
    if not user_id:
        return

    db_data = await get_jsonbin_data()
    subscriptions = [
        s for s in db_data.get("push_subscriptions", [])
        if s.get("user_id") == user_id
    ]
    if not subscriptions:
        return

    # Prepare notification payload
    payload = {
        "title": title,
        "body": body,
        "icon": icon or "/static/ram-icon.png",   # Make sure you have a square icon
        "data": data or {},
        "badge": "/static/badge.png"              # optional, for Android
    }

    # Send to each subscription
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub["endpoint"],
                    "keys": sub["keys"]
                },
                data=json.dumps(payload),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=VAPID_CLAIMS
            )
        except WebPushException as e:
            # If subscription is expired, remove it
            if e.response and e.response.status_code == 410:
                db_data["push_subscriptions"] = [
                    s for s in db_data.get("push_subscriptions", [])
                    if s.get("endpoint") != sub["endpoint"]
                ]
                await save_jsonbin_data(db_data)
            else:
                print(f"Push error: {e}")

            
async def check_and_expire_promotions():
  """Background task to check and expire promotions that have passed their expiry date"""
  try:
      data = await get_jsonbin_data()
      now = datetime.now()
      updated = False
      
      for promotion in data.get("promotions", []):
          if promotion.get("status") == "activated" and promotion.get("expires_at"):
              expires_at = datetime.fromisoformat(promotion["expires_at"])
              if now > expires_at:
                  promotion["status"] = "expired"
                  # Remove promotion flag from talo
                  for talo in data.get("talos", []):
                      if talo["id"] == promotion["talo_id"]:
                          talo["promoted"] = False
                          talo["promotion_level"] = 0
                          break
                  updated = True
                  logger.info(f"Expired promotion for talo: {promotion['talo_id']}")
      
      if updated:
          await save_jsonbin_data(data)
          logger.info("Checked and updated expired promotions")
  except Exception as e:
      logger.error(f"Error checking expired promotions: {e}")

async def promotion_expiry_loop():
  """Loop that runs every hour to check for expired promotions"""
  while True:
      await asyncio.sleep(3600)  # Check every hour (3600 seconds)
      await check_and_expire_promotions()
      
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