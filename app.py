import streamlit as st
import json
import hashlib
import secrets
from datetime import datetime
import os
from pathlib import Path

# ============================================================================
# CONFIGURATION & SETUP
# ============================================================================

# Set page config
st.set_page_config(
    page_title="Empower Voice Platform",
    page_icon="🎓",
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
    }
    
    .badge-student {
        background: #e3f2fd;
        color: #1976d2;
    }
    
    .badge-teacher {
        background: #f3e5f5;
        color: #7b1fa2;
    }
    
    .badge-senator {
        background: #e8f5e9;
        color: #388e3c;
    }
    
    .badge-admin {
        background: #fff3e0;
        color: #f57c00;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# DATA MANAGEMENT
# ============================================================================

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
MESSAGES_FILE = DATA_DIR / "messages.json"
ANONYMOUS_NAMES_FILE = DATA_DIR / "anonymous_names.json"

def load_json(filepath):
    """Load JSON data from file"""
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    """Save JSON data to file"""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

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
                "name": "Super Administrator",
                "email": "admin@empowerinternational.edu"
            }
        }
        save_json(USERS_FILE, users)
    
    if not MESSAGES_FILE.exists():
        save_json(MESSAGES_FILE, {"messages": []})
    
    if not ANONYMOUS_NAMES_FILE.exists():
        save_json(ANONYMOUS_NAMES_FILE, {})

# Initialize data
initialize_data()

# ============================================================================
# AUTHENTICATION
# ============================================================================

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
            "❤️": [],
            "💡": [],
            "👏": [],
            "🤔": []
        }
    }
    
    messages_data["messages"].append(message)
    save_json(MESSAGES_FILE, messages_data)
    return True

def get_messages(recipient=None, role=None):
    """Get messages filtered by recipient and/or role"""
    messages_data = load_json(MESSAGES_FILE)
    messages = messages_data["messages"]
    
    if recipient:
        messages = [m for m in messages if m["recipient"] == recipient]
    
    if role:
        messages = [m for m in messages if m["sender_role"] == role or m["recipient"] == "all_school"]
    
    # Sort by timestamp (newest first)
    messages.sort(key=lambda x: x["timestamp"], reverse=True)
    return messages

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
                    "❤️": [],
                    "💡": [],
                    "👏": [],
                    "🤔": []
                }
            
            # Toggle reaction - remove if already present, add if not
            if user_id in msg["reactions"][emoji]:
                msg["reactions"][emoji].remove(user_id)
            else:
                msg["reactions"][emoji].append(user_id)
            
            save_json(MESSAGES_FILE, messages_data)
            return True
    return False

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

def render_message_card(message, show_sender_id=False, user_id=None, show_reactions=True):
    """Render a message card"""
    flagged_class = "flagged" if message.get("flagged", False) else ""
    
    # Role badge
    role_badges = {
        "student": "badge-student",
        "teacher": "badge-teacher",
        "senator": "badge-senator",
        "super_admin": "badge-admin"
    }
    badge_class = role_badges.get(message["sender_role"], "badge-student")
    
    sender_display = message["sender_display"]
    if show_sender_id and message["is_anonymous"]:
        sender_display += f" (Real ID: {message['sender_id']})"
    
    timestamp = datetime.fromisoformat(message["timestamp"]).strftime("%B %d, %Y at %I:%M %p")
    
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
            {message['content']}
        </div>
        {f'<div style="margin-top: 0.5rem; color: #f44336; font-weight: 600;">⚠️ Flagged: {message["flag_reason"]}</div>' if message.get("flagged") else ''}
    </div>
    """, unsafe_allow_html=True)
    
    # Add reactions section
    if show_reactions and user_id:
        reactions = message.get("reactions", {
            "👍": [],
            "❤️": [],
            "💡": [],
            "👏": [],
            "🤔": []
        })
        
        st.markdown("#### React to this message:")
        cols = st.columns(5)
        
        for idx, (emoji, users) in enumerate(reactions.items()):
            with cols[idx]:
                count = len(users)
                has_reacted = user_id in users
                button_type = "primary" if has_reacted else "secondary"
                
                if st.button(f"{emoji} {count}", key=f"react_{message['id']}_{emoji}", type=button_type):
                    add_reaction(message['id'], user_id, emoji)
                    st.rerun()
        
        st.markdown("---")

# ============================================================================
# ROLE-SPECIFIC INTERFACES
# ============================================================================

def student_interface(user_info):
    """Student interface"""
    st.subheader("📝 Student Voice Platform")
    
    tab1, tab2, tab3 = st.tabs(["Send Message", "My Anonymous Profile", "View Messages"])
    
    with tab1:
        st.markdown("### Send a Message")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Message content
            message_content = st.text_area(
                "Your Message",
                placeholder="Share your thoughts, ideas, or concerns...",
                height=150,
                help="Be respectful and constructive in your communication"
            )
        
        with col2:
            # Anonymous option
            is_anonymous = st.checkbox(
                "Send Anonymously",
                value=True,
                help="Your identity will be hidden from recipients (but traceable by super admin if needed)"
            )
            
            # Recipient selection
            recipient = st.selectbox(
                "Send To",
                ["all_school", "senate"],
                format_func=lambda x: "Whole School" if x == "all_school" else "Senate"
            )
            
            st.info("⚠️ Note: Anonymous messages can be traced by administration if they violate community guidelines.")
        
        if st.button("📤 Send Message", type="primary"):
            if message_content.strip():
                anon_name = None
                if is_anonymous:
                    anon_name = get_or_create_anonymous_name(user_info["username"])
                
                create_message(
                    sender_id=user_info["username"],
                    sender_role="student",
                    content=message_content,
                    recipient=recipient,
                    is_anonymous=is_anonymous,
                    anonymous_name=anon_name
                )
                st.success("✅ Message sent successfully!")
                st.rerun()
            else:
                st.error("❌ Please enter a message")
    
    with tab2:
        st.markdown("### Your Anonymous Identity")
        
        anon_names = load_json(ANONYMOUS_NAMES_FILE)
        current_name = anon_names.get(user_info["username"], "Not set")
        
        st.info(f"**Current Anonymous Name:** {current_name}")
        
        new_name = st.text_input(
            "Choose a New Anonymous Name (optional)",
            placeholder="e.g., StudentVoice2024, ConcernedLearner",
            max_chars=20
        )
        
        if st.button("Update Anonymous Name"):
            if new_name.strip():
                anon_names = load_json(ANONYMOUS_NAMES_FILE)
                anon_names[user_info["username"]] = new_name.strip()
                save_json(ANONYMOUS_NAMES_FILE, anon_names)
                st.success(f"✅ Anonymous name updated to: {new_name.strip()}")
                st.rerun()
    
    with tab3:
        st.markdown("### School Messages")
        messages = get_messages(recipient="all_school")
        
        if messages:
            for msg in messages:
                render_message_card(msg, user_id=user_info["username"])
        else:
            st.info("No messages yet. Be the first to share your voice!")

def teacher_interface(user_info):
    """Teacher interface"""
    st.subheader("👨‍🏫 Teacher Platform")
    
    tab1, tab2 = st.tabs(["Send Message", "View Messages"])
    
    with tab1:
        st.markdown("### Send a Message")
        st.info("📢 Teachers must identify themselves - all messages are sent with your name")
        
        message_content = st.text_area(
            "Your Message",
            placeholder="Share announcements, feedback, or information...",
            height=150
        )
        
        recipient = st.selectbox(
            "Send To",
            ["all_school", "admin", "senate"],
            format_func=lambda x: {
                "all_school": "Whole School",
                "admin": "Administration",
                "senate": "Senate"
            }[x]
        )
        
        if st.button("📤 Send Message", type="primary"):
            if message_content.strip():
                create_message(
                    sender_id=user_info.get("name", user_info["username"]),
                    sender_role="teacher",
                    content=message_content,
                    recipient=recipient,
                    is_anonymous=False
                )
                st.success("✅ Message sent successfully!")
                st.rerun()
            else:
                st.error("❌ Please enter a message")
    
    with tab2:
        st.markdown("### School Messages")
        messages = get_messages(recipient="all_school")
        
        if messages:
            for msg in messages:
                render_message_card(msg, user_id=user_info.get("name", user_info["username"]))
        else:
            st.info("No messages available")

def senator_interface(user_info):
    """Senator interface"""
    st.subheader("🏛️ Senate Platform")
    
    tab1, tab2, tab3 = st.tabs(["Send Message", "Senate Discussion", "School Messages"])
    
    with tab1:
        st.markdown("### Send a Message")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            message_content = st.text_area(
                "Your Message",
                placeholder="Share your message...",
                height=150
            )
        
        with col2:
            recipient = st.selectbox(
                "Send To",
                ["all_school", "senate", "admin"],
                format_func=lambda x: {
                    "all_school": "Whole School",
                    "senate": "Senate Only",
                    "admin": "Administration"
                }[x]
            )
            
            is_anonymous = st.checkbox(
                "Send Anonymously to School",
                value=False,
                help="Only available when sending to whole school",
                disabled=(recipient != "all_school")
            )
            
            if recipient != "all_school":
                st.info("ℹ️ Messages to Senate and Admin are not anonymous")
        
        if st.button("📤 Send Message", type="primary"):
            if message_content.strip():
                anon_name = None
                use_anon = is_anonymous and recipient == "all_school"
                
                if use_anon:
                    anon_name = get_or_create_anonymous_name(user_info["username"])
                
                create_message(
                    sender_id=user_info.get("name", user_info["username"]),
                    sender_role="senator",
                    content=message_content,
                    recipient=recipient,
                    is_anonymous=use_anon,
                    anonymous_name=anon_name
                )
                st.success("✅ Message sent successfully!")
                st.rerun()
            else:
                st.error("❌ Please enter a message")
    
    with tab2:
        st.markdown("### Senate Discussion Board")
        messages = get_messages(recipient="senate")
        
        if messages:
            for msg in messages:
                render_message_card(msg, user_id=user_info.get("name", user_info["username"]))
        else:
            st.info("No senate messages yet")
    
    with tab3:
        st.markdown("### School Messages")
        messages = get_messages(recipient="all_school")
        
        if messages:
            for msg in messages:
                render_message_card(msg, user_id=user_info.get("name", user_info["username"]))
        else:
            st.info("No school messages yet")

def admin_interface(user_info):
    """Super admin interface"""
    st.subheader("👑 Super Admin Dashboard")
    
    tab1, tab2, tab3, tab4 = st.tabs(["All Messages", "Flagged Messages", "User Management", "Analytics"])
    
    with tab1:
        st.markdown("### All Platform Messages")
        
        filter_recipient = st.selectbox(
            "Filter by Recipient",
            ["all", "all_school", "senate", "admin"],
            format_func=lambda x: {
                "all": "All Messages",
                "all_school": "School Messages",
                "senate": "Senate Messages",
                "admin": "Admin Messages"
            }[x]
        )
        
        messages = get_messages(recipient=None if filter_recipient == "all" else filter_recipient)
        
        st.markdown(f"**Total Messages:** {len(messages)}")
        
        if messages:
            for msg in messages:
                with st.container():
                    render_message_card(msg, show_sender_id=True, user_id=user_info["username"], show_reactions=False)
                    
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        if not msg.get("flagged", False):
                            if st.button(f"🚩 Flag", key=f"flag_{msg['id']}"):
                                reason = st.text_input(
                                    "Reason for flagging",
                                    key=f"reason_{msg['id']}"
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
            st.warning(f"⚠️ {len(messages)} flagged message(s) requiring attention")
            for msg in messages:
                render_message_card(msg, show_sender_id=True)
        else:
            st.success("✅ No flagged messages")
    
    with tab3:
        st.markdown("### User Management")
        
        with st.expander("➕ Create New User"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            new_name = st.text_input("Full Name")
            new_email = st.text_input("Email")
            new_role = st.selectbox("Role", ["student", "teacher", "senator"])
            
            if st.button("Create User"):
                if new_username and new_password:
                    users = load_json(USERS_FILE)
                    if new_username not in users:
                        users[new_username] = {
                            "password": hash_password(new_password),
                            "role": new_role,
                            "name": new_name,
                            "email": new_email
                        }
                        save_json(USERS_FILE, users)
                        st.success(f"✅ User {new_username} created successfully!")
                    else:
                        st.error("❌ Username already exists")
                else:
                    st.error("❌ Please fill in all fields")
        
        # List all users
        st.markdown("### Registered Users")
        users = load_json(USERS_FILE)
        for username, info in users.items():
            if username != "superadmin":
                st.markdown(f"""
                - **{username}** ({info['role']}) - {info.get('name', 'N/A')}
                """)
    
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
        st.markdown("### 🔐 Login")
        
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
                        st.error("❌ Invalid credentials")
            
            st.info("📧 Contact administration for account access")
    
    else:
        # Show appropriate interface based on role
        user_info = st.session_state.user_info
        
        # Sidebar
        with st.sidebar:
            st.markdown(f"### Welcome, {user_info['name']}!")
            st.markdown(f"**Role:** {user_info['role'].replace('_', ' ').title()}")
            
            if st.button("🚪 Logout"):
                st.session_state.authenticated = False
                st.session_state.user_info = None
                st.rerun()
            
            st.markdown("---")
            st.markdown("### 📜 Community Guidelines")
            st.markdown("""
            - Be respectful and constructive
            - No bullying or harassment
            - No profanity or offensive language
            - Focus on solutions, not just problems
            - Respect anonymity of others
            """)
        
        # Main content based on role
        role = user_info["role"]
        
        if role == "student":
            student_interface(user_info)
        elif role == "teacher":
            teacher_interface(user_info)
        elif role == "senator":
            senator_interface(user_info)
        elif role == "super_admin":
            admin_interface(user_info)

if __name__ == "__main__":
    main()
