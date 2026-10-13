from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth_routes, behavior, dashboard, location, transactions


Base.metadata.create_all(bind=engine)

app = FastAPI(title="IntelliTrust FinGuard API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(transactions.router)
app.include_router(dashboard.router)
app.include_router(location.router)
app.include_router(behavior.router)


@app.get("/api/health")
def health():
    return {"status": "healthy"}
