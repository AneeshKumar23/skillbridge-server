from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from fastapi import Request, HTTPException
from google import genai
import uuid
import json
import os
from model import *
from utils import *
from config import *
from passlib.context import CryptContext
from typing import Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError

# ----- Load Environment Variables -----
load_dotenv()
MONGO_URL = os.getenv("MONGO_URL")
DATABASE_NAME = os.getenv("DATABASE_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

# ----- FastAPI App Initialization -----
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/generated", StaticFiles(directory="generated"), name="generated")

# ----- MongoDB Setup -----
client = AsyncIOMotorClient(MONGO_URL)
db = client[DATABASE_NAME]
users_collection = db["users"]
prompts_collection = db["user_prompts"]
outputs_collection = db["user_outputs"]

# ----- Password Hashing -----
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ----- OAuth2 Setup -----
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

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
    async def get_user_by_email(email: str):
        user = await users_collection.find_one({"email": email})
        if not user:
            return None
        user["_id"] = str(user["_id"])
        return user

    @staticmethod
    async def create_user(user: UserCreate):
        user_id = uuid.uuid4().hex
        user_dict = user.dict()
        user_dict["id"] = user_id
        
        # Hash password
        user_dict["password"] = pwd_context.hash(user_dict["password"])
        
        existing = await users_collection.find_one({"email": user.email})
        if existing:
            raise HTTPException(status_code=400, detail="User already exists")

        await users_collection.insert_one(user_dict)
        return {"msg": "User created", "id": user_id}

    @staticmethod
    async def authenticate_user(email: str, password: str):
        user = await UserService.get_user_by_email(email)
        if not user:
            return False
        if not pwd_context.verify(password, user["password"]):
            return False
        return user

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

# ----- Routes: Authentication -----
@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await UserService.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"]}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["id"]
    }

@app.post("/signup")
async def signup(user: UserCreate):
    return await UserService.create_user(user)

# ----- Routes: User Management -----
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
async def get_youtube_links(prompt: str) -> dict:
    if not prompt:
        return {"error": "Prompt is required"}
    try:
        result = generate_youtube_content(prompt)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate_article")
async def generate_article(prompt: str) -> dict:
    if not prompt.strip():
        return {"error": "Prompt is required"}
    try:
        result = fetch_article_links(prompt)
        return result
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail="Failed to parse response from Gemini")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/certificate/{user_id}")
async def certificate(user_id: str, request: Request):
    user = await UserService.get_user(user_id)
    name = user.get("first_name")
    if not name:
        raise HTTPException(status_code=400, detail="User does not have a first_name")

    file_path = generate_certificate(name)  # e.g., 'generated/Vachan42.png'
    await OutputService.add_output(user_id, file_path)

    # Remove "generated/" prefix to get the relative path
    relative_path = file_path.split("generated/")[-1]

    file_url = request.url_for("generated", path=relative_path)

    return {"msg": "Certificate generated", "file": str(file_url)}

@app.post("/api/generate_content")
async def generate_content(prompt: str) -> dict:
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