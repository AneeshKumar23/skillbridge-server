from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from google import genai
import uuid
import json
import os
from model import *
from utils import *
from config import *

# ----- Load Environment Variables -----
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ----- FastAPI App Initialization -----
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- MongoDB Setup -----
client = AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]
users_collection = db["users"]
prompts_collection = db["user_prompts"]
outputs_collection = db["user_outputs"]


# ----- Services -----
class UserService:
    @staticmethod
    async def get_user(user_id: str):
        user = await users_collection.find_one({"id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user["_id"] = str(user["_id"])
        return user

    @staticmethod
    async def create_user(user: UserCreate):
        user_id = uuid.uuid4().hex
        user_dict = user.dict()
        user_dict["id"] = user_id

        existing = await users_collection.find_one({"email": user.email})
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        await users_collection.insert_one(user_dict)
        return {"msg": "User created", "id": user_id}

class PromptService:
    @staticmethod
    async def add_prompt(user_id: str, prompt: str):
        await prompts_collection.update_one(
            {"id": user_id},
            {"$push": {"prompts": prompt}},
            upsert=True
        )
        return {"msg": "Prompt added"}

    @staticmethod
    async def get_prompts(user_id: str):
        doc = await prompts_collection.find_one({"id": user_id})
        return doc or {"id": user_id, "prompts": []}

class OutputService:
    @staticmethod
    async def add_output(user_id: str, output: str):
        await outputs_collection.update_one(
            {"id": user_id},
            {"$push": {"outputs": output}},
            upsert=True
        )
        return {"msg": "Output added"}

    @staticmethod
    async def get_outputs(user_id: str):
        doc = await outputs_collection.find_one({"id": user_id})
        if doc:
            doc["_id"] = str(doc["_id"])
            return doc
        return {"id": user_id, "outputs": []}

# ----- Routes: User Management -----
@app.post("/users/")
async def create_user(user: UserCreate):
    return await UserService.create_user(user)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    return await UserService.get_user(user_id)

# ----- Routes: Prompt Management -----
@app.post("/prompts/{user_id}")
async def add_prompt(user_id: str, prompt: str):
    return await PromptService.add_prompt(user_id, prompt)

@app.get("/prompts/{user_id}")
async def get_prompts(user_id: str):
    return await PromptService.get_prompts(user_id)

# ----- Routes: Output Management -----
@app.post("/outputs/{user_id}")
async def add_output(user_id: str, output: str):
    return await OutputService.add_output(user_id, output)

@app.get("/outputs/{user_id}")
async def get_outputs(user_id: str):
    return await OutputService.get_outputs(user_id)

# ----- Routes: Content Generation -----
@app.post("/api/generate_youtube_content")
def get_youtube_links(prompt: str) -> dict:
    if not prompt:
        return {"error": "Prompt is required"}
    try:
        result = generate_youtube_content(prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_article")
def generate_article(prompt: str) -> dict:
    if not prompt.strip():
        return {"error": "Prompt is required"}
    try:
        result = fetch_article_links(prompt)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail="Failed to parse response from Gemini")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate_content")
def generate_content(prompt: str) -> dict:
    if not prompt:
        return {"error": "Prompt is required"}
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=BASE_PROMPT + prompt,
        )
        data = json.loads(response.text[7:-3])
        return data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse response from Gemini")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
