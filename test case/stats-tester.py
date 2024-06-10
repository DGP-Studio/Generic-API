import concurrent.futures
import requests
import uuid


def patch_test():
    while True:
        random_uuid = str(uuid.uuid4())
        headers = {
            "x-device-id": random_uuid,
            "x-region": "cn",
            "user-agent": "Snap Hutao/12.0.0.0"
        }
        response = requests.get("http://127.0.0.1:8080/cn/patch/hutao", headers=headers)
        print(response.status_code)


def run_parallel():
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        futures = [executor.submit(patch_test) for _ in range(32)]
        concurrent.futures.wait(futures)


run_parallel()
