# create_admin.py
import streamlit as st
from utils.firebase_config import init_firebase
from utils.auth import create_user_account

def create_admin_user():
    """Create the initial admin user"""
    firebase = init_firebase()
    
    admin_email = "admin@disaster.com"
    admin_password = "Admin123!"
    
    print("Creating admin user...")
    
    result = create_user_account(
        email=admin_email,
        password=admin_password,
        full_name="System Administrator",
        phone="+1234567890",
        agency="Disaster Management Authority",
        role="admin",
        firebase=firebase
    )
    
    if result['success']:
        print(f"✅ Admin user created successfully!")
        print(f"Email: {admin_email}")
        print(f"Password: {admin_password}")
    else:
        print(f"❌ Error: {result['error']}")

if __name__ == "__main__":
    create_admin_user()