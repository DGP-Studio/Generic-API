import datetime
import time
import os
import redis
from datetime import date, timedelta
from scheduler import Scheduler
import config  # DO NOT REMOVE
from base_logger import logger
from mysql_app.schemas import DailyActiveUserStats, DailyEmailSentStats
from mysql_app.database import SessionLocal
from mysql_app.crud import dump_daily_active_user_stats, dump_daily_email_sent_stats


scan_duration = int(os.getenv("CENSOR_FILE_SCAN_DURATION", 30))  # Scan duration in *minutes*
tz_shanghai = datetime.timezone(datetime.timedelta(hours=8))
print(f"Scan duration: {scan_duration} minutes.")


def dump_daily_active_user_data() -> None:
    db = SessionLocal()
    redis_conn = redis.Redis(host="redis", port=6379, db=0)

    active_users_cn = redis_conn.scard("stat:active_users:cn")
    delete_cn_result = redis_conn.delete("stat:active_users:cn")
    logger.info(f"active_user_cn: {active_users_cn}, delete result: {delete_cn_result}")

    active_users_global = redis_conn.scard("stat:active_users:global")
    delete_global_result = redis_conn.delete("stat:active_users:global")
    logger.info(f"active_users_global: {active_users_global}, delete result: {delete_global_result}")

    active_users_unknown = redis_conn.scard("stat:active_users:unknown")
    delete_unknown_result = redis_conn.delete("stat:active_users:unknown")
    logger.info(f"active_users_unknown: {active_users_unknown}, delete result: {delete_unknown_result}")

    yesterday_date = date.today() - timedelta(days=1)
    daily_active_user_data = DailyActiveUserStats(date=yesterday_date, cn_user=active_users_cn,
                                                  global_user=active_users_global, unknown=active_users_unknown)
    logger.info(f"Daily active data of {yesterday_date}: {daily_active_user_data}; Data generated at {datetime.datetime.now()}.")
    dump_daily_active_user_stats(db, daily_active_user_data)
    db.close()
    logger.info(f"Daily active user data dumped at {datetime.datetime.now()}.")


def dump_daily_email_sent_data() -> None:
    db = SessionLocal()
    redis_conn = redis.Redis(host="redis", port=6379, db=0)

    email_requested = redis_conn.getdel("stat:email_requested")
    email_sent = redis_conn.getdel("stat:email_sent")
    email_failed = redis_conn.getdel("stat:email_failed")
    logger.info(f"email_requested: {email_requested}; email_sent: {email_sent}; email_failed: {email_failed}")

    yesterday_date = date.today() - timedelta(days=1)
    daily_email_sent_data = DailyEmailSentStats(date=yesterday_date, requested=email_requested, sent=email_sent, failed=email_failed)
    logger.info(f"Daily email sent data of {yesterday_date}: {daily_email_sent_data}; Data generated at {datetime.datetime.now()}.")
    dump_daily_email_sent_stats(db, daily_email_sent_data)
    db.close()
    logger.info(f"Daily email sent data dumped at {datetime.datetime.now()}.")


if __name__ == "__main__":
    schedule = Scheduler(tzinfo=tz_shanghai)
    schedule.daily(datetime.time(hour=0, minute=0, tzinfo=tz_shanghai), dump_daily_active_user_data)
    while True:
        schedule.exec_jobs()
        time.sleep(1)
        current_minute = datetime.datetime.now().minute
        if current_minute == 0 or current_minute == 30:
            print(schedule)
