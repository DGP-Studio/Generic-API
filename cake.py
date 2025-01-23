import os
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()

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

    print(f"{output_file} generated successfully.")
