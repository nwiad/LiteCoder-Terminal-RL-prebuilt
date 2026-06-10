#!/usr/bin/env python3
"""
Setup script for Reddit Community Toxicity Analyzer task.
Prepares the starting context by downloading a sample of Reddit comments data.
"""

import os
import json
import ssl
import random
import time
import urllib.request
import urllib.error
import urllib.parse


def create_directories():
    """Create necessary directories for the project."""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'raw')
    os.makedirs(data_dir, exist_ok=True)
    print(f"Created directory: {data_dir}")
    return data_dir


def fetch_reddit_comments(subreddit, limit=200, before=None):
    """
    Fetch comments from a subreddit using the Pushshift API.
    Uses only standard library - no external dependencies required.
    """
    base_url = "https://api.pushshift.io/reddit/search/comment/"
    params = {
        'subreddit': subreddit,
        'size': limit,
        'sort': 'desc',
        'sort_type': 'created_utc'
    }
    if before:
        params['before'] = before
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        request = urllib.request.Request(url)
        request.add_header('User-Agent', 'RedditToxicityAnalyzer/1.0')
        
        with urllib.request.urlopen(request, context=context, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('data', [])
    except Exception as e:
        print(f"  Warning: Failed to fetch from r/{subreddit}: {e}")
        return []


def generate_synthetic_comments(output_path, target_sample_size=500):
    """
    Generate realistic synthetic Reddit comments for toxicity analysis.
    These comments simulate real Reddit content from various subreddits.
    """
    subreddits = [
        'news', 'worldnews', 'politics', 'sports', 'gaming',
        'technology', 'science', 'AskReddit', 'relationship_advice',
        'AmITheWrong', 'confessions', 'unpopularopinion', 'TrueReddit'
    ]
    
    # Realistic comment templates simulating different toxicity levels
    nontoxic_comments = [
        "Great point! I've been thinking about this topic for a while.",
        "Thanks for sharing this information. It's really helpful.",
        "I completely agree with your analysis. Well reasoned.",
        "This is fascinating. Do you have any sources to back this up?",
        "I've had a similar experience. It really changed my perspective.",
        "Congratulations on your achievement! You deserve it.",
        "This is exactly what I was looking for. Very informative.",
        "I appreciate you taking the time to write this out.",
        "Interesting perspective. I hadn't considered that angle before.",
        "The data you presented here is quite compelling.",
        "This made my day! So grateful for communities like this.",
        "Well said. I think more people should understand this.",
        "Thank you for the clear explanation. Much appreciated.",
        "This is a really important topic that deserves more attention.",
        "I've learned something new today. Thanks!",
        "Your dedication to this topic is inspiring.",
        "Great discussion everyone. Very enlightening.",
        "I can relate to this on a personal level.",
        "This is a thoughtful analysis of a complex issue.",
        "Thanks for the recommendation! I'll check it out.",
    ]
    
    mildly_toxic_comments = [
        "I don't think that's quite right. Here's why...",
        "While I see your point, I disagree with the conclusion.",
        "This is a bit misleading without more context.",
        "I think you're oversimplifying a complex issue.",
        "Have you considered the opposite perspective?",
        "I'm skeptical of these claims without more evidence.",
        "This seems like a biased take on the situation.",
        "I understand where you're coming from, but...",
        "The argument has some logical flaws.",
        "This is not the whole picture. There's more to it.",
        "Your source might not be entirely reliable on this.",
        "I respectfully disagree with this assessment.",
        "This ignores some important factors.",
        "The reasoning here is flawed in several ways.",
        "I'd like to see more data before drawing conclusions.",
    ]
    
    moderately_toxic_comments = [
        "This is honestly one of the dumbest takes I've seen.",
        "Are you seriously defending this? It's ridiculous.",
        "You're completely wrong and here's why...",
        "I can't believe people actually think this way.",
        "This is garbage and anyone who believes it is naive.",
        "Stop spreading this misinformation. It's harmful.",
        "Honestly, this is why we can't have nice things.",
        "What a terrible argument. Do some research.",
        "This is the most absurd thing I've read today.",
        "You clearly don't understand what you're talking about.",
        "This is why people think [group] are idiots.",
        "What an absolutely stupid thing to say.",
        "I'm done arguing with people who refuse to see reason.",
        "This is exactly what's wrong with society today.",
        "Your ignorance is truly remarkable.",
    ]
    
    very_toxic_comments = [
        "You're a complete idiot. Delete your account.",
        "This is garbage. You should be ashamed of yourself.",
        "Nobody cares about your worthless opinion.",
        "You're such a troll. Go away.",
        "This is the dumbest thing I've ever read. Seriously.",
        "You're a piece of trash with nothing valuable to say.",
        "What a pathetic attempt at an argument. Embarrassing.",
        "Kill this thread. It's worthless.",
        "You're one of the worst examples of humanity.",
        "This is absolute trash. Nothing more.",
        "I have zero respect for anyone who thinks like this.",
        "Delete this. It's harmful and stupid.",
        "You're the reason this community is terrible.",
        "What a loser. Get a life.",
        "This is why [group] should be banned from the internet.",
    ]
    
    def create_comment(subreddit, body, score):
        """Create a comment record with realistic metadata."""
        comment_id = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
        return {
            'id': comment_id,
            'subreddit': subreddit,
            'author': f'User{random.randint(10000, 99999)}',
            'body': body,
            'created_utc': int(time.time()) - random.randint(0, 365 * 24 * 60 * 60),
            'score': score,
            'permalink': f'/r/{subreddit}/comments/{comment_id}'
        }
    
    all_comments = []
    comments_per_subreddit = target_sample_size // len(subreddits)
    
    print("Generating synthetic Reddit comments...")
    
    for subreddit in subreddits:
        comments = []
        # Generate a mix of toxicity levels for each subreddit
        # Distribution: 50% non-toxic, 25% mildly toxic, 15% moderately toxic, 10% very toxic
        for _ in range(comments_per_subreddit):
            toxicity_level = random.random()
            if toxicity_level < 0.50:
                body = random.choice(nontoxic_comments)
                score = random.randint(1, 500)
            elif toxicity_level < 0.75:
                body = random.choice(mildly_toxic_comments)
                score = random.randint(-50, 50)
            elif toxicity_level < 0.90:
                body = random.choice(moderately_toxic_comments)
                score = random.randint(-100, -10)
            else:
                body = random.choice(very_toxic_comments)
                score = random.randint(-500, -50)
            
            comments.append(create_comment(subreddit, body, score))
        
        all_comments.extend(comments)
        print(f"  Generated {len(comments)} comments from r/{subreddit}")
    
    # Shuffle all comments
    random.shuffle(all_comments)
    
    # Limit to target sample size
    if len(all_comments) > target_sample_size:
        all_comments = all_comments[:target_sample_size]
    
    print(f"\nTotal comments generated: {len(all_comments)}")
    
    # Save to JSONL format
    with open(output_path, 'w', encoding='utf-8') as f:
        for comment in all_comments:
            f.write(json.dumps(comment, ensure_ascii=False) + '\n')
    
    print(f"Saved comments to: {output_path}")
    return len(all_comments)


def download_reddit_comments_sample(output_path, target_sample_size=500):
    """
    Try to download real Reddit comments, fall back to synthetic data if API fails.
    """
    # First, try to fetch real data
    subreddits = [
        'news', 'worldnews', 'politics', 'sports', 'gaming',
        'technology', 'science', 'AskReddit', 'relationship_advice',
        'AmITheWrong', 'confessions', 'unpopularopinion', 'TrueReddit'
    ]
    
    all_comments = []
    comments_per_subreddit = target_sample_size // len(subreddits)
    
    print(f"Attempting to download Reddit comments from {len(subreddits)} subreddits...")
    
    api_success = False
    for i, subreddit in enumerate(subreddits):
        print(f"  [{i+1}/{len(subreddits)}] Fetching from r/{subreddit}...")
        comments = fetch_reddit_comments(subreddit, limit=comments_per_subreddit + 50)
        
        if comments:
            api_success = True
            # Filter to only include comments with body text
            valid_comments = [
                c for c in comments
                if c.get('body') and c.get('body') != '[removed]' and c.get('body') != '[deleted]'
            ][:comments_per_subreddit]
            
            all_comments.extend(valid_comments)
            print(f"    Retrieved {len(valid_comments)} valid comments")
        else:
            print(f"    No comments retrieved")
        
        # Small delay to be respectful to the API
        time.sleep(0.3)
    
    if api_success and len(all_comments) >= target_sample_size * 0.5:
        # Limit to target sample size
        if len(all_comments) > target_sample_size:
            random.shuffle(all_comments)
            all_comments = all_comments[:target_sample_size]
        
        print(f"\nTotal comments collected: {len(all_comments)}")
        
        # Save to JSONL format
        with open(output_path, 'w', encoding='utf-8') as f:
            for comment in all_comments:
                # Extract relevant fields for the toxicity analysis task
                record = {
                    'id': comment.get('id'),
                    'subreddit': comment.get('subreddit'),
                    'author': comment.get('author'),
                    'body': comment.get('body'),
                    'created_utc': comment.get('created_utc'),
                    'score': comment.get('score'),
                    'permalink': comment.get('permalink')
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        print(f"Saved comments to: {output_path}")
        return len(all_comments)
    else:
        # Fall back to synthetic data
        print("\nAPI unavailable or insufficient data. Generating synthetic comments...")
        return generate_synthetic_comments(output_path, target_sample_size)


def main():
    """Main setup function."""
    print("=" * 60)
    print("Reddit Community Toxicity Analyzer - Setup Script")
    print("=" * 60)
    print()
    
    # Step 1: Create directories
    print("Step 1: Creating project directory structure...")
    data_dir = create_directories()
    print()
    
    # Step 2: Download Reddit comments dataset
    print("Step 2: Downloading Reddit comments dataset...")
    output_path = os.path.join(data_dir, 'reddit_comments.jsonl')
    
    try:
        comment_count = download_reddit_comments_sample(output_path, target_sample_size=500)
        
        if comment_count > 0:
            print(f"\n{'=' * 60}")
            print(f"Setup Complete!")
            print(f"{'=' * 60}")
            print(f"Dataset: {output_path}")
            print(f"Comments: {comment_count}")
            print()
            print("The agent can now proceed with the Reddit toxicity analysis task.")
            print("Next steps for the agent:")
            print("  1. Explore and preprocess the comments data")
            print("  2. Train a toxicity classification model")
            print("  3. Analyze toxicity patterns by subreddit")
            print("  4. Generate visualizations and reports")
        else:
            print("\nWarning: No comments were downloaded. The setup may be incomplete.")
            print("Please check network connectivity and try again.")
            
    except Exception as e:
        print(f"\nError during dataset download: {e}")
        raise


if __name__ == '__main__':
    main()
