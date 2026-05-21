# utils/ml_classifier.py
import re
import logging
from typing import Dict, List
import streamlit as st

logger = logging.getLogger(__name__)

class MLDisasterClassifier:
    """Machine Learning classifier for disaster news"""
    
    def __init__(self):
        self.disaster_categories = [
            'flood', 'fire', 'storm', 'landslide', 'drought',
            'epidemic', 'building_collapse', 'accident', 'general_disaster'
        ]
        
        self.urgency_map = {
            'building_collapse': 'critical',
            'flood': 'high',
            'fire': 'high',
            'epidemic': 'high',
            'storm': 'medium',
            'landslide': 'high',
            'drought': 'medium',
            'accident': 'medium',
            'general_disaster': 'low'
        }
        
        self.nigerian_states = self._get_nigerian_states()
        self._load_keywords()
        self._load_sentiment_keywords()
        
        # Try to load BERT
        self.sentiment_pipeline = self._load_bert()
    
    def _get_nigerian_states(self):
        return [
            'lagos', 'anambra', 'kogi', 'bayelsa', 'delta', 'rivers', 'ogun', 'oyo',
            'edo', 'imo', 'abia', 'enugu', 'benue', 'plateau', 'kaduna', 'kano',
            'abuja', 'niger', 'kwara', 'osun', 'ekiti', 'ondo', 'cross river',
            'akwa ibom', 'borno', 'yobe', 'gombe', 'bauchi', 'jigawa', 'katsina',
            'kebbi', 'sokoto', 'zamfara', 'taraba', 'adamawa', 'ebonyi', 'nassarawa'
        ]
    
    def _load_keywords(self):
        self.disaster_keywords = {
            'flood': ['flood', 'flooding', 'flooded', 'water level', 'river overflow', 
                     'submerged', 'inundation', 'flash flood', 'heavy rainfall'],
            'fire': ['fire', 'inferno', 'blaze', 'burning', 'gas explosion', 
                    'fire outbreak', 'burned down', 'wildfire'],
            'building_collapse': ['building collapse', 'structure collapse', 'collapsed building', 
                                 'building fell', 'caved in'],
            'epidemic': ['outbreak', 'epidemic', 'cholera', 'lassa fever', 'measles',
                        'meningitis', 'yellow fever', 'monkeypox', 'covid'],
            'storm': ['storm', 'windstorm', 'cyclone', 'thunderstorm', 'heavy wind'],
            'landslide': ['landslide', 'landslip', 'mudslide', 'earth movement'],
            'drought': ['drought', 'dry spell', 'water scarcity', 'food shortage', 'famine'],
            'accident': ['accident', 'crash', 'collision', 'road accident', 'vehicle accident']
        }
    
    def _load_sentiment_keywords(self):
        self.sentiment_keywords = {
            'positive': ['rescue', 'saved', 'recovered', 'safe', 'evacuated', 'aid', 'relief'],
            'negative': ['death', 'killed', 'died', 'casualty', 'injured', 'trapped', 'missing',
                        'destroyed', 'collapsed', 'damage'],
            'neutral': ['reported', 'said', 'according', 'stated', 'announced']
        }
    
    def _load_bert(self):
        """Load BERT model for sentiment analysis"""
        try:
            from transformers import pipeline
            pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment", device=-1)
            return True
        except Exception as e:
            logger.warning(f"BERT not available: {e}")
            return None
    
    def classify_article(self, article: Dict) -> Dict:
        """Main classification method"""
        full_text = f"{article.get('title', '')} {article.get('summary', '')} {article.get('content', '')}"
        
        # Check if Nigeria-related
        is_nigeria_related = self._is_nigeria_related(full_text)
        
        # Keyword classification
        keyword_results = self._keyword_classify(full_text)
        
        # Sentiment analysis
        sentiment_result = self._keyword_sentiment(full_text)
        
        # Get classification results
        disaster_type = keyword_results.get('primary_type', 'general_disaster')
        confidence = keyword_results.get('confidence', 50)
        
        # Determine urgency
        urgency = self._determine_urgency(disaster_type, full_text, keyword_results)
        
        # Calculate severity
        severity_score = self._calculate_severity(full_text, disaster_type, sentiment_result)
        
        # Extract affected areas (only if Nigeria-related)
        affected_areas = []
        if is_nigeria_related:
            affected_areas = self._extract_affected_areas(full_text)
        
        # Extract key numbers
        key_numbers = self._extract_key_numbers(full_text)
        
        return {
            'disaster_type': disaster_type,
            'confidence': confidence,
            'urgency': urgency,
            'sentiment': sentiment_result,
            'severity_score': severity_score,
            'needs_attention': urgency in ['high', 'critical'],
            'affected_areas': affected_areas,
            'key_numbers': key_numbers,
            'is_nigeria_related': is_nigeria_related
        }
    
    def _is_nigeria_related(self, text: str) -> bool:
        """Check if article is about Nigeria"""
        text_lower = text.lower()
        for state in self.nigerian_states:
            if re.search(r'\b' + re.escape(state) + r'\b', text_lower):
                return True
        return False
    
    def _keyword_classify(self, text: str) -> Dict:
        """Classify using keywords"""
        text_lower = text.lower()
        scores = {}
        
        for disaster_type, keywords in self.disaster_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
            scores[disaster_type] = score
        
        if max(scores.values()) > 0:
            primary_type = max(scores, key=scores.get)
            confidence = min(95, int(scores[primary_type] / sum(scores.values()) * 100) if sum(scores.values()) > 0 else 30)
        else:
            primary_type = 'general_disaster'
            confidence = 30
        
        return {
            'primary_type': primary_type,
            'confidence': confidence,
            'scores': scores
        }
    
    def _keyword_sentiment(self, text: str) -> Dict:
        """Sentiment analysis using keywords"""
        text_lower = text.lower()
        
        positive = sum(1 for kw in self.sentiment_keywords['positive'] if kw in text_lower)
        negative = sum(1 for kw in self.sentiment_keywords['negative'] if kw in text_lower)
        
        if positive > negative:
            return {'sentiment': 'positive', 'confidence': min(95, int(positive / (positive + negative) * 100))}
        elif negative > positive:
            return {'sentiment': 'negative', 'confidence': min(95, int(negative / (positive + negative) * 100))}
        else:
            return {'sentiment': 'neutral', 'confidence': 50}
    
    def _determine_urgency(self, disaster_type: str, text: str, keyword_results: Dict) -> str:
        """Determine urgency level"""
        base = self.urgency_map.get(disaster_type, 'medium')
        text_lower = text.lower()
        
        critical_indicators = ['trapped', 'rescue', 'emergency', 'urgent', 'casualty', 'death', 'collapsed']
        high_indicators = ['evacuate', 'injured', 'displaced', 'flooded', 'fire outbreak', 'explosion']
        
        if any(kw in text_lower for kw in critical_indicators):
            return 'critical'
        if any(kw in text_lower for kw in high_indicators):
            return 'high'
        
        return base
    
    def _calculate_severity(self, text: str, disaster_type: str, sentiment: Dict) -> int:
        """Calculate severity score (0-100)"""
        severity_map = {
            'building_collapse': 90, 'fire': 75, 'epidemic': 80, 'flood': 70,
            'landslide': 70, 'storm': 60, 'drought': 50, 'accident': 65, 'general_disaster': 40
        }
        severity = severity_map.get(disaster_type, 50)
        
        text_lower = text.lower()
        if sentiment.get('sentiment') == 'negative':
            severity += 15
        if any(kw in text_lower for kw in ['death', 'killed', 'fatal']):
            severity = min(100, severity + 20)
        if any(kw in text_lower for kw in ['trapped', 'rescue']):
            severity = min(100, severity + 15)
        
        return min(100, max(0, severity))
    
    def _extract_affected_areas(self, text: str) -> List[str]:
        """Extract Nigerian locations from text"""
        text_lower = text.lower()
        areas = []
        
        for state in self.nigerian_states:
            if re.search(r'\b' + re.escape(state) + r'\b', text_lower):
                areas.append(state.title())
        
        return list(dict.fromkeys(areas))[:5]
    
    def _extract_key_numbers(self, text: str) -> Dict:
        """Extract key numbers from text"""
        text_lower = text.lower()
        numbers = {}
        
        patterns = {
            'deaths': r'(\d+)\s*(?:death|dead|killed|fatalities?)',
            'injured': r'(\d+)\s*(?:injured|wounded|hurt)',
            'displaced': r'(\d+)\s*(?:displaced|homeless|evacuated)',
            'affected': r'(\d+)\s*(?:affected|impacted|people)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                numbers[key] = int(match.group(1))
        
        return numbers