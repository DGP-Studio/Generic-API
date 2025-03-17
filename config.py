from dotenv import load_dotenv
import os
import socket


env_result = load_dotenv()

VALID_PROJECT_KEYS = ["snap-hutao", "snap-hutao-deployment"]

IMAGE_NAME = os.getenv("IMAGE_NAME", "generic-api")
SERVER_TYPE = os.getenv("SERVER_TYPE", "[Unknown Server Type]")
with open("build_number.txt", 'r') as f:
    BUILD_NUMBER = f.read().strip()
with open("current_commit.txt", 'r') as f:
    CURRENT_COMMIT_HASH = f.read().strip()

github_headers = {
    "Authorization": f"Bearer {os.environ.get('GITHUB_PAT')}",
    "X-GitHub-Api-Version": "2022-11-28"
}

API_TOKEN = os.environ.get("API_TOKEN")

HOMA_SERVER_IP = os.environ.get("HOMA_SERVER_IP", None)

DEBUG = True if "alpha" in IMAGE_NAME.lower() or "dev" in IMAGE_NAME.lower() else False

REDIS_HOST = os.getenv("REDIS_HOST", "redis")

SENTRY_URL = f"http://{os.getenv('SENTRY_TOKEN')}@{socket.gethostbyname('host.docker.internal')}:9510/5"

# FastAPI Config
TOS_URL = "https://hut.ao/statements/tos.html"
CONTACT_INFO = {
    "name": "Masterain",
    "url": "https://github.com/Masterain98",
    "email": "masterain@dgp-studio.cn"
}
LICENSE_INFO = {
    "name": "MIT License",
    "url": "https://github.com/DGP-Studio/Generic-API/blob/main/LICENSE"
}

MAIN_SERVER_DESCRIPTION = """
## Hutao Generic API

You reached this page as you are trying to access the Hutao Generic API in developing purpose.

[**Snap Hutao**](https://hut.ao) is a project by DGP Studio, and this API is designed to support various services for Snap Hutao project.
"""
