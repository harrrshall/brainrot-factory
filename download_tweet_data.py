#!/usr/bin/env python3
"""
Twitter/X Link Extraction and Analysis System
A sophisticated tool for extracting Twitter links, capturing screenshots,
and performing comprehensive engagement analysis with anti-bot detection.
"""

import os
import re
import json
import csv
import time
import random
import logging
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urlparse, unquote

# Web scraping and automation
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc
import yaml
# Image processing
from PIL import Image
import base64

# Reporting
from jinja2 import Template

# Utilities
import requests
from fake_useragent import UserAgent
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class TweetData:
    """Data structure for tweet information"""
    tweet_id: str
    url: str
    author_handle: str
    author_name: str
    author_verified: bool
    text: str
    hashtags: List[str]
    mentions: List[str]
    likes: int
    retweets: int
    replies: int
    views: int
    timestamp: str
    media_urls: List[str]
    screenshot_path: str
    categories: List[str]
    engagement_score: float
    viral_potential: str


class TwitterAnalyzer:
    """Main Twitter analysis class with anti-bot detection"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the Twitter analyzer"""
        self.config = self._load_config(config_path)
        self.setup_logging()
        self.setup_directories()
        self.user_agents = UserAgent()
        self.session_cookies = None
        self.request_count = 0
        self.last_request_time = time.time()
        
        # Analysis categories
        self.categories = {
            "knowledge": ["tutorial", "learn", "education", "how-to", "guide", "tip"],
            "controversial": ["debate", "opinion", "politics", "argue", "controversial"],
            "informative": ["news", "update", "report", "breaking", "announcement"],
            "funny": ["lol", "funny", "meme", "joke", "humor", "hilarious"],
            "thoughtprovoking": ["think", "insight", "perspective", "philosophy", "deep"],
            "trending": ["viral", "trending", "hot", "popular", "buzz"],
            "business": ["business", "career", "professional", "industry", "work"],
            "actionable": ["tip", "action", "do", "step", "guide", "how"]
        }
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        default_config = {
            "rate_limiting": {
                "requests_per_minute": 10,
                "min_delay": 2,
                "max_delay": 8
            },
            "screenshot": {
                "width": 1200,
                "height": 800,
                "quality": "high",
                "format": "png"
            },
            "analysis": {
                "sentiment_threshold": 0.1,
                "engagement_weights": {
                    "likes": 1.0,
                    "retweets": 2.0,
                    "replies": 1.5,
                    "views": 0.1
                }
            },
            "proxy": {
                "enabled": False,
                "rotation": True,
                "proxies": []
            }
        }
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        
        return default_config
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = Path("twitter_analysis/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "extraction.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def setup_directories(self):
        """Create directory structure"""
        base_dir = Path("twitter_analysis")
        directories = [
            "screenshots", "data", "logs", "reports",
            "screenshots/knowledge", "screenshots/controversial",
            "screenshots/informative", "screenshots/funny",
            "screenshots/thoughtprovoking", "screenshots/trending",
            "screenshots/business", "screenshots/actionable"
        ]
        
        for directory in directories:
            (base_dir / directory).mkdir(parents=True, exist_ok=True)
    
    def extract_twitter_links(self, input_source: str) -> List[str]:
        """Extract Twitter/X links from various input sources"""
        self.logger.info(f"Extracting Twitter links from: {input_source}")
        
        # Twitter URL patterns
        patterns = [
            r'https?://(?:www\.)?twitter\.com/\w+/status/\d+(?:\?\S*)?',
            r'https?://(?:www\.)?x\.com/\w+/status/\d+(?:\?\S*)?',
            r'https?://(?:mobile\.)?twitter\.com/\w+/status/\d+(?:\?\S*)?',
            r'https?://t\.co/\w+'
        ]
        
        text_content = self._get_text_content(input_source)
        links = []
        
        for pattern in patterns:
            found_links = re.findall(pattern, text_content, re.IGNORECASE)
            links.extend(found_links)
        
        # Expand shortened URLs
        expanded_links = []
        for link in links:
            if 't.co' in link:
                expanded = self._expand_shortened_url(link)
                if expanded:
                    expanded_links.append(expanded)
            else:
                expanded_links.append(link)
        
        unique_links = list(set(expanded_links))
        self.logger.info(f"Extracted {len(unique_links)} unique Twitter links")
        return unique_links
    
    def _get_text_content(self, input_source: str) -> str:
        """Get text content from various input sources"""
        if os.path.isfile(input_source):
            with open(input_source, 'r', encoding='utf-8') as f:
                if input_source.endswith('.csv'):
                    df = pd.read_csv(input_source)
                    return ' '.join(df.astype(str).values.flatten())
                else:
                    return f.read()
        else:
            return input_source
    
    def _expand_shortened_url(self, url: str) -> Optional[str]:
        """Expand shortened URLs"""
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            return response.url
        except Exception as e:
            self.logger.warning(f"Failed to expand URL {url}: {e}")
            return None
    
    def create_stealth_driver(self) -> webdriver.Chrome:
        """Create a stealth Chrome driver with anti-bot detection"""
        options = uc.ChromeOptions()
        
        # Stealth options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Random viewport
        width = random.randint(1200, 1920)
        height = random.randint(800, 1080)
        options.add_argument(f"--window-size={width},{height}")
        
        # User agent rotation
        user_agent = self.user_agents.random
        options.add_argument(f"--user-agent={user_agent}")
        
        # Additional stealth options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        try:
            driver = uc.Chrome(options=options)
            
            # Remove automation indicators
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return driver
        except Exception as e:
            self.logger.error(f"Failed to create stealth driver: {e}")
            raise
    
    def simulate_human_behavior(self, driver: webdriver.Chrome):
        """Simulate human-like behavior"""
        try:
            # Get viewport size
            viewport_width = driver.execute_script("return window.innerWidth;")
            viewport_height = driver.execute_script("return window.innerHeight;")
            
            # Use JavaScript to move mouse instead of ActionChains
            for _ in range(random.randint(2, 5)):
                x = random.randint(0, viewport_width - 1)
                y = random.randint(0, viewport_height - 1)
                driver.execute_script(f"""
                    var event = new MouseEvent('mousemove', {{
                        'view': window,
                        'bubbles': true,
                        'cancelable': true,
                        'clientX': {x},
                        'clientY': {y}
                    }});
                    document.dispatchEvent(event);
                """)
                time.sleep(random.uniform(0.1, 0.3))
            
            # Random scrolling with bounds checking
            scroll_pause_time = random.uniform(0.5, 2.0)
            
            # Scroll to 1/4 of page height
            driver.execute_script("window.scrollTo(0, Math.min(document.body.scrollHeight/4, window.innerHeight));")
            time.sleep(scroll_pause_time)
            
            # Scroll to 1/2 of page height
            driver.execute_script("window.scrollTo(0, Math.min(document.body.scrollHeight/2, window.innerHeight));")
            time.sleep(scroll_pause_time)
            
        except Exception as e:
            self.logger.warning(f"Error in human behavior simulation: {e}")
            # Continue execution even if simulation fails
            pass
    
    def rate_limit_check(self):
        """Check and enforce rate limiting"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        # Check requests per minute
        if self.request_count >= self.config["rate_limiting"]["requests_per_minute"]:
            sleep_time = 60 - time_since_last_request
            if sleep_time > 0:
                self.logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.request_count = 0
        
        # Random delay between requests
        delay = random.uniform(
            self.config["rate_limiting"]["min_delay"],
            self.config["rate_limiting"]["max_delay"]
        )
        time.sleep(delay)
        
        self.request_count += 1
        self.last_request_time = time.time()
    
    def capture_tweet_screenshot(self, driver: webdriver.Chrome, url: str, tweet_id: str) -> str:
        """Capture high-quality screenshot of tweet"""
        try:
            self.rate_limit_check()
            
            # Navigate to tweet
            driver.get(url)
            self.simulate_human_behavior(driver)
            
            # Wait for tweet to load
            wait = WebDriverWait(driver, 15)
            tweet_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
            )
            
            # Scroll tweet into view
            driver.execute_script("arguments[0].scrollIntoView(true);", tweet_element)
            time.sleep(2)
            
            # Take screenshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tweet_{tweet_id}_{timestamp}.png"
            screenshot_dir = Path("twitter_analysis/screenshots")
            screenshot_path = screenshot_dir / filename
            
            # Capture full page screenshot
            driver.save_screenshot(str(screenshot_path))
            
            # Crop to tweet area (optional enhancement)
            self._crop_to_tweet(screenshot_path, tweet_element)
            
            self.logger.info(f"Screenshot saved: {screenshot_path}")
            return str(screenshot_path)
            
        except Exception as e:
            self.logger.error(f"Failed to capture screenshot for {url}: {e}")
            return ""
    
    def _crop_to_tweet(self, screenshot_path: Path, tweet_element):
        """Crop screenshot to focus on tweet content"""
        try:
            # Get element coordinates
            location = tweet_element.location
            size = tweet_element.size
            
            # Open and crop image
            image = Image.open(screenshot_path)
            left = location['x']
            top = location['y']
            right = left + size['width']
            bottom = top + size['height']
            
            cropped_image = image.crop((left, top, right, bottom))
            cropped_image.save(screenshot_path)
            
        except Exception as e:
            self.logger.warning(f"Failed to crop screenshot: {e}")
    
    def extract_tweet_data(self, driver: webdriver.Chrome, url: str) -> Optional[TweetData]:
        """Extract comprehensive tweet data"""
        try:
            self.rate_limit_check()
            
            if url not in driver.current_url:
                driver.get(url)
                self.simulate_human_behavior(driver)
            
            # Wait for tweet to load
            wait = WebDriverWait(driver, 15)
            tweet_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
            )
            
            # Extract tweet ID from URL
            tweet_id = re.search(r'/status/(\d+)', url).group(1)
            
            # Extract author information
            try:
                author_element = driver.find_element(By.CSS_SELECTOR, '[data-testid="User-Name"]')
                author_name = author_element.find_element(By.TAG_NAME, 'span').text
                author_handle = driver.find_element(By.CSS_SELECTOR, '[role="link"] span').text
                author_verified = bool(driver.find_elements(By.CSS_SELECTOR, '[data-testid="icon-verified"]'))
            except:
                author_name = author_handle = "Unknown"
                author_verified = False
            
            # Extract tweet text
            try:
                text_element = driver.find_element(By.CSS_SELECTOR, '[data-testid="tweetText"]')
                text = text_element.text
            except:
                text = ""
            
            # Extract hashtags and mentions
            hashtags = re.findall(r'#\w+', text)
            mentions = re.findall(r'@\w+', text)
            
            # Extract engagement metrics
            likes = self._extract_metric(driver, 'like')
            retweets = self._extract_metric(driver, 'retweet')
            replies = self._extract_metric(driver, 'reply')
            views = self._extract_metric(driver, 'views')
            
            # Extract media URLs
            media_urls = []
            try:
                media_elements = driver.find_elements(By.CSS_SELECTOR, '[data-testid="tweetPhoto"] img')
                media_urls = [elem.get_attribute('src') for elem in media_elements]
            except:
                pass
            
            # Get timestamp
            try:
                time_element = driver.find_element(By.TAG_NAME, 'time')
                timestamp = time_element.get_attribute('datetime')
            except:
                timestamp = datetime.now().isoformat()
            
            # Capture screenshot
            screenshot_path = self.capture_tweet_screenshot(driver, url, tweet_id)
            
            # Create tweet data object
            tweet_data = TweetData(
                tweet_id=tweet_id,
                url=url,
                author_handle=author_handle,
                author_name=author_name,
                author_verified=author_verified,
                text=text,
                hashtags=hashtags,
                mentions=mentions,
                likes=likes,
                retweets=retweets,
                replies=replies,
                views=views,
                timestamp=timestamp,
                media_urls=media_urls,
                screenshot_path=screenshot_path,
                categories=[],
                engagement_score=0.0,
                viral_potential="Low"
            )
            
            self.logger.info(f"Extracted data for tweet: {tweet_id}")
            return tweet_data
            
        except Exception as e:
            self.logger.error(f"Failed to extract tweet data from {url}: {e}")
            return None
    
    def _extract_metric(self, driver: webdriver.Chrome, metric_type: str) -> int:
        """Extract engagement metrics from tweet"""
        try:
            selectors = {
                'like': '[data-testid="like"] span',
                'retweet': '[data-testid="retweet"] span', 
                'reply': '[data-testid="reply"] span',
                'views': '[role="group"] span[dir="ltr"]'
            }
            
            elements = driver.find_elements(By.CSS_SELECTOR, selectors.get(metric_type, ''))
            for element in elements:
                text = element.text
                if text and any(char.isdigit() for char in text):
                    # Convert abbreviated numbers (1.2K, 5.6M, etc.)
                    return self._parse_metric_number(text)
            return 0
        except:
            return 0
    
    def _parse_metric_number(self, text: str) -> int:
        """Parse metric numbers with K/M abbreviations"""
        text = text.replace(',', '').strip()
        if 'K' in text:
            return int(float(text.replace('K', '')) * 1000)
        elif 'M' in text:
            return int(float(text.replace('M', '')) * 1000000)
        elif text.isdigit():
            return int(text)
        return 0
    
    def analyze_tweet(self, tweet_data: TweetData) -> TweetData:
        """Perform comprehensive tweet analysis"""
        # Categorize tweet
        tweet_data.categories = self._categorize_tweet(tweet_data.text)
        
        # Calculate engagement score
        tweet_data.engagement_score = self._calculate_engagement_score(tweet_data)
        
        # Determine viral potential
        tweet_data.viral_potential = self._assess_viral_potential(tweet_data)
        
        # Move screenshot to appropriate category folder
        if tweet_data.categories and tweet_data.screenshot_path:
            self._organize_screenshot(tweet_data)
        
        return tweet_data
    
    def _categorize_tweet(self, text: str) -> List[str]:
        """Categorize tweet content"""
        text_lower = text.lower()
        categories = []
        
        for category, keywords in self.categories.items():
            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)
        
        return categories if categories else ["general"]
    
    def _calculate_engagement_score(self, tweet_data: TweetData) -> float:
        """Calculate weighted engagement score"""
        weights = self.config["analysis"]["engagement_weights"]
        
        score = (
            tweet_data.likes * weights["likes"] +
            tweet_data.retweets * weights["retweets"] +
            tweet_data.replies * weights["replies"] +
            tweet_data.views * weights["views"]
        )
        
        return round(score, 2)
    
    def _assess_viral_potential(self, tweet_data: TweetData) -> str:
        """Assess viral potential based on various factors"""
        score = 0
        
        # Engagement rate
        total_engagement = tweet_data.likes + tweet_data.retweets + tweet_data.replies
        if total_engagement > 1000:
            score += 3
        elif total_engagement > 100:
            score += 2
        elif total_engagement > 10:
            score += 1
        
        # Content factors
        if len(tweet_data.hashtags) >= 2:
            score += 1
        if len(tweet_data.mentions) >= 1:
            score += 1
        if tweet_data.media_urls:
            score += 2
            
        # Determine potential
        if score >= 6:
            return "High"
        elif score >= 3:
            return "Medium"
        else:
            return "Low"
    
    def _organize_screenshot(self, tweet_data: TweetData):
        """Move screenshot to appropriate category folder"""
        if not tweet_data.screenshot_path or not os.path.exists(tweet_data.screenshot_path):
            return
        
        category = tweet_data.categories[0] if tweet_data.categories else "general"
        
        # Create date folder
        date_str = datetime.now().strftime("%Y-%m-%d")
        category_dir = Path(f"twitter_analysis/screenshots/{date_str}/{category}")
        category_dir.mkdir(parents=True, exist_ok=True)
        
        # Move file
        old_path = Path(tweet_data.screenshot_path)
        new_path = category_dir / old_path.name
        
        try:
            old_path.rename(new_path)
            tweet_data.screenshot_path = str(new_path)
        except Exception as e:
            self.logger.warning(f"Failed to move screenshot: {e}")
    
    def process_tweets(self, urls: List[str]) -> List[TweetData]:
        """Process multiple tweets with batch processing"""
        self.logger.info(f"Processing {len(urls)} tweets")
        
        processed_tweets = []
        failed_urls = []
        
        driver = None
        try:
            driver = self.create_stealth_driver()
            
            for i, url in enumerate(urls, 1):
                self.logger.info(f"Processing tweet {i}/{len(urls)}: {url}")
                
                try:
                    tweet_data = self.extract_tweet_data(driver, url)
                    if tweet_data:
                        analyzed_tweet = self.analyze_tweet(tweet_data)
                        processed_tweets.append(analyzed_tweet)
                    else:
                        failed_urls.append(url)
                        
                except Exception as e:
                    self.logger.error(f"Failed to process {url}: {e}")
                    failed_urls.append(url)
                
                # Progress update
                if i % 10 == 0:
                    self.logger.info(f"Processed {i}/{len(urls)} tweets")
        
        finally:
            if driver:
                driver.quit()
        
        # Log failed URLs
        if failed_urls:
            self._log_failed_urls(failed_urls)
        
        self.logger.info(f"Successfully processed {len(processed_tweets)} tweets")
        return processed_tweets
    
    def _log_failed_urls(self, failed_urls: List[str]):
        """Log failed URLs to file"""
        failed_file = Path("twitter_analysis/logs/failed_urls.txt")
        with open(failed_file, 'a') as f:
            f.write(f"\n--- {datetime.now().isoformat()} ---\n")
            for url in failed_urls:
                f.write(f"{url}\n")
    
    def save_data(self, tweets: List[TweetData]):
        """Save processed data in multiple formats"""
        data_dir = Path("twitter_analysis/data")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw JSON
        json_path = data_dir / f"raw_tweets_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump([asdict(tweet) for tweet in tweets], f, indent=2, ensure_ascii=False)
        
        # Save CSV
        csv_path = data_dir / f"analyzed_tweets_{timestamp}.csv"
        df = pd.DataFrame([asdict(tweet) for tweet in tweets])
        df.to_csv(csv_path, index=False)
        
        # Save engagement report
        report_data = self._generate_engagement_report(tweets)
        report_path = data_dir / f"engagement_report_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Data saved: JSON({json_path}), CSV({csv_path}), Report({report_path})")
    
    def _generate_engagement_report(self, tweets: List[TweetData]) -> Dict:
        """Generate comprehensive engagement report"""
        if not tweets:
            return {}
        
        total_tweets = len(tweets)
        total_likes = sum(t.likes for t in tweets)
        total_retweets = sum(t.retweets for t in tweets)
        total_replies = sum(t.replies for t in tweets)
        
        # Category breakdown
        category_stats = {}
        for tweet in tweets:
            for category in tweet.categories:
                if category not in category_stats:
                    category_stats[category] = {
                        "count": 0,
                        "total_likes": 0,
                        "total_retweets": 0,
                        "avg_engagement": 0
                    }
                
                category_stats[category]["count"] += 1
                category_stats[category]["total_likes"] += tweet.likes
                category_stats[category]["total_retweets"] += tweet.retweets
        
        # Calculate averages
        for category in category_stats:
            count = category_stats[category]["count"]
            category_stats[category]["avg_engagement"] = (
                category_stats[category]["total_likes"] + 
                category_stats[category]["total_retweets"]
            ) / count
        
        # Top tweets
        top_tweets = sorted(tweets, key=lambda x: x.engagement_score, reverse=True)[:10]
        
        return {
            "summary": {
                "total_tweets": total_tweets,
                "total_likes": total_likes,
                "total_retweets": total_retweets,
                "total_replies": total_replies,
                "avg_likes": total_likes / total_tweets,
                "avg_retweets": total_retweets / total_tweets,
                "processing_date": datetime.now().isoformat()
            },
            "category_breakdown": category_stats,
            "viral_potential_distribution": {
                "high": len([t for t in tweets if t.viral_potential == "High"]),
                "medium": len([t for t in tweets if t.viral_potential == "Medium"]),
                "low": len([t for t in tweets if t.viral_potential == "Low"])
            },
            "top_tweets": [
                {
                    "tweet_id": t.tweet_id,
                    "text": t.text[:100] + "..." if len(t.text) > 100 else t.text,
                    "engagement_score": t.engagement_score,
                    "viral_potential": t.viral_potential
                }
                for t in top_tweets
            ]
        }
    
    def generate_html_report(self, tweets: List[TweetData]):
        """Generate comprehensive HTML report"""
        if not tweets:
            return
        
        # HTML template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Twitter Analysis Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background-color: #1da1f2; color: white; padding: 20px; border-radius: 10px; }
                .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
                .metric { display: inline-block; margin: 10px; padding: 10px; background-color: #f8f9fa; border-radius: 5px; }
                .tweet { border-left: 3px solid #1da1f2; padding: 10px; margin: 10px 0; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Twitter Analysis Report</h1>
                <p>Generated on {{ date }}</p>
            </div>
            
            <div class="section">
                <h2>Executive Summary</h2>
                <div class="metric">
                    <strong>Total Tweets:</strong> {{ summary.total_tweets }}
                </div>
                <div class="metric">
                    <strong>Total Engagement:</strong> {{ summary.total_likes + summary.total_retweets + summary.total_replies }}
                </div>
                <div class="metric">
                    <strong>Avg Likes:</strong> {{ "%.1f"|format(summary.avg_likes) }}
                </div>
                <div class="metric">
                    <strong>Avg Retweets:</strong> {{ "%.1f"|format(summary.avg_retweets) }}
                </div>
            </div>
            
            <div class="section">
                <h2>Category Breakdown</h2>
                {% for category, stats in category_breakdown.items() %}
                <div class="metric">
                    <strong>{{ category.title() }}:</strong> {{ stats.count }} tweets (Avg Engagement: {{ "%.1f"|format(stats.avg_engagement) }})
                </div>
                {% endfor %}
            </div>
            
            <div class="section">
                <h2>Viral Potential Distribution</h2>
                <div class="metric">
                    <strong>High:</strong> {{ viral_potential.high }}
                </div>
                <div class="metric">
                    <strong>Medium:</strong> {{ viral_potential.medium }}
                </div>
                <div class="metric">
                    <strong>Low:</strong> {{ viral_potential.low }}
                </div>
            </div>
            
            <div class="section">
                <h2>Top Performing Tweets</h2>
                {% for tweet in top_tweets[:5] %}
                <div class="tweet">
                    <p><strong>Tweet ID:</strong> {{ tweet.tweet_id }}</p>
                    <p><strong>Text:</strong> {{ tweet.text }}</p>
                    <p><strong>Engagement Score:</strong> {{ tweet.engagement_score }}</p>
                    <p><strong>Viral Potential:</strong> {{ tweet.viral_potential }}</p>
                </div>
                {% endfor %}
            </div>
        </body>
        </html>
        """
        
        # Generate report data
        report_data = self._generate_engagement_report(tweets)
        
        # Render template
        template = Template(html_template)
        html_content = template.render(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary=report_data["summary"],
            category_breakdown=report_data["category_breakdown"],
            viral_potential=report_data["viral_potential_distribution"],
            top_tweets=report_data["top_tweets"]
        )
        
        # Save HTML report
        report_dir = Path("twitter_analysis/reports")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = report_dir / f"analysis_report_{timestamp}.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"HTML report generated: {html_path}")
    
    def run_analysis(self, input_source: str):
        """Main method to run the complete analysis"""
        self.logger.info("Starting Twitter analysis")
        
        try:
            # Extract Twitter links
            urls = self.extract_twitter_links(input_source)
            if not urls:
                self.logger.warning("No Twitter links found in input")
                return
            
            # Process tweets
            tweets = self.process_tweets(urls)
            if not tweets:
                self.logger.warning("No tweets were successfully processed")
                return
            
            # Save data
            self.save_data(tweets)
            
            # Generate reports
            self.generate_html_report(tweets)
            
            # Print summary
            self._print_summary(tweets)
            
            self.logger.info("Analysis completed successfully")
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise
    
    def _print_summary(self, tweets: List[TweetData]):
        """Print analysis summary to console"""
        print("\n" + "="*50)
        print("TWITTER ANALYSIS SUMMARY")
        print("="*50)
        
        if not tweets:
            print("No tweets processed.")
            return
        
        total_tweets = len(tweets)
        total_engagement = sum(t.likes + t.retweets + t.replies for t in tweets)
        
        print(f"Total Tweets Processed: {total_tweets}")
        print(f"Total Engagement: {total_engagement:,}")
        print(f"Average Engagement: {total_engagement/total_tweets:.1f}")
        
        # Category breakdown
        categories = {}
        for tweet in tweets:
            for category in tweet.categories:
                categories[category] = categories.get(category, 0) + 1
        
        print(f"\nCategory Breakdown:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {category.title()}: {count}")
        
        # Viral potential
        viral_high = len([t for t in tweets if t.viral_potential == "High"])
        viral_medium = len([t for t in tweets if t.viral_potential == "Medium"])
        viral_low = len([t for t in tweets if t.viral_potential == "Low"])
        
        print(f"\nViral Potential:")
        print(f"  High: {viral_high}")
        print(f"  Medium: {viral_medium}")
        print(f"  Low: {viral_low}")
        
        # Top tweet
        top_tweet = max(tweets, key=lambda x: x.engagement_score)
        print(f"\nTop Performing Tweet:")
        print(f"  ID: {top_tweet.tweet_id}")
        print(f"  Engagement Score: {top_tweet.engagement_score}")
        print(f"  Text: {top_tweet.text[:100]}...")
        
        print("="*50)


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Twitter Link Extraction and Analysis Tool")
    parser.add_argument("input", help="Input source (file path or direct text)")
    parser.add_argument("--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize analyzer
    analyzer = TwitterAnalyzer(args.config)
    
    # Run analysis
    analyzer.run_analysis(args.input)


if __name__ == "__main__":
    main()