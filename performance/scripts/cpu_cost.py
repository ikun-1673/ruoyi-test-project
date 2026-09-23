"""单请求 CPU 成本测量：串行发压 + psutil cpu_times() 差值
用途：《压测报告.md》6.2 节量化证据——对比 POST /login 与 GET /system/user/list
     的单请求后端 CPU 成本，推算 bcrypt 等登录特有逻辑的占比。
方法：先预热（消除 JVM JIT/连接池冷启动影响），再串行发 N 次请求；
     测量前后读取后端进程 cpu_times() 总时间差与墙钟时间差，除以请求数。
     串行模式下测量窗口内基本只有后端在算，进程 CPU 差值≈这批请求的成本。
运行：python cpu_cost.py [N]   （默认 N=50）
前置：若依后端运行于 localhost:8080，验证码开关已关；pip install psutil requests
"""
import sys
import time

import psutil
import requests

BASE = "http://localhost:8080"
WARMUP = 10          # 预热请求数（不计入测量）
BACKEND_PORT = 8080


def find_backend_pid(port=BACKEND_PORT):
    """找到监听指定端口的进程 PID"""
    for conn in psutil.net_connections(kind="inet"):
        if conn.status == "LISTEN" and conn.laddr.port == port and conn.pid:
            return conn.pid
    return None


def measure(pid, n, make_request):
    """预热 WARMUP 次后串行发 n 次，返回 (单请求CPU毫秒, 单请求墙钟毫秒)"""
    for _ in range(WARMUP):
        make_request()
    p = psutil.Process(pid)
    cpu0 = sum(p.cpu_times()[:2])          # user + system（秒）
    t0 = time.perf_counter()
    for _ in range(n):
        make_request()
    cpu1 = sum(p.cpu_times()[:2])
    t1 = time.perf_counter()
    cpu_ms = (cpu1 - cpu0) * 1000 / n
    wall_ms = (t1 - t0) * 1000 / n
    return cpu_ms, wall_ms


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    pid = find_backend_pid()
    if not pid:
        sys.exit("未找到监听 %d 的后端进程，请确认若依已启动" % BACKEND_PORT)
    print("后端进程 PID =", pid, "｜ 测量次数 =", n, "｜ 预热 =", WARMUP)

    # 登录请求：每次完整走 bcrypt 校验 + token 生成 + 登录日志
    def login():
        r = requests.post(BASE + "/login",
                          json={"username": "admin", "password": "admin123",
                                "code": "", "uuid": ""}, timeout=30)
        assert r.json().get("code") == 200, "登录失败: %s" % r.text
        return r.json()["token"]

    token = login()

    # 高频读取接口：无 bcrypt，仅 token 校验 + SQL 查询（对照组）
    def user_list():
        r = requests.get(BASE + "/system/user/list",
                         headers={"Authorization": "Bearer " + token},
                         params={"pageNum": 1, "pageSize": 10}, timeout=30)
        assert r.json().get("code") == 200, "列表查询失败: %s" % r.text

    login_cpu, login_wall = measure(pid, n, login)
    list_cpu, list_wall = measure(pid, n, user_list)
    diff = login_cpu - list_cpu

    print("-" * 64)
    print("%-28s %12s %12s" % ("请求", "CPU(ms/次)", "墙钟(ms/次)"))
    print("%-28s %12.1f %12.1f" % ("POST /login", login_cpu, login_wall))
    print("%-28s %12.1f %12.1f" % ("GET /system/user/list", list_cpu, list_wall))
    print("%-28s %12.1f %12s" % ("差值（bcrypt 等登录特有）", diff, "-"))
    print("-" * 64)
    if login_cpu > 0:
        print("登录特有逻辑占单次登录 CPU 比例: %.1f%%" % (diff / login_cpu * 100))
    print("理论吞吐上限参考: 逻辑核数 %d ÷ 单次登录 CPU %.3fs ≈ %.0f TPS（后端独占 CPU 时）"
          % (psutil.cpu_count(logical=True), login_cpu / 1000,
             psutil.cpu_count(logical=True) / (login_cpu / 1000) if login_cpu else 0))


if __name__ == "__main__":
    main()
