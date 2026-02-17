from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.logging_config import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(application: FastAPI):
    # Start the MCP session manager
    from app.mcp.server import mcp as mcp_server

    async with mcp_server.session_manager.run():
        yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="BitWise Cloud",
        description="Hosted search for embedded systems documentation",
        version="0.1.0",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.public_host, "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router)

    # Mount MCP server at /mcp
    from app.mcp.server import mcp as mcp_server

    application.mount("/mcp", mcp_server.streamable_http_app())

    return application


app = create_app()
