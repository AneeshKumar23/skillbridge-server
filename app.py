from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import google.generativeai as genai
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
genai.configure(api_key="")
# ---- FastAPI App Setup ----
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/generated", StaticFiles(directory="generated"), name="generated")

# ---- MongoDB Setup ----
client = AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]
users_collection = db["users"]
prompts_collection = db["user_prompts"]
outputs_collection = db["user_outputs"]

# ---- Pydantic Models ----
class SkillSuggestionRequest(BaseModel):
    prompt: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class OnboardingUpdate(BaseModel):
    language: str
    skills: List[str]
    street_address: str
    city: str
    state: str
    zip_code: str
    country: str

# ---- Services ----
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

# ---- Routes: User Management ----
@app.post("/users/")
async def create_user(user: UserCreate):
    return await UserService.create_user(user)

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    return await UserService.get_user(user_id)

# ---- Routes: Prompt Management ----
@app.post("/prompts/{user_id}")
async def add_prompt(user_id: str, prompt: str):
    return await PromptService.add_prompt(user_id, prompt)

@app.get("/prompts/{user_id}")
async def get_prompts(user_id: str):
    return await PromptService.get_prompts(user_id)

# ---- Routes: Output Management ----
@app.post("/outputs/{user_id}")
async def add_output(user_id: str, output: str):
    return await OutputService.add_output(user_id, output)

@app.get("/outputs/{user_id}")
async def get_outputs(user_id: str):
    return await OutputService.get_outputs(user_id)

# ---- Content Generation with Gemini ----
@app.post("/api/generate_content")
async def generate_content_endpoint(payload: dict):
    prompt = payload.get("prompt", "")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=BASE_PROMPT + prompt,
        )
        response_text = response.text[7:-3]  # clean response
        data = json.loads(response_text)
        return data
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse response from Gemini")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- YouTube and Article Content (Optional) ----
@app.post("/api/generate_youtube_content")
def get_youtube_links(prompt: str) -> dict:
    if not prompt:
        return {"error": "Prompt is required"}
    try:
        return generate_youtube_content(prompt)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_article")
def generate_article(prompt: str) -> dict:
    if not prompt.strip():
        return {"error": "Prompt is required"}
    try:
        return fetch_article_links(prompt)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse response from Gemini")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- Certificate Generation ----
@app.post("/certificate/{user_id}")
async def certificate(user_id: str, request: Request):
    user = await UserService.get_user(user_id)
    name = user.get("first_name")
    if not name:
        raise HTTPException(status_code=400, detail="User does not have a first_name")

    file_path = generate_certificate(name)
    await OutputService.add_output(user_id, file_path)

    relative_path = file_path.split("generated/")[-1]
    file_url = request.url_for("generated", path=relative_path)

    return {"msg": "Certificate generated", "file": str(file_url)}

# ---- Login Route ----
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await users_collection.find_one({"email": form_data.username})
    if not user or user["password"] != form_data.password:
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return {
        "msg": "Login successful",
        "user_id": user["id"],
        "email": user["email"],
    }

# ---- Onboarding Update ----
@app.put("/users/{user_id}/onboarding")
async def update_user_onboarding(user_id: str, data: OnboardingUpdate):
    result = await users_collection.update_one(
        {"id": user_id},
        {
            "$set": {
                "language": data.language,
                "skills": data.skills,
                "street_address": data.street_address,
                "city": data.city,
                "state": data.state,
                "zip_code": data.zip_code,
                "country": data.country
            }
        }
    )
    if result.modified_count == 1:
        return {"msg": "User onboarding updated"}
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/api/suggest_skills")
async def suggest_skills(req: SkillSuggestionRequest):
    prompt = req.prompt.strip()

    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")

    try:
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content(
            f"Based on the user's interest: '{prompt}', suggest 5-10 relevant digital skills. Respond only with a comma-separated list."
        )

        # Extract the skill list
        skills = [skill.strip() for skill in response.text.split(',') if skill.strip()]
        return {"skills": skills}

    except Exception as e:
        print(f"❌ Error from Gemini: {e}")
        raise HTTPException(status_code=500, detail=str(e))