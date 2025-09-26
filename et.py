import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import sqlite3
import io
import hashlib

DB_NAME = "expense_tracker.db"

# Category Emojis
category_emoji = {"Food":"🍔","Travel":"✈️","Shopping":"🛍️","Entertainment":"🎮","Other":"📌"}

# CSS Styling
st.markdown("""
<style>
.card {background-color:#fdfcff; border-radius:15px; padding:15px; margin-bottom:10px; box-shadow:2px 2px 8px rgba(0,0,0,0.1);}
.stButton>button {background-color:#6a0dad; color:white; border-radius:10px; padding:6px 12px; margin-top:5px;}
.stButton>button:hover {background-color:#9b30ff;}
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
        """)
        c.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            category TEXT,
            amount REAL,
            note TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)
        conn.commit()

def get_user_id(username):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        res = c.fetchone()
        return res[0] if res else None

def get_expenses(user_id):
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        c = conn.cursor()
        c.execute("SELECT id,date,category,amount,note FROM expenses WHERE user_id=?", (user_id,))
        rows = c.fetchall()
        df = pd.DataFrame(rows, columns=["ID","Date","Category","Amount","Note"])
        return df

# Initialize DB
init_db()
# Session State
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "username" not in st.session_state: st.session_state["username"] = None

# Authentication
if not st.session_state["logged_in"]:
    st.title("🔐 Student Expense Tracker")
    option = st.selectbox("Select Option", ["Login", "Sign Up"])

    if option == "Sign Up":
        st.subheader("📝 Create Account")
        new_user = st.text_input("👤 Username", key="signup_user")
        new_pass = st.text_input("🔑 Password", type="password", key="signup_pass")
        confirm_pass = st.text_input("🔑 Confirm Password", type="password", key="signup_confirm")
        if st.button("Sign Up"):
            if new_user == "" or new_pass == "":
                st.error("❌ Fields cannot be empty.")
            elif new_pass != confirm_pass:
                st.error("❌ Passwords do not match.")
            else:
                try:
                    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
                        c = conn.cursor()
                        c.execute("INSERT INTO users(username,password) VALUES (?,?)",
                                  (new_user, hash_password(new_pass)))
                        conn.commit()
                    st.success("✅ Account created! Please login.")
                except sqlite3.IntegrityError:
                    st.error("❌ Username already exists.")

    elif option == "Login":
        st.subheader("🔑 Login")
        username = st.text_input("👤 Username", key="login_user")
        password = st.text_input("🔑 Password", type="password", key="login_pass")
        if st.button("Login"):
            hashed = hash_password(password)
            with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed))
                user = c.fetchone()
            if user:
                st.session_state["logged_in"] = True
                st.session_state["username"] = username
                st.success(f"✅ Welcome, {username}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
else:
    st.title("💸 Pocket Money Expense Tracker")
    st.subheader(f"✨ Welcome {st.session_state['username']}!")

    # Logout
    if st.button("🚪 Logout"):
        st.session_state["logged_in"] = False
        st.session_state["username"] = None
        st.rerun()

    user_id = get_user_id(st.session_state["username"])
    df = get_expenses(user_id)

    # Dashboard
    st.markdown("### 📊 Summary Dashboard")
    total_expense = df["Amount"].sum() if not df.empty else 0
    top_category = df.groupby("Category")["Amount"].sum().idxmax() if not df.empty else "N/A"
    recent_expenses = df.sort_values("Date", ascending=False).head(5) if not df.empty else pd.DataFrame()

    col1, col2 = st.columns(2)
    col1.metric("💰 Total Expenses", f"₹{total_expense}")
    col2.metric("🏆 Highest Spending Category", f"{category_emoji.get(top_category, '📌')} {top_category}")

    st.markdown("#### 📝 Recent 5 Expenses")
    for idx, row in recent_expenses.iterrows():
        st.markdown(f"""
            <div class="card">
            {category_emoji.get(row['Category'], '📌')} <b>{row['Category']}</b> | 📅 {row['Date']} | 💰 ₹{row['Amount']}<br>📝 {row['Note']}
            </div>
        """, unsafe_allow_html=True)
    # --- Add Expense ---
    st.markdown("### ➕ Add New Expense")
    col1, col2, col3 = st.columns(3)
    with col1:
        date = st.date_input("📅 Date", datetime.today())
    with col2:
        category = st.selectbox("📂 Category", ["Food", "Travel", "Shopping", "Entertainment", "Other"])
    with col3:
        amount = st.number_input("💰 Amount (₹)", min_value=1, step=1)
    note = st.text_input("📝 Note (Optional)")
    if st.button("➕ Add Expense"):
        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
            c = conn.cursor()
            c.execute("INSERT INTO expenses(user_id,date,category,amount,note) VALUES (?,?,?,?,?)",
                      (user_id, date.strftime("%Y-%m-%d"), category, amount, note))
            conn.commit()
        st.success("✅ Expense added successfully!")

    # --- Filter/Search ---
    if not df.empty:
        st.markdown("### 🔍 Filter / Search Expenses")
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_category = st.selectbox("Category", ["All"] + list(df["Category"].unique()))
        with col2:
            start_date = st.date_input("Start Date", df["Date"].min())
        with col3:
            end_date = st.date_input("End Date", df["Date"].max())

        filtered_df = df.copy()
        if filter_category != "All": filtered_df = filtered_df[filtered_df["Category"] == filter_category]
        filtered_df = filtered_df[(pd.to_datetime(filtered_df["Date"]) >= pd.to_datetime(start_date)) &
                                  (pd.to_datetime(filtered_df["Date"]) <= pd.to_datetime(end_date))]

        st.markdown("### 🗂 Your Expenses")
        for idx, row in filtered_df.iterrows():
            st.markdown(f"""
                <div class="card">
                {category_emoji.get(row['Category'], '📌')} <b>{row['Category']}</b> | 📅 {row['Date']} | 💰 ₹{row['Amount']}<br>📝 {row['Note']}
                </div>
            """, unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            if col1.button("✏️ Edit", key=f"edit_{row['ID']}"):
                with st.form(f"edit_form_{row['ID']}", clear_on_submit=True):
                    new_date = st.date_input("📅 Date", pd.to_datetime(row["Date"]))
                    new_category = st.selectbox("📂 Category", ["Food", "Travel", "Shopping", "Entertainment", "Other"],
                                                index=["Food", "Travel", "Shopping", "Entertainment", "Other"].index(
                                                    row["Category"]))
                    new_amount = st.number_input("💰 Amount (₹)", min_value=1, step=1, value=int(row["Amount"]))
                    new_note = st.text_input("📝 Note", value=row["Note"])
                    save = st.form_submit_button("💾 Save Changes")
                    if save:
                        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
                            c = conn.cursor()
                            c.execute("UPDATE expenses SET date=?,category=?,amount=?,note=? WHERE id=?",
                                      (new_date.strftime("%Y-%m-%d"), new_category, new_amount, new_note, row["ID"]))
                            conn.commit()
                        st.success("✅ Expense Updated! Refresh to see changes.")
            if col2.button("🗑️ Delete", key=f"delete_{row['ID']}"):
                with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
                    c = conn.cursor()
                    c.execute("DELETE FROM expenses WHERE id=?", (row["ID"],))
                    conn.commit()
                st.warning(f"🗑️ Deleted expense ID {row['ID']}! Refresh to update list.")

        # --- Category Summary ---
        category_summary = filtered_df.groupby("Category")["Amount"].sum().reset_index()
        st.markdown("### 📈 Expense Summary by Category")
        col1, col2 = st.columns(2)
        with col1:
            st.write(category_summary)
        with col2:
            fig, ax = plt.subplots()
            ax.bar(category_summary["Category"], category_summary["Amount"], color="#9b30ff")
            ax.set_title("Expenses by Category")
            st.pyplot(fig)

        # --- Monthly Report ---
        st.markdown("### 📅 Monthly Report")
        filtered_df["Month"] = pd.to_datetime(filtered_df["Date"]).dt.to_period("M")
        monthly_summary = filtered_df.groupby("Month")["Amount"].sum().reset_index()
        st.line_chart(monthly_summary.set_index("Month"))

        # --- Download CSV/Excel ---
        st.markdown("### 📥 Download Your Data")
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", data=csv_data, file_name="expenses.csv", mime="text/csv")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Expenses")
            monthly_summary.to_excel(writer, index=False, sheet_name="Monthly_Report")
            category_summary.to_excel(writer, index=False, sheet_name="Category_Summary")
        st.download_button("⬇️ Download Excel", data=buffer.getvalue(), file_name="expenses.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
