import streamlit as st
import json
import hashlib
import secrets
from datetime import datetime
import os
from pathlib import Path
from html import escape

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Set page config
st.set_page_config(
    page_title="EIA Voice Platform",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional appearance
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .message-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .message-card.flagged {
        border-left: 4px solid #f44336;
        background: #ffebee;
    }
    
    .message-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 0.5rem;
        font-size: 0.9rem;
        color: #666;
    }
    
    .message-content {
        font-size: 1.1rem;
        color: #333;
        line-height: 1.6;
    }
    
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        background: transparent;
        color: #333;
        border: 1px solid rgba(0,0,0,0.08);
    }
    
    .badge-student, .badge-teacher, .badge-senator, .badge-admin, .badge-super-admin {
        background: transparent;
        color: #333;
        border: 1px solid rgba(0,0,0,0.08);
    }

    /* Outline-style buttons for a clean, professional look */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        padding: 0.45rem 1rem;
        font-weight: 600;
        background: transparent !important;
        color: #333 !important;
        border: 1px solid rgba(0,0,0,0.12) !important;
        box-shadow: none !important;
    }
    
    .fb-nav-item {
        display: flex;
        align-items: center;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        cursor: pointer;
        margin-bottom: 0.5rem;
        font-size: 1rem;
        font-weight: 500;
        color: #333;
    }
    
    .feed-container {
        max-width: 650px;
        margin: 0 auto;
    }
    
    .post-composer {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .post-composer-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: transparent;
        color: #333;
        font-weight: 700;
        text-align: center;
        line-height: 40px;
        border: 1px solid rgba(0,0,0,0.12);
    }
    
    .notification-item {
        padding: 0.75rem;
        background: transparent;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border: 1px solid rgba(0,0,0,0.06);
    }
    .notification-item.unread {
        background-color: rgba(10,102,194,0.04);
        border: 1px solid rgba(10,102,194,0.15);
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA MANAGEMENT
# ============================================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
MESSAGES_FILE = DATA_DIR / "messages.json"
ANONYMOUS_NAMES_FILE = DATA_DIR / "anonymous_names.json"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.json"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def load_json(filepath):
    """Load JSON data from file"""
    # Return sensible defaults and handle corrupt/empty files gracefully
    if filepath.exists():
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                # Ensure messages file always returns a dict with 'messages'
                if filepath == MESSAGES_FILE:
                    if not isinstance(data, dict):
                        return {"messages": []}
                    return data
                return data
        except (json.JSONDecodeError, ValueError):
            # Corrupt or empty file — return defaults depending on file
            if filepath == MESSAGES_FILE:
                return {"messages": []}
            return {}
    # File doesn't exist yet — provide sensible default for messages file
    if filepath == MESSAGES_FILE:
        return {"messages": []}
    return {}

def save_json(filepath, data):
    """Save JSON data to file"""
    # Ensure parent dir exists (in case caller uses subfolders)
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    # Create a timestamped backup for important files so we can restore later
    try:
        if filepath in (USERS_FILE, MESSAGES_FILE, ANONYMOUS_NAMES_FILE, NOTIFICATIONS_FILE):
            ts = datetime.utcnow().isoformat().replace(':', '-')
            backup_path = BACKUP_DIR / f"{filepath.name}.{ts}.bak.json"
            with open(backup_path, 'w') as bf:
                json.dump(data, bf, indent=2)
    except Exception:
        # Non-fatal: don't block saving if backup fails
        pass


def _latest_backup_for(filepath):
    """Return path to the latest backup file for given filepath, or None."""
    try:
        files = [p for p in BACKUP_DIR.iterdir() if p.name.startswith(filepath.name + '.') and p.name.endswith('.bak.json')]
        if not files:
            return None
        files.sort(key=lambda p: p.stat().st_mtime)
        return files[-1]
    except Exception:
        return None


def _restore_from_latest_backup(filepath):
    """Restore filepath by copying the latest backup if available."""
    latest = _latest_backup_for(filepath)
    if not latest:
        return False
    try:
        with open(latest, 'r') as bf:
            data = json.load(bf)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

def hash_password(password):
    """Hash password for secure storage"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_anonymous_id():
    """Generate a unique anonymous ID"""
    return f"ANON_{secrets.token_hex(4).upper()}"

def initialize_data():
    """Initialize data files if they don't exist"""
    if not USERS_FILE.exists():
        # Create super admin account
        users = {
            "superadmin": {
                "password": hash_password("admin123"),  # Change this!
                "role": "super_admin",
                "name": "Super Administrator"
            }
        }
        save_json(USERS_FILE, users)
    
    if not MESSAGES_FILE.exists():
        save_json(MESSAGES_FILE, {"messages": []})
    
    if not ANONYMOUS_NAMES_FILE.exists():
        save_json(ANONYMOUS_NAMES_FILE, {})
    
    if not NOTIFICATIONS_FILE.exists():
        save_json(NOTIFICATIONS_FILE, {})

    # Attempt to restore from backups if any file looks empty/corrupt
    # This helps recover the database if the app restarted after long inactivity
    for p, default in [(USERS_FILE, {}), (MESSAGES_FILE, {"messages": []}), (ANONYMOUS_NAMES_FILE, {}), (NOTIFICATIONS_FILE, {})]:
        try:
            # If file exists but load_json returned default (likely empty or corrupt), try restoring
            loaded = load_json(p)
            if (loaded == default) or (p.exists() and p.stat().st_size == 0):
                restored = _restore_from_latest_backup(p)
                if restored:
                    st.info(f"Restored {p.name} from latest backup.")
        except Exception:
            # ignore restore failures
            pass

# Initialize data
initialize_data()

# ---------------------------------------------------------------------------
# DATABASE (SQLite) + FILE UPLOADS
# ---------------------------------------------------------------------------
import sqlite3

DB_FILE = DATA_DIR / "app.db"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30 MB


def init_db():
    """Initialize SQLite database and required tables."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Users table mirrors minimal info from users.json for compatibility
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            role TEXT,
            name TEXT,
            profile_photo TEXT,
            bio TEXT,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            follower TEXT,
            followee TEXT,
            created_at TEXT,
            PRIMARY KEY (follower, followee)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            author TEXT,
            content TEXT,
            visibility TEXT,
            is_complaint INTEGER,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS media (
            id TEXT PRIMARY KEY,
            owner TEXT,
            filename TEXT,
            path TEXT,
            mime TEXT,
            size INTEGER,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            user_a TEXT,
            user_b TEXT,
            anon_by_default INTEGER,
            created_at TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages_db (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            sender TEXT,
            content TEXT,
            is_anonymous INTEGER,
            anon_name TEXT,
            revealed INTEGER,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# Initialize DB
init_db()


def _sanitize_filename(name: str) -> str:
    """Remove potentially unsafe characters from a filename."""
    keepchars = " .-_()"
    return "".join(c for c in name if c.isalnum() or c in keepchars).strip()


def save_media_file(uploaded_file):
    """Save a Streamlit UploadedFile to the uploads folder enforcing size limits.

    Returns a dict with metadata on success, raises ValueError on violation.
    """
    # Streamlit's UploadedFile supports .name and .getbuffer() or .read()
    filename = getattr(uploaded_file, "name", "upload")
    safe_name = _sanitize_filename(filename)[:200]

    # Prefer to use buffer if available to avoid consuming the stream twice
    buf = None
    size = None
    if hasattr(uploaded_file, "getbuffer"):
        buf = uploaded_file.getbuffer()
        size = len(buf)
    else:
        # read once and keep the bytes
        try:
            raw = uploaded_file.read()
        except Exception:
            # as a last resort try seeking and reading
            try:
                uploaded_file.seek(0)
                raw = uploaded_file.read()
            except Exception:
                raw = b""
        buf = raw
        size = len(buf) if raw is not None else 0

    if size is None:
        size = 0

    if size > MAX_UPLOAD_BYTES:
        raise ValueError("File exceeds maximum allowed size of 30 MB")

    # Save with unique name
    unique = secrets.token_hex(8)
    dest_name = f"{unique}_{safe_name}"
    dest_path = UPLOAD_DIR / dest_name

    # Write file from the buffer we captured
    try:
        with open(dest_path, "wb") as f:
            if isinstance(buf, (bytes, bytearray)):
                f.write(buf)
            else:
                # memoryview or buffer-like
                f.write(buf.tobytes())
    except Exception:
        raise

    return {
        "id": unique,
        "filename": safe_name,
        "path": str(dest_path),
        "mime": getattr(uploaded_file, "type", "application/octet-stream"),
        "size": size,
        "created_at": datetime.utcnow().isoformat()
    }


def get_user_role(username):
    users = load_json(USERS_FILE)
    return users.get(username, {}).get("role")


def _ensure_normalized_conversation(a, b):
    """Return two usernames ordered so conversation is unique irrespective of order."""
    return (a, b) if a <= b else (b, a)


def create_or_get_conversation(user_a, user_b, anon_by_default=True):
    """Create a conversation row between two users or return existing one."""
    ua, ub = _ensure_normalized_conversation(user_a, user_b)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # look for existing
    c.execute("SELECT id, anon_by_default FROM conversations WHERE user_a=? AND user_b=?", (ua, ub))
    row = c.fetchone()
    if row:
        conv_id, anon_flag = row
        conn.close()
        return conv_id, bool(anon_flag)

    conv_id = secrets.token_hex(8)
    c.execute("INSERT INTO conversations (id, user_a, user_b, anon_by_default, created_at) VALUES (?, ?, ?, ?, ?)",
              (conv_id, ua, ub, 1 if anon_by_default else 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return conv_id, anon_by_default


def get_user_conversations(username):
    """Return list of conversation rows (id, user_a, user_b, anon_by_default, created_at) involving username"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, user_a, user_b, anon_by_default, created_at FROM conversations WHERE user_a=? OR user_b=? ORDER BY created_at DESC", (username, username))
    rows = c.fetchall()
    conn.close()
    return rows


def get_conversation_messages(conversation_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, sender, content, is_anonymous, anon_name, revealed, created_at FROM messages_db WHERE conversation_id=? ORDER BY created_at ASC", (conversation_id,))
    rows = c.fetchall()
    conn.close()
    # return as list of dicts
    msgs = []
    for r in rows:
        msgs.append({
            'id': r[0],
            'sender': r[1],
            'content': r[2],
            'is_anonymous': bool(r[3]),
            'anon_name': r[4],
            'revealed': bool(r[5]),
            'created_at': r[6]
        })
    return msgs


def send_db_message(conversation_id, sender, content, is_anonymous=None, anon_name=None, revealed=False):
    """Send a message in a conversation honoring the conversation's default anonymity.

    If is_anonymous is None, we use the convo's anon_by_default flag.
    """
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # get conv
    c.execute("SELECT anon_by_default, user_a, user_b FROM conversations WHERE id=?", (conversation_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError("Conversation not found")
    anon_default, user_a, user_b = row

    # Determine roles: if both students and no explicit flag, default to anonymous True
    if is_anonymous is None:
        # If both users are students, apply default True; else use anon_default
        other = user_a if sender != user_a else user_b
        sender_role = get_user_role(sender)
        other_role = get_user_role(other)
        if sender_role == "student" and other_role == "student":
            effective_anonymous = True
        else:
            effective_anonymous = bool(anon_default)
    else:
        effective_anonymous = bool(is_anonymous)

    msg_id = secrets.token_hex(8)
    c.execute("INSERT INTO messages_db (id, conversation_id, sender, content, is_anonymous, anon_name, revealed, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
              (msg_id, conversation_id, sender, content, 1 if effective_anonymous else 0, anon_name if effective_anonymous else None, 1 if revealed else 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    return msg_id


# -------------------------
# User & Follow helpers
# -------------------------

def sync_user_to_db(username):
    """Ensure a user exists in the SQLite users table mirroring users.json"""
    users = load_json(USERS_FILE)
    if username not in users:
        return False
    info = users[username]
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE username=?", (username,))
    # Normalize profile_photo to a string path for sqlite storage
    profile_photo_val = info.get('profile_photo', None)
    if isinstance(profile_photo_val, dict):
        profile_photo_db = profile_photo_val.get('path') or json.dumps(profile_photo_val)
    else:
        profile_photo_db = profile_photo_val

    if c.fetchone():
        # update
        c.execute("UPDATE users SET password=?, role=?, name=?, profile_photo=?, bio=?, created_at=? WHERE username=?",
                  (info.get('password'), info.get('role'), info.get('name'), profile_photo_db, info.get('bio', None), info.get('created_at', datetime.utcnow().isoformat()), username))
    else:
        c.execute("INSERT INTO users (username, password, role, name, profile_photo, bio, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (username, info.get('password'), info.get('role'), info.get('name'), profile_photo_db, info.get('bio', None), info.get('created_at', datetime.utcnow().isoformat())))
    conn.commit()
    conn.close()
    return True


# ---------- Reveal management helpers ----------
def get_revealed_list(username):
    users = load_json(USERS_FILE)
    return users.get(username, {}).get('revealed_to', [])


def set_revealed_list(username, reveal_list):
    users = load_json(USERS_FILE)
    if username in users:
        users[username]['revealed_to'] = list(reveal_list)
        save_json(USERS_FILE, users)
        try:
            sync_user_to_db(username)
        except Exception:
            pass
        return True
    return False


def has_revealed_to(viewed_username, viewer_username):
    return viewer_username in get_revealed_list(viewed_username)


def follow_user(follower, followee):
    if follower == followee:
        return False
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO follows (follower, followee, created_at) VALUES (?, ?, ?)",
                  (follower, followee, datetime.utcnow().isoformat()))
        conn.commit()
        # Notify followee that they have a new follower
        try:
            # Add notification with metadata so UI can offer follow-back
            users = load_json(USERS_FILE)
            # Determine actor display name: anonymous by default unless revealed to followee
            try:
                revealed = has_revealed_to(follower, followee)
            except Exception:
                revealed = False

            if revealed:
                actor_display = users.get(follower, {}).get('name', follower)
            else:
                actor_display = get_or_create_anonymous_name(follower)

            notifs = load_notifications()
            if followee not in notifs:
                notifs[followee] = []
            notifs[followee].append({
                "id": secrets.token_hex(4),
                "message_id": None,
                "text": f"{actor_display} started following you",
                "actor": follower,
                "actor_display": actor_display,
                "type": "follow",
                "read": False,
                "timestamp": datetime.now().isoformat()
            })
            save_notifications(notifs)
        except Exception:
            pass
        return True
    finally:
        conn.close()


def unfollow_user(follower, followee):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("DELETE FROM follows WHERE follower=? AND followee=?", (follower, followee))
        conn.commit()
        return True
    finally:
        conn.close()


def is_following(follower, followee):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM follows WHERE follower=? AND followee=?", (follower, followee))
    res = c.fetchone() is not None
    conn.close()
    return res


def get_followers_count(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM follows WHERE followee=?", (username,))
    n = c.fetchone()[0]
    conn.close()
    return n


def get_following_list(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT followee FROM follows WHERE follower=?", (username,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_following_count(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM follows WHERE follower=?", (username,))
    n = c.fetchone()[0]
    conn.close()
    return n


def get_user_profile(username):
    """Return profile dict merging users.json and sqlite stored photo/bio if available"""
    users = load_json(USERS_FILE)
    info = users.get(username, {})
    # ensure in sqlite
    try:
        sync_user_to_db(username)
    except Exception:
        pass
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT profile_photo, bio FROM users WHERE username=?", (username,))
    row = c.fetchone()
    conn.close()
    if row:
        profile_photo, bio = row
        if profile_photo:
            info['profile_photo'] = profile_photo
        if bio:
            info['bio'] = bio
    return info


def update_profile(username, new_name=None, new_bio=None, profile_photo_meta=None):
    """Update profile info in both users.json and sqlite"""
    users = load_json(USERS_FILE)
    if username not in users:
        return False
    if new_name is not None:
        users[username]['name'] = new_name
    if new_bio is not None:
        users[username]['bio'] = new_bio
    if profile_photo_meta is not None:
        users[username]['profile_photo'] = profile_photo_meta
    save_json(USERS_FILE, users)
    # sync into sqlite
    sync_user_to_db(username)
    # also store photo in sqlite directly (normalize dict -> path)
    profile_photo_val = users[username].get('profile_photo')
    if isinstance(profile_photo_val, dict):
        profile_photo_db = profile_photo_val.get('path') or json.dumps(profile_photo_val)
    else:
        profile_photo_db = profile_photo_val

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE users SET name=?, profile_photo=?, bio=? WHERE username=?",
              (users[username].get('name'), profile_photo_db, users[username].get('bio'), username))
    conn.commit()
    conn.close()
    return True


# ---------------------------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------------------------

def authenticate(username, password):
    """Authenticate user"""
    users = load_json(USERS_FILE)
    if username in users:
        if users[username]["password"] == hash_password(password):
            return users[username]
    return None

def get_or_create_anonymous_name(user_id, custom_name=None):
    """Get or create anonymous name for user"""
    anon_names = load_json(ANONYMOUS_NAMES_FILE)
    
    if user_id in anon_names:
        return anon_names[user_id]
    
    if custom_name and custom_name.strip():
        anon_name = custom_name.strip()[:20]  # Limit length
    else:
        anon_name = generate_anonymous_id()
    
    anon_names[user_id] = anon_name
    save_json(ANONYMOUS_NAMES_FILE, anon_names)
    return anon_name

# ============================================================================
# MESSAGE MANAGEMENT
# ============================================================================

def create_message(sender_id, sender_role, content, recipient, is_anonymous=False, anonymous_name=None):
    """Create a new message"""
    messages_data = load_json(MESSAGES_FILE)
    
    message = {
        "id": secrets.token_hex(8),
        "sender_id": sender_id,
        "sender_role": sender_role,
        "sender_display": anonymous_name if is_anonymous else sender_id,
        "is_anonymous": is_anonymous,
        "content": content,
        "recipient": recipient,
        "timestamp": datetime.now().isoformat(),
        "flagged": False,
        "flag_reason": "",
        "reactions": {
            "👍": [],
            "👎": []
        }
    }
    
    messages_data["messages"].append(message)
    save_json(MESSAGES_FILE, messages_data)
    return True

# -----------------
# Enter-to-send helpers
# -----------------
def _student_send_on_enter(username):
    key_input = f"msg_input_student_{username}"
    key_recipient = f"recipient_student_{username}"
    key_is_anon = f"is_anon_student_{username}"
    msg = st.session_state.get(key_input, "").strip()
    if not msg:
        return
    users = load_json(USERS_FILE)
    display_name = users.get(username, {}).get('name', username)
    recipient = st.session_state.get(key_recipient, "all_school")
    if recipient == "senate":
        effective_anonymous = False
        sender_id = display_name
    else:
        effective_anonymous = st.session_state.get(key_is_anon, False)
        sender_id = username
    anon_name = get_or_create_anonymous_name(username) if effective_anonymous else None
    create_message(
        sender_id=sender_id,
        sender_role="student",
        content=msg,
        recipient=recipient,
        is_anonymous=effective_anonymous,
        anonymous_name=anon_name
    )
    # clear the input
    st.session_state[key_input] = ""
    st.success("Message sent successfully!")
    st.rerun()

def _teacher_send_on_enter(username):
    key_input = f"msg_input_teacher_{username}"
    key_recipient = f"recipient_teacher_{username}"
    msg = st.session_state.get(key_input, "").strip()
    if not msg:
        return
    users = load_json(USERS_FILE)
    display_name = users.get(username, {}).get('name', username)
    recipient = st.session_state.get(key_recipient, "all_school")
    create_message(
        sender_id=display_name,
        sender_role="teacher",
        content=msg,
        recipient=recipient,
        is_anonymous=False
    )
    st.session_state[key_input] = ""
    st.success("Message sent successfully!")
    st.rerun()

def _senator_send_on_enter(username):
    key_input = f"msg_input_senator_{username}"
    key_recipient = f"recipient_senator_{username}"
    key_is_anon = f"is_anon_senator_{username}"
    msg = st.session_state.get(key_input, "").strip()
    if not msg:
        return
    users = load_json(USERS_FILE)
    display_name = users.get(username, {}).get('name', username)
    recipient = st.session_state.get(key_recipient, "all_school")
    use_anon = st.session_state.get(key_is_anon, False) and recipient == "all_school"
    anon_name = get_or_create_anonymous_name(username) if use_anon else None
    create_message(
        sender_id=display_name,
        sender_role="senator",
        content=msg,
        recipient=recipient,
        is_anonymous=use_anon,
        anonymous_name=anon_name
    )
    st.session_state[key_input] = ""
    st.success("Message sent successfully!")
    st.rerun()

def _admin_send_on_enter(username):
    key_input = f"msg_input_admin_{username}"
    key_recipient = f"recipient_admin_{username}"
    msg = st.session_state.get(key_input, "").strip()
    if not msg:
        return
    users = load_json(USERS_FILE)
    display_name = users.get(username, {}).get('name', username)
    recipient = st.session_state.get(key_recipient, "all_school")
    create_message(
        sender_id=display_name,
        sender_role="admin",
        content=msg,
        recipient=recipient,
        is_anonymous=False
    )
    st.session_state[key_input] = ""
    st.success("Message sent successfully!")
    st.rerun()

def get_messages(recipient=None, role=None):
    """Get messages filtered by recipient and/or role"""
    messages_data = load_json(MESSAGES_FILE)
    messages = messages_data["messages"]
    
    if recipient:
        messages = [m for m in messages if m["recipient"] == recipient]
    
    if role:
        messages = [m for m in messages if m["sender_role"] == role or m["recipient"] == "all_school"]
    
    # Sort by latest timestamp by default (newest first)
    try:
        messages.sort(key=lambda m: datetime.fromisoformat(m.get('timestamp', '1970-01-01T00:00:00')), reverse=True)
    except Exception:
        # Fallback: keep existing order if parse fails
        pass
    return messages


def sort_messages_for_user(messages, viewer_username):
    """Return messages sorted with messages from people the viewer follows first."""
    try:
        following = set(get_following_list(viewer_username))
    except Exception:
        following = set()

    def score(m):
        # higher score means higher priority
        # treat self messages as highest
        sender = m.get('sender_id')
        if sender == viewer_username:
            return (2, m.get('timestamp'))
        if sender in following:
            return (1, m.get('timestamp'))
        return (0, m.get('timestamp'))

    def parsed_time(t):
        try:
            return datetime.fromisoformat(t)
        except Exception:
            return datetime(1970,1,1)

    messages_sorted = sorted(messages, key=lambda m: ( -score(m)[0], parsed_time(m.get('timestamp','1970-01-01T00:00:00')) ), reverse=True)
    # Above sorts primarily by score then by timestamp (newest first)
    return messages_sorted

def flag_message(message_id, reason):
    """Flag a message as potentially abusive"""
    messages_data = load_json(MESSAGES_FILE)
    for msg in messages_data["messages"]:
        if msg["id"] == message_id:
            msg["flagged"] = True
            msg["flag_reason"] = reason
            save_json(MESSAGES_FILE, messages_data)
            return True
    return False

def add_reaction(message_id, user_id, emoji):
    """Add or remove a reaction to a message"""
    messages_data = load_json(MESSAGES_FILE)
    for msg in messages_data["messages"]:
        if msg["id"] == message_id:
            # Initialize reactions if not present (for old messages)
            if "reactions" not in msg:
                msg["reactions"] = {
                    "👍": [],
                    "👎": []
                }
            
            # Ensure both reaction types exist
            if "👍" not in msg["reactions"]:
                msg["reactions"]["👍"] = []
            if "👎" not in msg["reactions"]:
                msg["reactions"]["👎"] = []
            
            # Toggle reaction - remove if already present, add if not
            if user_id in msg["reactions"][emoji]:
                msg["reactions"][emoji].remove(user_id)
            else:
                msg["reactions"][emoji].append(user_id)
            
            save_json(MESSAGES_FILE, messages_data)
            # Send notification to message owner about the reaction (like)
            try:
                users = load_json(USERS_FILE)
                # Determine owner username from message sender_id
                owner_candidate = msg.get('sender_id')
                owner_username = None
                if owner_candidate in users:
                    owner_username = owner_candidate
                else:
                    # try to match by real name
                    for u, info in users.items():
                        if info.get('name') == owner_candidate:
                            owner_username = u
                            break

                if owner_username and owner_username != user_id:
                    # Determine actor display (anonymous unless revealed to owner)
                    try:
                        revealed = has_revealed_to(user_id, owner_username)
                    except Exception:
                        revealed = False

                    if revealed:
                        actor_display = users.get(user_id, {}).get('name', user_id)
                    else:
                        actor_display = get_or_create_anonymous_name(user_id)

                    notifs = load_notifications()
                    if owner_username not in notifs:
                        notifs[owner_username] = []
                    notifs[owner_username].append({
                        "id": secrets.token_hex(4),
                        "message_id": message_id,
                        "text": f"{actor_display} reacted {emoji} to your post",
                        "actor": user_id,
                        "actor_display": actor_display,
                        "type": "reaction",
                        "emoji": emoji,
                        "read": False,
                        "timestamp": datetime.now().isoformat()
                    })
                    save_notifications(notifs)
            except Exception:
                pass
            return True
    return False

def add_comment(message_id, user_id, username, content, user_role, is_anonymous=False, anonymous_name=None):
    """Add a comment to a message"""
    messages_data = load_json(MESSAGES_FILE)
    for msg in messages_data["messages"]:
        if msg["id"] == message_id:
            # Initialize comments if not present
            if "comments" not in msg:
                msg["comments"] = []
            
            comment = {
                "id": secrets.token_hex(6),
                "user_id": user_id,
                "username": username,
                "content": content,
                "role": user_role,
                "is_anonymous": is_anonymous,
                "anonymous_name": anonymous_name if is_anonymous else username,
                "timestamp": datetime.now().isoformat(),
                "reactions": {
                    "👍": [],
                    "👎": []
                }
            }
            msg["comments"].append(comment)
            save_json(MESSAGES_FILE, messages_data)
            return True
    return False

def delete_comment(message_id, comment_id, user_id, user_role):
    """Delete a comment - user can delete their own, super admin can delete any"""
    messages_data = load_json(MESSAGES_FILE)
    for msg in messages_data["messages"]:
        if msg["id"] == message_id:
            if "comments" not in msg:
                return False
            for idx, comment in enumerate(msg["comments"]):
                if comment["id"] == comment_id:
                    is_owner = comment["user_id"] == user_id
                    is_super_admin = user_role == "super_admin"
                    if is_owner or is_super_admin:
                        msg["comments"].pop(idx)
                        save_json(MESSAGES_FILE, messages_data)
                        return True
    return False

def add_comment_reaction(message_id, comment_id, user_id, emoji):
    """Add or remove reaction to a comment"""
    messages_data = load_json(MESSAGES_FILE)
    for msg in messages_data["messages"]:
        if msg["id"] == message_id:
            if "comments" not in msg:
                return False
            for comment in msg["comments"]:
                if comment["id"] == comment_id:
                    if "reactions" not in comment:
                        comment["reactions"] = {"👍": [], "👎": []}
                    
                    # Ensure both reactions exist
                    if "👍" not in comment["reactions"]:
                        comment["reactions"]["👍"] = []
                    if "👎" not in comment["reactions"]:
                        comment["reactions"]["👎"] = []
                    
                    if user_id in comment["reactions"][emoji]:
                        comment["reactions"][emoji].remove(user_id)
                    else:
                        comment["reactions"][emoji].append(user_id)
                    save_json(MESSAGES_FILE, messages_data)
                    return True
    return False

def delete_message(message_id, user_id, user_role):
    """Delete a message - users can delete their own, super admin can delete any"""
    messages_data = load_json(MESSAGES_FILE)
    for idx, msg in enumerate(messages_data["messages"]):
        if msg["id"] == message_id:
            # Check permissions
            is_owner = msg["sender_id"] == user_id
            is_super_admin = user_role == "super_admin"
            
            if is_owner or is_super_admin:
                messages_data["messages"].pop(idx)
                save_json(MESSAGES_FILE, messages_data)
                return True
    return False

def reset_user_password(username, new_password):
    """Reset a user's password"""
    users = load_json(USERS_FILE)
    if username in users:
        users[username]["password"] = hash_password(new_password)
        save_json(USERS_FILE, users)
        return True
    return False

def edit_user(username, new_name=None, new_role=None):
    """Edit user information"""
    users = load_json(USERS_FILE)
    if username in users and username != "superadmin":
        if new_name:
            users[username]["name"] = new_name
        if new_role:
            users[username]["role"] = new_role
        save_json(USERS_FILE, users)
        return True
    return False

def delete_user(username):
    """Delete a user (super admin only)"""
    if username == "superadmin":
        return False
    users = load_json(USERS_FILE)
    if username in users:
        del users[username]
        save_json(USERS_FILE, users)
        # Also remove their anonymous name if exists
        anon_names = load_json(ANONYMOUS_NAMES_FILE)
        if username in anon_names:
            del anon_names[username]
            save_json(ANONYMOUS_NAMES_FILE, anon_names)
        return True
    return False

def reset_anonymous_name(user_id):
    """Reset anonymous name to auto-generated ID"""
    anon_names = load_json(ANONYMOUS_NAMES_FILE)
    if user_id in anon_names:
        del anon_names[user_id]
        save_json(ANONYMOUS_NAMES_FILE, anon_names)
        # Generate new one
        new_name = generate_anonymous_id()
        anon_names[user_id] = new_name
        save_json(ANONYMOUS_NAMES_FILE, anon_names)
        return new_name
    else:
        new_name = generate_anonymous_id()
        anon_names[user_id] = new_name
        save_json(ANONYMOUS_NAMES_FILE, anon_names)
        return new_name

# ============================================================================
# NOTIFICATION MANAGEMENT
# ============================================================================

def load_notifications():
    """Load all notifications"""
    return load_json(NOTIFICATIONS_FILE)

def save_notifications(data):
    """Save notifications to file"""
    save_json(NOTIFICATIONS_FILE, data)

def add_notification(username, message_id, text):
    """Add a notification for a user"""
    # message_id may be None for non-message notifications (e.g., follows)
    notifs = load_notifications()
    if username not in notifs:
        notifs[username] = []

    entry = {
        "id": secrets.token_hex(4),
        "message_id": message_id,
        "text": text,
        "read": False,
        "timestamp": datetime.now().isoformat()
    }
    # Support optional metadata: actor and type can be provided by callers
    # If callers passed extras via kwargs, include them (backwards compatible)
    # Caller may add 'actor' and 'type' keys by updating the dict before calling save.
    notifs[username].append(entry)
    save_notifications(notifs)

def get_unread_notifications_count(username):
    """Get count of unread notifications for a user"""
    notifs = load_notifications().get(username, [])
    return sum(1 for n in notifs if not n.get("read", False))

def mark_notification_read(username, notif_id):
    """Mark a specific notification as read"""
    notifs = load_notifications()
    if username in notifs:
        for n in notifs[username]:
            if n["id"] == notif_id:
                n["read"] = True
                break
        save_notifications(notifs)

def mark_all_notifications_read(username):
    """Mark all notifications as read for a user"""
    notifs = load_notifications()
    if username in notifs:
        for n in notifs[username]:
            n["read"] = True
        save_notifications(notifs)

def distribute_notifications_for_message(message):
    """Distribute notifications based on message recipient"""
    users = load_json(USERS_FILE)
    recipient = message.get("recipient", "all_school")
    sender = message.get("sender_display", "Unknown")
    
    # Determine which users should receive notification
    notification_recipients = []
    
    if recipient == "all_school":
        notification_recipients = list(users.keys())
    elif recipient == "senate":
        notification_recipients = [u for u, info in users.items() if info.get("role") == "senator"]
    elif recipient == "teachers":
        notification_recipients = [u for u, info in users.items() if info.get("role") == "teacher"]
    elif recipient == "admins":
        notification_recipients = [u for u, info in users.items() if info.get("role") == "admin"]
    elif recipient == "super_admin":
        notification_recipients = [u for u, info in users.items() if info.get("role") == "super_admin"]
    
    # Create notification for each recipient (except sender)
    for username in notification_recipients:
        if username != message.get("sender_id"):  # Don't notify sender
            text = f"New message from {sender}"
            add_notification(username, message.get("id"), text)

# ============================================================================
# USER INTERFACE COMPONENTS
# ============================================================================

def render_header():
    """Render the main header"""
    st.markdown("""
    <div class="main-header">
        <h1>🎓 Empower International Academy</h1>
        <h2>Voice Platform - Empowering Student Expression</h2>
        <p>Share your ideas, concerns, and feedback safely and responsibly</p>
    </div>
    """, unsafe_allow_html=True)
 
def render_comments(message, user_id, user_name, user_role):
    """Render comments section like Facebook/Instagram"""
    comments = message.get("comments", [])
    message_id = message["id"]
    
    st.markdown("---")
    st.markdown(f"### 💬 Comments ({len(comments)})")
    
    # Add comment form
    st.markdown("**Add your comment:**")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        comment_text = st.text_area(
            "Write a comment...",
            placeholder="Share your thoughts...",
            height=60,
            key=f"comment_input_{message_id}",
            label_visibility="collapsed"
        )
    
    with col2:
        col2a, col2b = st.columns(2)
        with col2a:
            is_anon_comment = st.checkbox(
                "Anonymous",
                value=False,
                key=f"anon_comment_{message_id}"
            )
        with col2b:
            if st.button("Post", key=f"post_comment_{message_id}", type="primary"):
                if comment_text.strip():
                    anon_name = None
                    if is_anon_comment:
                        anon_name = get_or_create_anonymous_name(user_id)
                    add_comment(
                        message_id,
                        user_id,
                        user_name,
                        comment_text.strip(),
                        user_role,
                        is_anonymous=is_anon_comment,
                        anonymous_name=anon_name
                    )
                    st.success("✅ Comment posted!")
                    st.rerun()
                else:
                    st.error("Please write a comment")
    
    st.markdown("---")
    
    # Display comments
    if comments:
        for idx, comment in enumerate(comments):
            with st.container():
                # Comment header
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    comment_display = comment["anonymous_name"] if comment["is_anonymous"] else comment["username"]
                    role_badges = {
                        "student": "🎓",
                        "teacher": "👨‍🏫",
                        "senator": "🏛️",
                        "admin": "🏢",
                        "super_admin": "👑"
                    }
                    role_emoji = role_badges.get(comment["role"], "👤")
                    
                    # (removed misplaced top-bar CSS here)
                    if st.button(
                        "🗑️",
                        key=f"del_comment_{message_id}_{comment['id']}",
                        help="Delete comment"
                    ):
                        if delete_comment(message_id, comment["id"], user_id, user_role):
                            st.success("Comment deleted")
                            st.rerun()
                
                # Comment content and time
                comment_time = datetime.fromisoformat(comment["timestamp"]).strftime("%b %d, %I:%M %p")
                safe_comment = escape(comment.get('content', '')).replace('\n', '<br>')
                st.markdown(safe_comment, unsafe_allow_html=True)
                st.caption(comment_time)
                
                # Comment reactions (like/dislike only)
                reactions = comment.get("reactions", {"👍": [], "👎": []})
                
                # Ensure both reactions exist
                if "👍" not in reactions:
                    reactions["👍"] = []
                if "👎" not in reactions:
                    reactions["👎"] = []
                
                reaction_cols = st.columns(3)
                
                with reaction_cols[0]:
                    like_count = len(reactions.get("👍", []))
                    st.caption(f"👍 {like_count}")
                
                with reaction_cols[1]:
                    user_liked = user_id in reactions.get("👍", [])
                    like_type = "primary" if user_liked else "secondary"
                    
                    if st.button(
                        f"{'👍 Unlike' if user_liked else '👍 Like'}",
                        key=f"comment_like_{message_id}_{comment['id']}",
                        type=like_type,
                        use_container_width=True
                    ):
                        add_comment_reaction(message_id, comment["id"], user_id, "👍")
                        st.rerun()
                
                with reaction_cols[2]:
                    user_disliked = user_id in reactions.get("👎", [])
                    dislike_type = "primary" if user_disliked else "secondary"
                    
                    if st.button(
                        f"{'👎 Undo' if user_disliked else '👎 Dislike'}",
                        key=f"comment_dislike_{message_id}_{comment['id']}",
                        type=dislike_type,
                        use_container_width=True
                    ):
                        add_comment_reaction(message_id, comment["id"], user_id, "👎")
                        st.rerun()
                
                st.divider()
    else:
        st.info("No comments yet. Be the first to comment!")

def render_message_card(message, show_sender_id=False, user_id=None, show_reactions=True, user_role=None, enable_comments=True, user_info=None, context=""):
    """Render a message card"""
    flagged_class = "flagged" if message.get("flagged", False) else ""
    
    # Role badge
    role_badges = {
        "student": "badge-student",
        "teacher": "badge-teacher",
        "senator": "badge-senator",
        "admin": "badge-admin",
        "super_admin": "badge-super-admin"
    }
    badge_class = role_badges.get(message["sender_role"], "badge-student")
    
    sender_display = message["sender_display"]
    if show_sender_id and message["is_anonymous"]:
        sender_display += f" (Real ID: {message['sender_id']})"
    
    timestamp = datetime.fromisoformat(message["timestamp"]).strftime("%B %d, %Y at %I:%M %p")
    
    # Escape message content to prevent raw HTML from breaking layout
    safe_content = escape(message.get('content', '')).replace('\n', '<br>')

    st.markdown(f"""
    <div class="message-card {flagged_class}">
        <div class="message-header">
            <div>
                <span class="badge {badge_class}">{message['sender_role'].replace('_', ' ').title()}</span>
                <strong>{sender_display}</strong>
            </div>
            <div style="text-align: right;">
                <div>To: <strong>{message['recipient'].replace('_', ' ').title()}</strong></div>
                <div style="font-size: 0.8rem; color: #999;">{timestamp}</div>
            </div>
        </div>
        <div class="message-content">
            {safe_content}
        </div>
        {f'<div style="margin-top: 0.5rem; color: #f44336; font-weight: 600;">⚠️ Flagged: {message["flag_reason"]}</div>' if message.get("flagged") else ''}
    </div>
    """, unsafe_allow_html=True)
    
    # Add action buttons (delete for owner/super admin, flag for super admin)
    if user_id:
        # Determine ownership and super-admin status
        is_owner = message["sender_id"] == user_id
        is_super_admin = user_role == "super_admin"
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        # Delete button for owner or super admin
        if is_owner or is_super_admin:
            with col2:
                delete_key = f"delete_msg_{message['id']}_{context}"
                if st.button(
                    "🗑️ Delete",
                    key=delete_key,
                    type="secondary",
                    use_container_width=True
                ):
                    if delete_message(message['id'], user_id, user_role or ""):
                        st.success("✅ Message deleted")
                        st.rerun()
                    else:
                        st.error("❌ Could not delete message")
    
    # Like/Dislike and Comments count (Facebook style)
    if show_reactions and user_id:
        reactions = message.get("reactions", {"👍": [], "👎": []})
        like_count = len(reactions.get("👍", []))
        dislike_count = len(reactions.get("👎", []))
        comment_count = len(message.get("comments", []))
        
        # Show counts
        col_counts1, col_counts2 = st.columns(2)
        with col_counts1:
            st.caption(f"👍 {like_count} likes")
        with col_counts2:
            st.caption(f"💬 {comment_count} comments")
        
        st.markdown("---")
        
        # Like/Dislike buttons
        col_like, col_dislike = st.columns(2)
        
        with col_like:
            user_liked = user_id in reactions.get("👍", [])
            like_type = "primary" if user_liked else "secondary"
            
            if st.button(
                f"👍 {'Unlike' if user_liked else 'Like'}",
                key=f"like_msg_{message['id']}_{context}",
                type=like_type,
                use_container_width=True
            ):
                add_reaction(message['id'], user_id, "👍")
                st.rerun()
        
        with col_dislike:
            user_disliked = user_id in reactions.get("👎", [])
            dislike_type = "primary" if user_disliked else "secondary"
            
            if st.button(
                f"👎 {'Undo' if user_disliked else 'Dislike'}",
                key=f"dislike_msg_{message['id']}_{context}",
                type=dislike_type,
                use_container_width=True
            ):
                add_reaction(message['id'], user_id, "👎")
                st.rerun()
    
    # Add collapsible comments section
    if enable_comments and user_id and user_info:
        with st.expander(f"💬 Comments ({len(message.get('comments', []))})", expanded=False):
            render_comments(message, user_id, user_info.get("name", user_info["username"]), user_role)
# ============================================================================
# ROLE-SPECIFIC INTERFACES
# ============================================================================

def student_interface(user_info):
    """Student interface"""
    st.subheader(" Student Voice Platform")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Send Message", "My Anonymous Profile", "View Messages", "Account Settings"])
    
    with tab1:
        st.markdown("### Send a Message")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
                # Message input (press Enter to send)
                message_content = st.text_input(
                    "Your Message (press Enter to send)",
                    placeholder="Share your thoughts, ideas, or concerns...",
                    key=f"msg_input_student_{user_info['username']}",
                    on_change=_student_send_on_enter,
                    args=(user_info['username'],)
                )
        
        with col2:
            # Recipient selection (track with a key so we can reactively enable/disable anonymity)
            recipient = st.selectbox(
                "Send To",
                ["all_school", "senate"],
                format_func=lambda x: {
                    "all_school": "Whole School",
                    "senate": "Senate"
                }[x],
                key=f"recipient_student_{user_info['username']}"
            )

            # Anonymous option: only available when sending to whole school
            anon_disabled = (recipient != "all_school")
            is_anonymous = st.checkbox(
                "Send Anonymously",
                value=(not anon_disabled),
                help="Your identity will be hidden from recipients (but traceable by super admin if needed)",
                key=f"is_anon_student_{user_info['username']}",
                disabled=anon_disabled
            )

            if recipient != "all_school":
                st.info("Messages sent to the Senate are NOT anonymous and will include your name.")
            else:
                st.info(" **Tip:** To reach teachers or administration, send to 'Whole School' or contact the Senate who can forward your message.")

            st.info(" Note: Anonymous messages can be traced by administration if they violate community guidelines.")
        
        if st.button(" Send Message", type="primary", key=f"send_msg_student_{user_info['username']}"):
            msg = st.session_state.get(f"msg_input_student_{user_info['username']}", "").strip()
            if msg:
                # Determine effective anonymity and sender id
                if recipient == "senate":
                    effective_anonymous = False
                    sender_id = user_info.get("name", user_info["username"])
                else:
                    effective_anonymous = is_anonymous
                    sender_id = user_info["username"]

                anon_name = None
                if effective_anonymous:
                    anon_name = get_or_create_anonymous_name(user_info["username"])

                create_message(
                    sender_id=sender_id,
                    sender_role="student",
                    content=msg,
                    recipient=recipient,
                    is_anonymous=effective_anonymous,
                    anonymous_name=anon_name
                )
                st.session_state[f"msg_input_student_{user_info['username']}"] = ""
                st.success(" Message sent successfully!")
                st.rerun()
            else:
                st.error(" Please enter a message")
    
    with tab2:
        st.markdown("### Your Anonymous Identity")
        
        anon_names = load_json(ANONYMOUS_NAMES_FILE)
        current_name = anon_names.get(user_info["username"], "Not set")
        
        st.info(f"**Current Anonymous Name:** {current_name}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_name = st.text_input(
                "Choose a New Anonymous Name (optional)",
                placeholder="e.g., StudentVoice2024, ConcernedLearner",
                max_chars=20,
                key=f"anon_new_{user_info['username']}"
            )
            
            if st.button("Update Anonymous Name", key=f"update_anon_{user_info['username']}"):
                if new_name.strip():
                    anon_names = load_json(ANONYMOUS_NAMES_FILE)
                    anon_names[user_info["username"]] = new_name.strip()
                    save_json(ANONYMOUS_NAMES_FILE, anon_names)
                    st.success(f" Anonymous name updated to: {new_name.strip()}")
                    st.rerun()
        
        with col2:
            st.write("Or:")
            if st.button(" Reset to Auto-Generated Name", key=f"reset_anon_{user_info['username']}"):
                new_anon_name = reset_anonymous_name(user_info["username"])
                st.success(f" Anonymous name reset to: {new_anon_name}")
                st.rerun()
    
    with tab3:
        st.markdown("###  School Feed")
        st.caption("Messages sorted by engagement - most popular and recent first")
        
        messages = get_messages(recipient="all_school")
        messages = sort_messages_for_user(messages, user_info['username'])
        
        if messages:
            # Infinite scroll style - show messages in a continuous feed
            for idx, msg in enumerate(messages):
                with st.container():
                    render_message_card(msg, user_id=user_info["username"], user_role="student", enable_comments=True, user_info=user_info, context=f"student_{user_info['username']}_{idx}")
                    
                    # Add spacing between messages
                    if idx < len(messages) - 1:
                        st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info(" No messages yet. Be the first to share your voice!")
    
    with tab4:
        st.markdown("### Account Settings")
        
        st.markdown("#### Change Password")
        st.info("Keep your password secure and change it regularly")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_password = st.text_input("Current Password", type="password", key=f"current_pw_student_{user_info['username']}")
            new_password = st.text_input("New Password", type="password", key=f"new_pw_student_{user_info['username']}")
            confirm_password = st.text_input("Confirm New Password", type="password", key=f"confirm_pw_student_{user_info['username']}")
            
            if st.button("Change Password", key=f"change_pw_student_{user_info['username']}"):
                # Verify current password
                user = authenticate(user_info["username"], current_password)
                if not user:
                    st.error(" Current password is incorrect")
                elif new_password != confirm_password:
                    st.error(" New passwords do not match")
                elif len(new_password) < 6:
                    st.error(" New password must be at least 6 characters")
                else:
                    if reset_user_password(user_info["username"], new_password):
                        st.success(" Password changed successfully!")
                    else:
                        st.error(" Failed to change password")

def teacher_interface(user_info):
    """Teacher interface"""
    st.subheader(" Teacher Platform")
    
    tab1, tab2, tab3 = st.tabs(["Send Message", "View Messages", "Account Settings"])
    
    with tab1:
        st.markdown("### Send a Message")
        st.info(" Teachers must identify themselves - all messages are sent with your name")
        
        message_content = st.text_input(
            "Your Message (press Enter to send)",
            placeholder="Share announcements, feedback, or information...",
            key=f"msg_input_teacher_{user_info['username']}",
            on_change=_teacher_send_on_enter,
            args=(user_info['username'],)
        )
        
        recipient = st.selectbox(
            "Send To",
            ["all_school", "senate", "super_admin", "teachers"],
            format_func=lambda x: {
                "all_school": "Whole School",
                "senate": "Senate",
                "super_admin": "Super Admin",
                "teachers": "Teachers Only"
            }[x],
            key=f"recipient_teacher_{user_info['username']}"
        )
        
        if st.button(" Send Message", type="primary", key=f"send_msg_teacher_{user_info['username']}"):
            msg = st.session_state.get(f"msg_input_teacher_{user_info['username']}", "").strip()
            if msg:
                create_message(
                    sender_id=user_info.get("name", user_info["username"]),
                    sender_role="teacher",
                    content=msg,
                    recipient=recipient,
                    is_anonymous=False
                )
                st.session_state[f"msg_input_teacher_{user_info['username']}"] = ""
                st.success(" Message sent successfully!")
                st.rerun()
            else:
                st.error(" Please enter a message")
    
    with tab2:
        st.markdown("###  School Feed")
        st.caption("Messages sorted by engagement - most popular and recent first")

        view_choice = st.selectbox(
            "View",
            ["all_school", "teachers"],
            format_func=lambda x: {
                "all_school": "Whole School",
                "teachers": "Teachers Only"
            }[x],
            key=f"view_teacher_feed_{user_info['username']}"
        )

        messages = get_messages(recipient=view_choice)
        messages = sort_messages_for_user(messages, user_info['username'])

        if messages:
            for idx, msg in enumerate(messages):
                with st.container():
                    render_message_card(msg, user_id=user_info.get("name", user_info["username"]), user_role="teacher", enable_comments=True, user_info=user_info, context=f"teacher_{user_info['username']}_{idx}")

                    if idx < len(messages) - 1:
                        st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info(" No messages available")
    
    with tab3:
        st.markdown("### Account Settings")
        
        st.markdown("#### Change Password")
        st.info("Keep your password secure and change it regularly")
        
        current_password = st.text_input("Current Password", type="password", key=f"current_pw_teacher_{user_info['username']}")
        new_password = st.text_input("New Password", type="password", key=f"new_pw_teacher_{user_info['username']}")
        confirm_password = st.text_input("Confirm New Password", type="password", key=f"confirm_pw_teacher_{user_info['username']}")
        
        if st.button("Change Password", key=f"change_pw_teacher_{user_info['username']}"):
            # Verify current password
            user = authenticate(user_info["username"], current_password)
            if not user:
                st.error(" Current password is incorrect")
            elif new_password != confirm_password:
                st.error(" New passwords do not match")
            elif len(new_password) < 6:
                st.error(" New password must be at least 6 characters")
            else:
                if reset_user_password(user_info["username"], new_password):
                    st.success(" Password changed successfully!")
                else:
                    st.error(" Failed to change password")

def senator_interface(user_info):
    """Senator interface"""
    st.subheader(" Senate Platform")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Send Message", "Senate Discussion", "School Messages", "Account Settings"])
    
    with tab1:
        st.markdown("### Send a Message")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            message_content = st.text_input(
                "Your Message (press Enter to send)",
                placeholder="Share your message...",
                key=f"msg_input_senator_{user_info['username']}",
                on_change=_senator_send_on_enter,
                args=(user_info['username'],)
            )
        
        with col2:
            recipient = st.selectbox(
                "Send To",
                ["all_school", "senate", "super_admin", "teachers", "admins"],
                format_func=lambda x: {
                    "all_school": "Whole School",
                    "senate": "Senate Only",
                    "super_admin": "Super Admin",
                    "teachers": "Teachers",
                    "admins": "Administrators"
                }[x],
                key=f"recipient_senator_{user_info['username']}"
            )
            
            is_anonymous = st.checkbox(
                "Send Anonymously to School",
                value=False,
                help="Only available when sending to whole school",
                disabled=(recipient != "all_school"),
                key=f"is_anon_senator_{user_info['username']}"
            )
            
            if recipient != "all_school":
                st.info("ℹ Messages to Senate and Super Admin are not anonymous")
        
        if st.button(" Send Message", type="primary", key=f"send_msg_senator_{user_info['username']}"):
            msg = st.session_state.get(f"msg_input_senator_{user_info['username']}", "").strip()
            if msg:
                anon_name = None
                use_anon = is_anonymous and recipient == "all_school"

                if use_anon:
                    anon_name = get_or_create_anonymous_name(user_info["username"])

                create_message(
                    sender_id=user_info.get("name", user_info["username"]),
                    sender_role="senator",
                    content=msg,
                    recipient=recipient,
                    is_anonymous=use_anon,
                    anonymous_name=anon_name
                )
                st.session_state[f"msg_input_senator_{user_info['username']}"] = ""
                st.success(" Message sent successfully!")
                st.rerun()
            else:
                st.error(" Please enter a message")
    
    with tab2:
        st.markdown("### Senate Discussion Board")
        messages = get_messages(recipient="senate")
        
        if messages:
            for idx, msg in enumerate(messages):
                render_message_card(msg, user_id=user_info.get("name", user_info["username"]), user_role="senator", enable_comments=True, user_info=user_info, context=f"senator_discuss_{user_info['username']}_{idx}")
        else:
            st.info("No senate messages yet")
    
    with tab3:
        st.markdown("###  School Feed")
        st.caption("Messages sorted by engagement - most popular and recent first")
        
        messages = get_messages(recipient="all_school")
        
        if messages:
            for idx, msg in enumerate(messages):
                with st.container():
                    render_message_card(msg, user_id=user_info.get("name", user_info["username"]), user_role="senator", enable_comments=True, user_info=user_info, context=f"senator_feed_{user_info['username']}_{idx}")
                    
                    if idx < len(messages) - 1:
                        st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info(" No school messages yet")
    
    with tab4:
        st.markdown("### Account Settings")
        
        st.markdown("#### Change Password")
        st.info("Keep your password secure and change it regularly")
        
        current_password = st.text_input("Current Password", type="password", key=f"current_pw_senator_{user_info['username']}")
        new_password = st.text_input("New Password", type="password", key=f"new_pw_senator_{user_info['username']}")
        confirm_password = st.text_input("Confirm New Password", type="password", key=f"confirm_pw_senator_{user_info['username']}")
        
        if st.button("Change Password", key=f"change_pw_senator_{user_info['username']}"):
            # Verify current password
            user = authenticate(user_info["username"], current_password)
            if not user:
                st.error(" Current password is incorrect")
            elif new_password != confirm_password:
                st.error(" New passwords do not match")
            elif len(new_password) < 6:
                st.error(" New password must be at least 6 characters")
            else:
                if reset_user_password(user_info["username"], new_password):
                    st.success(" Password changed successfully!")
                else:
                    st.error(" Failed to change password")

def admin_interface(user_info):
    """Admin interface - similar to teacher with additional viewing capabilities"""
    st.subheader(" Administration Panel")
    
    tab1, tab2, tab3 = st.tabs(["Send Message", "View Messages", "Account Settings"])
    
    with tab1:
        st.markdown("### Send a Message")
        st.info(" Administrators must identify themselves - all messages are sent with your name")
        
        message_content = st.text_input(
            "Your Message (press Enter to send)",
            placeholder="Share announcements, feedback, or information...",
            key=f"msg_input_admin_{user_info['username']}",
            on_change=_admin_send_on_enter,
            args=(user_info['username'],)
        )
        
        recipient = st.selectbox(
            "Send To",
            ["all_school", "senate", "super_admin", "admins"],
            format_func=lambda x: {
                "all_school": "Whole School",
                "senate": "Senate",
                "super_admin": "Super Admin",
                "admins": "Admins Only"
            }[x],
            key=f"recipient_admin_{user_info['username']}"
        )
        
        if st.button(" Send Message", type="primary", key=f"send_msg_admin_{user_info['username']}"):
            msg = st.session_state.get(f"msg_input_admin_{user_info['username']}", "").strip()
            if msg:
                create_message(
                    sender_id=user_info.get("name", user_info["username"]),
                    sender_role="admin",
                    content=msg,
                    recipient=recipient,
                    is_anonymous=False
                )
                st.session_state[f"msg_input_admin_{user_info['username']}"] = ""
                st.success(" Message sent successfully!")
                st.rerun()
            else:
                st.error(" Please enter a message")
    
    with tab2:
        st.markdown("###  School Feed")
        st.caption("Messages sorted by engagement - most popular and recent first")

        view_choice = st.selectbox(
            "View",
            ["all_school", "admins"],
            format_func=lambda x: {
                "all_school": "Whole School",
                "admins": "Admins Only"
            }[x],
            key=f"view_admin_feed_{user_info['username']}"
        )

        messages = get_messages(recipient=view_choice)

        if messages:
            for idx, msg in enumerate(messages):
                with st.container():
                    render_message_card(msg, user_id=user_info.get("name", user_info["username"]), user_role="admin", enable_comments=True, user_info=user_info, context=f"admin_feed_{user_info['username']}_{idx}")

                    if idx < len(messages) - 1:
                        st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info(" No messages available")
    
    with tab3:
        st.markdown("### Account Settings")
        
        st.markdown("#### Change Password")
        st.info("Keep your password secure and change it regularly")
        
        current_password = st.text_input("Current Password", type="password", key=f"current_pw_admin_{user_info['username']}")
        new_password = st.text_input("New Password", type="password", key=f"new_pw_admin_{user_info['username']}")
        confirm_password = st.text_input("Confirm New Password", type="password", key=f"confirm_pw_admin_{user_info['username']}")
        
        if st.button("Change Password", key=f"change_pw_admin_{user_info['username']}"):
            # Verify current password
            user = authenticate(user_info["username"], current_password)
            if not user:
                st.error(" Current password is incorrect")
            elif new_password != confirm_password:
                st.error(" New passwords do not match")
            elif len(new_password) < 6:
                st.error(" New password must be at least 6 characters")
            else:
                if reset_user_password(user_info["username"], new_password):
                    st.success(" Password changed successfully!")
                else:
                    st.error(" Failed to change password")

def super_admin_interface(user_info):
    """Super admin interface"""
    st.subheader(" Super Admin Dashboard")
    
    tab1, tab2, tab3, tab4 = st.tabs(["All Messages", "Flagged Messages", "User Management", "Analytics"])
    
    with tab1:
        st.markdown("### All Platform Messages")
        
        # Add explanation of flagging
        with st.expander(" What does 'Flagging' mean?"):
            st.markdown("""
            ### 🚩 Message Flagging System
            
            **What is flagging?**
            Flagging is a moderation tool that allows the Super Admin to mark messages that may violate community guidelines.
            
            **Why flag a message?**
            Messages should be flagged if they contain:
            -  **Abusive language** or personal attacks
            -  **Bullying or harassment** of any individual or group
            -  **Profanity or offensive content**
            -  **Hate speech** or discrimination
            -  **False information** intended to mislead
            -  **Content that could incite conflicts** or arguments
            
            **What happens when a message is flagged?**
            - The message is **marked with a red warning**
            - The **reason for flagging is displayed** to all users
            - The message **remains visible** but highlighted as concerning
            - The **sender's real identity is revealed** to the Super Admin (even if anonymous)
            - Super Admin can take further action if needed
            
            **Important Notes:**
            -  Flagging helps maintain a **safe and respectful** environment
            -  It's not about censorship, but about **accountability**
            -  This protects all community members from harmful content
            -  Students should follow **community guidelines** to avoid having messages flagged
            """)
        
        st.markdown("---")
        
        filter_recipient = st.selectbox(
            "Filter by Recipient",
            ["all", "all_school", "senate", "super_admin"],
            format_func=lambda x: {
                "all": "All Messages",
                "all_school": "School Messages",
                "senate": "Senate Messages",
                "super_admin": "Super Admin Messages"
            }[x]
        )
        
        messages = get_messages(recipient=None if filter_recipient == "all" else filter_recipient)
        
        st.markdown(f"**Total Messages:** {len(messages)}")
        
        if messages:
            for idx, msg in enumerate(messages):
                with st.container():
                    render_message_card(msg, show_sender_id=True, user_id=user_info["username"], show_reactions=False, user_role="super_admin", enable_comments=False, user_info=user_info, context=f"super_all_{idx}")
                    
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        if not msg.get("flagged", False):
                            if st.button(f"🚩 Flag", key=f"flag_msg_{msg['id']}_{idx}"):
                                reason = st.text_input(
                                    "Reason for flagging",
                                    key=f"reason_{msg['id']}_{idx}"
                                )
                                if reason:
                                    flag_message(msg["id"], reason)
                                    st.rerun()
        else:
            st.info("No messages found")
    
    with tab2:
        st.markdown("### Flagged Messages")
        messages = [m for m in get_messages() if m.get("flagged", False)]
        
        if messages:
            st.warning(f" {len(messages)} flagged message(s) requiring attention")
            for idx, msg in enumerate(messages):
                render_message_card(msg, show_sender_id=True, user_id=user_info["username"], show_reactions=False, user_role="super_admin", enable_comments=False, user_info=user_info, context=f"super_flagged_{idx}")
        else:
            st.success(" No flagged messages")
    
    with tab3:
        st.markdown("### User Management")
        
        with st.expander(" Create New User"):
            new_username = st.text_input("Username", key="new_user_username")
            new_password = st.text_input("Password", type="password", key="new_user_password")
            new_name = st.text_input("Full Name", key="new_user_name")
            new_role = st.selectbox("Role", ["student", "teacher", "senator", "admin"], key="new_user_role")
            
            if st.button("Create User", key="create_user_btn"):
                if new_username and new_password:
                    users = load_json(USERS_FILE)
                    if new_username not in users:
                        users[new_username] = {
                            "password": hash_password(new_password),
                            "role": new_role,
                            "name": new_name
                        }
                        save_json(USERS_FILE, users)
                        # Ensure SQLite mirror is created for consistent persistence
                        try:
                            sync_user_to_db(new_username)
                        except Exception:
                            pass
                        # Ensure SQLite mirror is created for consistent persistence
                        try:
                            sync_user_to_db(new_username)
                        except Exception:
                            pass
                        st.success(f" User {new_username} created successfully!")
                    else:
                        st.error(" Username already exists")
                else:
                    st.error(" Please fill in all required fields")
        
        # List all users with edit/delete options
        st.markdown("### Registered Users")
        users = load_json(USERS_FILE)
        
        for username, info in users.items():
            if username != "superadmin":
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{username}** ({info['role']}) - {info.get('name', 'N/A')}")
                
                with col2:
                    if st.button(" Edit", key=f"edit_btn_{username}"):
                        st.session_state[f"edit_{username}"] = True
                
                with col3:
                    if st.button(" Delete", key=f"delete_btn_{username}"):
                        st.session_state[f"confirm_delete_{username}"] = True
                
                # Edit user form
                if st.session_state.get(f"edit_{username}", False):
                    with st.expander(f"Edit {username}", expanded=True):
                        edit_name = st.text_input(
                            "Name",
                            value=info.get("name", ""),
                            key=f"edit_name_{username}"
                        )
                        # Role selection - compute index safely in case stored role is unexpected
                        role_options = ["student", "teacher", "senator", "admin"]
                        try:
                            role_index = role_options.index(info.get('role', 'student'))
                        except ValueError:
                            role_index = 0
                        edit_role = st.selectbox(
                            "Role",
                            role_options,
                            index=role_index,
                            key=f"edit_role_{username}"
                        )
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("Save Changes", key=f"save_edit_{username}"):
                                success = edit_user(username, new_name=edit_name, new_role=edit_role)
                                if success:
                                    st.success(f" User {username} updated successfully!")
                                    st.session_state[f"edit_{username}"] = False
                                    st.rerun()
                                else:
                                    st.error("Failed to update user. Check server logs and try again.")
                        
                        with col_cancel:
                            if st.button("Cancel", key=f"cancel_edit_{username}"):
                                st.session_state[f"edit_{username}"] = False
                                st.rerun()
                
                # Delete confirmation
                if st.session_state.get(f"confirm_delete_{username}", False):
                    st.warning(f" Are you sure you want to delete user '{username}'? This action cannot be undone!")
                    col_confirm, col_cancel_del = st.columns(2)
                    
                    with col_confirm:
                        if st.button("Yes, Delete", key=f"confirm_del_{username}", type="primary"):
                            if delete_user(username):
                                st.success(f" User {username} deleted successfully!")
                                st.session_state[f"confirm_delete_{username}"] = False
                                st.rerun()
                    
                    with col_cancel_del:
                        if st.button("Cancel", key=f"cancel_del_{username}"):
                            st.session_state[f"confirm_delete_{username}"] = False
                            st.rerun()
                
                st.divider()
    
    with tab4:
        st.markdown("### Platform Analytics")
        
        messages = get_messages()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Messages", len(messages))
        
        with col2:
            flagged = len([m for m in messages if m.get("flagged", False)])
            st.metric("Flagged Messages", flagged)
        
        with col3:
            anonymous = len([m for m in messages if m.get("is_anonymous", False)])
            st.metric("Anonymous Messages", anonymous)
        
        # Messages by role
        st.markdown("### Messages by Role")
        role_counts = {}
        for msg in messages:
            role = msg["sender_role"]
            role_counts[role] = role_counts.get(role, 0) + 1
        
        for role, count in role_counts.items():
            st.markdown(f"- **{role.replace('_', ' ').title()}**: {count} messages")
        
        # Reaction analytics
        st.markdown("### Reaction Analytics")
        total_reactions = 0
        reaction_counts = {"👍": 0, "❤️": 0, "💡": 0, "👏": 0, "🤔": 0}
        
        for msg in messages:
            reactions = msg.get("reactions", {})
            for emoji, users in reactions.items():
                count = len(users)
                total_reactions += count
                if emoji in reaction_counts:
                    reaction_counts[emoji] += count
        
        st.metric("Total Reactions", total_reactions)
        
        col1, col2, col3, col4, col5 = st.columns(5)
        cols = [col1, col2, col3, col4, col5]
        for idx, (emoji, count) in enumerate(reaction_counts.items()):
            with cols[idx]:
                st.metric(emoji, count)

# ============================================================================
# ACCOUNT SETTINGS & FEED RENDERING
# ============================================================================

def render_account_settings(user_info, role=None):
    """Render account settings"""
    st.markdown("#### Change Password")
    st.info("Keep your password secure and change it regularly")
    
    current_password = st.text_input("Current Password", type="password", key=f"current_pw_{user_info['username']}")
    new_password = st.text_input("New Password", type="password", key=f"new_pw_{user_info['username']}")
    confirm_password = st.text_input("Confirm New Password", type="password", key=f"confirm_pw_{user_info['username']}")
    
    if st.button("Change Password", key=f"change_pw_{user_info['username']}"):
        user = authenticate(user_info["username"], current_password)
        if not user:
            st.error("Current password is incorrect")
        elif new_password != confirm_password:
            st.error("New passwords do not match")
        elif len(new_password) < 6:
            st.error("New password must be at least 6 characters")
        else:
            if reset_user_password(user_info["username"], new_password):
                st.success("Password changed successfully!")
            else:
                st.error("Failed to change password")
    
    # Anonymous name settings for students
    if role == "student" or user_info.get("role") == "student":
        st.markdown("---")
        st.markdown("#### Your Anonymous Identity")
        st.info("Customize how you appear when sending anonymous messages")
        
        anon_names = load_json(ANONYMOUS_NAMES_FILE)
        current_anon_name = anon_names.get(user_info["username"], "Not set")
        
        st.markdown(f"**Current Anonymous Name:** `{current_anon_name}`")
        
        col1, col2 = st.columns(2)
        
        with col1:
            new_anon_name = st.text_input(
                "Choose a New Anonymous Name (optional)",
                placeholder="e.g., VoiceOfChange, ConcernedLearner",
                max_chars=20,
                key=f"anon_new_{user_info['username']}"
            )
            
            if st.button("Update Anonymous Name", key=f"update_anon_{user_info['username']}", use_container_width=True):
                if new_anon_name.strip():
                    anon_names = load_json(ANONYMOUS_NAMES_FILE)
                    anon_names[user_info["username"]] = new_anon_name.strip()[:20]
                    save_json(ANONYMOUS_NAMES_FILE, anon_names)
                    st.success(f"✅ Anonymous name updated to: {new_anon_name.strip()}")
                    st.rerun()
                else:
                    st.error("Please enter a name")
        
        with col2:
            st.write("")
            if st.button("🔄 Reset to Auto-Generated Name", key=f"reset_anon_{user_info['username']}", use_container_width=True):
                new_name = reset_anonymous_name(user_info["username"])
                st.success(f"✅ Reset to: {new_name}")
                st.rerun()

def render_profile(viewer_info, viewed_username):
    """Render a user's profile with follow/unfollow and edit options"""
    profile = get_user_profile(viewed_username)
    viewer = viewer_info['username']

    # Owner viewing their own profile sees full details
    if viewer == viewed_username:
        st.markdown(f"### {profile.get('name', viewed_username)} (@{viewed_username})")
    else:
        # By default show only anonymous identity: anonymous name, profile pic and bio.
        # Real name and username are only shown if the viewed user has explicitly revealed to this viewer.
        try:
            revealed = has_revealed_to(viewed_username, viewer)
        except Exception:
            revealed = False

        if revealed:
            st.markdown(f"### {profile.get('name', viewed_username)} (@{viewed_username})")
        else:
            anon_name = get_or_create_anonymous_name(viewed_username)
            st.markdown(f"### {anon_name} (Anonymous)")

    # Profile photo
    photo = profile.get('profile_photo')
    if photo:
        # support dict or string path
        img_path = photo.get('path') if isinstance(photo, dict) else photo
        try:
            st.image(img_path, width=150)
        except Exception:
            st.markdown("(Profile image not found)")
    else:
        st.markdown("_(No profile photo)_")

    # Bio
    bio = profile.get('bio', '')
    if bio:
        st.markdown(f"**Bio:** {bio}")
    else:
        st.markdown("_(No bio)_")

    # Follow counts
    followers = get_followers_count(viewed_username)
    following = get_following_count(viewed_username)
    st.markdown(f"**Followers:** {followers} • **Following:** {following}")

    # If viewing someone else, show follow/unfollow and message
    viewer = viewer_info['username']
    if viewer != viewed_username:
        if is_following(viewer, viewed_username):
            if st.button("Unfollow", key=f"unfollow_{viewer}_{viewed_username}"):
                unfollow_user(viewer, viewed_username)
                st.success("Unfollowed")
                st.rerun()
        else:
            if st.button("Follow", key=f"follow_{viewer}_{viewed_username}"):
                follow_user(viewer, viewed_username)
                st.success("Now following")
                st.rerun()

        # Only allow starting a private conversation when users are mutual followers (friends)
        are_following = is_following(viewer, viewed_username)
        are_followed_back = is_following(viewed_username, viewer)
        if are_following and are_followed_back:
            if st.button("Start Conversation", key=f"start_conv_{viewer}_{viewed_username}"):
                conv_id, anon_default = create_or_get_conversation(viewer, viewed_username, anon_by_default=True)
                st.success("Conversation opened")
                st.session_state['open_conversation'] = conv_id
                st.session_state['current_view'] = 'conversations'
        else:
            if not are_following:
                st.info("You are not following this user. Follow them to request a connection.")
            elif not are_followed_back:
                st.info("They are not following you back yet. If they follow you, you'll become friends and can message each other.")
    else:
        # Editing own profile
        st.markdown("---")
        st.markdown("#### Edit Profile")
        col1, col2 = st.columns([2,1])
        with col1:
            new_name = st.text_input("Display Name", value=profile.get('name', viewer), key=f"edit_name_{viewer}")
            new_bio = st.text_area("Bio", value=profile.get('bio', ''), key=f"edit_bio_{viewer}")
            photo_file = st.file_uploader("Upload Profile Photo (max 30 MB)", type=None, key=f"profile_photo_{viewer}")
            if st.button("Save Profile", key=f"save_profile_{viewer}"):
                photo_meta = None
                if photo_file is not None:
                    try:
                        photo_meta = save_media_file(photo_file)
                    except ValueError as e:
                        st.error(str(e))
                        return
                if update_profile(viewer, new_name, new_bio, profile_photo_meta=(photo_meta if photo_meta else profile.get('profile_photo'))):
                    st.success("Profile updated")
                    st.rerun()
                else:
                    st.error("Failed to update profile")
        with col2:
            st.markdown("#### Manage")
            if st.button("Reset Anonymous Name", key=f"reset_anon_profile_{viewer}"):
                new_name = reset_anonymous_name(viewer)
                st.success(f"Anonymous name reset to {new_name}")
                st.rerun()
            # Reveal management: choose specific users who may see your real name
            st.markdown("---")
            st.markdown("**Reveal Real Identity To (optional)**")
            users = load_json(USERS_FILE)
            all_other_users = [u for u in users.keys() if u != viewer]
            current_revealed = get_revealed_list(viewer)
            selected = st.multiselect("Select users to reveal your real identity to:", options=all_other_users, default=current_revealed, key=f"reveal_select_{viewer}")
            if st.button("Update Reveal List", key=f"update_reveal_{viewer}"):
                set_revealed_list(viewer, selected)
                st.success("Reveal list updated")
                st.rerun()


def render_people_directory(viewer_info):
    """Render a searchable people directory where users can follow and view profiles."""
    st.markdown("### People")
    users = load_json(USERS_FILE)
    search = st.text_input("Search users by username or name", key="people_search")

    # viewer username must be known for reveal/follow checks
    viewer = viewer_info['username']

    # Build a list of matching usernames
    matches = []
    for username, info in users.items():
        if username == "superadmin":
            continue
        display = info.get('name', '')
        if not search or (search.lower() in username.lower()) or (search.lower() in display.lower()):
            matches.append((username, info))

    if not matches:
        st.info("No users found")
        return

    for username, info in matches:
        col1, col2, col3, col4 = st.columns([1, 3, 1, 1])
        with col1:
            photo = info.get('profile_photo')
            if photo:
                img_path = photo.get('path') if isinstance(photo, dict) else photo
                try:
                    st.image(img_path, width=60)
                except Exception:
                    st.write("")
            else:
                st.write("")
        with col2:
            # Determine whether to show real identity or anonymous name
            try:
                revealed = has_revealed_to(username, viewer)
            except Exception:
                revealed = False

            if viewer == username or revealed:
                # Owner or explicitly revealed: show real name and username
                st.markdown(f"**{info.get('name', username)}** (@{username})")
                st.caption(info.get('role', ''))
            else:
                # Public browsing: only show anonymous identity, profile pic and bio
                anon_name = get_or_create_anonymous_name(username)
                st.markdown(f"**{anon_name}** (Anonymous)")
                # optionally show role lightly or omit; we omit to maximize privacy
                bio = info.get('bio', '')
                if bio:
                    st.caption(bio)
        with col3:
            viewer = viewer_info['username']
            if is_following(viewer, username):
                if st.button("Unfollow", key=f"people_unfollow_{viewer}_{username}"):
                    unfollow_user(viewer, username)
                    st.success("Unfollowed")
                    st.rerun()
            else:
                if st.button("Follow", key=f"people_follow_{viewer}_{username}"):
                    follow_user(viewer, username)
                    st.success("Now following")
                    st.rerun()
        with col4:
            # Friend badge if mutual follow
            if is_following(viewer, username) and is_following(username, viewer):
                st.markdown("**Friend**")
            if st.button("View Profile", key=f"viewprofile_{viewer}_{username}"):
                st.session_state['profile_view_user'] = username
                st.session_state['current_view'] = 'profile'
                st.rerun()


def render_post_composer(user_info, role):
    """Render the post composer box"""
    st.markdown('<div class="post-composer">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([0.15, 0.85])
    
    with col1:
        avatar_char = user_info['name'][0].upper() if user_info['name'] else user_info['username'][0].upper()
        st.markdown(f'<div class="post-composer-avatar">{avatar_char}</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"**{user_info['name']}** ({role.replace('_', ' ').title()})")
        st.markdown("*What's on your mind?*")
    
    st.markdown('</div>', unsafe_allow_html=True)


def render_conversation_view(conv_id, viewer_info):
    """Render a single conversation chat view with send box."""
    viewer = viewer_info['username']
    # Fetch conversation participants
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT user_a, user_b, anon_by_default FROM conversations WHERE id=?", (conv_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        st.error("Conversation not found")
        return
    ua, ub, anon_default = row
    other = ua if viewer != ua else ub

    # Header: show real name only if other revealed to viewer
    try:
        other_revealed = has_revealed_to(other, viewer)
    except Exception:
        other_revealed = False
    if other_revealed:
        other_display = load_json(USERS_FILE).get(other, {}).get('name', other)
    else:
        other_display = get_or_create_anonymous_name(other)
    st.markdown(f"### Conversation with {other_display}")

    # Show messages
    msgs = get_conversation_messages(conv_id)
    box = st.container()
    with box:
        for m in msgs:
            timestamp = m.get('created_at')
            # Determine display name: if message is anonymous show anon_name; else show real name only if revealed
            sender = m.get('sender')
            if m.get('is_anonymous'):
                sender_display = m.get('anon_name') or get_or_create_anonymous_name(sender)
            else:
                # check reveal
                if has_revealed_to(sender, viewer):
                    sender_display = load_json(USERS_FILE).get(sender, {}).get('name', sender)
                else:
                    sender_display = m.get('anon_name') or get_or_create_anonymous_name(sender)

            st.markdown(f"**{sender_display}** — {escape(m.get('content',''))}")
            st.caption(timestamp)

    st.markdown("---")
    # Send message box
    key_in = f"conv_input_{conv_id}_{viewer}"
    msg = st.text_input("Write a message", key=key_in)
    anon_key = f"conv_anon_{conv_id}_{viewer}"
    send_anon = st.checkbox("Send anonymously", value=bool(anon_default), key=anon_key)
    if st.button("Send", key=f"send_conv_{conv_id}_{viewer}"):
        content = st.session_state.get(key_in, "").strip()
        if not content:
            st.error("Please enter a message")
        else:
            anon_name = get_or_create_anonymous_name(viewer) if send_anon else None
            try:
                send_db_message(conv_id, viewer, content, is_anonymous=send_anon, anon_name=anon_name)
                st.success("Message sent")
                st.session_state[key_in] = ""
                st.rerun()
            except Exception as e:
                st.error(f"Failed to send message: {e}")


def render_conversations(viewer_info):
    """List conversations and allow opening one."""
    viewer = viewer_info['username']
    st.markdown("### Conversations")
    convs = get_user_conversations(viewer)
    if not convs:
        st.info("No conversations yet. Start one from a profile.")
        return
    for conv in convs:
        conv_id, a, b, anon_by_default, created_at = conv
        other = a if viewer != a else b
        # Show other user's anon display unless revealed
        try:
            revealed = has_revealed_to(other, viewer)
        except Exception:
            revealed = False
        if revealed:
            display = load_json(USERS_FILE).get(other, {}).get('name', other)
        else:
            display = get_or_create_anonymous_name(other)

        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown(f"**{display}**")
            # show last message preview
            msgs = get_conversation_messages(conv_id)
            if msgs:
                last = msgs[-1]
                preview = last.get('content','')[:120]
                st.caption(preview)
        with col2:
            if st.button("Open", key=f"open_conv_{conv_id}"):
                st.session_state['open_conversation'] = conv_id
                st.session_state['current_view'] = 'conversations'
                st.rerun()

    # If an open conversation is set, render it below
    open_conv = st.session_state.get('open_conversation')
    if open_conv:
        st.markdown("---")
        render_conversation_view(open_conv, viewer_info)

def student_feed(user_info):
    """Student feed with post composer and messages"""
    render_post_composer(user_info, "student")
    
    # Post composer
    col1, col2 = st.columns([2, 1])
    
    with col1:
        message_input = st.text_input(
            "Your Message (press Enter to send)",
            placeholder="Share your thoughts...",
            key=f"msg_input_student_{user_info['username']}",
            on_change=_student_send_on_enter,
            args=(user_info['username'],)
        )
    
    with col2:
        recipient = st.selectbox(
            "Send To",
            ["all_school", "senate"],
            format_func=lambda x: {"all_school": "School", "senate": "Senate"}[x],
            key=f"recipient_student_{user_info['username']}"
        )
    
    # Anonymous checkbox
    is_anonymous = st.checkbox(
        "Send Anonymously",
        value=True,
        key=f"is_anon_student_{user_info['username']}",
        disabled=(recipient != "all_school")
    )
    
    st.markdown("---")
    
    # Feed
    st.markdown("### Messages")
    messages = get_messages(recipient="all_school")
    
    if messages:
        for idx, msg in enumerate(messages):
            with st.container():
                render_message_card(msg, user_id=user_info["username"], user_role="student", enable_comments=True, user_info=user_info, context=f"student_{user_info['username']}_{idx}")
                if idx < len(messages) - 1:
                    st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No messages yet. Be the first to share!")

def teacher_feed(user_info):
    """Teacher feed"""
    render_post_composer(user_info, "teacher")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        message_input = st.text_input(
            "Your Message (press Enter to send)",
            placeholder="Share announcements...",
            key=f"msg_input_teacher_{user_info['username']}",
            on_change=_teacher_send_on_enter,
            args=(user_info['username'],)
        )
    
    with col2:
        recipient = st.selectbox(
            "Send To",
            ["all_school", "teachers", "senate", "super_admin"],
            format_func=lambda x: {"all_school": "School", "teachers": "Teachers", "senate": "Senate", "super_admin": "Admin"}[x],
            key=f"recipient_teacher_{user_info['username']}"
        )
    
    st.markdown("---")
    
    view = st.selectbox("View", ["all_school", "teachers"], format_func=lambda x: {"all_school": "School Feed", "teachers": "Teachers Only"}[x], key=f"view_teacher_{user_info['username']}")
    
    messages = get_messages(recipient=view)
    
    if messages:
        for idx, msg in enumerate(messages):
            with st.container():
                render_message_card(msg, user_id=user_info.get("name", user_info["username"]), user_role="teacher", enable_comments=True, user_info=user_info, context=f"teacher_{user_info['username']}_{idx}")
                if idx < len(messages) - 1:
                    st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No messages available")

def senator_feed(user_info):
    """Senator feed"""
    render_post_composer(user_info, "senator")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        message_input = st.text_input(
            "Your Message (press Enter to send)",
            placeholder="Share your message...",
            key=f"msg_input_senator_{user_info['username']}",
            on_change=_senator_send_on_enter,
            args=(user_info['username'],)
        )
    
    with col2:
        recipient = st.selectbox(
            "Send To",
            ["all_school", "senate", "teachers", "admins", "super_admin"],
            format_func=lambda x: {"all_school": "School", "senate": "Senate", "teachers": "Teachers", "admins": "Admins", "super_admin": "Admin"}[x],
            key=f"recipient_senator_{user_info['username']}"
        )
    
    is_anonymous = st.checkbox(
        "Send Anonymously",
        value=False,
        key=f"is_anon_senator_{user_info['username']}",
        disabled=(recipient != "all_school")
    )
    
    st.markdown("---")
    
    messages = get_messages(recipient="all_school")
    
    if messages:
        for idx, msg in enumerate(messages):
            with st.container():
                render_message_card(msg, user_id=user_info.get("name", user_info["username"]), user_role="senator", enable_comments=True, user_info=user_info, context=f"senator_{user_info['username']}_{idx}")
                if idx < len(messages) - 1:
                    st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No school messages yet")

def admin_feed(user_info):
    """Admin feed"""
    render_post_composer(user_info, "admin")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        message_input = st.text_input(
            "Your Message (press Enter to send)",
            placeholder="Share announcements...",
            key=f"msg_input_admin_{user_info['username']}",
            on_change=_admin_send_on_enter,
            args=(user_info['username'],)
        )
    
    with col2:
        recipient = st.selectbox(
            "Send To",
            ["all_school", "admins", "senate", "super_admin"],
            format_func=lambda x: {"all_school": "School", "admins": "Admins", "senate": "Senate", "super_admin": "Admin"}[x],
            key=f"recipient_admin_{user_info['username']}"
        )
    
    st.markdown("---")
    
    view = st.selectbox("View", ["all_school", "admins"], format_func=lambda x: {"all_school": "School Feed", "admins": "Admins Only"}[x], key=f"view_admin_{user_info['username']}")
    
    messages = get_messages(recipient=view)
    
    if messages:
        for idx, msg in enumerate(messages):
            with st.container():
                render_message_card(msg, user_id=user_info.get("name", user_info["username"]), user_role="admin", enable_comments=True, user_info=user_info, context=f"admin_{user_info['username']}_{idx}")
                if idx < len(messages) - 1:
                    st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("No messages available")

def super_admin_feed(user_info):
    """Super admin feed"""
    st.subheader("Admin Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["All Messages", "Flagged", "User Management"])
    
    with tab1:
        filter_recipient = st.selectbox(
            "Filter by Recipient",
            ["all", "all_school", "senate"],
            format_func=lambda x: {"all": "All", "all_school": "School", "senate": "Senate"}[x]
        )
        
        messages = get_messages(recipient=None if filter_recipient == "all" else filter_recipient)
        st.markdown(f"**Total Messages:** {len(messages)}")
        
        for idx, msg in enumerate(messages):
            render_message_card(msg, show_sender_id=True, user_id=user_info["username"], show_reactions=False, user_role="super_admin", enable_comments=False, user_info=user_info, context=f"super_all_{idx}")
    
    with tab2:
        messages = [m for m in get_messages() if m.get("flagged", False)]
        st.warning(f"{len(messages)} flagged message(s)")
        
        for idx, msg in enumerate(messages):
            render_message_card(msg, show_sender_id=True, user_id=user_info["username"], show_reactions=False, user_role="super_admin", enable_comments=False, user_info=user_info, context=f"super_flagged_{idx}")
    
    with tab3:
        st.markdown("### User Management")
        with st.expander("Create New User"):
            new_username = st.text_input("Username", key="new_user_username")
            new_password = st.text_input("Password", type="password", key="new_user_password")
            new_name = st.text_input("Full Name", key="new_user_name")
            new_role = st.selectbox("Role", ["student", "teacher", "senator", "admin"], key="new_user_role")
            
            if st.button("Create User", key="create_user_btn"):
                if new_username and new_password:
                    users = load_json(USERS_FILE)
                    if new_username not in users:
                        users[new_username] = {
                            "password": hash_password(new_password),
                            "role": new_role,
                            "name": new_name
                        }
                        save_json(USERS_FILE, users)
                        # ensure SQLite has same user
                        try:
                            sync_user_to_db(new_username)
                        except Exception:
                            pass
                        st.success(f"User {new_username} created!")
                    else:
                        st.error("Username exists")
                else:
                    st.error("Fill in all fields")
        
        st.markdown("### Registered Users")
        users = load_json(USERS_FILE)
        
        for username, info in users.items():
            if username != "superadmin":
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.markdown(f"**{username}** ({info['role']})")
                
                with col2:
                    if st.button("Edit", key=f"edit_btn_{username}"):
                        st.session_state[f"edit_{username}"] = True
                
                with col3:
                    if st.button("Delete", key=f"delete_btn_{username}"):
                        st.session_state[f"confirm_delete_{username}"] = True

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application"""
    render_header()
    
    # Session state for authentication
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_info = None
    
    # Login/Logout
    if not st.session_state.authenticated:
        st.markdown("###  Login")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login", type="primary")
                
                if submit:
                    user = authenticate(username, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_info = {
                            "username": username,
                            "role": user["role"],
                            "name": user.get("name", username),
                            "email": user.get("email", "")
                        }
                        st.rerun()
                    else:
                        st.error(" Invalid credentials")
            
            st.info(" Contact administration for account access")
    
    else:
        # Show appropriate interface based on role
        user_info = st.session_state.user_info
        role = user_info["role"]
        
        # TOP BAR: Navigation and Notifications
        st.markdown("---")
        # wrapper ensures icons use currentColor and dark-mode rules
        st.markdown('<div class="topbar-wrapper">', unsafe_allow_html=True)
        top_col1, top_col2, top_col3, top_col4, top_col5, top_col6 = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 1])

        # Top-bar styles: bold text buttons matching username display
        st.markdown("""
        <style>
        .topbar-nav-btn {
            font-size: 16px;
            font-weight: 700;
            color: inherit;
            background: none;
            border: none;
            padding: 0.5rem 0.75rem;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            border-radius: 4px;
            transition: background 0.2s;
        }
        .topbar-nav-btn:hover {
            background: rgba(0,0,0,0.05);
        }
        .topbar-nav-btn:focus {
            outline: 2px solid currentColor;
            outline-offset: 2px;
        }
        @media (prefers-color-scheme: dark) {
            .topbar-nav-btn:hover { background: rgba(255,255,255,0.05); }
        }
        </style>
        """, unsafe_allow_html=True)

        with top_col1:
            st.markdown('**Home**', unsafe_allow_html=True)
            if st.button("", key="nav_home", use_container_width=True, help="Go to Home"):
                st.session_state['current_view'] = 'home'
                st.rerun()

        with top_col2:
            try:
                unread = get_unread_notifications_count(user_info['username'])
            except Exception:
                unread = 0
            notif_label = f"**Notifications** ({unread})" if unread > 0 else "**Notifications**"
            st.markdown(notif_label, unsafe_allow_html=True)
            if st.button("", key="nav_notif", use_container_width=True, help="View Notifications"):
                st.session_state['current_view'] = 'notifications'
                st.rerun()

        with top_col3:
            st.markdown('**Settings**', unsafe_allow_html=True)
            if st.button("", key="nav_settings", use_container_width=True, help="Account Settings"):
                st.session_state['current_view'] = 'settings'
                st.rerun()

        with top_col4:
            st.markdown('**People**', unsafe_allow_html=True)
            if st.button("", key="nav_people", use_container_width=True, help="Browse People"):
                st.session_state['current_view'] = 'people'
                st.rerun()

        with top_col5:
            st.markdown('**Profile**', unsafe_allow_html=True)
            if st.button(user_info['name'], key='nav_profile', use_container_width=True, help='View Profile'):
                st.session_state['current_view'] = 'profile'
                st.session_state['profile_view_user'] = user_info['username']
                st.rerun()

        with top_col6:
            st.markdown('**Log Out**', unsafe_allow_html=True)
            if st.button("", key=f"logout_btn_{user_info['username']}", use_container_width=True, help="Log Out"):
                st.session_state.authenticated = False
                st.session_state.user_info = None
                st.rerun()

        # close wrapper
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")

        # MAIN CONTENT AREA
        current_view = st.session_state.get('current_view', 'home')
        
        if current_view == 'home':
            if role == "student":
                student_feed(user_info)
            elif role == "teacher":
                teacher_feed(user_info)
            elif role == "senator":
                senator_feed(user_info)
            elif role == "admin":
                admin_feed(user_info)
            elif role == "super_admin":
                super_admin_feed(user_info)
        
        elif current_view == 'settings':
            st.subheader("⚙️ Account Settings")
            render_account_settings(user_info, role=role)
        
        elif current_view == 'about':
            st.subheader("📖 Community Guidelines")
            st.markdown("""
            ### Guidelines
            - Be respectful and constructive
            - No bullying or harassment
            - No profanity or offensive language
            - Focus on solutions, not problems
            - Respect anonymity of others
            
            ### 🚩 Message Flagging
            Messages may be flagged by Super Admin if they:
            - Contain abusive/offensive content
            - Violate community guidelines
            - Could harm or mislead others
            """)
        
        elif current_view == 'profile':
            st.subheader("👤 Profile")
            viewed_username = st.session_state.get('profile_view_user', user_info['username'])
            render_profile(user_info, viewed_username)

        elif current_view == 'people':
            render_people_directory(user_info)

        elif current_view == 'conversations':
            render_conversations(user_info)

        elif current_view == 'notifications':
            st.subheader("🔔 All Notifications")
            try:
                unread = get_unread_notifications_count(user_info['username'])
            except Exception:
                unread = 0
            
            notifs = load_notifications().get(user_info['username'], [])
            
            if notifs:
                st.markdown(f"**Unread Notifications:** {unread}")
                st.markdown("---")
                
                for n in notifs:  # Show all notifications
                            read_status = "🔔" if not n.get('read') else "✓"
                            # Render notification text
                            st.markdown(f"""
                            <div class="notification-item {'unread' if not n.get('read') else ''}">
                            {read_status} {n.get('text')}<br>
                            <small>{n.get('timestamp', 'N/A')}</small>
                            </div>
                            """, unsafe_allow_html=True)

                            # If this is a follow notification, provide a follow-back button
                            try:
                                if n.get('type') == 'follow' and n.get('actor'):
                                    actor = n.get('actor')
                                    actor_display = n.get('actor_display', actor)
                                    # If current user is not already following actor, show follow-back
                                    if not is_following(user_info['username'], actor):
                                        if st.button(f"Follow back {actor_display}", key=f"followback_{n['id']}"):
                                            follow_user(user_info['username'], actor)
                                            st.success(f"You are now following {actor_display}")
                                            # mark notification read and refresh
                                            mark_notification_read(user_info['username'], n['id'])
                                            st.rerun()
                            except Exception:
                                pass
                
                if st.button("Mark all notifications as read", key=f"mark_read_{user_info['username']}", use_container_width=True):
                    mark_all_notifications_read(user_info['username'])
                    st.rerun()
            else:
                st.info("No notifications yet")

if __name__ == "__main__":
    main()
