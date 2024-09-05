import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import time
import random
import feedparser
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

def scrape_text(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'article', 'div', 'span'])
        text = ' '.join([elem.get_text(strip=True) for elem in text_elements if elem.get_text(strip=True)])
        
        if len(text) < 500:
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
            if main_content:
                text = main_content.get_text(strip=True)
        
        return text[:5000]
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def scrape_rss(url):
    try:
        feed = feedparser.parse(url)
        entries = feed.entries[:5]  # Get the 5 most recent entries
        text = "\n".join([f"Title: {entry.title}\nLink: {entry.link}\nSummary: {entry.summary}" for entry in entries])
        return text[:5000]
    except Exception as e:
        print(f"Error scraping RSS feed {url}: {e}")
        return ""

def send_email(content):
    message = Mail(
        from_email='newsletter@callreverie.com',
        to_emails='noah@callreverie.com',
        subject='Prairie Matters: Your Daily Saskatchewan Newsletter',
        html_content=content)
    try:
        sg = SendGridAPIClient(os.environ['SENDGRID_API_KEY'])
        response = sg.send(message)
        print(f"Email sent successfully. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending email: {e}")

# List of URLs to scrape
urls = [
    ('https://www.reddit.com/r/saskatchewan/top/.rss', scrape_rss),
    ('https://www.reddit.com/r/saskatoon/top/.rss', scrape_rss),
    ('https://www.cbc.ca/cmlink/rss-canada-saskatoon', scrape_rss),
    ('https://thestarphoenix.com/feed', scrape_rss)
]

# Scrape text from all URLs
scraped_texts = []
for url, scrape_function in urls:
    print(f"Scraping {url}...")
    text = scrape_function(url)
    scraped_texts.append(f"From {url}:\n{text}")
    time.sleep(random.uniform(1, 3))  # Random delay between requests

scraped_text = '\n\n'.join(scraped_texts)

print("Sending to OpenAI API...")
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are the editor-in-chief of the daily newsletter, Prairie Matters. It's a daily email newsletter that explores current events and interesting happenings in Saskatchewan and Saskatoon. You will receive a stream of news - you need to pick what is most interesting and important. You should output a newsletter with some commentary for each story - don't be too professional; you will have a very casual style. You should separate the newsletter to separate sections with borders with rounded corners, and only include notable news or interesting stories with images (ignore requests for suggestions, etc) - feel free to use bullet points with inline hyperlinks if there are lots of stories too; Also for links, make sure youdon't just add 'read here' or something - add links to relevant text. You should also add this sponsored message: Reverie is a journal app that calls you every day. Simply pick up the phone and speak your mind! -- with a link to callreverie.com. You should make the title section consistent like this: Emoji TITLE and then line below should be subheading. It should be a minimal, grayscale design. Feel free to use emojis. Output in HTML with images, with rounded borders around each section."},
            {"role": "user", "content": f"Analyze the following latest news and stories and write today's newsletter:\n\n{scraped_text}"}
        ]
    )
    
    preprocessed = response.choices[0].message.content
    newsletter_content = preprocessed.replace('```html', '').replace('```', '')
    print("Newsletter content generated. Sending email...")
    send_email(newsletter_content)
except Exception as e:
    print(f"Error calling OpenAI API or sending email: {e}")