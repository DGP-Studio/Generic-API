import os
from dotenv import load_dotenv
import subprocess


def get_short_commit_hash(length=7):
    try:
        short_hash_result = subprocess.check_output(['git', 'rev-parse', f'--short={length}', 'HEAD']).strip().decode('utf-8')
        return short_hash_result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    load_dotenv(dotenv_path=".env")

    input_file = "docker-compose.yml.base"
    output_file = "docker-compose.yml"

    # Required environment variables
    required_variables = [
        "IMAGE_NAME",
        "SERVER_TYPE",
        "EXTERNAL_PORT"
    ]

    # Check missing environment variables
    missing_variables = [var for var in required_variables if not os.getenv(var)]

    if missing_variables:
        raise EnvironmentError(f"{len(missing_variables)} variables are missing: {', '.join(missing_variables)}")

    # Get environment variables
    IMAGE_NAME = os.getenv("IMAGE_NAME")
    SERVER_TYPE = os.getenv("SERVER_TYPE")
    EXTERNAL_PORT = os.getenv("EXTERNAL_PORT")
    variables = {
        "fastapi_service_name": f"{IMAGE_NAME}-{SERVER_TYPE}-server",
        "fastapi_container_name": f"{IMAGE_NAME}-{SERVER_TYPE}-server",
        "redis_service_name": f"{IMAGE_NAME}-{SERVER_TYPE}-redis",
        "scheduled_tasks_service_name": f"{IMAGE_NAME}-{SERVER_TYPE}-scheduled-tasks",
        "tunnel_service_name": f"{IMAGE_NAME}-{SERVER_TYPE}-tunnel",
    }

    # load templates
    with open(input_file, "r", encoding="utf-8") as file:
        content = file.read()

    # Generate the final docker-compose.yml file
    for placeholder, value in variables.items():
        content = content.replace(f"%{placeholder}%", value)

    with open(output_file, "w+", encoding="utf-8") as file:
        file.write(content)

    short_hash = get_short_commit_hash()
    if short_hash:
        with open("current_commit.txt", "w+", encoding="utf-8") as file:
            file.write(short_hash)
        print(f"Commit hash {short_hash} saved successfully.")

    print(f"{output_file} generated successfully.")
