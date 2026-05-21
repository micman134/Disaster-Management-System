# utils/firebase_config.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from datetime import datetime, timedelta
import json

class FirebaseManager:
    """Firebase initialization and management"""
    
    def __init__(self):
        self._init_admin_sdk()
    
    def _init_admin_sdk(self):
        """Initialize Firebase Admin SDK with Streamlit secrets"""
        try:
            # Get Firebase config from Streamlit secrets
            firebase_config = dict(st.secrets["firebase"])
            
            # Convert private key string properly (handles \n)
            if 'private_key' in firebase_config:
                firebase_config['private_key'] = firebase_config['private_key'].replace('\\n', '\n')
            
            # Initialize only if not already initialized
            if not firebase_admin._apps:
                cred = credentials.Certificate(firebase_config)
                firebase_admin.initialize_app(cred, {
                    'storageBucket': firebase_config.get('storage_bucket', 'disaster-management-syst-8cffd.firebasestorage.app')
                })
            
            self.db = firestore.client()
            self.bucket = storage.bucket()
            
            # Initialize Pyrebase for client-side auth (this is what we need!)
            import pyrebase
            
            # Pyrebase config (using the same values)
            pyrebase_config = {
                "apiKey": firebase_config.get("api_key") or firebase_config.get("apiKey", ""),
                "authDomain": firebase_config.get("auth_domain") or firebase_config.get("authDomain", ""),
                "projectId": firebase_config.get("project_id") or firebase_config.get("projectId", ""),
                "storageBucket": firebase_config.get("storage_bucket") or firebase_config.get("storageBucket", ""),
                "messagingSenderId": firebase_config.get("messaging_sender_id") or firebase_config.get("messagingSenderId", ""),
                "appId": firebase_config.get("app_id") or firebase_config.get("appId", ""),
                "databaseURL": firebase_config.get("database_url") or firebase_config.get("databaseURL", "")
            }
            
            self.pyrebase = pyrebase.initialize_app(pyrebase_config)
            self.auth = self.pyrebase.auth()  # This gives us the auth methods!
            
            print("✅ Firebase initialized successfully!")
            
        except Exception as e:
            st.error(f"❌ Firebase initialization failed: {e}")
            raise e
    
    # ============================================================
    # INCIDENTS
    # ============================================================
    
    def add_incident(self, incident_data):
        """Add a new incident"""
        incident_data['created_at'] = datetime.now().isoformat()
        incident_data['updated_at'] = datetime.now().isoformat()
        
        doc_ref = self.db.collection('incidents').document()
        incident_data['id'] = doc_ref.id
        doc_ref.set(incident_data)
        return incident_data['id']
    
    def get_incidents(self, limit=100, days_back=7):
        """Get incidents from last N days"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        incidents = self.db.collection('incidents')\
            .where('created_at', '>=', cutoff_date)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        
        return [doc.to_dict() for doc in incidents]
    
    def update_incident(self, incident_id, data):
        """Update incident"""
        data['updated_at'] = datetime.now().isoformat()
        self.db.collection('incidents').document(incident_id).update(data)
    
    # ============================================================
    # ALERTS
    # ============================================================
    
    def add_alert(self, alert_data):
        """Add a new alert"""
        alert_data['created_at'] = datetime.now().isoformat()
        alert_data['is_read'] = False
        alert_data['is_acknowledged'] = False
        
        doc_ref = self.db.collection('alerts').document()
        alert_data['id'] = doc_ref.id
        doc_ref.set(alert_data)
        return alert_data['id']
    
    def get_active_alerts(self, limit=50):
        """Get unread/unacknowledged alerts"""
        alerts = self.db.collection('alerts')\
            .where('is_read', '==', False)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        
        return [doc.to_dict() for doc in alerts]
    
    def acknowledge_alert(self, alert_id, user_id):
        """Mark alert as acknowledged"""
        self.db.collection('alerts').document(alert_id).update({
            'is_acknowledged': True,
            'is_read': True,
            'acknowledged_by': user_id,
            'acknowledged_at': datetime.now().isoformat()
        })
    
    # ============================================================
    # NEWS ARTICLES
    # ============================================================
    
    def add_news_article(self, article):
        """Add or update news article"""
        article['updated_at'] = datetime.now().isoformat()
        
        # Check if article already exists
        existing = self.db.collection('news_articles').where('id', '==', article.get('id')).limit(1).stream()
        existing_list = list(existing)
        
        if existing_list:
            # Update existing
            doc_id = existing_list[0].id
            self.db.collection('news_articles').document(doc_id).update(article)
            return doc_id
        else:
            # Create new
            article['created_at'] = datetime.now().isoformat()
            doc_ref = self.db.collection('news_articles').document()
            article['id'] = doc_ref.id
            doc_ref.set(article)
            return article['id']
    
    def get_news_articles(self, limit=100, days_back=7):
        """Get news articles from last N days"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        articles = self.db.collection('news_articles')\
            .where('collected_at', '>=', cutoff_date)\
            .order_by('collected_at', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        
        return [doc.to_dict() for doc in articles]
    
    def get_news_by_urgency(self, urgency, limit=50):
        """Get news filtered by urgency"""
        articles = self.db.collection('news_articles')\
            .where('urgency', '==', urgency)\
            .order_by('severity_score', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        
        return [doc.to_dict() for doc in articles]
    
    # ============================================================
    # LOCATIONS
    # ============================================================
    
    def add_location(self, location_data):
        """Add a new location"""
        location_data['created_at'] = datetime.now().isoformat()
        
        doc_ref = self.db.collection('locations').document()
        location_data['id'] = doc_ref.id
        doc_ref.set(location_data)
        return location_data['id']
    
    def get_locations(self, location_type=None):
        """Get all locations"""
        query = self.db.collection('locations')
        if location_type:
            query = query.where('location_type', '==', location_type)
        
        locations = query.stream()
        return [doc.to_dict() for doc in locations]
    
    def update_location(self, location_id, data):
        """Update location"""
        data['updated_at'] = datetime.now().isoformat()
        self.db.collection('locations').document(location_id).update(data)
    
    # ============================================================
    # CLASSIFICATION HISTORY
    # ============================================================
    
    def add_classification(self, classification_data):
        """Add classification result to history"""
        classification_data['created_at'] = datetime.now().isoformat()
        
        doc_ref = self.db.collection('classification_history').document()
        classification_data['id'] = doc_ref.id
        doc_ref.set(classification_data)
        return classification_data['id']
    
    def get_classification_history(self, limit=50):
        """Get classification history"""
        history = self.db.collection('classification_history')\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        
        return [doc.to_dict() for doc in history]
    
    # ============================================================
    # SYSTEM LOGS
    # ============================================================
    
    def add_log(self, log_data):
        """Add system log"""
        log_data['timestamp'] = datetime.now().isoformat()
        doc_ref = self.db.collection('system_logs').document()
        doc_ref.set(log_data)
        return doc_ref.id
    
    def get_logs(self, limit=100):
        """Get system logs"""
        logs = self.db.collection('system_logs')\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        
        return [doc.to_dict() for doc in logs]
    
    # ============================================================
    # STATISTICS
    # ============================================================
    
    def get_stats(self, days_back=7):
        """Get system statistics"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        # Count incidents
        incidents_count = len(list(self.db.collection('incidents')
            .where('created_at', '>=', cutoff_date).limit(1000).stream()))
        
        # Count active alerts
        alerts_count = len(list(self.db.collection('alerts')
            .where('is_read', '==', False).stream()))
        
        # Count news articles
        news_count = len(list(self.db.collection('news_articles')
            .where('collected_at', '>=', cutoff_date).limit(1000).stream()))
        
        # Count locations
        locations_count = len(list(self.db.collection('locations').stream()))
        
        return {
            'incidents': incidents_count,
            'alerts': alerts_count,
            'news': news_count,
            'locations': locations_count
        }
    
    def get_incidents_by_urgency(self, days_back=7):
        """Get incident counts grouped by urgency"""
        cutoff_date = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        incidents = self.db.collection('incidents')\
            .where('created_at', '>=', cutoff_date)\
            .stream()
        
        urgency_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for inc in incidents:
            data = inc.to_dict()
            urgency = data.get('urgency_level', 'low')
            if urgency in urgency_counts:
                urgency_counts[urgency] += 1
        
        return urgency_counts


# Singleton instance
@st.cache_resource
def init_firebase():
    return FirebaseManager()