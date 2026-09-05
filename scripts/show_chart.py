"""
اسکریپت نمایش لحظه‌ای چارت یک نماد (بدون نیاز به رسیدن به هشدار).
با GitHub Actions به‌صورت دستی (workflow_dispatch) و با ورودی symbol اجرا می‌شود:
- قیمت لحظه‌ای/آخرین قیمت شناخته‌شده نماد را می‌گیرد
- نمودار ۲ ماه اخیر (روزانه) را با خط تمام هشدارهای ثبت‌شده همان نماد می‌سازد
- پیام + عکس را به تلگرام می‌فرستد
- برخلاف check_alerts.py، به ساعات بازار وابسته نیست و همیشه اجرا می‌شود
"""

import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import mplfinance as mpf
import pytse_client as tse

ALERTS_PATH = "alerts.json"
TEHRAN = ZoneInfo("Asia/Tehran")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SYMBOL = os.environ.get("SYMBOL", "").strip()


def load_alert_prices_for_symbol(symbol: str):
    if not os.path.exists(ALERTS_PATH):
        return []
    with open(ALERTS_PATH, "r", encoding="utf-8") as f:
        alerts = json.load(f)
    return [float(a["targetPrice"]) for a in alerts if a.get("symbol") == symbol]


def build_chart(symbol: str, alert_prices):
    ticker = tse.Ticker(symbol)
    hist = ticker.history.copy()
    hist["date"] = pd.to_datetime(hist["date"])
    hist = hist.set_index("date").sort_index()

    cutoff = hist.index.max() - pd.Timedelta(days=62)
    hist = hist[hist.index >= cutoff]
    hist = hist.rename(columns={
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume",
    })

    levels = sorted(set(float(p) for p in alert_prices))

    mc = mpf.make_marketcolors(
        up="#3FB889", down="#DB5C50", edge="inherit", wick="inherit", volume="inherit"
    )
    style = mpf.make_mpf_style(
        base_mpf_style="nightclouds",
        marketcolors=mc,
        facecolor="#10141A",
        edgecolor="#2A323D",
        gridcolor="#1D2530",
        figcolor="#10141A",
        rc={"axes.labelcolor": "#EDEFF2", "xtick.color": "#8A94A3", "ytick.color": "#8A94A3"},
    )

    plot_kwargs = dict(
        type="candle", style=style, title=f"{symbol} - Live Snapshot",
        ylabel="Price", figsize=(9, 5), returnfig=True,
    )
    if levels:
        plot_kwargs["hlines"] = dict(
            hlines=levels, colors=["#C9973F"] * len(levels), linestyle="--", linewidths=1.2
        )

    fig, axlist = mpf.plot(hist, **plot_kwargs)
    ax = axlist[0]
    for p in levels:
        ax.text(
            1.005, p, f"{p:g}",
            transform=ax.get_yaxis_transform(),
            color="#C9973F", fontsize=9, fontweight="bold",
            va="center", ha="left",
        )

    path = f"/tmp/{symbol}_snapshot.png"
    fig.savefig(path, dpi=150, facecolor="#10141A", bbox_inches="tight")
    return path, ticker, hist


def main():
    if not SYMBOL:
        print("نماد وارد نشده است.")
        return
    if not BOT_TOKEN or not CHAT_ID:
        print("توکن بات یا آیدی چت تلگرام تنظیم نشده (Secrets را بررسی کنید).")
        return

    alert_prices = load_alert_prices_for_symbol(SYMBOL)

    try:
        chart_path, ticker, hist = build_chart(SYMBOL, alert_prices)
    except Exception as e:
        print(f"خطا در دریافت اطلاعات {SYMBOL}: {e}")
        return

    now_str = datetime.now(TEHRAN).strftime("%Y-%m-%d %H:%M")
    last_row = hist.iloc[-1]
    levels_text = "، ".join(f"{p:g}" for p in sorted(set(alert_prices))) or "بدون هشدار ثبت‌شده"
    caption = (
        "📈 نمایش لحظه‌ای چارت\n\n"
        f"نماد: {SYMBOL}\n"
        f"شرکت: {ticker.title or SYMBOL}\n"
        f"آخرین قیمت پایانی ثبت‌شده: {last_row['Close']:g}\n"
        f"سطوح هشدار این نماد: {levels_text}\n"
        f"زمان درخواست: {now_str}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(chart_path, "rb") as f:
        resp = requests.post(
            url,
            data={"chat_id": CHAT_ID, "caption": caption},
            files={"photo": f},
            timeout=60,
        )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "خطای نامشخص از تلگرام"))
    print(f"چارت لحظه‌ای {SYMBOL} ارسال شد.")


if __name__ == "__main__":
    main()
