from datetime import datetime, timezone

# 获取当前时间
now = datetime.now()

# 获取系统时区的 UTC 偏差
utc_offset = datetime.now().astimezone().utcoffset().total_seconds() / 3600

# 打印 UTC 偏差
print(f"当前系统时区: {now.astimezone().tzname()}")  # 系统时区名称
print(f"当前系统时区的 UTC 偏差值: {utc_offset:+.0f} 小时")
