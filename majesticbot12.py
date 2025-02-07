import os
import json
import logging
import requests
import praw
import time
import snscrape.modules.twitter as sntwitter
from bs4 import BeautifulSoup
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# === LOAD ENVIRONMENT VARIABLES ===
load_dotenv()

# === CONFIGURATION ===
SCOPES = ['https://www.googleapis.com/auth/drive.file', 'https://www.googleapis.com/auth/spreadsheets']
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "credentials.json")
LOG_FILE = "majesticbot12.log"
DATA_FILE = "reddit_data.json"
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "YOUR_GOOGLE_SHEET_ID")

# Email settings
SENDER_EMAIL = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
RECIPIENT_EMAIL = os.getenv("EMAIL_RECIPIENT")

# === SET UP LOGGING ===
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === LOAD SOURCES ===
def load_sources():
    try:
        with open("sources.json", "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"❌ Error loading sources.json: {e}")
        return {}

sources = load_sources()
subreddits = sources.get("subreddits", [])
news_sites = sources.get("news_sites", [])
forums = sources.get("forums", [])

# === GOOGLE SHEETS SETUP ===
def connect_google_sheets():
    try:
        credentials = Credentials.from_authorized_user_file('token.json', SCOPES)
        gc = gspread.authorize(credentials)
        sheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1
        return sheet
    except Exception as e:
        logging.error(f"❌ Error connecting to Google Sheets: {e}")
        return None

# === REDDIT API SETUP ===
try:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
    )
except Exception as e:
    logging.error(f"❌ Error initializing Reddit API: {e}")

# === SCRAPE REDDIT ===
def scrape_reddit():
    data = []
    for subreddit in subreddits:
        logging.info(f"📌 Scraping r/{subreddit}...")
        try:
            for post in reddit.subreddit(subreddit).new(limit=10):
                data.append([post.title, post.url, post.score, post.num_comments, subreddit])
        except Exception as e:
            logging.error(f"⚠️ Error scraping r/{subreddit}: {e}")

    # Save to Google Sheets
    sheet = connect_google_sheets()
    if sheet:
        sheet.append_rows(data, value_input_option="USER_ENTERED")
        logging.info("✅ Reddit data saved to Google Sheets.")

# === SCRAPE TWITTER (USING SNSCRAPE) ===
def scrape_twitter():
    keywords = ["UFO", "aliens", "paranormal", "telekinesis", "zero-point energy"]
    data = []
    
    for keyword in keywords:
        logging.info(f"🐦 Searching Twitter for: {keyword}")
        try:
            for tweet in sntwitter.TwitterSearchScraper(f"{keyword} since:2023-01-01").get_items():
                data.append([tweet.date.strftime("%Y-%m-%d"), tweet.content, tweet.user.username, tweet.url])
                if len(data) >= 10:
                    break
        except Exception as e:
            logging.error(f"⚠️ Error scraping Twitter for {keyword}: {e}")

    # Save to Google Sheets
    sheet = connect_google_sheets()
    if sheet:
        sheet.append_rows(data, value_input_option="USER_ENTERED")
        logging.info("✅ Twitter data saved to Google Sheets.")

# === SCRAPE NEWS SITES ===
def scrape_news():
    data = []
    for site in news_sites:
        logging.info(f"📰 Scraping news site: {site}")
        try:
            response = requests.get(site, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            articles = soup.find_all("article")[:5]

            for article in articles:
                title_tag = article.find("h2") or article.find("h3") or article.find("a")
                link_tag = article.find("a", href=True)
                if title_tag and link_tag:
                    data.append([title_tag.get_text(strip=True), link_tag["href"], site])
        except Exception as e:
            logging.error(f"⚠️ Error scraping {site}: {e}")

    # Save to Google Sheets
    sheet = connect_google_sheets()
    if sheet:
        sheet.append_rows(data, value_input_option="USER_ENTERED")
        logging.info("✅ News data saved to Google Sheets.")

# === SEND WEEKLY EMAIL REPORT ===
def send_email_report():
    try:
        subject = "🔍 MajesticBot12 Weekly Report"
        body = "MajesticBot12 has finished collecting data. The latest findings are available in Google Sheets."

        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())

        logging.info("✅ Weekly email report sent successfully.")
    except Exception as e:
        logging.error(f"❌ Failed to send email report: {e}")

# === RUN ALL TASKS ===
if __name__ == "__main__":
    try:
        logging.info("🚀 Starting MajesticBot12 script...")
        print("🚀 Running MajesticBot12...")  # Print to CMD
        scrape_reddit()
        scrape_twitter()
        scrape_news()
        send_email_report()
        print("✅ MajesticBot12 script completed.")  # Print to CMD
        logging.info("✅ MajesticBot12 script completed.")
    except Exception as e:
        print(f"❌ ERROR: {e}")
        logging.error(f"❌ ERROR: {e}")
