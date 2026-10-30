
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time

st.set_page_config(page_title="Chat")

if not firebase_admin._apps:
    key = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(key)
    firebase_admin.initialize_app(cred)

db = firestore.client()

if "user" not in st.session_state:
    st.session_state.user = None

if "chat" not in st.session_state:
    st.session_state.chat = None

# LOGIN

if not st.session_state.user:
    st.title("Welcome")

    with st.form("login"):
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
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
            st.error("Wrong login")

    if reg:
        old = db.collection("users").where(
            "username", "==", u
        ).get()

        if u and p and not old:
            db.collection("users").add({
                "username": u,
                "password": p
            })
            st.success("Created")
        else:
            st.error("Username taken or empty")

# MAIN

else:
    me = st.session_state.user

    st.write("User:", me)

    if st.button("Logout"):
        st.session_state.user = None
        st.session_state.chat = None
        st.rerun()

    st.divider()
    st.subheader("Search Users")

    q = st.text_input("Search")

    if q:
        users = db.collection("users").stream()

        for user in users:
            name = user.to_dict().get("username", "")

            if name != me and q.lower() in name.lower():
                if st.button("Chat: " + name):
                    st.session_state.chat = name
                    st.rerun()

    st.divider()

    if st.session_state.chat:
        other = st.session_state.chat
        st.subheader("Chat: " + other)

        try:
            msgs = db.collection("messages").stream()
            chat_msgs = []

            for msg in msgs:
                d = msg.to_dict()
                s = d.get("sender")
                r = d.get("receiver")

                if (s == me and r == other):
                    chat_msgs.append(d)

                elif (s == other and r == me):
                    chat_msgs.append(d)

            chat_msgs.sort(
                key=lambda x: x.get("time", 0)
            )

            box = st.container(height=400)

            with box:
                for m in chat_msgs:
                    who = m["sender"]
                    role = "user" if who == me else "assistant"

                    with st.chat_message(role):
                        st.caption(who)
                        st.write(m.get("text", ""))

        except Exception as e:
            st.error(str(e))

        msg = st.chat_input("Message...")

        if msg and msg.strip():
            try:
                db.collection("messages").add({
                    "sender": me,
                    "receiver": other,
                    "text": msg.strip(),
                    "time": time.time()
                })
                st.rerun()

            except Exception as e:
                st.error(str(e))

    else:
        st.info("Search for a user.")

