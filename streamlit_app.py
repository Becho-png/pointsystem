import streamlit as st
import psycopg2
import hashlib
import pandas as pd

# --- DB Connection (no caching) ---
def get_connection():
    return psycopg2.connect(st.secrets["NEON_DB_URL"], sslmode="require")

# --- Password hashing ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Admin login verification ---
def verify_admin(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT password FROM adminuser WHERE username = %s;", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row and row[0] == hash_password(password)

# --- ID generation ---
def generate_userid():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pointuser;")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return f"u{count + 1}"

def generate_pid():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pointsystem;")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return f"p{count + 1}"

# --- Database operations ---
def get_all_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT userid, username, discord_name, points FROM pointuser ORDER BY userid;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def insert_pointuser(userid, username, discord_name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO pointuser (userid, username, discord_name, points) VALUES (%s, %s, %s, 0);",
                (userid, username, discord_name))
    conn.commit()
    cur.close()
    conn.close()

def update_user_points(userid, amount):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE pointuser SET points = points + %s WHERE userid = %s;", (amount, userid))
    conn.commit()
    cur.close()
    conn.close()

def insert_point_log(userid, amount, padded):
    conn = get_connection()
    cur = conn.cursor()
    pid = generate_pid()
    cur.execute("INSERT INTO pointsystem (pid, userid, pamount, padded) VALUES (%s, %s, %s, %s);",
                (pid, userid, amount, padded))
    conn.commit()
    cur.close()
    conn.close()

# --- Predefined point actions ---
POINT_ACTIONS = {
    "Joined Discord": (20, True),
    "Referred Friend (Joined Server)": (50, True),
    "Referred Friend (Got SGT)": (100, True),
    "Redeemed $10 Reward": (-250, False),
    "Redeemed $5 Steam Giftcard": (-250, False)
}

# --- Streamlit Setup ---
st.set_page_config(page_title="Admin Panel", layout="centered")
st.title("🛡️ Admin Login")

# --- Admin Login ---
if "admin_logged_in" not in st.session_state:
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if verify_admin(username, password):
            st.session_state["admin_logged_in"] = True
            st.rerun()
        else:
            st.error("❌ Invalid credentials.")
else:
    st.success("✅ Admin logged in.")
    st.title("🛠️ Admin Panel: Point System")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🔍 View Users",
        "➕ Create User",
        "🏆 Apply Point Action",
        "📊 View & Export Points"
    ])

    # --- Tab 1: View Users ---
    with tab1:
        users = get_all_users()
        if users:
            user_display = [f"{u[1]} ({u[2]}) - {u[3]} pts" for u in users]
            selected = st.selectbox("Select user:", user_display)
            if selected:
                st.info(f"Selected: {selected}")
        else:
            st.warning("No users found.")

    # --- Tab 2: Create User ---
    with tab2:
        uname = st.text_input("Username")
        dname = st.text_input("Discord Name")
        if st.button("Create User"):
            if uname:
                uid = generate_userid()
                insert_pointuser(uid, uname, dname)
                st.success(f"✅ Created user {uname} with ID {uid}")
                st.rerun()
            else:
                st.error("❌ Username required.")

    # --- Tab 3: Apply Point Action ---
    with tab3:
        users = get_all_users()
        if users:
            usernames = [f"{u[1]} ({u[2]})" for u in users]
            selected_user = st.selectbox("Select User", usernames)
            action = st.selectbox("Select Action", list(POINT_ACTIONS.keys()))

            if st.button("Apply Action"):
                user = users[usernames.index(selected_user)]
                userid = user[0]
                amount, padded = POINT_ACTIONS[action]
                update_user_points(userid, amount)
                insert_point_log(userid, amount, padded)
                st.success(f"✅ {action} applied to {user[1]} ({user[0]})")
                st.rerun()
        else:
            st.warning("No users to assign actions.")

    # --- Tab 4: View + Export Points ---
    with tab4:
        st.subheader("📊 All Users and Their Points")
        users = get_all_users()
        if users:
            df = pd.DataFrame(users, columns=["User ID", "Username", "Discord Name", "Points"])
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="⬇️ Export as CSV",
                data=csv,
                file_name="point_users.csv",
                mime="text/csv"
            )
        else:
            st.info("No users found.")
