import os
import subprocess
from dotenv import load_dotenv


def get_short_commit_hash(length=7):
    try:
        short_hash_result = subprocess.check_output(['git', 'rev-parse', f'--short={length}', 'HEAD']).strip().decode('utf-8')
        return short_hash_result
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        return None


def get_container_ip(container_name):
    try:
        result = subprocess.check_output(
            [
                'docker',
                'inspect',
                '-f',
                '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}',
                container_name,
            ]
        )
    except subprocess.CalledProcessError as e:
        error_output = e.output.decode('utf-8', errors='ignore').strip()
        raise RuntimeError(
            f"Failed to retrieve IP address for container {container_name}: {error_output}"
        ) from e
    except FileNotFoundError as e:
        raise RuntimeError("Docker is not available on this system.") from e

    container_ip = result.decode('utf-8').strip()
    if not container_ip:
        raise RuntimeError(f"Failed to retrieve IP address for container {container_name}")

    return container_ip


def update_env_file(env_file_path, key, value):
    if not os.path.exists(env_file_path):
        raise RuntimeError(
            f"Environment file '{env_file_path}' not found. Please ensure it contains a {key} entry."
        )

    with open(env_file_path, 'r', encoding='utf-8') as env_file:
        env_lines = env_file.readlines()

    for index, line in enumerate(env_lines):
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith('#'):
            continue

        variable, separator, _ = line.partition('=')
        if separator and variable.strip() == key:
            newline = '\n' if line.endswith('\n') else ''
            env_lines[index] = f"{variable}{separator}{value}{newline}"
            break
    else:
        raise RuntimeError(
            f"{key} was not found in {env_file_path}. Please add it manually to avoid duplicate entries."
        )

    with open(env_file_path, 'w', encoding='utf-8') as env_file:
        env_file.writelines(env_lines)


if __name__ == "__main__":
    env_file = ".env"
    container_name = "Homa-Server"

    try:
        container_ip = get_container_ip(container_name)
        update_env_file(env_file, "HOMA_SERVER_IP", container_ip)
        os.environ["HOMA_SERVER_IP"] = container_ip
        print(f"Updated {env_file} with HOMA_SERVER_IP={container_ip}")
    except RuntimeError as error:
        raise SystemExit(error)

    load_dotenv(dotenv_path=env_file, override=True)

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
