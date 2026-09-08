from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends

from api.auth.security import get_current_user

from fastapi.responses import FileResponse

from api.schemas import ChatRequest, ChatResponse

from app import ask_maintain_ai

from api.auth.database import initialize_users_database
from api.auth.routes import router as auth_router

from memory import conversation
from memory.conversation import (
    initialize_memory,
    create_conversation,
    get_user_conversations,
    get_conversation,
    get_conversation_history,
    save_message,
    update_conversation_title,
    delete_conversation,
)

# ==========================================
# APPLICATION
# ==========================================

app = FastAPI(
    title="Maintain AI API",
    description="AI-powered maintenance planning and engineering assistant",
    version="1.0.0"
)


# ==========================================
# PATHS
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = BASE_DIR / "frontend"


# ==========================================
# DATABASE INITIALIZATION
# ==========================================

# Conversation memory
initialize_memory()

# User authentication database
initialize_users_database()


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

app.include_router(auth_router)


# ==========================================
# FRONTEND
# ==========================================

@app.get("/")
def root():
    """
    Serve the Maintain AI homepage.
    """

    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.get("/login.html")
def login_page():
    """
    Serve the login page.
    """

    return FileResponse(
        FRONTEND_DIR / "login.html"
    )


@app.get("/register.html")
def register_page():
    """
    Serve the registration page.
    """

    return FileResponse(
        FRONTEND_DIR / "register.html"
    )


@app.get("/dashboard.html")
def dashboard_page():
    """
    Serve the dashboard page.
    """

    return FileResponse(
        FRONTEND_DIR / "dashboard.html"
    )


# ==========================================
# CSS
# ==========================================

@app.get("/style.css")
def stylesheet():
    """
    Serve global stylesheet.
    """

    return FileResponse(
        FRONTEND_DIR / "style.css"
    )


@app.get("/dashboard.css")
def dashboard_stylesheet():
    """
    Serve dashboard stylesheet.
    """

    return FileResponse(
        FRONTEND_DIR / "dashboard.css"
    )


# ==========================================
# JAVASCRIPT
# ==========================================

@app.get("/app.js")
def javascript():
    """
    Serve frontend JavaScript.
    """

    return FileResponse(
        FRONTEND_DIR / "app.js"
    )


# ==========================================
# HEALTH CHECK
# ==========================================

@app.get("/health")
def health():
    """
    API health check.
    """

    return {
        "status": "healthy"
    }


# ==========================================
# AI CHAT
# ==========================================

# ==========================================
# CONVERSATION ENDPOINTS
# ==========================================

@app.post("/conversations")
def create_new_conversation(
    current_user=Depends(get_current_user)
):
    import uuid

    conversation_id = str(uuid.uuid4())

    create_conversation(
        conversation_id=conversation_id,
        user_id=current_user["id"],
        title="New conversation"
    )

    return {
        "conversation_id": conversation_id,
        "title": "New conversation"
    }


@app.get("/conversations")
def list_conversations(
    current_user=Depends(get_current_user)
):
    return get_user_conversations(
        current_user["id"]
    )


@app.get("/conversations/{conversation_id}")
def load_conversation(
    conversation_id: str,
    current_user=Depends(get_current_user)
):
    conversation = get_conversation(
        conversation_id,
        current_user["id"]
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    messages = get_conversation_history(
        conversation_id,
        limit=100
    )

    return {
        "conversation": conversation,
        "messages": messages
    }


@app.delete("/conversations/{conversation_id}")
def remove_conversation(
    conversation_id: str,
    current_user=Depends(get_current_user)
):
    conversation = get_conversation(
        conversation_id,
        current_user["id"]
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )

    delete_conversation(
        conversation_id,
        current_user["id"]
    )

    return {
        "message": "Conversation deleted successfully."
    }


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user=Depends(get_current_user)
):
    question = request.question.strip()


    if not question:

        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty."
        )

    conversation = get_conversation(
        request.conversation_id,
        current_user["id"]
    )

    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found."
        )



    # --------------------------------------
    # Retrieve conversation history
    # --------------------------------------

    history = get_conversation_history(
        request.conversation_id,
        limit=10
    )


    print("\nConversation history:")
    print(history)


    # --------------------------------------
    # Run Maintain AI pipeline
    # --------------------------------------

    result = ask_maintain_ai(
        question,
        history
    )


    # --------------------------------------
    # Remove internal performance metadata
    # --------------------------------------

    result.pop(
        "_performance",
        None
    )


    # --------------------------------------
    # Save user message
    # --------------------------------------

    save_message(
        request.conversation_id,
        "user",
        question
    )

    if conversation["title"] == "New conversation":

        title = question.strip()

        if len(title) > 50:
            title = title[:50] + "..."

        update_conversation_title(
            request.conversation_id,
            current_user["id"],
            title
        )

    # --------------------------------------
    # Save AI response
    # --------------------------------------

    save_message(
        request.conversation_id,
        "assistant",
        result.get("answer", "")
    )


    # --------------------------------------
    # Return structured response
    # --------------------------------------

    return result
