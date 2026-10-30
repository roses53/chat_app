
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time
from datetime import datetime
from datetime import timezone, timedelta

st.set_page_config(
    page_title="NOVA CHAT",
    layout="centered"
)

# CSS

with open("style.css", encoding="utf-8") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True
    )

# FIREBASE

if not firebase_admin._apps:
    key = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(key)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# SESSION

if "user" not in st.session_state:
    st.session_state.user = None

if "chat" not in st.session_state:
    st.session_state.chat = None

# FUNCTIONS

def avatar(name):
    if name:
        return name[0].upper()
    return "?"

def online(name):
    users = db.collection("users").where(
        "username", "==", name
    ).limit(1).get()

    if users:
        last = users[0].to_dict().get(
            "last_seen", 0
        )
        return time.time() - last < 60

    return False

def unread(name):
    msgs = db.collection("messages").where(
        "receiver", "==", st.session_state.user
    ).stream()

    count = 0

    for m in msgs:
        d = m.to_dict()

        if d.get("sender") == name:
            if not d.get("read", False):
                count += 1

    return count

def set_read(name):
    msgs = db.collection("messages").where(
        "receiver", "==", st.session_state.user
    ).stream()

    for m in msgs:
        d = m.to_dict()

        if d.get("sender") == name:
            if not d.get("read", False):
                m.reference.update({"read": True})

# LOGIN

if not st.session_state.user:

    st.title("NOVA CHAT")
    st.caption("YOUR PRIVATE SPACE")

    with st.form("login"):
        u = st.text_input("Username").strip()
        p = st.text_input(
            "Password",
            type="password"
        )

        a, b = st.columns(2)
        login = a.form_submit_button("Login")
        reg = b.form_submit_button("Sign Up")

    if login:
        users = db.collection("users").where(
            "username", "==", u
        ).where("password", "==", p).get()

        if users:
            st.session_state.user = u
            st.rerun()
        else:
            st.error("Invalid login")

    if reg:
        old = db.collection("users").where(
            "username", "==", u
        ).get()

        if u and p and not old:
            db.collection("users").add({
                "username": u,
                "password": p,
                "last_seen": time.time()
            })
            st.success("Account created")
        else:
            st.error("Username unavailable")

# MAIN

else:
    me = st.session_state.user

    # PRESENCE

    users = db.collection("users").where(
        "username", "==", me
    ).limit(1).get()

    if users:
        users[0].reference.update({
            "last_seen": time.time()
        })

    a, b = st.columns([3, 1])

    with a:
        st.title("NOVA")
        st.caption("PRIVATE MESSAGING")

    with b:
        if st.button("Logout"):
            if users:
                users[0].reference.update({
                    "last_seen": 0
                })

            st.session_state.user = None
            st.session_state.chat = None
            st.rerun()

    st.divider()

    # SEARCH

    st.subheader("Discover People")
    q = st.text_input("Search username")

    if q:
        people = db.collection("users").stream()

        for person in people:
            name = person.to_dict().get(
                "username", ""
            )

            if name != me and q.lower() in name.lower():
                status = "ONLINE" if online(name) else "OFFLINE"
                count = unread(name)

                label = status + " | "
                label += avatar(name) + " "
                label += name

                if count:
                    label += " (" + str(count) + ")"

                if st.button(label, key=name):
 
