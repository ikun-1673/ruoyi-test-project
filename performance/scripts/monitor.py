# -*- coding: utf-8 -*-
"""
压测实时监控脚本（P3 用）
--------------------------------------------------------------------------
用法：
    双击运行 或 命令行执行：python monitor.py
    运行后保持窗口开着，压测期间每 2 秒刷新一次；Ctrl+C 停止

输出：
    ① 控制台实时数据
    ② 同目录下 monitor_YYYYmmdd_HHMMSS.csv（压测结束后贴给我分析）

监控内容：
    系统总 CPU / 可用内存
    若依后端进程（java，监听 8080）的 CPU 与内存
    JMeter 进程（java）的 CPU 与内存
    MySQL 进程（mysqld）的 CPU 与内存
    MySQL 连接数（Threads_connected / Threads_running）
"""
import csv
import datetime
import os
import subprocess
import sys
import time

import psutil
import pymysql

sys.stdout.reconfigure(encoding="utf-8")

# ============ 配置区（如需修改只改这里） ============
BACKEND_PORT = 8080                 # 若依后端端口
INTERVAL = 2                        # 采样间隔（秒）
DB = dict(host="127.0.0.1", port=3306, user="root",
          password="123456", database="ry-vue", charset="utf8mb4")
# ==================================================

_proc_cache = {}   # pid -> (采样时间, 累计CPU时间)，用于计算进程CPU占用率


def find_backend_pid():
    """通过端口 8080 找到后端 java 进程 PID"""
    try:
        out = subprocess.check_output("netstat -ano", shell=True,
                                      stderr=subprocess.DEVNULL).decode("gbk", "ignore")
        for line in out.splitlines():
            if ":%d" % BACKEND_PORT in line and "LISTENING" in line:
                return int(line.split()[-1])
    except Exception:
        pass
    return None


def proc_stats(pid):
    """返回 (cpu%, rss_MB)，进程不存在返回 (None, None)
    说明：不使用 psutil.cpu_percent（每次新建 Process 对象会因缺少基线而恒为 0），
    改用 cpu_times 差值计算，稳定可靠。"""
    global _proc_cache
    now = time.time()
    try:
        p = psutil.Process(pid)
        ct = p.cpu_times()
        total = ct.user + ct.system
        mem = round(p.memory_info().rss / 1024 / 1024, 1)
        prev = _proc_cache.get(pid)
        _proc_cache[pid] = (now, total)
        if prev and now - prev[0] > 0:
            return round((total - prev[1]) / (now - prev[0]) * 100, 1), mem
        return 0.0, mem
    except Exception:
        _proc_cache.pop(pid, None)
        return None, None


def find_by_name(name):
    """按进程名找 PID 列表"""
    pids = []
    for p in psutil.process_iter(["pid", "name"]):
        try:
            if p.info["name"] and name.lower() in p.info["name"].lower():
                pids.append(p.info["pid"])
        except Exception:
            continue
    return pids


def mysql_connections():
    """MySQL 连接数"""
    try:
        conn = pymysql.connect(**DB, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SHOW STATUS LIKE 'Threads_connected'")
        connected = int(cur.fetchone()[1])
        cur.execute("SHOW STATUS LIKE 'Threads_running'")
        running = int(cur.fetchone()[1])
        conn.close()
        return connected, running
    except Exception:
        return None, None


def main():
    print("=" * 78)
    print("  若依压测实时监控  |  每 %d 秒采样  |  Ctrl+C 停止" % INTERVAL)
    print("=" * 78)

    # 初始化 CPU 采样（第一次调用返回 0，先预热）
    psutil.cpu_percent(interval=None)
    backend_pid = find_backend_pid()
    print("  后端进程 PID（监听 %d）: %s" % (BACKEND_PORT, backend_pid or "未找到！请确认后端已启动"))
    print("-" * 78)
    print("%-8s %-7s %-9s %-13s %-13s %-12s %s" %
          ("时间", "总CPU%", "可用内存", "后端CPU/内存", "JMeter CPU/内存", "MySQL CPU", "DB连接(活/运)"))
    print("-" * 78)

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # 脚本位于 scripts/ 下，CSV 统一输出到上一级目录的 results/
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _out_dir = os.path.join(_root, "results")
    os.makedirs(_out_dir, exist_ok=True)
    csv_path = os.path.join(_out_dir, "monitor_%s.csv" % ts)
    f = open(csv_path, "w", newline="", encoding="utf-8-sig")
    writer = csv.writer(f)
    writer.writerow(["时间", "系统总CPU%", "可用内存MB", "后端CPU%", "后端内存MB",
                     "JMeterCPU%", "JMeter内存MB", "MySQLCPU%", "MySQL内存MB",
                     "DB连接数", "DB活跃连接"])

    last_summary = 0
    try:
        while True:
            now = datetime.datetime.now().strftime("%H:%M:%S")
            cpu = psutil.cpu_percent(interval=None)
            avail = round(psutil.virtual_memory().available / 1024 / 1024)

            if backend_pid is None or not psutil.pid_exists(backend_pid):
                backend_pid = find_backend_pid()
            b_cpu, b_mem = proc_stats(backend_pid) if backend_pid else (None, None)

            # JMeter = 除后端外的 java 进程，取 CPU 最高的那个
            j_cpu = j_mem = None
            best = -1
            for pid in find_by_name("java"):
                if pid == backend_pid:
                    continue
                c, m = proc_stats(pid)
                if c is not None and c > best:
                    best, j_cpu, j_mem = c, c, m

            m_cpu = m_mem = None
            for pid in find_by_name("mysqld"):
                c, m = proc_stats(pid)
                if c is not None:
                    m_cpu, m_mem = c, m
                    break

            db_conn, db_run = mysql_connections()

            b_str = "%s%% / %sMB" % (round(b_cpu) if b_cpu is not None else "-",
                                     b_mem if b_mem is not None else "-")
            j_str = "%s%% / %sMB" % (round(j_cpu) if j_cpu is not None else "-",
                                     j_mem if j_mem is not None else "-")
            m_str = "%s%%" % (round(m_cpu) if m_cpu is not None else "-")
            db_str = "%s / %s" % (db_conn if db_conn is not None else "-",
                                  db_run if db_run is not None else "-")

            print("%-8s %-7s %-9s %-13s %-13s %-12s %s" %
                  (now, round(cpu), "%sMB" % avail, b_str, j_str, m_str, db_str))

            writer.writerow([now, round(cpu), avail,
                             round(b_cpu) if b_cpu is not None else "",
                             b_mem if b_mem is not None else "",
                             round(j_cpu) if j_cpu is not None else "",
                             j_mem if j_mem is not None else "",
                             round(m_cpu) if m_cpu is not None else "",
                             m_mem if m_mem is not None else "",
                             db_conn if db_conn is not None else "",
                             db_run if db_run is not None else ""])
            f.flush()
            time.sleep(INTERVAL)
    except KeyboardInterrupt:
        print("\n" + "-" * 78)
        print("监控已停止，数据已保存：%s" % csv_path)
        print("把这个 CSV 文件路径发给 AI 做瓶颈分析即可。")
    finally:
        f.close()


if __name__ == "__main__":
    main()
