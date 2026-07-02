from pymongo import MongoClient
import streamlit as st

def get_mongo_client():
    return MongoClient(
        st.secrets["MONGO_URI"],
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=5000
    )

def get_db():
    client = get_mongo_client()
    return client['tugasakhir']

def get_collection(collection_name):
    db = get_db()
    return db[collection_name]
