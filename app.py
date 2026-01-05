# importing necessary libraries
import re # for regex operations (validating password strength)
import hashlib # for hashing passwords
from datetime import date  # for handling dates
from io import BytesIO # for handling byte streams (image uploads)

import pandas as pd 
import pymysql
import streamlit as st  



# CONFIG ------------------


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "plantlog_db",
    "cursorclass": pymysql.cursors.DictCursor, # return results as dictionaries
    "autocommit": True, # auto commit changes
}

SEASONS = ["Winter", "Spring", "Summer", "Autumn"] 
STATUSES = ["Seed", "Sprout", "Growing", "Flowering", "Harvested"]
LOCATIONS = ["Indoor", "Outdoor", "Pot", "Ground"]





# DB --------------------
def get_conn(): 
    return pymysql.connect(**DB_CONFIG)


def init_db():
    sql = """
    CREATE TABLE IF NOT EXISTS users (
      id INT AUTO_INCREMENT PRIMARY KEY,
      email VARCHAR(120) NOT NULL UNIQUE,
      password_hash CHAR(64) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS plant_logs (
      id INT AUTO_INCREMENT PRIMARY KEY,
      user_id INT NOT NULL,
      plant_name VARCHAR(120) NOT NULL,
      planting_date DATE NOT NULL,
      season ENUM('Winter','Spring','Summer','Autumn') NOT NULL,
      status ENUM('Seed','Sprout','Growing','Flowering','Harvested') NOT NULL,
      location ENUM('Indoor','Outdoor','Pot','Ground') NOT NULL,
      notes TEXT,
      photo LONGBLOB NULL,
      photo_mime VARCHAR(40) NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
    conn = get_conn()
    with conn.cursor() as cur: 
        for statement in sql.split(";"): # split multiple statements
            s = statement.strip()
            if s:
                cur.execute(s)
    conn.close()


# SECURITY HELPERS
# -----------------------------
def sha256_hash(text: str) -> str: # hash text using SHA-256 
    return hashlib.sha256(text.encode("utf-8")).hexdigest() 


def is_strong_password(pw: str) -> bool: # validate password strength
    if len(pw) < 8:
        return False
    if not re.search(r"[A-Z]", pw):
        return False
    if not re.search(r"[0-9]", pw):
        return False
    if not re.search(r"[^A-Za-z0-9]", pw):
        return False
    return True


# -----------------------------
# AUTH
# -----------------------------
def register_user(email: str, password: str) -> tuple[bool, str]: # register new user
    if not email or "@" not in email:
        return False, "Enter a valid email."
    if not is_strong_password(password):
        return False, "Password must be 8+ chars with uppercase, number, and special character."

    conn = get_conn()
    try:
        with conn.cursor() as cur: # check if email exists
            cur.execute("SELECT id FROM users WHERE email=%s", (email,))
            if cur.fetchone():
                return False, "Email already exists. Login instead."
            cur.execute(
                "INSERT INTO users(email, password_hash) VALUES(%s, %s)",
                (email, sha256_hash(password)),
            )
        return True, "Account created. You can login now." 
    finally:
        conn.close()


def login_user(email: str, password: str) -> tuple[bool, str]: # login existing user
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE email=%s", (email,))
            row = cur.fetchone()
            if not row:
                return False, "User not found."
            if row["password_hash"] != sha256_hash(password):
                return False, "Wrong password."
            st.session_state["user_id"] = row["id"]
            st.session_state["user_email"] = email
            return True, "Logged in."
    finally:
        conn.close()


def logout(): # logout user
    st.session_state.pop("user_id", None)
    st.session_state.pop("user_email", None)


# CRUD
# -----------------------------


# Create

def create_log(user_id: int, plant_name: str, planting_date: date, season: str, # create new plant log 
               status: str, location: str, notes: str, photo_bytes: bytes | None, photo_mime: str | None): 
    conn = get_conn()
    try:
        with conn.cursor() as cur: # insert new record
            cur.execute(
                """
                INSERT INTO plant_logs(user_id, plant_name, planting_date, season, status, location, notes, photo, photo_mime)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (user_id, plant_name, planting_date, season, status, location, notes, photo_bytes, photo_mime), # insert values
            )
    finally:
        conn.close()




# Read 


def fetch_logs(user_id: int, search: str, sort_key: str, sort_dir: str): # fetch plant logs with search and sorting
    allowed_sort = {"plant_name": "plant_name", "planting_date": "planting_date"}
    sort_col = allowed_sort.get(sort_key, "plant_name") # default to plant_name
    direction = "ASC" if sort_dir == "ASC" else "DESC" # default to DESC

    conn = get_conn() 
    try:
        with conn.cursor() as cur:  
            if search: # if search term provided
                cur.execute(
                    f"""
                    SELECT id, plant_name, planting_date, season, status, location, notes, photo_mime
                    FROM plant_logs
                    WHERE user_id=%s AND plant_name LIKE %s
                    ORDER BY {sort_col} {direction}
                    """,
                    (user_id, f"%{search}%"),
                )
            else:
                cur.execute(
                    f"""
                    SELECT id, plant_name, planting_date, season, status, location, notes, photo_mime
                    FROM plant_logs
                    WHERE user_id=%s
                    ORDER BY {sort_col} {direction}
                    """,
                    (user_id,),
                )
            return cur.fetchall()
    finally:
        conn.close()



# Update picture

def fetch_photo(user_id: int, log_id: int): # fetch photo for a specific log
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT photo, photo_mime FROM plant_logs WHERE id=%s AND user_id=%s",
                (log_id, user_id),
            )
            return cur.fetchone()
    finally:
        conn.close()



# Update data
def update_log(user_id: int, log_id: int, plant_name: str, planting_date: date, season: str,
               status: str, location: str, notes: str, photo_bytes: bytes | None, photo_mime: str | None,
               replace_photo: bool):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if replace_photo:
                cur.execute(
                    """
                    UPDATE plant_logs
                    SET plant_name=%s, planting_date=%s, season=%s, status=%s, location=%s, notes=%s, photo=%s, photo_mime=%s
                    WHERE id=%s AND user_id=%s
                    """,
                    (plant_name, planting_date, season, status, location, notes, photo_bytes, photo_mime, log_id, user_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE plant_logs
                    SET plant_name=%s, planting_date=%s, season=%s, status=%s, location=%s, notes=%s
                    WHERE id=%s AND user_id=%s
                    """,
                    (plant_name, planting_date, season, status, location, notes, log_id, user_id),
                )
    finally:
        conn.close()

#  Delete

def delete_log(user_id: int, log_id: int): # delete a plant log
    conn = get_conn()
    try:
        with conn.cursor() as cur: 
            cur.execute("DELETE FROM plant_logs WHERE id=%s AND user_id=%s", (log_id, user_id))
    finally:
        conn.close()
# -----------------------------



# UI
# -----------------------------
st.set_page_config(page_title="PlantLog", page_icon="🌿", layout="wide") 

init_db() # ensure DB and tables exist

if "user_id" not in st.session_state: # not logged in
    st.title("🌿 PlantLog")
    st.caption("Streamlit + MySQL 8.0 | Login → Dashboard → CRUD") # app description

    tab1, tab2 = st.tabs(["Login", "Register"]) # tabs for login and registration

    with tab1:
        email = st.text_input("Email", key="login_email") # email input
        pw = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            ok, msg = login_user(email, pw)
            st.success(msg) if ok else st.error(msg)
            if ok:
                st.rerun()

    with tab2:
        r_email = st.text_input("Email", key="reg_email") # registration email input
        r_pw = st.text_input("Password", type="password", key="reg_pw")
        st.caption("Rule: 8+ chars, 1 uppercase, 1 number, 1 special.")
        if st.button("Create Account"):
            ok, msg = register_user(r_email, r_pw)
            st.success(msg) if ok else st.error(msg)

    st.stop()



# Dashboard
user_id = st.session_state["user_id"] # get logged in user ID
st.title("🌿 PlantLog Dashboard") 
colA, colB = st.columns([1, 1]) # layout for user info and logout button
with colA:
    st.write(f"**Logged in as:** {st.session_state['user_email']}") # display logged in user email
with colB:
    if st.button("Logout"): # logout button
        logout()
        st.rerun()

# Sidebar controls
st.sidebar.header("Controls") # sidebar header for controls
search = st.sidebar.text_input("Search (plant name)", "") # search input
sort_field = st.sidebar.selectbox("Sort field", ["plant_name", "planting_date"]) # select sort field
sort_dir = st.sidebar.selectbox("Sort direction", ["ASC", "DESC"]) # select sort direction

rows = fetch_logs(user_id, search, sort_field, sort_dir)
df = pd.DataFrame(rows)

# Summary cards
st.subheader("Quick Summary")
c1, c2, c3 = st.columns(3) # layout for summary metrics
total = len(df) if not df.empty else 0 # total plants
this_month = 0 # plants planted this month
if not df.empty:
    df["planting_date"] = pd.to_datetime(df["planting_date"]) # convert planting_date to datetime
    now = pd.Timestamp.today() 
    this_month = int((df["planting_date"].dt.month == now.month).sum()) # count this month's plantings

c1.metric("Total Plants", total) 
c2.metric("Planted This Month", this_month)
c3.metric("Unique Seasons", int(df["season"].nunique()) if not df.empty else 0)

tab_add, tab_manage, tab_analytics, tab_export = st.tabs(["➕ Add", "🛠️ Manage", "📊 Analytics", "⬇️ Export"]) # main tabs for different functionalities

with tab_add:
    st.subheader("Add New Plant Log") # form to add a new plant log
    with st.form("add_form", clear_on_submit=True):
        plant_name = st.text_input("Plant Name")
        planting_date = st.date_input("Planting Date", value=date.today())
        season = st.selectbox("Season", SEASONS)
        status = st.selectbox("Status", STATUSES)
        location = st.selectbox("Location", LOCATIONS)
        notes = st.text_area("Notes", height=120)

        photo_file = st.file_uploader("Upload Photo (optional)", type=["png", "jpg", "jpeg"]) # photo upload input
        photo_bytes, photo_mime = None, None
        if photo_file is not None:
            photo_bytes = photo_file.getvalue()
            photo_mime = photo_file.type

        submit = st.form_submit_button("Save") # submit button
        if submit:
            if not plant_name.strip():
                st.error("Plant name is required.")
            else:
                create_log(user_id, plant_name.strip(), planting_date, season, status, location, notes, photo_bytes, photo_mime)
                st.success("Saved.")
                st.rerun()

with tab_manage:
    st.subheader("View / Update / Delete") # manage existing plant logs
    if df.empty:
        st.info("No records yet. Add one in the Add tab.")
    else:
        st.dataframe(df.drop(columns=["photo_mime"], errors="ignore"), use_container_width=True)

        ids = df["id"].tolist()
        selected_id = st.selectbox("Select record ID to edit", ids)

        # pull row details
        row = df[df["id"] == selected_id].iloc[0] # get selected row details


# Edit form
        st.markdown("### Edit Selected Row")
        with st.form("edit_form"):
            e_name = st.text_input("Plant Name", value=str(row["plant_name"]))
            e_date = st.date_input("Planting Date", value=pd.to_datetime(row["planting_date"]).date())
            e_season = st.selectbox("Season", SEASONS, index=SEASONS.index(row["season"]))
            e_status = st.selectbox("Status", STATUSES, index=STATUSES.index(row["status"]))
            e_location = st.selectbox("Location", LOCATIONS, index=LOCATIONS.index(row["location"]))
            e_notes = st.text_area("Notes", value=row.get("notes") or "", height=120)

# Photo handling
            st.markdown("**Photo**")
            photo_row = fetch_photo(user_id, int(selected_id))
            if photo_row and photo_row.get("photo"):
                st.image(BytesIO(photo_row["photo"]), caption="Current photo", use_container_width=False)
            else:
                st.caption("No photo stored.")

            replace_photo = st.checkbox("Replace photo?")
            new_photo_file = st.file_uploader("Upload new photo", type=["png", "jpg", "jpeg"], disabled=not replace_photo)

# get new photo bytes if replacing
            new_photo_bytes, new_photo_mime = None, None
            if replace_photo and new_photo_file is not None:
                new_photo_bytes = new_photo_file.getvalue()
                new_photo_mime = new_photo_file.type

            save = st.form_submit_button("Update")
            if save:
                if not e_name.strip():
                    st.error("Plant name is required.")
                else:
                    update_log(
                        user_id=user_id,
                        log_id=int(selected_id),
                        plant_name=e_name.strip(),
                        planting_date=e_date,
                        season=e_season,
                        status=e_status,
                        location=e_location,
                        notes=e_notes,
                        photo_bytes=new_photo_bytes,
                        photo_mime=new_photo_mime,
                        replace_photo=replace_photo,
                    )
                    st.success("Updated.")
                    st.rerun()



# Delete section



        st.markdown("### Delete Selected Row")
        confirm = st.checkbox("Yes, I want to delete this record permanently.") # confirmation checkbox
        if st.button("Delete Now", disabled=not confirm):
            delete_log(user_id, int(selected_id)) # delete the selected log
            st.success("Deleted.")
            st.rerun()
 

 # Analytics

with tab_analytics:
    st.subheader("Charts") # display charts for data analysis
    if df.empty:
        st.info("No data to chart yet.")
    else:
        season_counts = df["season"].value_counts().reset_index() # count by season
        season_counts.columns = ["season", "count"]
        st.write("Plants by Season")
        st.bar_chart(season_counts.set_index("season")) # bar chart by season



        status_counts = df["status"].value_counts().reset_index() # count by status
        status_counts.columns = ["status", "count"]
        st.write("Plants by Status")
        st.bar_chart(status_counts.set_index("status"))

with tab_export:
    st.subheader("Export to CSV") # export data to CSV file
    if df.empty:
        st.info("No data to export.")
    else:
        export_df = df.drop(columns=["photo_mime"], errors="ignore").copy() # drop photo_mime column
       
        # convert datetime for clean CSV
        if "planting_date" in export_df.columns:
            export_df["planting_date"] = pd.to_datetime(export_df["planting_date"]).dt.date

# generate CSV bytes
        csv_bytes = export_df.to_csv(index=False).encode("utf-8") # convert to bytes
        st.download_button(
            label="Download CSV",# download_button
            data=csv_bytes, 
            file_name="plantlog_export.csv",
            mime="text/csv",
        )