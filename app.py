import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
import time

st.set_page_config(page_title="Chat", layout="centered")

with open("style.css", "r", encoding="utf-8") as f:
    css = f.read()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

if "firebase" not in st.session_state:
    key_dict = json.loads(st.secrets["firebase_key"])
    cred = credentials.Certificate(key_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    st.session_state.firebase = firestore.client()

db = st.session_state.firebase

if "user" not in st.session_state:
    st.session_state.user = None
if "chat_with" not in st.session_state:
    st.session_state.chat_with = None

if st.session_state.user is None:
    st.write("## Welcome")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            login = st.form_submit_button("Login")
        with col2:
            register = st.form_submit_button("Sign Up")

        if login:
            users = db.collection("users").where("username", "==", username).where("password", "==", password).get()
            if users:
                st.session_state.user = username
                st.rerun()
            else:
                st.error("Invalid credentials")
        if register:
            if username and password:
                existing = db.collection("users").where("username", "==", username).get()
                if existing:
                    st.error("Username taken")
                else:
                    db.collection("users").add({"username": username, "password": password})
                    st.success("Account created!")
            else:
                st.warning("Fill all fields")

else:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("User:", st.session_state.user)
    with col2:
        if st.button("Logout"):
            st.session_state.user = None
            st.session_state.chat_with = None
            st.rerun()
            
    st.divider()

    st.write("### Search Users")
    search_query = st.text_input("Search...")
    
    if search_query:
        users_ref = db.collection("users").stream()
        found_users = []
        for u in users_ref:
            u_data = u.to_dict()
            if u_data.get('username') != st.session_state.user:
                if search_query.lower() in u_data.get('username', '').lower():
                    found_users.append(u_data['username'])
        
        for f_user in found_users:
            if st.button(f"Chat with {f_user}"):
                st.session_state.chat_with = f_user
                st.rerun()

    st.divider()

    if st.session_state.chat_with:
        st.write(f"### Chat with {st.session_state.chat_with}")
        
        chat_container = st.container(height=400)
        with chat_container:
            messages_ref = db.collection("messages").order_by("time").stream()
            for msg in messages_ref:
                data = msg.to_dict()
                sender = data.get('sender')
                receiver = data.get('receiver')
                text = data.get('text', '')
                
                cond1 = (sender == st.session_state.user)
                cond2 = (receiver == st.session_state.chat_with)
                cond3 = (sender == st.session_state.chat_with)
                cond4 = (receiver == st.session_state.user)
                
                if (cond1 and cond2) or (cond3 and cond4):
                    is_me = sender == st.session_state.user
                    avatar = "user" if is_me else "assistant"
                    with st.chat_message(avatar):
                        st.write(sender)
                        st.write(text)

        if prompt := st.chat_input("Type a message..."):
            new_msg = {}
            new_msg["sender"] = st.session_state.user
            new_msg["receiver"] = st.session_state.chat_with
    
