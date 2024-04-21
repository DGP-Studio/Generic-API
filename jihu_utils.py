import concurrent.futures
import json
import time
import os
import httpx
import tarfile
import shutil
import redis
import schedule
from datetime import date, timedelta
import config  # DO NOT REMOVE
from utils.email_utils import send_system_email
from mysql_app.schemas import DailyActiveUserStats
from mysql_app.database import SessionLocal
from mysql_app.crud import dump_daily_active_user_stats
from base_logger import logger

scan_duration = int(os.getenv("CENSOR_FILE_SCAN_DURATION", 30))


def process_file(upstream_github_repo: str, jihulab_repo: str, branch: str, file: str) -> tuple:
    file_path = "upstream/" + upstream_github_repo.split('/')[1] + "-" + branch + "/" + file
    checked_time = 0
    censored_files = []
    broken_json_files = []
    while checked_time < 3:
        try:
            logger.info(f"Checking file: {file}")
            url = f"https://jihulab.com/{jihulab_repo}/-/raw/main/{file}"
            headers = {
                "Accept-Language": "zh-CN;q=0.8,zh;q=0.7"
            }
            resp = httpx.get(url, headers=headers)
            text_raw = resp.text
        except Exception:
            logger.exception(f"Failed to check file: {file}, retry after 3 seconds...")
            checked_time += 1
            time.sleep(3)
            continue
        if "根据相关法律政策" in text_raw or "According to the relevant laws and regulations" in text_raw:
            logger.warning(f"Found censored file: {file}")
            censored_files.append(file)
        elif file.endswith(".json"):
            try:
                resp.json()
            except json.JSONDecodeError:
                logger.warning(f"Found non-json file: {file}")
                broken_json_files.append(file)
        break
    os.remove(file_path)
    return censored_files, broken_json_files


def jihulab_regulatory_checker(upstream_github_repo: str, jihulab_repo: str, branch: str) -> list:
    """
    Compare the mirror between GitHub and gitlab.
    :param upstream_github_repo: name of the GitHub repository such as 'kubernetes/kubernetes'
    :param jihulab_repo: name of the gitlab repository such as 'kubernetes/kubernetes'
    :param branch: name of the branch such as 'main'
    :return: a list of file which files in downstream are different from upstream
    """
    logger.info(f"Starting regulatory checker for {jihulab_repo}...")
    os.makedirs("./cache", exist_ok=True)
    if os.path.exists("./cache/censored_files.json"):
        with open("./cache/censored_files.json", "r", encoding="utf-8") as f:
            content = f.read()
        older_censored_files = json.loads(content)
        # If last modified time is less than 30 minutes, skip this check
        if time.time() - os.path.getmtime("./cache/censored_files.json") < 60 * scan_duration:
            logger.info(f"Last check is less than {60 * scan_duration} minutes, skip this check.")
            return older_censored_files
    else:
        older_censored_files = []
    censored_files = []
    broken_json_files = []

    # Download and unzip upstream content
    os.makedirs("upstream", exist_ok=True)
    github_live_archive = f"https://codeload.github.com/{upstream_github_repo}/tar.gz/refs/heads/{branch}"
    with httpx.stream("GET", github_live_archive) as resp:
        with open("upstream.tar.gz", "wb") as f:
            for data in resp.iter_bytes():
                f.write(data)
    with tarfile.open("upstream.tar.gz") as f:
        f.extractall("upstream")
    upstream_files = []
    for root, dirs, files in os.walk(f"upstream/{upstream_github_repo.split('/')[1]}-{branch}/"):
        for file in files:
            file_path = os.path.join(root, file)
            file_path = file_path.replace(f"upstream/{upstream_github_repo.split('/')[1]}-{branch}/", "")
            file_path = file_path.replace("\\", "/")
            upstream_files.append(file_path)
    logger.info(f"Current upstream files: {upstream_files}")

    cpu_count = os.cpu_count()

    def process_file_wrapper(file_name: str):
        nonlocal censored_files, broken_json_files
        censored, broken_json = process_file(upstream_github_repo, jihulab_repo, branch, file_name)
        censored_files.extend(censored)
        broken_json_files.extend(broken_json)

    with concurrent.futures.ThreadPoolExecutor(max_workers=cpu_count) as executor:
        executor.map(process_file_wrapper, upstream_files)

    # Merge two lists
    censored_files += broken_json_files
    censored_files = list(set(censored_files))
    url_list = [f"https://jihulab.com/{jihulab_repo}/-/blob/main/{file}" for file in censored_files]

    print("-" * 20)
    logger.info(f"Censored files: {censored_files}")
    for file in url_list:
        logger.info(file)

    # Send email to admin
    if len(censored_files) > 0:
        if len(older_censored_files) == 0:
            # 开始出现被拦截的文件
            email_content = f"致系统管理员：\n\n 检测到 {jihulab_repo} 仓库中的以下文件被审查系统拦截，请及时处理：\n"
            for url in url_list:
                email_content += f"{url}\n"
            email_content += "若内部检查后确认文件内容无违规，请将本邮件转发至 usersupport@gitlab.cn 以做恢复处理。\n\n   -- DGP-Studio 审核系统"
            email_subject = "请求人工复审被拦截的文件 - " + jihulab_repo
            send_system_email(email_subject, email_content, "support@dgp-studio.cn")
        elif censored_files == older_censored_files:
            logger.info("No change in censored file list.")
        else:
            added_files = set(censored_files) - set(older_censored_files)
            different_files = set(censored_files) ^ set(older_censored_files)
            # 开始出现不同的被拦截的文件
            email_content = f"致系统管理员：\n\n 检测到 {jihulab_repo} 仓库中的以下文件被审查系统拦截，请及时处理：\n"
            email_content += "新增被拦截的文件：\n"
            for file in added_files:
                url = f"https://jihulab.com/{jihulab_repo}/-/blob/main/{file}"
                email_content += f"{url}\n"
            email_content += "\n被拦截的文件已恢复访问：\n"
            for file in different_files:
                url = f"https://jihulab.com/{jihulab_repo}/-/blob/main/{file}"
                email_content += f"{url}\n"
            email_content += "若内部检查后确认文件内容无违规，请将本邮件转发至 usersupport@gitlab.cn 以做恢复处理。\n\n   -- DGP-Studio 审核系统"
            email_subject = "请求人工复审被拦截的文件 - " + jihulab_repo
            send_system_email(email_subject, email_content, "support@dgp-studio.cn")
    else:
        if len(older_censored_files) == 0:
            pass
        else:
            email_content = f"致系统管理员：\n\n 检测到 {jihulab_repo} 仓库中的以下文件已恢复：\n"
            for file in older_censored_files:
                email_content += f"https://jihulab.com/{jihulab_repo}/-/blob/main/{file}"
            email_content += "\n   -- DGP-Studio 审核系统"
            email_subject = "被拦截的文件已恢复访问 - " + jihulab_repo
            send_system_email(email_subject, email_content, "support@dgp-studio.cn")

    # Clean up
    os.remove("upstream.tar.gz")
    shutil.rmtree("upstream")
    with open("./cache/censored_files.json", "w+", encoding="utf-8") as f:
        f.write(json.dumps(censored_files, ensure_ascii=False, indent=2))
    return censored_files


def jihulab_regulatory_checker_task() -> None:
    redis_conn = redis.Redis(host="redis", port=6379, db=0)
    regulatory_check_result = jihulab_regulatory_checker("DGP-Studio/Snap.Metadata", "DGP-Studio/Snap.Metadata",
                                                         "main")
    logger.info(f"Regulatory check result: {regulatory_check_result}")
    redis_conn.set("metadata_censored_files", json.dumps(regulatory_check_result), ex=60 * scan_duration * 2)


def dump_daily_active_user_data() -> None:
    db = SessionLocal()
    redis_conn = redis.Redis(host="redis", port=6379, db=1)
    active_users_cn = redis_conn.getdel("active_users_cn")
    active_users_global = redis_conn.getdel("active_users_global")
    active_users_unknown = redis_conn.getdel("active_users_unknown")
    if active_users_cn is None:
        active_users_cn = 0
    if active_users_global is None:
        active_users_global = 0
    if active_users_unknown is None:
        active_users_unknown = 0
    daily_active_user_data = DailyActiveUserStats(date=date.today() - timedelta(days=1), cn_user=active_users_cn,
                                                  global_user=active_users_global, unknown=active_users_unknown)
    dump_daily_active_user_stats(db, daily_active_user_data)


if __name__ == "__main__":
    schedule.every(scan_duration).hour.do(jihulab_regulatory_checker_task)
    schedule.every().day.at("00:00", "Asia/Shanghai").do(dump_daily_active_user_data)
    while True:
        schedule.run_pending()
        time.sleep(1)

