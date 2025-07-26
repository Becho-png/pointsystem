import streamlit as st
import psycopg2
import hashlib
import uuid
import pandas as pd

# --- Database Connection ---
def get_connection():
    return psycopg2.connect(st.secrets["NEON_DB_URL"])

# --- Password Hashing ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Verify Admin Login ---
def verify_admin(username, password):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT password FROM adminuser WHERE username = %s;", (username,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row and row[0] == hash_password(password)
    except Exception as e:
        st.error(f"Error verifying admin: {e}")
        return False

# --- Get All Users ---
def get_all_users():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT userid, username, discord, points FROM pointuser;")
        users = cur.fetchall()
        cur.close()
        conn.close()
        return users
    except Exception as e:
        st.error(f"Error fetching users: {e}")
        return []

# --- Get Point History ---
def get_point_history():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT pid, userid, pamount, padded FROM pointsystem;")
        data = cur.fetchall()
        cur.close()
        conn.close()
        return data
    except Exception as e:
        st.error(f"Error fetching point history: {e}")
        return []

# --- Add Points ---
def add_points(user_id, amount):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE pointuser SET points = points + %s WHERE userid = %s;", (amount, user_id))
        cur.execute("INSERT INTO pointsystem (pid, userid, pamount, padded) VALUES (%s, %s, %s, %s);",
                    (f"p{uuid.uuid4().hex[:6]}", user_id, amount, True))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Error adding points: {e}")

# --- Remove Points ---
def remove_points(user_id, amount):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE pointuser SET points = points - %s WHERE userid = %s;", (amount, user_id))
        cur.execute("INSERT INTO pointsystem (pid, userid, pamount, padded) VALUES (%s, %s, %s, %s);",
                    (f"p{uuid.uuid4().hex[:6]}", user_id, -amount, False))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"Error removing points: {e}")

# --- UI Start ---
st.set_page_config(page_title="Admin Point System", layout="centered")

# --- Login ---
if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False

if not st.session_state["admin_logged_in"]:
    st.title("Admin Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if verify_admin(username, password):
            st.session_state["admin_logged_in"] = True
            st.rerun()
        else:
            st.error("Invalid credentials.")
    st.stop()

# --- Admin Panel ---
st.title("Admin Control Panel")

tab1, tab2, tab3 = st.tabs(["View Users", "Add/Remove Points", "Point History"])

# --- Tab 1: View Users ---
with tab1:
    users = get_all_users()
    if users:
        user_display = [f"{u[1]} ({u[2]}) - {u[3]} pts" for u in users]
        st.write("### Users")
        for user in user_display:
            st.write(user)
    else:
        st.info("No users found.")

# --- Tab 2: Add/Remove Points ---
with tab2:
    users = get_all_users()
    if users:
        user_map = {f"{u[1]} ({u[2]}) - {u[3]} pts": u[0] for u in users}
        selected = st.selectbox("Select user:", list(user_map.keys()))
        amount = st.number_input("Point Amount", min_value=1, step=1)
        if st.button("Add Points"):
            add_points(user_map[selected], amount)
            st.success("Points added successfully.")
            st.rerun()
        if st.button("Remove Points"):
            remove_points(user_map[selected], amount)
            st.success("Points removed successfully.")
            st.rerun()
    else:
        st.info("No users available.")

# --- Tab 3: Point History ---
with tab3:
    history = get_point_history()
    if history:
        df = pd.DataFrame(history, columns=["PID", "User ID", "Point Amount", "Added"])
        st.write("### Point History")
        st.dataframe(df)
    else:
        st.info("No point history found.")
