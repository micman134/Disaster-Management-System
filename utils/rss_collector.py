# utils/rss_collector.py
import feedparser
import requests
import hashlib
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import random
import time

logger = logging.getLogger(__name__)

class RSSNewsCollector:
    """Collect Nigeria-specific disaster news from RSS feeds"""
    
    def __init__(self):
        self.feeds = {
            'punch': {'url': 'https://punchng.com/feed', 'reliability': 0.85, 'active': True},
            'daily_trust': {'url': 'https://dailytrust.com/feed', 'reliability': 0.85, 'active': True},
            'channels': {'url': 'https://www.channelstv.com/feed/', 'reliability': 0.85, 'active': True},
            'thisday': {'url': 'https://www.thisdaylive.com/feed', 'reliability': 0.85, 'active': True},
            'vanguard': {'url': 'https://www.vanguardngr.com/feed', 'reliability': 0.87, 'active': True}
        }
        
        # Comprehensive disaster keywords
        self.disaster_keywords = {
            'flood': ['flood', 'flooding', 'flooded', 'water level', 'submerged', 'inundation', 
                     'flash flood', 'heavy rainfall', 'rainstorm', 'downpour', 'water rises'],
            'fire': ['fire', 'inferno', 'blaze', 'burning', 'gas explosion', 'fire outbreak', 
                    'burned down', 'wildfire', 'fire razes', 'fire guts', 'fire service', 'arson'],
            'building_collapse': ['building collapse', 'structure collapse', 'collapsed building', 
                                 'building fell', 'caved in', 'collapsed structure', 'storey building',
                                 'building crumbles', 'structural failure'],
            'epidemic': ['outbreak', 'epidemic', 'cholera', 'lassa fever', 'measles', 'meningitis',
                        'yellow fever', 'monkeypox', 'covid', 'pandemic', 'health emergency',
                        'disease outbreak', 'virus', 'quarantine'],
            'accident': ['accident', 'crash', 'collision', 'road accident', 'vehicle accident',
                        'tanker explosion', 'auto crash', 'fatal accident', 'bus crash', 
                        'multiple accident', 'train accident'],
            'storm': ['storm', 'windstorm', 'cyclone', 'thunderstorm', 'heavy wind', 'tornado',
                     'hurricane', 'typhoon', 'gale', 'wind damage'],
            'landslide': ['landslide', 'landslip', 'mudslide', 'earth movement', 'soil erosion'],
            'drought': ['drought', 'dry spell', 'water scarcity', 'food shortage', 'famine',
                       'crop failure', 'agricultural drought']
        }
        
        # Nigerian states (complete list)
        self.nigerian_states = [
            'lagos', 'abuja', 'anambra', 'kogi', 'bayelsa', 'delta', 'rivers', 'ogun', 'oyo',
            'edo', 'imo', 'abia', 'enugu', 'benue', 'plateau', 'kaduna', 'kano', 'niger',
            'kwara', 'osun', 'ekiti', 'ondo', 'cross river', 'akwa ibom', 'borno', 'yobe',
            'gombe', 'bauchi', 'jigawa', 'katsina', 'kebbi', 'sokoto', 'zamfara', 'taraba',
            'adamawa', 'ebonyi', 'nassarawa', 'abia', 'imo'
        ]
        
        # Nigerian cities
        self.nigerian_cities = [
            'lagos', 'ibadan', 'abuja', 'kano', 'port harcourt', 'benin', 'aba', 'maiduguri',
            'zaria', 'ilorin', 'jos', 'warri', 'sokoto', 'enugu', 'onitsha', 'kaduna',
            'owerri', 'calabar', 'uyo', 'akure', 'minna', 'lokoja', 'makurdi', 'yola',
            'gwagwalada', 'kuje', 'bwari'
        ]
        
        # Sports keywords to filter out
        self.sports_keywords = [
            'football', 'soccer', 'match', 'stadium', 'pitch', 'goal', 'player', 'coach',
            'team', 'league', 'tournament', 'championship', 'cup', 'super eagles',
            'premier league', 'champions league', 'world cup', 'afcon', 'nff', 'npfl',
            'messi', 'ronaldo', 'osimhen', 'lookman', 'transfer', 'signing', 'contract',
            'halftime', 'fulltime', 'penalty', 'red card', 'yellow card'
        ]
        
        # Nigeria indicators
        self.nigeria_indicators = [
            'nigeria', 'nigerian', 'naija', 'nema', 'federal government', 'state government'
        ]
        
        self.seen_articles = set()
    
    def _is_nigeria_related(self, article: Dict) -> bool:
        """Check if article is Nigeria-related"""
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        
        # Check for Nigerian states
        for state in self.nigerian_states:
            if re.search(r'\b' + re.escape(state) + r'\b', text):
                return True
        
        # Check for Nigerian cities
        for city in self.nigerian_cities:
            if re.search(r'\b' + re.escape(city) + r'\b', text):
                return True
        
        # Check for Nigeria indicators
        for indicator in self.nigeria_indicators:
            if indicator in text:
                return True
        
        return False
    
    def _is_sports_related(self, article: Dict) -> bool:
        """Check if article is sports-related - filter out"""
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        
        # Count sports keywords
        sports_count = 0
        for keyword in self.sports_keywords:
            if keyword in text:
                sports_count += 1
                if sports_count >= 2:  # If 2 or more sports keywords, it's sports
                    return True
        
        return False
    
    def _is_disaster_related(self, article: Dict) -> bool:
        """Check if article is disaster-related - ONLY disaster news"""
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        
        # Check for disaster keywords
        for category, keywords in self.disaster_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    logger.debug(f"  ✅ Disaster detected: {category} - {keyword}")
                    return True
        
        # Check for urgent disaster terms
        urgent_terms = ['emergency', 'urgent', 'disaster', 'crisis', 'alert', 
                       'casualty', 'casualties', 'death toll', 'victims', 'rescue']
        
        for term in urgent_terms:
            if term in text:
                logger.debug(f"  ✅ Emergency term detected: {term}")
                return True
        
        return False
    
    def _parse_entry(self, entry, source_name, feed_info):
        """Parse feed entry into article dict"""
        title = entry.get('title', '').strip()
        if not title or len(title) < 15:
            return None
        
        # Get summary
        summary = entry.get('summary', entry.get('description', ''))
        if summary:
            # Remove HTML tags
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = re.sub(r'\s+', ' ', summary).strip()
            summary = summary[:800]
        
        link = entry.get('link', '')
        if not link:
            return None
        
        # Get published date
        published = ''
        published_timestamp = None
        
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            published = time.strftime('%Y-%m-%d %H:%M:%S', entry.published_parsed)
            published_timestamp = time.mktime(entry.published_parsed)
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            published = time.strftime('%Y-%m-%d %H:%M:%S', entry.updated_parsed)
            published_timestamp = time.mktime(entry.updated_parsed)
        
        # Get content if available
        content = ''
        if hasattr(entry, 'content') and entry.content:
            content = entry.content[0].value if isinstance(entry.content, list) else entry.content
            content = re.sub(r'<[^>]+>', '', content)[:1000]
        
        # Extract locations from text
        locations = self._extract_locations(f"{title} {summary}")
        
        return {
            'id': hashlib.md5(link.encode()).hexdigest(),
            'source': source_name,
            'title': title,
            'summary': summary if summary else title[:300],
            'link': link,
            'published': published,
            'published_timestamp': published_timestamp,
            'collected_at': datetime.now().isoformat(),
            'content': content,
            'locations': locations
        }
    
    def _extract_locations(self, text: str) -> List[str]:
        """Extract Nigerian locations from text"""
        text_lower = text.lower()
        locations = []
        
        # Extract states
        for state in self.nigerian_states:
            if re.search(r'\b' + re.escape(state) + r'\b', text_lower):
                formatted = ' '.join(word.capitalize() for word in state.split())
                locations.append(formatted)
        
        # Extract cities
        for city in self.nigerian_cities:
            if re.search(r'\b' + re.escape(city) + r'\b', text_lower):
                formatted = ' '.join(word.capitalize() for word in city.split())
                if formatted not in locations:
                    locations.append(formatted)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_locations = []
        for loc in locations:
            if loc.lower() not in seen:
                seen.add(loc.lower())
                unique_locations.append(loc)
        
        return unique_locations[:5]  # Limit to 5 locations
    
    def collect_all_feeds(self, hours_back: int = 72, limit_per_feed: int = 20) -> List[Dict]:
        """Collect disaster news from all RSS feeds"""
        all_articles = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        cutoff_timestamp = cutoff_time.timestamp()
        
        logger.info(f"=" * 60)
        logger.info(f"🌊 Collecting disaster news from {len(self.feeds)} feeds...")
        logger.info(f"Looking back {hours_back} hours (since {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')})")
        logger.info(f"=" * 60)
        
        for source_name, feed_info in self.feeds.items():
            if not feed_info.get('active'):
                continue
            
            try:
                logger.info(f"\n📡 Fetching from: {source_name.upper()}")
                
                response = requests.get(feed_info['url'], timeout=20, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code != 200:
                    logger.warning(f"  ⚠️ HTTP {response.status_code} for {source_name}")
                    continue
                
                feed = feedparser.parse(response.content)
                articles_collected = 0
                
                for entry in feed.entries[:limit_per_feed]:
                    article = self._parse_entry(entry, source_name, feed_info)
                    
                    if not article or not article.get('title'):
                        continue
                    
                    # Skip old articles
                    published_ts = article.get('published_timestamp')
                    if published_ts and published_ts < cutoff_timestamp:
                        continue
                    
                    # Filter 1: Must be Nigeria-related
                    if not self._is_nigeria_related(article):
                        continue
                    
                    # Filter 2: Not sports-related
                    if self._is_sports_related(article):
                        logger.debug(f"  🏈 Filtered sports article: {article['title'][:50]}...")
                        continue
                    
                    # Filter 3: Must be disaster-related
                    if not self._is_disaster_related(article):
                        logger.debug(f"  ❌ Not disaster-related: {article['title'][:50]}...")
                        continue
                    
                    # Check for duplicates
                    article_id = self._generate_article_id(article)
                    if article_id in self.seen_articles:
                        continue
                    
                    self.seen_articles.add(article_id)
                    all_articles.append(article)
                    articles_collected += 1
                    
                    logger.info(f"  ✅ [{articles_collected}] {article['title'][:70]}...")
                
                if articles_collected > 0:
                    logger.info(f"  📊 Total from {source_name}: {articles_collected} disaster articles")
                else:
                    logger.info(f"  📊 No disaster articles found in {source_name}")
                
                # Be polite to servers
                time.sleep(random.uniform(1, 1.5))
                
            except requests.exceptions.Timeout:
                logger.error(f"  ❌ Timeout for {source_name}")
                continue
            except requests.exceptions.ConnectionError:
                logger.error(f"  ❌ Connection error for {source_name}")
                continue
            except Exception as e:
                logger.error(f"  ❌ Error collecting from {source_name}: {e}")
                continue
        
        # Sort by published date (newest first)
        all_articles.sort(key=lambda x: x.get('published_timestamp', 0), reverse=True)
        
        logger.info(f"\n" + "=" * 60)
        logger.info(f"✅ TOTAL DISASTER ARTICLES COLLECTED: {len(all_articles)}")
        logger.info(f"📅 Time range: Last {hours_back} hours")
        logger.info("=" * 60)
        
        return all_articles
    
    def collect_disaster_only(self, limit: int = 30) -> List[Dict]:
        """Convenience method - only fetch disaster news"""
        return self.collect_all_feeds(hours_back=72, limit_per_feed=15)[:limit]
    
    def _generate_article_id(self, article: Dict) -> str:
        """Generate unique article ID"""
        unique = f"{article['title']}_{article['link']}_{article['source']}"
        return hashlib.md5(unique.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear seen articles cache"""
        cache_size = len(self.seen_articles)
        self.seen_articles.clear()
        logger.info(f"Cleared article cache ({cache_size} articles)")
    
    def get_feed_status(self) -> Dict:
        """Get status of all feeds"""
        status = {}
        for source_name, feed_info in self.feeds.items():
            status[source_name] = {
                'url': feed_info['url'],
                'active': feed_info.get('active', True),
                'reliability': feed_info.get('reliability', 0.5)
            }
        return status