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

API_VERSION = "0.9.0"
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

CHINA_SERVER_DESCRIPTION = """
## Hutao Generic API (China Ver.)

All the API endpoints in this application are designed to support the services in the China region.

To access the Global version of the API, please visit the `/global` path from management server, or use a network in 
the Global region.

Click **[here](../global/docs)** to enter Swagger UI for the Global version of the API **(if you are in management 
server)**."""

GLOBAL_SERVER_DESCRIPTION = """
## Hutao Generic API (Global Ver.)

All the API endpoints in this application are designed to support the services in the Global region.

To access the China version of the API, please visit the `/cn` path from management server, or use a network in the 
China region.

Click **[here](../cn/docs)** to enter Swagger UI for the China version of the API **(if you are in management server)**.
    
"""
