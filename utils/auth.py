# utils/auth.py
import streamlit as st
from datetime import datetime
import re

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, ""

def authenticate_user(email, password, firebase):
    """Authenticate user using Firebase"""
    try:
        # Sign in with Firebase Auth
        user = firebase.auth.sign_in_with_email_and_password(email, password)
        
        # Get user role from Firestore
        try:
            user_doc = firebase.db.collection('users').document(user['localId']).get()
            user_data = user_doc.to_dict() if user_doc.exists else {}
        except:
            user_data = {}
        
        return {
            'success': True,
            'user_id': user['localId'],
            'email': email,
            'role': user_data.get('role', 'viewer'),
            'full_name': user_data.get('full_name', email.split('@')[0]),
            'id_token': user.get('idToken', '')
        }
    except Exception as e:
        error_msg = str(e)
        if 'INVALID_PASSWORD' in error_msg:
            return {'success': False, 'error': 'Invalid password. Please try again.'}
        elif 'EMAIL_NOT_FOUND' in error_msg:
            return {'success': False, 'error': 'Email not found. Please sign up first.'}
        elif 'USER_DISABLED' in error_msg:
            return {'success': False, 'error': 'Account has been disabled. Contact administrator.'}
        else:
            return {'success': False, 'error': f'Login failed: {error_msg}'}

def create_user_account(email, password, full_name, phone, agency, role, firebase):
    """Create a new user account in Firebase"""
    try:
        # Validate inputs
        if not validate_email(email):
            return {'success': False, 'error': 'Invalid email format'}
        
        valid, msg = validate_password(password)
        if not valid:
            return {'success': False, 'error': msg}
        
        if not full_name:
            return {'success': False, 'error': 'Full name is required'}
        
        # Create user in Firebase Auth
        user = firebase.auth.create_user_with_email_and_password(email, password)
        
        # Store user data in Firestore
        user_data = {
            'email': email,
            'full_name': full_name,
            'phone': phone or '',
            'agency': agency or '',
            'role': role,
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat(),
            'classification_count': 0,
            'alert_acknowledged_count': 0
        }
        
        firebase.db.collection('users').document(user['localId']).set(user_data)
        
        return {
            'success': True,
            'user_id': user['localId'],
            'message': 'Account created successfully! You can now login.'
        }
        
    except Exception as e:
        error_msg = str(e)
        if 'EMAIL_EXISTS' in error_msg:
            return {'success': False, 'error': 'Email already exists. Please login instead.'}
        elif 'WEAK_PASSWORD' in error_msg:
            return {'success': False, 'error': 'Password is too weak. Use at least 6 characters with letters and numbers.'}
        elif 'INVALID_EMAIL' in error_msg:
            return {'success': False, 'error': 'Invalid email address format.'}
        else:
            return {'success': False, 'error': f'Registration failed: {error_msg}'}

def reset_password(email, firebase):
    """Send password reset email"""
    try:
        firebase.auth.send_password_reset_email(email)
        return {'success': True, 'message': 'Password reset email sent! Check your inbox.'}
    except Exception as e:
        error_msg = str(e)
        if 'EMAIL_NOT_FOUND' in error_msg:
            return {'success': False, 'error': 'Email not found'}
        else:
            return {'success': False, 'error': f'Failed to send reset email: {error_msg}'}

def show_login_page(firebase):
    """Display login and signup page"""
    
    st.markdown("""
        <style>
        .auth-container {
            max-width: 500px;
            margin: 40px auto;
            padding: 35px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.15);
        }
        .auth-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .auth-header h2 {
            color: #667eea;
            margin-top: 10px;
            font-size: 28px;
        }
        .auth-header p {
            color: #718096;
            font-size: 14px;
        }
        .role-selector {
            margin: 15px 0;
            padding: 15px;
            background: #f7fafc;
            border-radius: 12px;
        }
        .divider {
            text-align: center;
            margin: 25px 0;
            position: relative;
        }
        .divider::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 0;
            right: 0;
            height: 1px;
            background: #e2e8f0;
        }
        .divider span {
            background: white;
            padding: 0 15px;
            position: relative;
            color: #a0aec0;
            font-size: 12px;
        }
        .forgot-link {
            text-align: right;
            margin-top: 10px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Initialize session state for auth tab
    if 'auth_tab' not in st.session_state:
        st.session_state.auth_tab = 'login'
    if 'show_forgot_password' not in st.session_state:
        st.session_state.show_forgot_password = False
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.markdown('<div class="auth-header">', unsafe_allow_html=True)
        
        st.image("https://img.icons8.com/color/96/000000/disaster.png", width=80)
        st.markdown("<h2>🌊 Disaster Management System</h2>", unsafe_allow_html=True)
        st.markdown("<p>Real-time disaster monitoring and alert system for Nigeria</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        if st.session_state.show_forgot_password:
            # Forgot Password Section
            st.markdown("### 🔐 Reset Password")
            
            forgot_email = st.text_input("Email Address", placeholder="Enter your registered email", key="forgot_email")
            
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("📧 Send Reset Link", key="send_reset_btn", use_container_width=True):
                    if forgot_email:
                        with st.spinner("Sending reset email..."):
                            result = reset_password(forgot_email, firebase)
                            if result['success']:
                                st.success(result['message'])
                                st.session_state.show_forgot_password = False
                                st.rerun()
                            else:
                                st.error(result['error'])
                    else:
                        st.warning("Please enter your email address")
            
            with col_b:
                if st.button("← Back to Login", key="back_to_login_btn", use_container_width=True):
                    st.session_state.show_forgot_password = False
                    st.rerun()
        
        else:
            # Create two columns for tabs
            col_login, col_signup = st.columns(2)
            
            with col_login:
                if st.button("🔐 Login", use_container_width=True, key="login_tab_btn",
                            type="primary" if st.session_state.auth_tab == 'login' else "secondary"):
                    st.session_state.auth_tab = 'login'
                    st.rerun()
            
            with col_signup:
                if st.button("📝 Sign Up", use_container_width=True, key="signup_tab_btn",
                            type="primary" if st.session_state.auth_tab == 'signup' else "secondary"):
                    st.session_state.auth_tab = 'signup'
                    st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.session_state.auth_tab == 'login':
                # LOGIN FORM
                with st.form("login_form"):
                    email = st.text_input("📧 Email Address", placeholder="Enter your email", key="login_email")
                    password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_password")
                    
                    submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")
                    
                    if submitted:
                        if email and password:
                            with st.spinner("Authenticating..."):
                                result = authenticate_user(email, password, firebase)
                                if result['success']:
                                    st.session_state.logged_in = True
                                    st.session_state.user_email = result['email']
                                    st.session_state.user_role = result['role']
                                    st.session_state.user_name = result['full_name']
                                    st.session_state.user_id = result['user_id']
                                    st.success(f"Welcome back, {result['full_name']}!")
                                    st.rerun()
                                else:
                                    st.error(result['error'])
                        else:
                            st.warning("Please enter email and password")
                
                # Forgot password link
                st.markdown('<div class="forgot-link">', unsafe_allow_html=True)
                if st.button("Forgot Password?", key="forgot_btn"):
                    st.session_state.show_forgot_password = True
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Info for new users
                st.markdown('<div class="divider"><span>New to the system?</span></div>', unsafe_allow_html=True)
                st.markdown("""
                    <div style="text-align: center;">
                        <p>Don't have an account? Click <strong>Sign Up</strong> above to create one.</p>
                    </div>
                """, unsafe_allow_html=True)
            
            else:
                # SIGNUP FORM
                with st.form("signup_form"):
                    full_name = st.text_input("👤 Full Name", placeholder="John Doe", key="signup_name")
                    email = st.text_input("📧 Email Address", placeholder="john@example.com", key="signup_email")
                    phone = st.text_input("📱 Phone Number (Optional)", placeholder="+234 XXX XXX XXXX", key="signup_phone")
                    agency = st.text_input("🏢 Organization/Agency", placeholder="NEMA, Red Cross, etc.", key="signup_agency")
                    password = st.text_input("🔒 Password", type="password", placeholder="Min. 6 characters with uppercase and number", key="signup_password")
                    confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Re-enter password", key="signup_confirm")
                    
                    # Password strength indicator
                    if password:
                        has_upper = any(c.isupper() for c in password)
                        has_lower = any(c.islower() for c in password)
                        has_digit = any(c.isdigit() for c in password)
                        has_length = len(password) >= 6
                        
                        strength = 0
                        if has_length: strength += 1
                        if has_upper and has_lower: strength += 1
                        if has_digit: strength += 1
                        
                        strength_text = ["Weak", "Fair", "Good"][min(2, strength-1)] if strength > 0 else "Weak"
                        strength_color = ["#dc2626", "#eab308", "#10b981"][min(2, strength-1)] if strength > 0 else "#dc2626"
                        
                        st.markdown(f"""
                            <div style="margin-top: -10px; margin-bottom: 10px;">
                                <small>Password strength: 
                                    <span style="color: {strength_color}; font-weight: bold;">{strength_text}</span>
                                </small>
                                <div style="height: 3px; background: #e2e8f0; border-radius: 2px; margin-top: 4px;">
                                    <div style="width: {strength*33}%; height: 3px; background: {strength_color}; border-radius: 2px;"></div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    # Role selection
                    st.markdown('<div class="role-selector">', unsafe_allow_html=True)
                    st.markdown("**Select Account Type**", unsafe_allow_html=True)
                    
                    role_options = {
                        'viewer': '👁️ Viewer - Read-only access to view incidents and news',
                        'responder': '🚑 Responder - Can acknowledge alerts and respond to incidents',
                        'analyst': '📊 Analyst - Can classify text and analyze disaster data'
                    }
                    
                    role = st.selectbox(
                        "Account Type",
                        list(role_options.keys()),
                        format_func=lambda x: role_options[x],
                        key="signup_role"
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.caption("ℹ️ Admin accounts can only be created by existing administrators.")
                    
                    submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")
                    
                    if submitted:
                        # Validate form
                        if not full_name:
                            st.error("❌ Please enter your full name")
                        elif not email:
                            st.error("❌ Please enter your email")
                        elif not validate_email(email):
                            st.error("❌ Please enter a valid email address")
                        elif not password:
                            st.error("❌ Please enter a password")
                        elif password != confirm_password:
                            st.error("❌ Passwords do not match")
                        else:
                            with st.spinner("Creating your account..."):
                                result = create_user_account(
                                    email, password, full_name, phone, agency, role, firebase
                                )
                                
                                if result['success']:
                                    st.success("✅ " + result['message'])
                                    st.balloons()
                                    st.info("🎉 You can now login with your credentials")
                                    import time
                                    time.sleep(2)
                                    st.session_state.auth_tab = 'login'
                                    st.rerun()
                                else:
                                    st.error("❌ " + result['error'])
                
                st.markdown('<div class="divider"><span>Why Sign Up?</span></div>', unsafe_allow_html=True)
                st.markdown("""
                    <div style="font-size: 13px; color: #718096; text-align: center;">
                        ✅ Access real-time disaster alerts<br>
                        ✅ Classify and analyze disaster news<br>
                        ✅ Receive critical notifications<br>
                        ✅ Track incidents across Nigeria
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def logout():
    """Logout user"""
    for key in ['logged_in', 'user_email', 'user_role', 'user_name', 'user_id', 'id_token']:
        if key in st.session_state:
            del st.session_state[key]
    st.success("✅ Logged out successfully!")
    st.rerun()

def login_required(func):
    """Decorator to require login"""
    def wrapper(*args, **kwargs):
        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            st.error("🔐 Please login to access this page")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def admin_required(func):
    """Decorator to require admin role"""
    def wrapper(*args, **kwargs):
        if 'logged_in' not in st.session_state or not st.session_state.logged_in:
            st.error("🔐 Please login to access this page")
            st.stop()
        if st.session_state.get('user_role') != 'admin':
            st.error("⚠️ Admin access required for this page")
            st.stop()
        return func(*args, **kwargs)
    return wrapper

def role_required(allowed_roles):
    """Decorator to require specific role"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if 'logged_in' not in st.session_state or not st.session_state.logged_in:
                st.error("🔐 Please login to access this page")
                st.stop()
            if st.session_state.get('user_role') not in allowed_roles:
                st.error(f"⚠️ Access denied. Required role: {', '.join(allowed_roles)}")
                st.stop()
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_current_user(firebase):
    """Get current user data from Firestore"""
    if 'user_id' not in st.session_state:
        return None
    
    try:
        user_doc = firebase.db.collection('users').document(st.session_state.user_id).get()
        if user_doc.exists:
            return user_doc.to_dict()
    except:
        pass
    return None

def update_user_profile(firebase, updates):
    """Update current user's profile"""
    if 'user_id' not in st.session_state:
        return False
    
    try:
        updates['updated_at'] = datetime.now().isoformat()
        firebase.db.collection('users').document(st.session_state.user_id).update(updates)
        return True
    except:
        return False