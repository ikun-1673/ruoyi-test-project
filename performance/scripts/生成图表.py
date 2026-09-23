# -*- coding: utf-8 -*-
"""
从 JTL + 监控数据生成 README 用的趋势图
用法：python 生成图表.py
输出：charts/01_核心指标趋势.png、charts/02_瓶颈分析.png
"""
import csv
import glob
import os
import sys
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_jtl import analyze  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPT_DIR)          # jmeter 根目录
CHART_DIR = os.path.join(BASE, "charts")
os.makedirs(CHART_DIR, exist_ok=True)

# 中文字体
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 130

TIERS = [("result_50", 50), ("result_100", 100), ("result_200", 200), ("result_300", 300)]
TIER_WINDOWS = {
    50: ("11:01:53", "11:03:53"),
    100: ("11:08:36", "11:10:37"),
    200: ("11:11:43", "11:13:45"),
    300: ("11:14:54", "11:16:57"),
}

# ---------- 读取指标 ----------
stats = []
for tag, threads in TIERS:
    s = analyze(os.path.join(BASE, "results", f"{tag}.jtl"))
    s["threads"] = threads
    stats.append(s)

threads = [s["threads"] for s in stats]
tps = [s["tps"] for s in stats]
avg = [s["avg"] for s in stats]
p95 = [s["p95"] for s in stats]
p99 = [s["p99"] for s in stats]
err = [s["error_pct"] for s in stats]

# ---------- 读取监控 CPU ----------
cpu_by_tier = {}
mf = glob.glob(os.path.join(BASE, "results", "monitor_*.csv"))
if mf:
    rows = list(csv.DictReader(open(mf[0], encoding="utf-8-sig")))
    for t in threads:
        t0, t1 = TIER_WINDOWS[t]
        win = [r for r in rows if t0 <= r["时间"] <= t1]
        vals = []
        for r in win:
            try:
                vals.append(float(r["系统总CPU%"]))
            except (ValueError, TypeError):
                pass
        cpu_by_tier[t] = sum(vals) / len(vals) if vals else None

# ============ 图 1：核心指标趋势（2×2）============
fig, axes = plt.subplots(2, 2, figsize=(13, 8.5))
fig.subplots_adjust(hspace=0.42, wspace=0.28, top=0.90, bottom=0.08, left=0.07, right=0.97)
fig.suptitle("若依登录接口阶梯压测 · 核心指标趋势（每档 120 秒）",
             fontsize=14, fontweight="bold")

# (1) TPS
ax = axes[0][0]
ax.plot(threads, tps, "o-", color="#2E75B6", lw=2.5, ms=8, label="实测 TPS")
ax.axhline(y=60, color="#C00000", ls="--", lw=1.5, alpha=0.7)
ax.text(55, 62, "吞吐平台期 ≈ 60 TPS", color="#C00000", fontsize=10)
ax.scatter([5], [16.26], color="#7F7F7F", s=70, zorder=5, label="冒烟基线（5线程）")
ax.set_title("① TPS 趋势：50 线程后饱和", fontsize=12, fontweight="bold")
ax.set_xlabel("并发线程数")
ax.set_ylabel("TPS（次/秒）")
ax.set_ylim(0, 85)
ax.set_xlim(0, 320)
ax.grid(alpha=0.3)
ax.legend(fontsize=9, loc="lower right")

# (2) 响应时间
ax = axes[0][1]
ax.plot(threads, avg, "o-", color="#2E75B6", lw=2.5, ms=7, label="平均")
ax.plot(threads, p95, "s-", color="#ED7D31", lw=2.5, ms=7, label="95 线")
ax.plot(threads, p99, "^-", color="#A5A5A5", lw=2, ms=7, label="99 线")
ax.axhline(y=2000, color="#C00000", ls="--", lw=1.8)
ax.text(52, 2150, "SLA 阈值 2000ms", color="#C00000", fontsize=10)
ax.fill_between([100, 200], 0, 7000, color="#FFE699", alpha=0.35)
ax.text(125, 6300, "SLA 失守区", color="#BF8F00", fontsize=10, fontweight="bold")
ax.set_title("② 响应时间：随并发线性恶化", fontsize=12, fontweight="bold")
ax.set_xlabel("并发线程数")
ax.set_ylabel("响应时间（ms）")
ax.set_ylim(0, 7000)
ax.set_xlim(40, 310)
ax.grid(alpha=0.3)
ax.legend(fontsize=9)

# (3) 错误率
ax = axes[1][0]
bars = ax.bar([str(t) for t in threads], err,
              color=["#70AD47", "#FFC000", "#C00000", "#C00000"], width=0.55)
for b, v in zip(bars, err):
    ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v}%",
            ha="center", fontsize=11, fontweight="bold")
ax.set_title("③ 错误率：全部为\"响应>2s\"的 SLA 违约（零 HTTP 错误）",
             fontsize=12, fontweight="bold")
ax.set_xlabel("并发线程数")
ax.set_ylabel("错误率（%）")
ax.set_ylim(0, 112)
ax.grid(alpha=0.3, axis="y")

# (4) 系统 CPU
ax = axes[1][1]
if cpu_by_tier and any(cpu_by_tier.values()):
    cpus = [cpu_by_tier.get(t, 0) for t in threads]
    bars = ax.bar([str(t) for t in threads], cpus, color="#4472C4", width=0.55)
    for b, v in zip(bars, cpus):
        ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}%",
                ha="center", fontsize=11, fontweight="bold")
    ax.axhline(y=100, color="#C00000", ls="--", lw=1.5, alpha=0.8)
    ax.annotate("CPU 打满", xy=(3, 100), xytext=(1.5, 116),
                color="#C00000", fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#C00000", lw=1.3))
ax.set_title("④ 压测机系统 CPU：全程打满（瓶颈证据）", fontsize=12, fontweight="bold")
ax.set_xlabel("并发线程数")
ax.set_ylabel("系统 CPU（%）")
ax.set_ylim(0, 128)
ax.grid(alpha=0.3, axis="y")

out1 = os.path.join(CHART_DIR, "01_核心指标趋势.png")
plt.savefig(out1, bbox_inches="tight")
plt.close()
print("已生成:", out1)

# ============ 图 2：瓶颈分析 ============
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
fig.subplots_adjust(top=0.82, bottom=0.22, wspace=0.3, left=0.08, right=0.97)
fig.suptitle("登录接口 CPU 成本分解与吞吐上限推算", fontsize=14, fontweight="bold")

# 左：单次请求 CPU 成本
ax = axes[0]
labels = ["bcrypt 与登录\n特有逻辑", "登录其余开销\n(SQL/token/日志)", "对照：用户查询接口\n(无 bcrypt)"]
values = [189, 25, 25]
colors = ["#C00000", "#2E75B6", "#A5A5A5"]
bars = ax.bar(labels, values, color=colors, width=0.55)
for b, v in zip(bars, values):
    ax.text(b.get_x() + b.get_width() / 2, v + 5, f"{v} ms", ha="center",
            fontsize=11, fontweight="bold")
ax.set_ylabel("单次请求 CPU 成本（ms）")
ax.set_title("① 单次登录 CPU = 214ms，其中 bcrypt 类逻辑占 88%", fontsize=11)
ax.grid(alpha=0.3, axis="y")
ax.set_ylim(0, 235)

# 右：吞吐上限推算
ax = axes[1]
names = ["理论上限\n(后端独占 16 核)", "实测峰值\n(200 线程)"]
vals = [75, 63]
colors = ["#70AD47", "#ED7D31"]
bars = ax.bar(names, vals, color=colors, width=0.42)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v} TPS", ha="center",
            fontsize=11, fontweight="bold")
ax.annotate("达到理论上限的 84%", xy=(1, 63), xytext=(0.15, 78),
            color="#C00000", fontsize=10, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#C00000", lw=1.3))
ax.set_ylabel("TPS（次/秒）")
ax.set_title("② 实测峰值与理论推算互相印证（瓶颈 = CPU）", fontsize=11)
ax.grid(alpha=0.3, axis="y")
ax.set_ylim(0, 95)

out2 = os.path.join(CHART_DIR, "02_瓶颈分析.png")
plt.savefig(out2, bbox_inches="tight")
plt.close()
print("已生成:", out2)
