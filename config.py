from dotenv import load_dotenv
import os

env_result = load_dotenv()

github_headers = {
    "Authorization": f"Bearer {os.environ.get('GITHUB_PAT')}",
    "X-GitHub-Api-Version": "2022-11-28"
}
