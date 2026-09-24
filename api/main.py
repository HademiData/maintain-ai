from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from api.schemas import (
    ChatRequest,
    ChatResponse,
)

from app import (
    ask_maintain_ai,
    is_ai_configured,
)

from api.auth.database import (
    initialize_users_database,
)

from api.auth.routes import (
    router as auth_router,
)

from memory.conversation import (
    initialize_memory,
    save_message,
    get_conversation_history,
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Maintain AI API",
    description=(
        "AI-powered maintenance planning and "
        "general engineering assistant."
    ),
    version="1.1.0",
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = (
    BASE_DIR / "frontend"
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

initialize_memory()

initialize_users_database()


# ============================================================
# AUTHENTICATION
# ============================================================

app.include_router(
    auth_router
)


# ============================================================
# FRONTEND
# ============================================================

@app.get("/")
def root():
    return FileResponse(
        FRONTEND_DIR / "index.html"
    )


@app.get("/login.html")
def login_page():
    return FileResponse(
        FRONTEND_DIR / "login.html"
    )


@app.get("/register.html")
def register_page():
    return FileResponse(
        FRONTEND_DIR / "register.html"
    )


@app.get("/dashboard.html")
def dashboard_page():
    return FileResponse(
        FRONTEND_DIR / "dashboard.html"
    )


@app.get("/style.css")
def stylesheet():
    return FileResponse(
        FRONTEND_DIR / "style.css"
    )


@app.get("/dashboard.css")
def dashboard_stylesheet():
    return FileResponse(
        FRONTEND_DIR / "dashboard.css"
    )


@app.get("/app.js")
def javascript():
    return FileResponse(
        FRONTEND_DIR / "app.js"
    )

@app.get("/hero.png")
def hero_image():
    return FileResponse(
        FRONTEND_DIR / "hero.png"
    )

# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    """
    Lightweight health endpoint.

    This endpoint intentionally does not initialize the RAG system
    or contact Hugging Face. Render can therefore use it as a fast
    service health check.
    """

    return {
        "status": "healthy",
        "service": "maintain-ai",
        "ai_configured": is_ai_configured(),
    }


# ============================================================
# CHAT
# ============================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    request: ChatRequest,
):
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    # --------------------------------------------------------
    # Conversation history
    # --------------------------------------------------------

    history = get_conversation_history(
        request.conversation_id,
        limit=10,
    )

    try:

        result = ask_maintain_ai(
            question,
            history,
        )

    except RuntimeError as error:

        # Configuration errors such as a missing HF_TOKEN.
        raise HTTPException(
            status_code=503,
            detail=str(error),
        ) from error

    except TimeoutError as error:

        raise HTTPException(
            status_code=504,
            detail=(
                "The AI service took too long to respond. "
                "Please try again."
            ),
        ) from error

    except Exception as error:

        # Keep the actual error in Render logs but avoid exposing
        # internal implementation details to the client.
        print(
            f"Maintain AI request failed: {error}"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "The AI service could not complete the request. "
                "Please try again."
            ),
        ) from error

    # --------------------------------------------------------
    # Remove internal diagnostics
    # --------------------------------------------------------

    result.pop(
        "_performance",
        None,
    )

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    save_message(
        request.conversation_id,
        "user",
        question,
    )

    # --------------------------------------------------------
    # Save assistant response
    # --------------------------------------------------------

    save_message(
        request.conversation_id,
        "assistant",
        result.get(
            "answer",
            "",
        ),
    )

    return result