from googleapiclient.discovery import build
import google.generativeai as genai
from dotenv import load_dotenv
import os
import json
from PIL import Image, ImageDraw, ImageFont
import random

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name=os.getenv("MODEL_NAME", "gemini-pro"))

def search_youtube(query, max_results=5):
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    results = youtube.search().list(
        q=query,
        part="snippet",
        type="video",
        maxResults=max_results
    ).execute()

    videos = []
    for item in results["items"]:
        videos.append({
            "type": "video",
            "title": item["snippet"]["title"],
            "link": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
        })
    return videos

def generate_certificate(name: str) -> str:
    img = Image.open("assets/image.png")  
    d = ImageDraw.Draw(img)
    location = (600, 550)  
    text_color = (18, 48, 134)  
    font = ImageFont.truetype(
        "assets/aerial.ttf", 75
    )
    d.text(location, name, fill=text_color, font=font)
    if not os.path.exists("generated"):
        os.makedirs("generated")
    #name should replaced by hash from dev
    file_name = "generated/" + name + ".png"
    img.save(file_name)
    return file_name

def generate_youtube_content(query):
    # Step 1: Get YouTube videos
    video_links = search_youtube(query, max_results=5)

    # Step 2: Ask Gemini to generate the title/description
    prompt = f"""
You are helping a user learn a new skill: "{query}".
Below are the YouTube video links.

Generate a JSON with the following format:
{{
  "title": "...",
  "description": "...",
  "materials": [ <use the videos below as-is> ]
}}

Use this exact list for "materials":

{json.dumps(video_links, indent=4)}
"""

    response = client.models.generate_content(
        model=os.getenv("MODEL_NAME"),
        contents=prompt,
    )

    text = response.text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Strip Markdown formatting if needed
        text = text.strip("```json").strip("```")
        data = json.loads(text)

    return data


def fetch_article_links(prompt):
    base_prompt = f"""
grab all the contents from internet and give the article links with title in the given format:

{{
[
    {{
        "title": "<title>",
        "link": "<link>"
    }},
    {{
        "title": "<title>",
        "link": "<link>"
    }},
    {{
        "title": "<title>",
        "link": "<link>"
    }},
    {{
        "title": "<title>",
        "link": "<link>"
    }},
    {{
        "title": "<title>",
        "link": "<link>"
    }}
]
}}
    I want the output to be in JSON format.
    Do not include any additional text or explanations. No youtube links only the website links. Generate 5 article links with their titles.
"""

    response = client.models.generate_content(
        model=os.getenv("MODEL_NAME"),
        contents=base_prompt + prompt,
    )

    text = response.text
    data = json.loads(text[7:-3])
    try:
        data = json.loads(text[7:-3])
    except json.JSONDecodeError:
        text = text.strip("```json").strip("```")
        data = json.loads(text)

    return data
