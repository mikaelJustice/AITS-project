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
    
    .badge-super-admin {
        background: #fce4ec;
        color: #c2185b;
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
                "name": "Super Administrator"
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
    
    # Sort by engagement score (reactions + recency)
    def calculate_engagement_score(msg):
        # Get total reactions
        reactions = msg.get("reactions", {})
        total_reactions = sum(len(users) for users in reactions.values())
        
        # Calculate time decay (newer = higher score)
        msg_time = datetime.fromisoformat(msg["timestamp"])
        hours_old = (datetime.now() - msg_time).total_seconds() / 3600
        time_score = max(0, 100 - (hours_old * 2))  # Decays over time
        
        # Combined score: reactions * 10 + time_score
        return (total_reactions * 10) + time_score
    
    messages.sort(key=calculate_engagement_score, reverse=True)
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
                    "❤️": [],
                    "😂": [],
                    "😢": []
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
    """Add reaction to a comment"""
    messages_data = load_json(MESSAGES_FILE)
    for msg in messages_data["messages"]:
        if msg["id"] == message_id:
            if "comments" not in msg:
                return False
            for comment in msg["comments"]:
                if comment["id"] == comment_id:
                    if "reactions" not in comment:
                        comment["reactions"] = {"👍": [], "❤️": [], "😂": [], "😢": []}
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
                    
                    st.markdown(
                        f"**{role_emoji} {comment_display}** "
                        f"({'Anonymous' if comment['is_anonymous'] else 'Verified'})"
                    )
                
                # Delete button
                is_comment_owner = comment["user_id"] == user_id
                is_super_admin = user_role == "super_admin"
                
                if is_comment_owner or is_super_admin:
                    with col3:
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
                
                # Comment reactions
                reactions = comment.get("reactions", {"👍": [], "❤️": [], "😂": [], "😢": []})
                reaction_cols = st.columns(4)
                
                for r_idx, (emoji, users) in enumerate(reactions.items()):
                    with reaction_cols[r_idx]:
                        count = len(users)
                        has_reacted = user_id in users
                        button_type = "primary" if has_reacted else "secondary"
                        
                        if st.button(
                            f"{emoji} {count}",
                            key=f"comment_react_{message_id}_{comment['id']}_{emoji}",
                            type=button_type,
                            use_container_width=True
                        ):
                            add_comment_reaction(message_id, comment["id"], user_id, emoji)
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
                
                react_key = f"react_msg_{message['id']}_{emoji}_{context}"
                if st.button(
                    f"{emoji} {count}",
                    key=react_key,
                    type=button_type,
                    use_container_width=True
                ):
                    add_reaction(message['id'], user_id, emoji)
                    st.rerun()
    
    # Add comments section
    if enable_comments and user_id and user_info:
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
                # Message content
                message_content = st.text_area(
                    "Your Message",
                    placeholder="Share your thoughts, ideas, or concerns...",
                    height=150,
                    help="Be respectful and constructive in your communication",
                    key=f"msg_content_student_{user_info['username']}"
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
            if message_content.strip():
                # Determine effective anonymity and sender id
                if recipient == "senate":
                    # Senate messages must be identified
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
                    content=message_content,
                    recipient=recipient,
                    is_anonymous=effective_anonymous,
                    anonymous_name=anon_name
                )
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
        
        message_content = st.text_area(
            "Your Message",
            placeholder="Share announcements, feedback, or information...",
            height=150,
            key=f"msg_content_teacher_{user_info['username']}"
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
            if message_content.strip():
                create_message(
                    sender_id=user_info.get("name", user_info["username"]),
                    sender_role="teacher",
                    content=message_content,
                    recipient=recipient,
                    is_anonymous=False
                )
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
            message_content = st.text_area(
                "Your Message",
                placeholder="Share your message...",
                height=150,
                key=f"msg_content_senator_{user_info['username']}"
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
        
        message_content = st.text_area(
            "Your Message",
            placeholder="Share announcements, feedback, or information...",
            height=150,
            key=f"msg_content_admin_{user_info['username']}"
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
            if message_content.strip():
                create_message(
                    sender_id=user_info.get("name", user_info["username"]),
                    sender_role="admin",
                    content=message_content,
                    recipient=recipient,
                    is_anonymous=False
                )
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
                        edit_role = st.selectbox(
                            "Role",
                            ["student", "teacher", "senator", "admin"],
                            index=["student", "teacher", "senator", "admin"].index(info['role']),
                            key=f"edit_role_{username}"
                        )
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("Save Changes", key=f"save_edit_{username}"):
                                if edit_user(username, new_name=edit_name, new_role=edit_role):
                                    st.success(f" User {username} updated successfully!")
                                    st.session_state[f"edit_{username}"] = False
                                    st.rerun()
                        
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
        
        # Sidebar
        with st.sidebar:
            st.markdown(f"### Welcome, {user_info['name']}!")
            st.markdown(f"**Role:** {user_info['role'].replace('_', ' ').title()}")
            
            if st.button(" Logout", key=f"logout_btn_{user_info['username']}"):
                st.session_state.authenticated = False
                st.session_state.user_info = None
                st.rerun()
            
            st.markdown("---")
            st.markdown("###  Community Guidelines")
            st.markdown("""
            - Be respectful and constructive
            - No bullying or harassment
            - No profanity or offensive language
            - Focus on solutions, not just problems
            - Respect anonymity of others
            
            ---
            
            ### 🚩 About Message Flagging
            
            Messages may be **flagged** by the Super Admin if they:
            - Contain abusive or offensive content
            - Violate community guidelines
            - Could harm or mislead others
            
            **Flagged messages:**
            - Are marked with a red warning
            - Show the reason for flagging
            - Reveal sender identity to Super Admin
            
            Always communicate respectfully! 
            """)
        
        # Main content based on role
        role = user_info["role"]
        
        if role == "student":
            student_interface(user_info)
        elif role == "teacher":
            teacher_interface(user_info)
        elif role == "senator":
            senator_interface(user_info)
        elif role == "admin":
            admin_interface(user_info)
        elif role == "super_admin":
            super_admin_interface(user_info)

if __name__ == "__main__":
    main()
