from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging
import os
import time
import json
from datetime import datetime

from auth import create_access_token, verify_token, hash_password, verify_password
from database import get_db, init_db, User, Document
from rag_engine import get_answer, process_document_for_user
from utils import logger, event_tracker

# Setup Google Cloud Logging
if os.getenv("GOOGLE_CLOUD_PROJECT"):
    try:
        from google.cloud import logging as cloud_logging
        client = cloud_logging.Client()
        client.setup_logging()
    except ImportError:
        pass

app = FastAPI(title="AppLydi API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour Cloud Run, on autorise tout temporairement
    allow_credentials=False,  # Doit être False avec allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise e

# Health check endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "AppLydi API is running", "status": "ok"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "AppLydi API"}

# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class QuestionRequest(BaseModel):
    question: str
    selected_documents: list[int] = []  # List of document IDs to use

# Routes
@app.post("/register")
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Register new user"""
    try:
        # Check if user exists
        if db.query(User).filter(User.username == user.username).first():
            raise HTTPException(status_code=400, detail="Username already registered")
        
        if db.query(User).filter(User.email == user.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        hashed_password = hash_password(user.password)
        db_user = User(
            username=user.username,
            email=user.email,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"User registered: {user.username}")
        event_tracker.track_user_action(db_user.id, "user_registered")
        
        return {"message": "User created successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """Login user"""
    try:
        db_user = db.query(User).filter(User.username == user.username).first()
        if not db_user or not verify_password(user.password, db_user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        access_token = create_access_token(data={"sub": str(db_user.id)})
        logger.info(f"User logged in: {user.username}")
        event_tracker.track_user_action(db_user.id, "user_login")
        
        return {"access_token": access_token, "token_type": "bearer"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/ask")
async def ask_question(
    request: QuestionRequest,
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Ask question to RAG system"""
    start_time = time.time()
    
    try:
        logger.info(f"Processing question from user {user_id}: {request.question}")
        logger.info(f"Selected documents: {request.selected_documents}")
        
        # Get answer from RAG engine
        answer = get_answer(request.question, int(user_id), db, selected_doc_ids=request.selected_documents)
        
        response_time = time.time() - start_time
        logger.info(f"Question answered for user {user_id} in {response_time:.2f}s")
        event_tracker.track_question_asked(int(user_id), request.question, response_time)
        
        return {"answer": answer}
    
    except Exception as e:
        logger.error(f"Error answering question for user {user_id}: {e}")
        # Return more specific error message to help with debugging
        return {"answer": f"Désolé, une erreur s'est produite lors du traitement de votre question. Détails: {str(e)}"}

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Upload and process document"""
    try:
        # Check file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 10MB)")
        
        # Check file type
        allowed_types = ['.pdf', '.txt', '.docx']
        if not any(file.filename.lower().endswith(ext) for ext in allowed_types):
            raise HTTPException(status_code=400, detail="File type not supported")
        
        content = await file.read()
        doc_id = process_document_for_user(file.filename, content, int(user_id), db)
        
        logger.info(f"Document uploaded for user {user_id}: {file.filename}")
        event_tracker.track_document_upload(int(user_id), file.filename, len(content))
        
        return {"filename": file.filename, "document_id": doc_id, "status": "uploaded"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

@app.get("/test-jwt")
async def test_jwt():
    """Test JWT configuration"""
    import os
    from auth import SECRET_KEY
    
    return {
        "jwt_secret_found": bool(os.getenv("JWT_SECRET_KEY")),
        "jwt_secret_length": len(SECRET_KEY) if SECRET_KEY else 0,
        "jwt_secret_prefix": SECRET_KEY[:10] + "..." if SECRET_KEY else "None",
        "environment_vars": {
            key: "***" if "KEY" in key or "SECRET" in key or "PASSWORD" in key 
            else value for key, value in os.environ.items() 
            if key.startswith(("JWT", "OPENAI", "DATABASE", "GOOGLE"))
        }
    }

@app.get("/test-auth")
async def test_auth(user_id: str = Depends(verify_token)):
    """Test authentication"""
    return {
        "status": "success",
        "message": "Authentication successful",
        "user_id": user_id,
        "timestamp": time.time()
    }

@app.get("/test-openai")
async def test_openai():
    """Test OpenAI connection"""
    try:
        import os
        import requests
        
        # Check if API key is accessible
        api_key = os.getenv("OPENAI_API_KEY")
        
        # Clean the API key - remove any whitespace/newlines (CRITICAL!)
        if api_key:
            api_key = api_key.strip()
            
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        
        response_data = {
            "api_key_found": bool(api_key),
            "api_key_length": len(api_key) if api_key else 0,
            "api_key_prefix": api_key[:10] + "..." if api_key else "None",
            "project_id": project_id,
        }
        
        if not api_key:
            return {
                "status": "error", 
                "message": "OPENAI_API_KEY not found in environment",
                "debug": response_data
            }
        
        # Test with direct HTTP request instead of OpenAI client
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "input": "test",
                "model": "text-embedding-3-small"
            }
            
            # Test multiple endpoints
            endpoints_to_try = [
                "https://api.openai.com/v1/embeddings",
                "https://api.openai.com/v1/embeddings",  # Try twice for consistency
            ]
            
            for i, endpoint in enumerate(endpoints_to_try):
                try:
                    # Simple requests test
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        json=data,
                        timeout=30,
                        verify=True  # Ensure SSL verification
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return {
                            "status": "success", 
                            "message": f"OpenAI connection successful with requests (endpoint {i+1})",
                            "embedding_length": len(result['data'][0]['embedding']),
                            "endpoint_used": endpoint,
                            "debug": response_data
                        }
                    else:
                        response_data[f"attempt_{i+1}"] = f"Status {response.status_code}: {response.text[:100]}"
                        
                except Exception as e:
                    response_data[f"attempt_{i+1}_error"] = str(e)
                    continue
            
            # If all direct requests failed, return detailed error
            return {
                "status": "error", 
                "message": "All direct HTTP requests failed",
                "debug": response_data
            }
                
        except Exception as e:
            # Try with openai client as fallback
            from openai_client import client
            response = client.embeddings.create(
                input="test",
                model="text-embedding-3-small"
            )
            
            return {
                "status": "success", 
                "message": "OpenAI connection successful with client",
                "embedding_length": len(response.data[0].embedding),
                "debug": response_data
            }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": str(e),
            "debug": response_data if 'response_data' in locals() else {}
        }

@app.get("/user/documents")
async def get_user_documents(
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Get user's documents"""
    try:
        documents = db.query(Document).filter(Document.user_id == int(user_id)).all()
        return {
            "documents": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "created_at": doc.created_at.isoformat()
                }
                for doc in documents
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    """Delete a user's document"""
    try:
        # Check if document exists and belongs to user
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == int(user_id)
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete document
        db.delete(document)
        db.commit()
        
        logger.info(f"Document {document_id} deleted by user {user_id}")
        event_tracker.track_user_action(int(user_id), f"document_deleted:{document.filename}")
        
        return {"message": "Document deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
