from fastapi import FastAPI

from social_video_formatter.api.routes import router
from social_video_formatter.core.database import init_db


def create_app() -> FastAPI:
    init_db()
    app = FastAPI(title="Social Video Formatter", version="0.1.0")
    app.include_router(router)
    return app


app = create_app()
