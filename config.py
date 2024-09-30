from dotenv import load_dotenv
import os

env_result = load_dotenv()

VALID_PROJECT_KEYS = ["snap-hutao", "snap-hutao-deployment"]

github_headers = {
    "Authorization": f"Bearer {os.environ.get('GITHUB_PAT')}",
    "X-GitHub-Api-Version": "2022-11-28"
}

API_TOKEN = os.environ.get("API_TOKEN")


# FastAPI Config

API_VERSION = "1.11.1"  # API Version follows the least supported version of Snap Hutao
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

You reached this page as you are trying to access the Hutao Generic API in manage purpose.

There is no actual API endpoint on this page. Please use the following links to access the API documentation.

### China API Application
China API is hosted on the `/cn` path.

Click **[here](../cn/docs)** to enter Swagger UI for the China version of the API.

### Global API Application
Global API is hosted on the `/global` path.

Click **[here](../global/docs)** to enter Swagger UI for the Global version of the API.
"""
