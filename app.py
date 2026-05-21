# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import hashlib
import re
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster
from utils.firebase_config import init_firebase
from utils.ml_classifier import MLDisasterClassifier
from utils.rss_collector import RSSNewsCollector

# Page configuration
st.set_page_config(
    page_title="Disaster Management System",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .stat-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-3px);
    }
    .alert-critical {
        border-left: 4px solid #dc2626;
        background: #fef2f2;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    .alert-high {
        border-left: 4px solid #f97316;
        background: #fff7ed;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
    }
    .badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-critical { background: #dc2626; color: white; }
    .badge-high { background: #f97316; color: white; }
    .badge-medium { background: #eab308; color: white; }
    .badge-low { background: #10b981; color: white; }
    
    .auth-header {
        text-align: center;
        margin-bottom: 30px;
    }
    .auth-header h2 {
        color: #667eea;
        margin-top: 10px;
        font-size: 28px;
    }
    .role-selector {
        margin: 15px 0;
        padding: 15px;
        background: #f7fafc;
        border-radius: 12px;
    }
    .source-link {
        color: #667eea;
        text-decoration: none;
        font-weight: 500;
    }
    .source-link:hover {
        text-decoration: underline;
    }
    .news-card {
        transition: transform 0.2s;
        margin-bottom: 1rem;
    }
    .news-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================
# NIGERIAN LOCATIONS COORDINATES
# ============================================================

NIGERIAN_LOCATIONS = {
    'lagos': {'lat': 6.5244, 'lon': 3.3792, 'type': 'state', 'risk': 'very_high'},
    'abuja': {'lat': 9.0765, 'lon': 7.3986, 'type': 'state', 'risk': 'medium'},
    'anambra': {'lat': 6.2204, 'lon': 6.9369, 'type': 'state', 'risk': 'very_high'},
    'kogi': {'lat': 7.8024, 'lon': 6.7399, 'type': 'state', 'risk': 'very_high'},
    'bayelsa': {'lat': 4.7700, 'lon': 6.0800, 'type': 'state', 'risk': 'very_high'},
    'delta': {'lat': 5.7050, 'lon': 6.0799, 'type': 'state', 'risk': 'very_high'},
    'rivers': {'lat': 4.8156, 'lon': 6.9730, 'type': 'state', 'risk': 'very_high'},
    'ogun': {'lat': 7.1605, 'lon': 3.3482, 'type': 'state', 'risk': 'high'},
    'oyo': {'lat': 7.3775, 'lon': 3.9470, 'type': 'state', 'risk': 'medium'},
    'edo': {'lat': 6.3176, 'lon': 5.6145, 'type': 'state', 'risk': 'medium'},
    'imo': {'lat': 5.4836, 'lon': 7.0333, 'type': 'state', 'risk': 'high'},
    'abia': {'lat': 5.4200, 'lon': 7.4900, 'type': 'state', 'risk': 'high'},
    'enugu': {'lat': 6.4612, 'lon': 7.4882, 'type': 'state', 'risk': 'medium'},
    'benue': {'lat': 7.7524, 'lon': 8.5432, 'type': 'state', 'risk': 'high'},
    'plateau': {'lat': 9.8965, 'lon': 8.8583, 'type': 'state', 'risk': 'medium'},
    'kaduna': {'lat': 10.5105, 'lon': 7.4165, 'type': 'state', 'risk': 'low'},
    'kano': {'lat': 12.0022, 'lon': 8.5919, 'type': 'state', 'risk': 'low'},
    'niger': {'lat': 9.5836, 'lon': 6.5463, 'type': 'state', 'risk': 'high'},
    'kwara': {'lat': 8.9700, 'lon': 4.5600, 'type': 'state', 'risk': 'high'},
    'osun': {'lat': 7.5000, 'lon': 4.5000, 'type': 'state', 'risk': 'medium'},
    'ekiti': {'lat': 7.6700, 'lon': 5.2200, 'type': 'state', 'risk': 'medium'},
    'ondo': {'lat': 7.2500, 'lon': 5.1900, 'type': 'state', 'risk': 'high'},
    'cross river': {'lat': 5.8700, 'lon': 8.5900, 'type': 'state', 'risk': 'high'},
    'akwa ibom': {'lat': 4.9057, 'lon': 7.8537, 'type': 'state', 'risk': 'high'},
    'borno': {'lat': 11.8300, 'lon': 13.1500, 'type': 'state', 'risk': 'low'},
    'yobe': {'lat': 12.2900, 'lon': 11.4400, 'type': 'state', 'risk': 'low'},
    'gombe': {'lat': 10.2800, 'lon': 11.1700, 'type': 'state', 'risk': 'low'},
    'bauchi': {'lat': 10.3100, 'lon': 9.8400, 'type': 'state', 'risk': 'low'},
    'jigawa': {'lat': 12.3300, 'lon': 9.5700, 'type': 'state', 'risk': 'low'},
    'katsina': {'lat': 12.9855, 'lon': 7.6017, 'type': 'state', 'risk': 'low'},
    'sokoto': {'lat': 13.0059, 'lon': 5.2476, 'type': 'state', 'risk': 'low'},
    'zamfara': {'lat': 12.1700, 'lon': 6.6600, 'type': 'state', 'risk': 'low'},
    'taraba': {'lat': 7.5500, 'lon': 10.4500, 'type': 'state', 'risk': 'medium'},
    'adamawa': {'lat': 9.3300, 'lon': 12.5000, 'type': 'state', 'risk': 'medium'},
    'ebonyi': {'lat': 6.2500, 'lon': 8.1000, 'type': 'state', 'risk': 'high'},
    'nassarawa': {'lat': 8.5700, 'lon': 8.0700, 'type': 'state', 'risk': 'medium'},
    'ibadan': {'lat': 7.3775, 'lon': 3.9470, 'type': 'city', 'risk': 'medium'},
    'port harcourt': {'lat': 4.8156, 'lon': 7.0498, 'type': 'city', 'risk': 'high'},
    'benin city': {'lat': 6.3176, 'lon': 5.6145, 'type': 'city', 'risk': 'medium'},
    'onitsha': {'lat': 6.1500, 'lon': 6.7833, 'type': 'city', 'risk': 'high'},
    'warri': {'lat': 5.5167, 'lon': 5.7500, 'type': 'city', 'risk': 'high'},
    'maiduguri': {'lat': 11.8333, 'lon': 13.1500, 'type': 'city', 'risk': 'medium'},
    'jos': {'lat': 9.9333, 'lon': 8.8833, 'type': 'city', 'risk': 'low'},
    'owerri': {'lat': 5.4836, 'lon': 7.0333, 'type': 'city', 'risk': 'medium'},
    'calabar': {'lat': 4.9581, 'lon': 8.3245, 'type': 'city', 'risk': 'medium'},
    'makurdi': {'lat': 7.7325, 'lon': 8.5391, 'type': 'city', 'risk': 'high'}
}

# ============================================================
# SOURCE ICONS AND LINKS
# ============================================================

SOURCE_INFO = {
    'punch': {'icon': '📰', 'color': '#dc2626', 'url': 'https://punchng.com'},
    'daily_trust': {'icon': '📰', 'color': '#2563eb', 'url': 'https://dailytrust.com'},
    'vanguard': {'icon': '📰', 'color': '#16a34a', 'url': 'https://www.vanguardngr.com'},
    'thisday': {'icon': '📰', 'color': '#7c3aed', 'url': 'https://www.thisdaylive.com'},
    'channels': {'icon': '📺', 'color': '#eab308', 'url': 'https://www.channelstv.com'},
    'guardian': {'icon': '📰', 'color': '#0891b2', 'url': 'https://guardian.ng'},
    'premium_times': {'icon': '📰', 'color': '#ec489a', 'url': 'https://www.premiumtimesng.com'},
    'tribune': {'icon': '📰', 'color': '#f97316', 'url': 'https://tribuneonlineng.com'},
    'system': {'icon': '⚠️', 'color': '#dc2626', 'url': '#'}
}

# ============================================================
# AUTHENTICATION FUNCTIONS
# ============================================================

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, ""

def authenticate_user(email, password, firebase):
    try:
        user = firebase.auth.sign_in_with_email_and_password(email, password)
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
            'full_name': user_data.get('full_name', email.split('@')[0])
        }
    except Exception as e:
        error_msg = str(e)
        if 'INVALID_PASSWORD' in error_msg:
            return {'success': False, 'error': 'Invalid password. Please try again.'}
        elif 'EMAIL_NOT_FOUND' in error_msg:
            return {'success': False, 'error': 'Email not found. Please sign up first.'}
        else:
            return {'success': False, 'error': f'Login Username or password'}

def create_user_account(email, password, full_name, phone, agency, role, firebase):
    if not validate_email(email):
        return {'success': False, 'error': 'Invalid email format'}
    
    valid, msg = validate_password(password)
    if not valid:
        return {'success': False, 'error': msg}
    
    if not full_name:
        return {'success': False, 'error': 'Full name is required'}
    
    try:
        user = firebase.auth.create_user_with_email_and_password(email, password)
        
        user_data = {
            'email': email,
            'full_name': full_name,
            'phone': phone or '',
            'agency': agency or '',
            'role': role,
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'last_login': datetime.now().isoformat()
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
        else:
            return {'success': False, 'error': f'Registration failed: {error_msg}'}

def show_login_page(firebase):
    if 'auth_tab' not in st.session_state:
        st.session_state.auth_tab = 'login'
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        st.markdown('<div class="auth-header">', unsafe_allow_html=True)
        st.markdown("<h2>🌊 Disaster Management System</h2>", unsafe_allow_html=True)
        st.markdown("<p>Real-time disaster monitoring for Nigeria</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        col_login, col_signup = st.columns(2)
        with col_login:
            if st.button("🔐 Login", width='stretch', type="primary" if st.session_state.auth_tab == 'login' else "secondary"):
                st.session_state.auth_tab = 'login'
                st.rerun()
        with col_signup:
            if st.button("📝 Sign Up", width='stretch', type="primary" if st.session_state.auth_tab == 'signup' else "secondary"):
                st.session_state.auth_tab = 'signup'
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.auth_tab == 'login':
            with st.form("login_form"):
                email = st.text_input("📧 Email Address", placeholder="Enter your email")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In", width='stretch', type="primary")
                
                if submitted:
                    if email and password:
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
        else:
            with st.form("signup_form"):
                full_name = st.text_input("👤 Full Name", placeholder="John Doe")
                email = st.text_input("📧 Email Address", placeholder="john@example.com")
                phone = st.text_input("📱 Phone Number (Optional)", placeholder="+234 XXX XXX XXXX")
                agency = st.text_input("🏢 Organization/Agency", placeholder="NEMA, Red Cross, etc.")
                password = st.text_input("🔒 Password", type="password", placeholder="Min. 6 characters with uppercase and number")
                confirm_password = st.text_input("🔒 Confirm Password", type="password", placeholder="Re-enter password")
                
                st.markdown('<div class="role-selector">', unsafe_allow_html=True)
                st.markdown("**Select Account Type**", unsafe_allow_html=True)
                role_options = {
                    'viewer': '👁️ Viewer - Read-only access',
                    'responder': '🚑 Responder - Can acknowledge alerts',
                    'analyst': '📊 Analyst - Can classify text'
                }
                role = st.selectbox("Account Type", list(role_options.keys()), format_func=lambda x: role_options[x])
                st.markdown('</div>', unsafe_allow_html=True)
                
                submitted = st.form_submit_button("Create Account", width='stretch', type="primary")
                
                if submitted:
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
                        result = create_user_account(email, password, full_name, phone, agency, role, firebase)
                        if result['success']:
                            st.success("✅ " + result['message'])
                            st.balloons()
                            time.sleep(1.5)
                            st.session_state.auth_tab = 'login'
                            st.rerun()
                        else:
                            st.error("❌ " + result['error'])
        
        st.markdown('</div>', unsafe_allow_html=True)

def logout():
    for key in ['logged_in', 'user_email', 'user_role', 'user_name', 'user_id']:
        if key in st.session_state:
            del st.session_state[key]
    st.success("Logged out successfully!")
    st.rerun()

# ============================================================
# HELPER FUNCTION: EXTRACT MAIN LOCATION
# ============================================================

def extract_main_location(text):
    text_lower = text.lower()
    for loc_name in NIGERIAN_LOCATIONS.keys():
        if loc_name in text_lower:
            if NIGERIAN_LOCATIONS[loc_name]['type'] == 'state':
                return loc_name.title()
    for loc_name in NIGERIAN_LOCATIONS.keys():
        if loc_name in text_lower:
            return loc_name.title()
    return None

# ============================================================
# INITIALIZE SERVICES
# ============================================================

@st.cache_resource
def init_services():
    try:
        firebase = init_firebase()
        classifier = MLDisasterClassifier()
        collector = RSSNewsCollector()
        return firebase, classifier, collector
    except Exception as e:
        st.warning(f"Firebase not available: {e}")
        return None, None, None

try:
    firebase, classifier, collector = init_services()
    if firebase is None:
        st.error("Firebase connection failed. Please check your configuration.")
        st.stop()
except Exception as e:
    st.error(f"Service initialization failed: {e}")
    st.stop()

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = datetime.now()
if 'articles' not in st.session_state:
    st.session_state.articles = []
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

# ============================================================
# AUTHENTICATION CHECK
# ============================================================

if not st.session_state.logged_in:
    show_login_page(firebase)
    st.stop()

# ============================================================
# DATA LOADING FUNCTIONS
# ============================================================

def load_articles():
    if st.session_state.articles:
        return st.session_state.articles
    if firebase:
        try:
            cutoff = (datetime.now() - timedelta(days=7)).isoformat()
            news_ref = firebase.db.collection('news_articles')\
                .where('collected_at', '>=', cutoff)\
                .order_by('collected_at', direction='DESCENDING')\
                .limit(50)\
                .stream()
            articles = []
            for doc in news_ref:
                article = doc.to_dict()
                article['id'] = doc.id
                articles.append(article)
            if articles:
                st.session_state.articles = articles
                return articles
        except:
            pass
    return st.session_state.articles

def load_alerts():
    if st.session_state.alerts:
        return st.session_state.alerts
    if firebase:
        try:
            alerts_ref = firebase.db.collection('alerts')\
                .where('is_read', '==', False)\
                .order_by('created_at', direction='DESCENDING')\
                .limit(20)\
                .stream()
            alerts = [doc.to_dict() for doc in alerts_ref]
            if alerts:
                st.session_state.alerts = alerts
                return alerts
        except:
            pass
    return st.session_state.alerts

# ============================================================
# LOAD AND PROCESS DATA
# ============================================================

all_articles = load_articles()
db_alerts = load_alerts()
total_articles = len(all_articles)

# Process articles and extract locations
articles_with_locations = []
for article in all_articles:
    affected_areas = article.get('affected_areas', [])
    main_location = affected_areas[0] if affected_areas else extract_main_location(f"{article.get('title', '')} {article.get('summary', '')}")
    
    source_name = article.get('source', 'unknown').lower()
    source_info = SOURCE_INFO.get(source_name, SOURCE_INFO.get('punch'))
    
    if main_location:
        articles_with_locations.append({
            'id': article.get('id'),
            'title': article.get('title', 'No title'),
            'summary': article.get('summary', 'No summary'),
            'link': article.get('link', '#'),
            'published': article.get('published_at', article.get('published', datetime.now().isoformat())),
            'source': article.get('source', 'unknown'),
            'source_icon': source_info['icon'],
            'source_color': source_info['color'],
            'source_url': source_info['url'],
            'disaster_type': article.get('disaster_type', 'general'),
            'confidence': article.get('confidence', 0),
            'urgency': article.get('urgency', 'low'),
            'severity_score': article.get('severity_score', 0),
            'sentiment': article.get('sentiment', 'neutral'),
            'main_location': main_location,
            'location_coords': NIGERIAN_LOCATIONS.get(main_location.lower(), {'lat': 9.0820, 'lon': 8.6753})
        })

# Count alerts
high_critical_alerts = 0
for alert in db_alerts:
    if alert.get('severity') in ['critical', 'high']:
        high_critical_alerts += 1
for article in articles_with_locations:
    if article.get('urgency') in ['high', 'critical']:
        high_critical_alerts += 1

# Group incidents by location for map
location_incidents = {}
for article in articles_with_locations:
    location = article['main_location']
    if location not in location_incidents:
        location_incidents[location] = []
    location_incidents[location].append(article)

# Disaster type distribution
disaster_types = {}
for art in articles_with_locations:
    dt = art.get('disaster_type', 'general')
    disaster_types[dt] = disaster_types.get(dt, 0) + 1
disaster_types = dict(sorted(disaster_types.items(), key=lambda x: x[1], reverse=True)[:8])

# Urgency stats
urgency_stats = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
for art in articles_with_locations:
    u = art.get('urgency', 'low')
    urgency_stats[u] = urgency_stats.get(u, 0) + 1

# Daily trend
daily_counts = {}
last_7_days_labels = []
for i in range(6, -1, -1):
    date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
    label = (datetime.now() - timedelta(days=i)).strftime('%b %d')
    last_7_days_labels.append(label)
    daily_counts[date] = 0

for art in articles_with_locations:
    pub_raw = art.get('published', '')
    if pub_raw:
        pub_date = str(pub_raw)[:10] if len(str(pub_raw)) >= 10 else datetime.now().strftime('%Y-%m-%d')
    else:
        pub_date = datetime.now().strftime('%Y-%m-%d')
    if pub_date in daily_counts:
        daily_counts[pub_date] += 1

daily_values = list(daily_counts.values())

# Prepare alert articles
alert_articles = []
for alert in db_alerts:
    alert_articles.append({
        'title': alert.get('title', 'Alert'),
        'summary': alert.get('message', 'No message'),
        'published': alert.get('created_at', datetime.now().isoformat()),
        'urgency': 'critical' if alert.get('severity') == 'critical' else 'high',
        'severity_score': 85,
        'source': 'system',
        'link': '#'
    })
for article in articles_with_locations:
    if article.get('urgency') in ['high', 'critical']:
        existing = [a.get('title') for a in alert_articles]
        if article.get('title') not in existing:
            alert_articles.append({
                'title': article.get('title', 'Alert'),
                'summary': article.get('summary', 'No summary'),
                'published': article.get('published', datetime.now().isoformat()),
                'urgency': article.get('urgency', 'high'),
                'severity_score': article.get('severity_score', 70),
                'link': article.get('link', '#'),
                'source': article.get('source', 'unknown')
            })

# Remove duplicates
seen = set()
unique_alerts = []
for alert in alert_articles:
    if alert.get('title') not in seen:
        seen.add(alert.get('title'))
        unique_alerts.append(alert)
alert_articles = unique_alerts

# Get unique sources
sources = set()
for art in articles_with_locations:
    if art.get('source'):
        sources.add(art.get('source'))

unique_locations_count = len(location_incidents)

# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; 
                    border-radius: 10px; 
                    color: white;
                    margin-bottom: 1rem;">
            <h4>👋 Welcome,</h4>
            <h3>{st.session_state.get('user_name', 'User')}</h3>
            <p style="margin: 0; opacity: 0.9;">📧 {st.session_state.get('user_email', '')}</p>
            <p style="margin: 0; opacity: 0.9;">🎭 Role: <strong>{st.session_state.get('user_role', 'viewer').upper()}</strong></p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    page = st.radio(
        "📋 Navigation",
        ["Dashboard", "Alerts", "Classify Text"],
        index=0
    )
    
    st.markdown("---")
    st.caption(f"Last refresh: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if st.button("🚪 Logout", width='stretch'):
        logout()

# ============================================================
# DASHBOARD PAGE
# ============================================================

if page == "Dashboard":
    st.markdown('<div class="main-header"><h1>📊 Disaster Management Dashboard</h1></div>', unsafe_allow_html=True)
    st.caption("Showing data from <strong>last 7 days</strong>")
    
    # Stats cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="stat-card"><h3>{total_articles}</h3><p>News Articles</p><small>Last 7 Days</small></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="stat-card"><h3 style="color: #dc2626;">{high_critical_alerts}</h3><p>Active Alerts</p><small>Critical / High</small></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="stat-card"><h3>{unique_locations_count}</h3><p>Locations with Incidents</p><small>Affected Areas</small></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="stat-card"><h3>{len(sources)}</h3><p>Active Sources</p><small>News sources</small></div>""", unsafe_allow_html=True)
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_conf = int(sum(a.get('confidence', 0) for a in articles_with_locations) / max(total_articles, 1))
        st.metric("🎯 Avg Confidence", f"{avg_conf}%")
    with col2:
        avg_sev = int(sum(a.get('severity_score', 0) for a in articles_with_locations) / max(total_articles, 1))
        st.metric("⚠️ Avg Severity", f"{avg_sev}/100")
    with col3:
        st.metric("🚨 Critical Alerts", urgency_stats.get('critical', 0))
    with col4:
        st.metric("📡 Active Sources", len(sources))
    
    # Graphs
    col1, col2 = st.columns(2)
    with col1:
        if daily_values and any(daily_values):
            fig_trend = go.Figure()
            fig_trend.add_trace(go.Scatter(x=last_7_days_labels, y=daily_values, mode='lines+markers', name='Incidents', line=dict(color='#dc2626', width=2), marker=dict(size=8, color='#dc2626')))
            fig_trend.update_layout(title="Incident Trend (Last 7 Days)", xaxis_title="Date", yaxis_title="Number of Incidents", height=350)
            st.plotly_chart(fig_trend, use_container_width=True)
        else:
            st.info("No trend data available. Click 'Fetch Latest Disaster News' to get data.")
    
    with col2:
        if disaster_types:
            fig_pie = px.pie(values=list(disaster_types.values()), names=[d.replace('_', ' ').title() for d in disaster_types.keys()], title="Disaster Type Distribution", color_discrete_sequence=px.colors.sequential.Reds_r)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No disaster data available.")
    
    # Incident Map with Folium
    st.markdown("### 🗺️ Incident Map")
    st.caption(f"📍 {unique_locations_count} locations with incidents | {total_articles} total articles")
    
    if location_incidents:
        # Create map centered on Nigeria
        map_center = [9.0820, 8.6753]
        m = folium.Map(location=map_center, zoom_start=6, control_scale=True)
        
        # Add tile layer
        folium.TileLayer('OpenStreetMap').add_to(m)
        
        # Add marker cluster for better organization
        marker_cluster = MarkerCluster().add_to(m)
        
        # Add markers for each location
        for location, incidents in location_incidents.items():
            coords = NIGERIAN_LOCATIONS.get(location.lower(), {'lat': 9.0820, 'lon': 8.6753})
            
            # Determine marker color based on highest urgency
            highest_urgency = 'low'
            for inc in incidents:
                if inc['urgency'] == 'critical':
                    highest_urgency = 'critical'
                    break
                elif inc['urgency'] == 'high' and highest_urgency != 'critical':
                    highest_urgency = 'high'
                elif inc['urgency'] == 'medium' and highest_urgency not in ['critical', 'high']:
                    highest_urgency = 'medium'
            
            # Marker color mapping
            marker_colors = {
                'critical': 'red',
                'high': 'orange',
                'medium': 'yellow',
                'low': 'green'
            }
            marker_color = marker_colors.get(highest_urgency, 'blue')
            
            # Create popup content with incident details
            popup_html = f"""
                <div style="min-width: 280px; max-width: 350px;">
                    <h4 style="color: #dc2626; margin: 0 0 10px 0;">📍 {location}</h4>
                    <p style="font-weight: bold; margin: 5px 0;">Total Incidents: {len(incidents)}</p>
                    <hr style="margin: 8px 0;">
            """
            
            # Add top 5 incidents in popup
            for i, inc in enumerate(incidents[:5]):
                urgency_icon = "🔴" if inc['urgency'] == 'critical' else "🟠" if inc['urgency'] == 'high' else "🟡" if inc['urgency'] == 'medium' else "🟢"
                popup_html += f"""
                    <div style="margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #eee;">
                        <div style="display: flex; gap: 5px; flex-wrap: wrap; margin-bottom: 3px;">
                            <span style="background: {SOURCE_INFO.get(inc['source'].lower(), SOURCE_INFO['punch'])['color']}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;">
                                {inc['source'].upper()}
                            </span>
                            <span style="background: {marker_colors.get(inc['urgency'], 'gray')}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 10px;">
                                {inc['urgency'].upper()}
                            </span>
                        </div>
                        <strong>{inc['title'][:80]}...</strong><br>
                        <small>{inc['published'][:16] if inc['published'] else ''}</small><br>
                        <a href="{inc['link']}" target="_blank" style="font-size: 11px;">📖 Read full article →</a>
                    </div>
                """
            
            popup_html += f"""
                    {f'<div style="margin-top: 8px;"><em>+ {len(incidents) - 5} more incidents...</em></div>' if len(incidents) > 5 else ''}
                </div>
            """
            
            # Create marker with custom icon based on urgency
            folium.Marker(
                location=[coords['lat'], coords['lon']],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"{location} - {len(incidents)} incidents (Highest: {highest_urgency.upper()})",
                icon=folium.Icon(color=marker_color, icon='info-sign', icon_color='white')
            ).add_to(marker_cluster)
        
        # Fit bounds to show all markers
        m.fit_bounds([[p['lat'], p['lon']] for p in incident_points]) if 'incident_points' in locals() else None
        
        # Display the map
        st_folium(m, width='100%', height=500, returned_objects=[])
        
        # Location summary below map
        st.markdown("#### 📍 Affected Locations Summary")
        cols = st.columns(4)
        for i, (location, incidents) in enumerate(location_incidents.items()):
            with cols[i % 4]:
                # Determine urgency level for color coding
                urgency_level = 'low'
                for inc in incidents:
                    if inc['urgency'] == 'critical':
                        urgency_level = 'critical'
                        break
                    elif inc['urgency'] == 'high' and urgency_level != 'critical':
                        urgency_level = 'high'
                    elif inc['urgency'] == 'medium' and urgency_level not in ['critical', 'high']:
                        urgency_level = 'medium'
                
                urgency_color = "#dc2626" if urgency_level == 'critical' else "#f97316" if urgency_level == 'high' else "#eab308" if urgency_level == 'medium' else "#10b981"
                urgency_icon = "🔴" if urgency_level == 'critical' else "🟠" if urgency_level == 'high' else "🟡" if urgency_level == 'medium' else "🟢"
                
                st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; border-left: 3px solid {urgency_color};">
                        <strong>{urgency_icon} {location}</strong><br>
                        <small>📰 {len(incidents)} incidents</small><br>
                        <small>⚠️ Max urgency: <span style="color: {urgency_color}; font-weight: bold;">{urgency_level.upper()}</span></small>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No incident locations to display. Click 'Fetch Latest Disaster News' to get data.")
    
    # Alerts Section
    if alert_articles:
        st.markdown("### 🚨 URGENT ALERTS")
        for alert in alert_articles[:5]:
            urgency = alert.get('urgency', 'high')
            source = alert.get('source', 'system')
            source_info = SOURCE_INFO.get(source.lower(), SOURCE_INFO['system'])
            
            st.markdown(f"""
                <div style="border-left: 4px solid {'#dc2626' if urgency=='critical' else '#f97316'}; 
                            background: {'#fef2f2' if urgency=='critical' else '#fff7ed'}; 
                            padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap;">
                        <span class="badge bg-secondary" style="background: {source_info['color']};">{source_info['icon']} {source.upper()}</span>
                        <span class="badge badge-{urgency}">{urgency.upper()} URGENCY</span>
                    </div>
                    <h6><strong>{alert.get('title', 'Alert')[:100]}</strong></h6>
                    <p>{alert.get('summary', '')[:200]}...</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <small>📅 {alert.get('published', '')[:16] if alert.get('published') else ''}</small>
                        {f'<a href="{alert.get("link", "#")}" target="_blank" style="color: #667eea; text-decoration: none;">📖 Read full article →</a>' if alert.get('link') and alert.get('link') != '#' else ''}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    
    # News Feed with Source Links
    st.markdown("### 📰 ML-Classified News Feed")
    
    if articles_with_locations:
        for article in articles_with_locations[:10]:
            urgency = article.get('urgency', 'low')
            confidence = article.get('confidence', 0)
            severity = article.get('severity_score', 0)
            sentiment = article.get('sentiment', 'neutral')
            disaster = article.get('disaster_type', 'unspecified')
            location = article.get('main_location', 'Unknown')
            source = article.get('source', 'unknown')
            source_icon = article.get('source_icon', '📰')
            source_color = article.get('source_color', '#667eea')
            source_url = article.get('source_url', '#')
            article_link = article.get('link', '#')
            
            border_color = '#dc2626' if urgency == 'critical' else '#f97316' if urgency == 'high' else '#eab308' if urgency == 'medium' else '#10b981'
            
            st.markdown(f"""
                <div class="news-card" style="border-left: 4px solid {border_color}; 
                            background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem;">
                        <span class="badge bg-secondary" style="background: {source_color};">{source_icon} {source.upper()}</span>
                        <span class="badge badge-{urgency}">{urgency.upper()}</span>
                        <span class="badge bg-info text-dark">🔥 {disaster.replace('_', ' ').title()}</span>
                        <span class="badge" style="background: {'#10b981' if sentiment=='positive' else '#dc2626' if sentiment=='negative' else '#6b7280'}; color: white;">
                            {sentiment.upper()}
                        </span>
                        <span class="badge bg-primary">📍 {location}</span>
                    </div>
                    <h5><strong>{article.get('title', 'No title')[:150]}</strong></h5>
                    <p>{article.get('summary', 'No summary')[:200]}...</p>
                    <div style="display: flex; gap: 1rem; font-size: 0.8rem; color: #666; flex-wrap: wrap; margin-bottom: 0.5rem;">
                        <span>🎯 Confidence: {confidence}%</span>
                        <span>⚠️ Severity: {severity}/100</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <small>📅 {article.get('published', '')[:16] if article.get('published') else ''}</small>
                        <div style="display: flex; gap: 1rem;">
                            <a href="{source_url}" target="_blank" class="source-link" style="font-size: 12px;">🏠 Visit {source.upper()}</a>
                            <a href="{article_link}" target="_blank" class="source-link" style="font-size: 12px;">📖 Read full article →</a>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No articles found. Click 'Fetch Latest Disaster News' to get real data from Nigerian RSS feeds.")
    
    # Fetch Button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Fetch Latest Disaster News", width='stretch', type="primary"):
            if collector:
                with st.spinner("Fetching disaster news from Nigerian RSS feeds..."):
                    articles = collector.collect_all_feeds(hours_back=72, limit_per_feed=15)
                    count = 0
                    new_articles = []
                    for article in articles:
                        if classifier:
                            ml_result = classifier.classify_article({'title': article.get('title', ''), 'summary': article.get('summary', ''), 'content': article.get('content', '')})
                            article['disaster_type'] = ml_result['disaster_type']
                            article['confidence'] = ml_result['confidence']
                            article['urgency'] = ml_result['urgency']
                            article['severity_score'] = ml_result['severity_score']
                            article['sentiment'] = ml_result['sentiment']['sentiment']
                            article['affected_areas'] = ml_result['affected_areas']
                        article['published_at'] = article.get('published', datetime.now().isoformat())
                        new_articles.append(article)
                        count += 1
                        if firebase:
                            try:
                                firebase.db.collection('news_articles').document(article['id']).set(article)
                            except:
                                pass
                    st.session_state.articles = new_articles + st.session_state.articles
                    st.session_state.last_refresh = datetime.now()
                    st.success(f"✅ Fetched and classified {count} new disaster articles")
                    time.sleep(1.5)
                    st.rerun()
            else:
                st.error("RSS Collector not available")

# ============================================================
# ALERTS PAGE
# ============================================================

elif page == "Alerts":
    st.markdown('<div class="main-header"><h1>🚨 Active Alerts</h1></div>', unsafe_allow_html=True)
    
    if alert_articles:
        for alert in alert_articles:
            urgency = alert.get('urgency', 'high')
            severity = alert.get('severity_score', 85)
            source = alert.get('source', 'system')
            source_info = SOURCE_INFO.get(source.lower(), SOURCE_INFO['system'])
            
            st.markdown(f"""
                <div style="border-left: 4px solid {'#dc2626' if urgency=='critical' else '#f97316'}; 
                            background: {'#fef2f2' if urgency=='critical' else '#fff7ed'}; 
                            padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="display: flex; gap: 0.5rem; margin-bottom: 0.5rem; flex-wrap: wrap;">
                        <span class="badge bg-secondary" style="background: {source_info['color']};">{source_info['icon']} {source.upper()}</span>
                        <span class="badge badge-{urgency}">{urgency.upper()} URGENCY</span>
                        <span class="badge bg-secondary">Severity {severity}/100</span>
                    </div>
                    <h4>⚠️ {alert.get('title', 'Alert')[:150]}</h4>
                    <p>{alert.get('summary', 'No message')[:400]}...</p>
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                        <small>📅 {alert.get('published', '')[:19] if alert.get('published') else ''}</small>
                        {f'<a href="{alert.get("link", "#")}" target="_blank" class="source-link">📖 Read full article →</a>' if alert.get('link') and alert.get('link') != '#' else ''}
                    </div>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ No active alerts at this time")

# ============================================================
# CLASSIFY TEXT PAGE
# ============================================================

elif page == "Classify Text":
    st.markdown('<div class="main-header"><h1>🤖 ML Text Classification</h1></div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### Classify Disaster News Text
    Enter a news article or disaster report to classify it using our ML model.
    """)
    
    text_input = st.text_area(
        "Enter disaster-related text to classify",
        height=200,
        placeholder="Example: Heavy flooding in Anambra has displaced over 500 families. Rescue teams have been deployed to the affected communities."
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔍 Classify Text", width='stretch', type="primary"):
            if text_input:
                with st.spinner("Analyzing with ML model..."):
                    if classifier:
                        result = classifier.classify_article({
                            'title': text_input[:100],
                            'summary': text_input[:500],
                            'content': text_input
                        })
                        
                        st.markdown("### 📊 Classification Results")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Disaster Type", result['disaster_type'].replace('_', ' ').title())
                        with col2:
                            st.metric("Urgency", result['urgency'].upper())
                        with col3:
                            st.metric("Confidence", f"{result['confidence']}%")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Severity Score", f"{result['severity_score']}/100")
                        with col2:
                            st.metric("Sentiment", result['sentiment']['sentiment'].upper())
                        with col3:
                            st.metric("Needs Attention", "✅ Yes" if result['needs_attention'] else "❌ No")
                        
                        if result.get('affected_areas'):
                            st.markdown("### 📍 Affected Areas")
                            st.write(", ".join(result['affected_areas']))
                        
                        if result.get('key_numbers'):
                            st.markdown("### 🔢 Key Numbers")
                            st.json(result['key_numbers'])
                        
                        with st.expander("🔬 View Detailed Analysis"):
                            st.json(result)
                    else:
                        st.error("ML Classifier not available")
            else:
                st.warning("Please enter some text to classify")
    
    # Sample texts
    st.markdown("---")
    st.markdown("### 📝 Sample Texts to Try")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏗️ Building Collapse", width='stretch'):
            sample = "A three-storey building collapsed in Lagos Island this morning. Rescue workers are searching for survivors. At least 15 people are feared trapped under the rubble."
            st.session_state.sample_text = sample
            st.rerun()
        if st.button("🌊 Flooding", width='stretch'):
            sample = "Heavy flooding has displaced over 500 families in Anambra State. Many homes are submerged and residents are trapped on rooftops."
            st.session_state.sample_text = sample
            st.rerun()
    with col2:
        if st.button("🔥 Fire Outbreak", width='stretch'):
            sample = "A fire outbreak at a market in Kano has destroyed over 200 shops. Firefighters are struggling to contain the blaze."
            st.session_state.sample_text = sample
            st.rerun()
        if st.button("🦠 Disease Outbreak", width='stretch'):
            sample = "A cholera outbreak has been reported in Benue State. 50 cases have been confirmed and 3 deaths recorded."
            st.session_state.sample_text = sample
            st.rerun()
    
    if 'sample_text' in st.session_state:
        st.info(f"Sample loaded. Click 'Classify Text' above to analyze.")
        st.code(st.session_state.sample_text)
