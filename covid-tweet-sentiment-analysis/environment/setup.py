#!/usr/bin/env python3
"""
Setup script for Twitter Sentiment Analysis on COVID-19 Dataset.

This script prepares the starting context for the sentiment analysis task:
- Installs system utilities needed for setup (wget)
- Downloads a sample COVID-19 Twitter dataset
- Creates basic project directory structure
"""

import subprocess
import sys
import os


def install_system_dependencies():
    """Install system dependencies required for setup logic."""
    print("Installing system dependencies...")
    
    subprocess.check_call(["apt-get", "update", "-y"])
    subprocess.check_call(["apt-get", "install", "-y", "wget"])
    
    print("System dependencies installed successfully.")


def cleanup_empty_files(data_dir):
    """Remove empty files that may remain from failed download attempts."""
    empty_files = ["covid19_tweet_ids.txt", "covid19_tweets.csv"]
    for filename in empty_files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath) and os.path.getsize(filepath) == 0:
            os.remove(filepath)
            print(f"Removed empty file: {filepath}")


def download_covid19_twitter_dataset():
    """Download a sample COVID-19 Twitter dataset."""
    print("Downloading COVID-19 Twitter dataset...")
    
    data_dir = "/app/data"
    os.makedirs(data_dir, exist_ok=True)
    
    dataset_url = "https://raw.githubusercontent.com/echen102/COVID-19-TweetIDs/master/tweetids_2020-01.txt"
    dataset_path = os.path.join(data_dir, "covid19_tweet_ids.txt")
    
    try:
        subprocess.check_call(["wget", "-O", dataset_path, dataset_url])
        print(f"Dataset downloaded successfully to {dataset_path}")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to download from primary source: {e}")
        print("Attempting alternative dataset source...")
        
        alternative_url = "https://raw.githubusercontent.com/thepanacealab/covid19_twitter/master/datasets/August/cleaned_active_users.csv"
        try:
            subprocess.check_call(["wget", "-O", os.path.join(data_dir, "covid19_tweets.csv"), alternative_url])
            print("Alternative dataset downloaded successfully.")
        except subprocess.CalledProcessError:
            print("Warning: Could not download real dataset. Creating realistic sample...")
            create_sample_dataset(data_dir)
    
    cleanup_empty_files(data_dir)


def create_sample_dataset(data_dir):
    """Create a realistic sample COVID-19 Twitter dataset."""
    import csv
    
    sample_file = os.path.join(data_dir, "covid19_tweets_sample.csv")
    
    sample_tweets = [
        ["1", "2020-03-15", "I just got tested for COVID-19 and thankfully I'm negative. Stay safe everyone! #COVID19 #StayHome"],
        ["2", "2020-03-16", "This pandemic is terrifying. The news keeps showing scary numbers. I hope it ends soon. #CoronaVirus"],
        ["3", "2020-03-17", "Just finished my remote work setup. Working from home isn't so bad after all! #WFH #COVID19"],
        ["4", "2020-03-18", "Why are people hoarding toilet paper? This is insane. Please think about others! #PanicBuying"],
        ["5", "2020-03-19", "Grateful for all the healthcare workers on the front lines. You're true heroes! #HealthcareHeroes"],
        ["6", "2020-03-20", "COVID-19 is just a flu, people are overreacting. The media is causing unnecessary panic. #FakeNews"],
        ["7", "2020-03-21", "My small business had to close today. So worried about the future. #SmallBusiness #EconomicImpact"],
        ["8", "2020-03-22", "Virtual happy hour with friends tonight! We may be isolated but we're still connected. #SocialDistancing"],
        ["9", "2020-03-23", "The president announced new guidelines today. Finally some leadership during this crisis. #Leadership"],
        ["10", "2020-03-24", "Feeling so anxious and alone. This whole situation is overwhelming. #MentalHealth #Anxiety"],
        ["11", "2020-03-25", "Scientists are working hard on a vaccine. Have faith in science! #ScienceHope"],
        ["12", "2020-03-26", "Some people still refuse to take this seriously. It's infuriating! #Irresponsible"],
        ["13", "2020-03-27", "Donated to the local food bank today. Let's help those in need. #CommunitySupport"],
        ["14", "2020-03-28", "Online classes are a mess. I miss my university so much! #OnlineLearning"],
        ["15", "2020-03-29", "The curve is starting to flatten in our area. Stay home and keep it up! #FlattenTheCurve"],
        ["16", "2020-03-30", "Lost my job today due to COVID-19. This is the worst day of my life. #Unemployment"],
        ["17", "2020-03-31", "The internet is full of misinformation. Please verify before sharing! #FactCheck"],
        ["18", "2020-04-01", "April Fools but COVID-19 is no joke. Stay safe! #COVID19"],
        ["19", "2020-04-02", "Telemedicine is a game changer. So convenient to see a doctor from home. #Telehealth"],
        ["20", "2020-04-03", "Protests against lockdowns are selfish. Think about the vulnerable populations! #StayHome"],
    ]
    
    with open(sample_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['tweet_id', 'date', 'text'])
        writer.writerows(sample_tweets)
    
    print(f"Sample dataset created at {sample_file}")


def create_project_structure():
    """Create basic project directory structure for the agent."""
    print("Creating project directory structure...")
    
    directories = [
        "/app/data",
        "/app/output",
        "/app/notebooks",
        "/app/src",
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")
    
    print("Project structure created successfully.")


def main():
    """Main setup function."""
    print("=" * 60)
    print("Twitter Sentiment Analysis - Setup Script")
    print("=" * 60)
    
    try:
        install_system_dependencies()
        create_project_structure()
        download_covid19_twitter_dataset()
        
        print("=" * 60)
        print("Setup completed successfully!")
        print("=" * 60)
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Command failed with return code {e.returncode}")
        print(f"Command: {e.cmd}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
