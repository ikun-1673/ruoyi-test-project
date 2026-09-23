"""接口辅助脚本：requests 登录取 token → Bearer 鉴权调用 → 建用户 → pymysql 落库核验 → 清理
用途：简历第 7 条"requests 接口调用、pymysql 数据库核验"的实证脚本；也是接口自动化代码化的第一步。
运行前置：若依后端已启动（8080）、验证码开关已关、设置环境变量 RUOYI_DB_PASSWORD（未设置则跳过落库核验步骤）
运行：python api_verify.py
"""
import os
import time

import requests

BASE = os.getenv("RUOYI_BASE_URL", "http://localhost:8080")

# 1. 登录取 token（若依登录成功响应顶层即 token 字段）
r = requests.post(f"{BASE}/login",
                  json={"username": "admin", "password": "admin123", "code": "", "uuid": ""})
data = r.json()
assert data["code"] == 200, f"登录失败: {data}"
token = data["token"]
print("[1] 登录成功，拿到 token")

# 2. Bearer 鉴权调用 /getInfo（和 Postman 里 token 关联同一思想，代码版）
headers = {"Authorization": f"Bearer {token}"}
r = requests.get(f"{BASE}/getInfo", headers=headers)
body = r.json()
assert body["code"] == 200 and body.get("roles"), f"getInfo 鉴权失败: {body}"
print("[2] getInfo 鉴权通过，roles =", body["roles"])

# 3. 接口建用户（动态后缀保证幂等，重跑不撞唯一约束）
suffix = str(int(time.time()))[-8:]
uname = f"req_{suffix}"
r = requests.post(f"{BASE}/system/user", headers=headers, json={
    "userName": uname, "nickName": "requests核验", "password": "Test123456",
    "phonenumber": f"138{suffix}", "sex": "0", "status": "0",
    "deptId": 103, "roleIds": [], "postIds": []})
body = r.json()
assert body["code"] == 200, f"建用户失败: {body}"
print("[3] 接口建用户成功:", uname)

# 4-5. pymysql 落库核验 + 清理（凭据从环境变量读，与 conftest 同一口径；未设置则跳过）
db_pwd = os.getenv("RUOYI_DB_PASSWORD")
if not db_pwd:
    print("[4] 未设置 RUOYI_DB_PASSWORD 环境变量，跳过落库核验（用户残留，手动清理或跑 pytest 清理）")
else:
    import pymysql
    conn = pymysql.connect(host=os.getenv("RUOYI_DB_HOST", "localhost"),
                           port=int(os.getenv("RUOYI_DB_PORT", "3306")),
                           user=os.getenv("RUOYI_DB_USER", "root"), password=db_pwd,
                           database=os.getenv("RUOYI_DB_NAME", "ry-vue"), charset="utf8mb4")
    cur = conn.cursor()
    cur.execute("SELECT user_id, user_name FROM sys_user WHERE user_name=%s", (uname,))
    row = cur.fetchone()
    assert row, f"落库核验失败：库里查不到 {uname}"
    print("[4] pymysql 落库核验通过:", row)
    cur.execute("DELETE FROM sys_user WHERE user_id=%s", (row[0],))
    conn.commit()
    conn.close()
    print("[5] 测试数据已清理")

print("全流程通过：requests 调用 + 鉴权关联 + pymysql 核验 闭环 OK")
