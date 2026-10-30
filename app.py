
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
 
                    st.session_state.chat = name
                    st.rerun()

    # CHAT

    if st.session_state.chat:
        other = st.session_state.chat

        if st.button("Back to users"):
            st.session_state.chat = None
            st.rerun()

        st.title(other)

        status = "ONLINE" if online(other) else "OFFLINE"
        st.caption(status)

        set_read(other)

        messages = db.collection("messages").stream()
        chat_messages = []

        for item in messages:
            msg = item.to_dict()

            pair = (
                msg.get("sender") == me
                and msg.get("receiver") == other
            )

            reverse = (
                msg.get("sender") == other
                and msg.get("receiver") == me
            )

            if pair or reverse:
                chat_messages.append(msg)

        chat_messages.sort(
            key=lambda x: x.get("time", 0)
        )

        with st.container(height=400):
            for msg in chat_messages:
                sender = msg.get("sender", "")

                with st.chat_message(
                    "user" if sender == me else "assistant"
                ):
                    st.write(msg.get("text", ""))

                    stamp = msg.get("time", 0)
                    st.caption(
                        datetime.fromtimestamp(
                            stamp
                        ).strftime("%H:%M")
                    )

        with st.form("send", clear_on_submit=True):
            msg_text = st.text_input("Message")
            send = st.form_submit_button("Send")

            if send and msg_text.strip():
                db.collection("messages").add({
                    "sender": me,
                    "receiver": other,
                    "text": msg_text.strip(),
                    "time": time.time(),
                    "read": False
                })

                st.rerun()
