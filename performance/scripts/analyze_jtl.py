# -*- coding: utf-8 -*-
"""
JMeter JTL 结果分析脚本
用法：python analyze_jtl.py results/smoke.jtl   （可传多个文件）
输出：控制台统计表 + 同目录 CSV（多文件时自动对比）
"""
import csv
import os
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding="utf-8")
TZ = timezone(timedelta(hours=8))  # 北京时间


def load(path):
    rows = []
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # 跳过 JMeter 的统计汇总行（如果有）
            if not r.get("timeStamp", "").strip().isdigit() and "|" in r.get("timeStamp", ""):
                continue
            try:
                rows.append({
                    "ts": int(r["timeStamp"]) / 1000,
                    "elapsed": int(r["elapsed"]),
                    "code": r.get("responseCode", ""),
                    "msg": r.get("responseMessage", ""),
                    "success": str(r.get("success", "")).lower() == "true",
                    "failure": r.get("failureMessage", "") or "",
                    "bytes": int(r["bytes"]) if r.get("bytes", "").isdigit() else 0,
                    "connect": int(r["Connect"]) if r.get("Connect", "").isdigit() else 0,
                    "latency": int(r["Latency"]) if r.get("Latency", "").isdigit() else 0,
                })
            except (ValueError, KeyError):
                continue
    return rows


def pct(data, p):
    """百分位数（线性插值，和 JMeter HTML 报告口径接近）"""
    if not data:
        return 0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100)
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 1)


def analyze(path):
    rows = load(path)
    if not rows:
        return None
    t0, t1 = min(r["ts"] for r in rows), max(r["ts"] + r["elapsed"] / 1000 for r in rows)
    dur = max(t1 - t0, 0.001)
    ok = [r for r in rows if r["success"]]
    bad = [r for r in rows if not r["success"]]
    rt = [r["elapsed"] for r in rows]

    return {
        "file": os.path.basename(path),
        "start": datetime.fromtimestamp(t0, TZ).strftime("%Y-%m-%d %H:%M:%S"),
        "duration": round(dur, 1),
        "samples": len(rows),
        "success": len(ok),
        "failed": len(bad),
        "error_pct": round(len(bad) / len(rows) * 100, 2),
        "tps": round(len(rows) / dur, 2),
        "avg": round(statistics.mean(rt), 1),
        "median": round(statistics.median(rt), 1),
        "p90": pct(rt, 90),
        "p95": pct(rt, 95),
        "p99": pct(rt, 99),
        "min": min(rt),
        "max": max(rt),
        "avg_connect": round(statistics.mean([r["connect"] for r in rows]), 1),
        "avg_latency": round(statistics.mean([r["latency"] for r in rows]), 1),
        "total_mb": round(sum(r["bytes"] for r in rows) / 1024 / 1024, 2),
        "errors": Counter(
            f'{r["code"]} {r["msg"][:40]} {r["failure"][:60]}'.strip() for r in bad
        ),
    }


def print_one(s):
    print("=" * 74)
    print(f'文件: {s["file"]}')
    print("=" * 74)
    print(f'  开始时间      : {s["start"]}')
    print(f'  实际运行时长  : {s["duration"]} 秒')
    print(f'  总请求数      : {s["samples"]}')
    print(f'  成功 / 失败   : {s["success"]} / {s["failed"]}')
    print(f'  错误率        : {s["error_pct"]} %')
    print(f'  TPS(吞吐量)   : {s["tps"]} 次/秒')
    print("-" * 74)
    print(f'  平均响应时间  : {s["avg"]} ms')
    print(f'  中位数(50%)   : {s["median"]} ms')
    print(f'  90 线         : {s["p90"]} ms')
    print(f'  95 线         : {s["p95"]} ms')
    print(f'  99 线         : {s["p99"]} ms')
    print(f'  最小 / 最大   : {s["min"]} / {s["max"]} ms')
    print("-" * 74)
    print(f'  平均建连时间  : {s["avg_connect"]} ms')
    print(f'  平均延迟      : {s["avg_latency"]} ms')
    print(f'  总接收数据量  : {s["total_mb"]} MB')
    if s["errors"]:
        print("-" * 74)
        print("  错误明细:")
        for k, v in s["errors"].most_common():
            print(f'    {v} 次: {k}')
    print()


if __name__ == "__main__":
    args = sys.argv[1:]
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT = os.path.dirname(SCRIPT_DIR)          # jmeter 根目录
    RESULT_DIR = os.path.join(ROOT, "results")
    if not args:
        # 默认分析 results 目录下所有 jtl
        args = [os.path.join(RESULT_DIR, f) for f in sorted(os.listdir(RESULT_DIR)) if f.endswith(".jtl")]
    stats = [analyze(p) for p in args]
    stats = [s for s in stats if s]
    for s in stats:
        print_one(s)

    if len(stats) > 1:
        print("=" * 74)
        print("对比总表")
        print("=" * 74)
        print("%-22s %8s %8s %10s %10s %10s" % ("文件", "TPS", "平均(ms)", "95线(ms)", "错误率%", "请求数"))
        for s in stats:
            print("%-22s %8s %8s %10s %10s %10s" % (
                s["file"], s["tps"], s["avg"], s["p95"], s["error_pct"], s["samples"]))

        out = os.path.join(RESULT_DIR, "压测指标汇总.csv")
        with open(out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["文件", "开始时间", "时长(秒)", "总请求数", "成功", "失败", "错误率%",
                        "TPS", "平均RT(ms)", "中位数", "90线", "95线", "99线", "最小", "最大", "接收MB"])
            for s in stats:
                w.writerow([s["file"], s["start"], s["duration"], s["samples"], s["success"],
                            s["failed"], s["error_pct"], s["tps"], s["avg"], s["median"],
                            s["p90"], s["p95"], s["p99"], s["min"], s["max"], s["total_mb"]])
        print(f"\n汇总已保存: {out}")
