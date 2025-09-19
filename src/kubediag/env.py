import os

SECRET_KEY = os.getenv("SECRET_KEY", "secret_key")

PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8000")

CAS_URL = os.getenv("CAS_URL", "http://localhost:8000/cas")

SERVER_NAME = os.getenv("SERVER_NAME", "KubeDiag")


__all__ = ("SECRET_KEY", "PUBLIC_URL", "CAS_URL", "SERVER_NAME")
