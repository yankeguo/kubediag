import logging
import time
from urllib.parse import urlencode
import aiohttp
import jwt
from os import path
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import RedirectResponse, PlainTextResponse
from starlette.routing import Mount, Route
import jinja2
from starlette.requests import Request
from starlette.templating import Jinja2Templates

from .env import *
from .mcp import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp_app = mcp.http_app(path="/")

_templates_loader = jinja2.FileSystemLoader(path.join(path.dirname(__file__), "view"))

_templates_env = jinja2.Environment(
    loader=_templates_loader,
    autoescape=True,
)

templates = Jinja2Templates(
    env=_templates_env,
)


class CASResponse(BaseModel):
    class ServiceResponse(BaseModel):
        class AuthenticationSuccess(BaseModel):
            user: str

        authenticationSuccess: AuthenticationSuccess

    serviceResponse: ServiceResponse


async def route_index(req: Request):
    ticket = req.query_params.get("ticket", None)
    if not ticket:
        query = urlencode({"service": PUBLIC_URL})
        return RedirectResponse(f"{CAS_URL}?{query}")

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{CAS_URL}/p3/serviceValidate",
            params={"service": PUBLIC_URL, "ticket": ticket, "format": "json"},
        ) as resp:
            data = CASResponse(**await resp.json(content_type=None))

    user_id = data.serviceResponse.authenticationSuccess.user

    logger.info(f"CAS authentication successful for user: {user_id}")

    jwt_token = jwt.encode(
        {
            "sub": user_id,
            "iat": int(time.time()),
        },
        SECRET_KEY,
        algorithm="HS256",
    )

    return templates.TemplateResponse(
        req,
        "index.html.j2",
        context={
            "user_id": user_id,
            "jwt_token": jwt_token,
            "mcp_url": f"{PUBLIC_URL}/mcp/",
            "server_name": SERVER_NAME,
        },
    )


app = Starlette(
    routes=[
        Mount("/mcp", mcp_app),
        Route("/", route_index),
    ],
    lifespan=mcp_app.lifespan,
)

__all__ = ("app",)
