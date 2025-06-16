#!/usr/bin/env python3
"""
Twitter TTS Narration Generator
Processes Twitter data from JSON files and generates TTS-ready narration scripts.
"""

import json
import re
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/tts_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class NarrationConfig:
    """Configuration for narration generation"""
    min_engagement_score: float = 0
    min_likes: int = 0
    min_retweets: int = 0
    max_text_length: int = 2800
    include_author_name: bool = True
    default_style: str = "casual"
    output_dir: str = "twitter_analysis/narrations"
    
    # Narration styles and their descriptions
    styles: Dict[str, str] = None
    
    def __post_init__(self):
        if self.styles is None:
            self.styles = {
                "casual": "conversational and friendly",
                "dramatic": "exciting and engaging",
                "analytical": "professional and informative",
                "news": "formal news reporting style",
                "commentary": "opinion and discussion focused"
            }

@dataclass
class TweetData:
    """Structured tweet data"""
    tweet_id: str
    author_name: str
    author_handle: str
    text: str
    likes: int
    retweets: int
    replies: int
    views: int
    engagement_score: float
    viral_potential: str
    timestamp: str
    categories: List[str]
    hashtags: List[str]
    mentions: List[str]

@dataclass
class NarrationScript:
    """Generated narration script"""
    tweet_id: str
    author_name: str
    original_text: str
    cleaned_text: str
    narration_text: str
    style: str
    engagement_context: str
    duration_estimate: int
    metadata: Dict

class TwitterTTSGenerator:
    """Main class for generating TTS narration scripts from Twitter data"""
    
    def __init__(self, config: Optional[NarrationConfig] = None):
        self.narration_config = config or NarrationConfig()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            self.narration_config.output_dir,
            "logs"
        ]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def load_tweets_from_json(self, file_path: str) -> List[TweetData]:
        """Load and parse tweets from JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                raw_data = json.load(file)
            
            tweets = []
            for tweet_raw in raw_data:
                try:
                    tweet = TweetData(
                        tweet_id=tweet_raw.get('tweet_id', ''),
                        author_name=tweet_raw.get('author_name', ''),
                        author_handle=tweet_raw.get('author_handle', ''),
                        text=tweet_raw.get('text', ''),
                        likes=tweet_raw.get('likes', 0),
                        retweets=tweet_raw.get('retweets', 0),
                        replies=tweet_raw.get('replies', 0),
                        views=tweet_raw.get('views', 0),
                        engagement_score=tweet_raw.get('engagement_score', 0),
                        viral_potential=tweet_raw.get('viral_potential', 'Low'),
                        timestamp=tweet_raw.get('timestamp', ''),
                        categories=tweet_raw.get('categories', []),
                        hashtags=tweet_raw.get('hashtags', []),
                        mentions=tweet_raw.get('mentions', [])
                    )
                    tweets.append(tweet)
                except Exception as e:
                    logger.error(f"Error parsing tweet: {e}")
                    continue
            
            logger.info(f"Loaded {len(tweets)} tweets from {file_path}")
            return tweets
            
        except Exception as e:
            logger.error(f"Error loading tweets from {file_path}: {e}")
            return []
    
    def filter_tweets(self, tweets: List[TweetData]) -> List[TweetData]:
        """Filter tweets based on engagement thresholds"""
        filtered = []
        
        for tweet in tweets:
            # Check engagement thresholds
            if (tweet.engagement_score >= self.narration_config.min_engagement_score or
                tweet.likes >= self.narration_config.min_likes or
                tweet.retweets >= self.narration_config.min_retweets):
                
                # Check text length
                if len(tweet.text) <= self.narration_config.max_text_length:
                    filtered.append(tweet)
        
        logger.info(f"Filtered {len(filtered)} tweets from {len(tweets)} total")
        return filtered
    
    def clean_text_for_tts(self, text: str) -> str:
        """Clean and sanitize tweet text for TTS"""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Handle mentions - convert @username to "at username"
        text = re.sub(r'@(\w+)', r'at \1', text)
        
        # Handle hashtags - remove # but keep the word
        text = re.sub(r'#(\w+)', r'\1', text)
        
        # Remove special characters that might cause TTS issues
        text = re.sub(r'[^\w\s.,!?;:\'-]', ' ', text)
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def get_engagement_context(self, tweet: TweetData) -> str:
        """Generate engagement context phrases based on metrics"""
        if tweet.viral_potential == "High":
            return "This is absolutely blowing up"
        elif tweet.viral_potential == "Medium":
            return "This is getting some serious attention"
        elif tweet.engagement_score > 1000:
            return "People are really talking about this"
        elif tweet.engagement_score > 500:
            return "This is gaining traction"
        elif tweet.likes > 200:
            return "This caught people's attention"
        else:
            return "This got some engagement"
    
    def generate_narration_templates(self, tweet: TweetData, style: str = "casual") -> str:
        """Generate narration text based on style"""
        author = tweet.author_name if (self.narration_config.include_author_name and tweet.author_name) else "this person"
        if not tweet.author_name or tweet.author_name.lower() == "log in":
            author = "this person"
        
        cleaned_text = self.clean_text_for_tts(tweet.text)
        engagement_context = self.get_engagement_context(tweet)
        
        templates = {
            "casual": f"Hey there, {author} just posted something that's getting attention. Here's what they said: {cleaned_text}. {engagement_context}.",
            
            "dramatic": f"Breaking! {author} just dropped this bombshell on Twitter: {cleaned_text}. {engagement_context.lower()}!",
            
            "analytical": f"Analyzing a recent tweet from {author}: {cleaned_text}.  {engagement_context.lower()}.",
            
            "news": f"In social media news, {author} shared: {cleaned_text}. Suggesting {engagement_context.lower()}.",
            
            "commentary": f"So {author} decided to share their thoughts: {cleaned_text}. What do you think about this take?"
        }
        
        return templates.get(style, templates["casual"])
    
    def estimate_duration(self, text: str) -> int:
        """Estimate TTS duration in seconds (roughly 150 words per minute)"""
        word_count = len(text.split())
        duration = int((word_count / 150) * 60) + 2  # Add 2 seconds buffer
        return max(duration, 5)  # Minimum 5 seconds
    
    def generate_narration_script(self, tweet: TweetData, style: str = "casual") -> NarrationScript:
        """Generate complete narration script for a tweet"""
        cleaned_text = self.clean_text_for_tts(tweet.text)
        narration_text = self.generate_narration_templates(tweet, style)
        engagement_context = self.get_engagement_context(tweet)
        duration_estimate = self.estimate_duration(narration_text)
        
        metadata = {
            "original_engagement_score": tweet.engagement_score,
            "viral_potential": tweet.viral_potential,
            "categories": tweet.categories,
            "timestamp": tweet.timestamp,
            "author_handle": tweet.author_handle,
            "word_count": len(narration_text.split()),
            "character_count": len(narration_text)
        }
        
        return NarrationScript(
            tweet_id=tweet.tweet_id,
            author_name=tweet.author_name,
            original_text=tweet.text,
            cleaned_text=cleaned_text,
            narration_text=narration_text,
            style=style,
            engagement_context=engagement_context,
            duration_estimate=duration_estimate,
            metadata=metadata
        )
    
    def process_tweets_batch(self, tweets: List[TweetData], style: str = None) -> List[NarrationScript]:
        """Process multiple tweets and generate narration scripts"""
        if style is None:
            style = self.narration_config.default_style
        
        scripts = []
        
        for tweet in tweets:
            try:
                script = self.generate_narration_script(tweet, style)
                scripts.append(script)
            except Exception as e:
                logger.error(f"Error generating script for tweet {tweet.tweet_id}: {e}")
                continue
        
        logger.info(f"Generated {len(scripts)} narration scripts")
        return scripts
    
    def save_narration_scripts(self, scripts: List[NarrationScript], output_file: str = None) -> str:
        """Save narration scripts to JSON file"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{self.narration_config.output_dir}/narration_scripts_{timestamp}.json"
        
        # Convert scripts to dictionaries for JSON serialization
        scripts_data = []
        for script in scripts:
            script_dict = {
                "tweet_id": script.tweet_id,
                "author_name": script.author_name,
                "original_text": script.original_text,
                "cleaned_text": script.cleaned_text,
                "narration_text": script.narration_text,
                "style": script.style,
                "engagement_context": script.engagement_context,
                "duration_estimate": script.duration_estimate,
                "metadata": script.metadata
            }
            scripts_data.append(script_dict)
        
        try:
            with open(output_file, 'w', encoding='utf-8') as file:
                json.dump(scripts_data, file, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(scripts)} narration scripts to {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Error saving narration scripts: {e}")
            raise
    
    def generate_summary_report(self, scripts: List[NarrationScript]) -> Dict:
        """Generate summary report of narration scripts"""
        if not scripts:
            return {}
        
        total_duration = sum(script.duration_estimate for script in scripts)
        styles_count = {}
        viral_potential_count = {}
        
        for script in scripts:
            styles_count[script.style] = styles_count.get(script.style, 0) + 1
            viral_potential = script.metadata.get('viral_potential', 'Unknown')
            viral_potential_count[viral_potential] = viral_potential_count.get(viral_potential, 0) + 1
        
        report = {
            "total_scripts": len(scripts),
            "total_estimated_duration_minutes": round(total_duration / 60, 2),
            "average_duration_seconds": round(total_duration / len(scripts), 2),
            "styles_breakdown": styles_count,
            "viral_potential_breakdown": viral_potential_count,
            "generated_at": datetime.now().isoformat()
        }
        
        return report

def main():
    """Main execution function"""
    # Set up command line arguments
    parser = argparse.ArgumentParser(description="Generate TTS narration scripts from Twitter data")
    parser.add_argument("--style", type=str, default="casual",
                      choices=["casual", "dramatic", "analytical", "news", "commentary"],
                      help="Narration style to use (default: casual)")
    args = parser.parse_args()
    
    # Initialize generator with custom configuration
    custom_config = NarrationConfig(
        min_engagement_score=50,  # Lower threshold for more tweets
        min_likes=25,
        min_retweets=5,
        include_author_name=True,
        default_style=args.style
    )
    generator = TwitterTTSGenerator(config=custom_config)
    
    # Find the most recent raw tweets file
    data_dir = Path("twitter_analysis/data")
    if not data_dir.exists():
        print("twitter_analysis/data directory not found. Please check your file structure.")
        return
    
    # Look for raw_tweets_*.json files
    tweet_files = list(data_dir.glob("raw_tweets_*.json"))
    
    if not tweet_files:
        print("No raw_tweets_*.json files found in twitter_analysis/data/")
        return
    
    # Process the most recent file
    latest_file = max(tweet_files, key=os.path.getctime)
    print(f"Processing file: {latest_file}")
    
    # Load tweets
    tweets = generator.load_tweets_from_json(str(latest_file))
    
    if not tweets:
        print("No tweets loaded. Please check your input file.")
        return
    
    # Filter tweets
    filtered_tweets = generator.filter_tweets(tweets)
    
    if not filtered_tweets:
        print("No tweets passed the filtering criteria.")
        return
    
    # Generate narration scripts with specified style
    scripts = generator.process_tweets_batch(filtered_tweets, args.style)
    
    # Save scripts
    output_file = generator.save_narration_scripts(scripts)
    
    # Generate and display summary
    summary = generator.generate_summary_report(scripts)
    print("\n=== Narration Generation Summary ===")
    print(f"Total scripts generated: {summary.get('total_scripts', 0)}")
    print(f"Total estimated duration: {summary.get('total_estimated_duration_minutes', 0)} minutes")
    print(f"Average script duration: {summary.get('average_duration_seconds', 0)} seconds")
    print(f"Narration style: {args.style}")
    print(f"Output file: {output_file}")
    
    # Save summary report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    summary_file = f"twitter_analysis/reports/narration_summary_{timestamp}.json"
    Path("twitter_analysis/reports").mkdir(parents=True, exist_ok=True)
    
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"Summary report saved to: {summary_file}")

if __name__ == "__main__":
    main()