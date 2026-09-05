"""
اسکریپت بررسی هشدار قیمت سهام بورس ایران.
این فایل توسط GitHub Actions به‌صورت زمان‌بندی‌شده اجرا می‌شود:
- فایل alerts.json را می‌خواند
- برای هر هشدار فعال، آخرین قیمت نماد را از tsetmc می‌گیرد
- اگر قیمت هدف رسیده باشد، نمودار ۲ ماه اخیر (روزانه) را می‌سازد
  و پیام + عکس را به کانال تلگرام ارسال می‌کند
  (روی چارت، خط تمام هشدارهای فعال/غیرفعالِ همان نماد رسم و قیمتشان کنار خط نوشته می‌شود)
- alerts.json را با وضعیت جدید به‌روزرسانی می‌کند (توسط ورک‌فلو کامیت می‌شود)
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
FORCE_CHECK = os.environ.get("FORCE_CHECK", "false").lower() == "true"

# روزهای معاملاتی بورس تهران: شنبه تا چهارشنبه
# Python weekday(): دوشنبه=0 ... یکشنبه=6  -> شنبه=5، یکشنبه=6، دوشنبه=0، سه‌شنبه=1، چهارشنبه=2
TRADING_WEEKDAYS = {5, 6, 0, 1, 2}
MARKET_OPEN_MIN = 9 * 60          # 09:00
MARKET_CLOSE_MIN = 12 * 60 + 30   # 12:30


def in_market_hours() -> bool:
    now = datetime.now(TEHRAN)
    if now.weekday() not in TRADING_WEEKDAYS:
        return False
    minutes = now.hour * 60 + now.minute
    return MARKET_OPEN_MIN <= minutes <= MARKET_CLOSE_MIN


def load_alerts():
    if not os.path.exists(ALERTS_PATH):
        return []
    with open(ALERTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_alerts(alerts):
    with open(ALERTS_PATH, "w", encoding="utf-8") as f:
        json.dump(alerts, f, ensure_ascii=False, indent=2)


def build_chart(symbol: str, alert_prices) -> str:
    """نمودار کندل‌استیک ۲ ماه اخیر با خط تمام سطوح هشدار این نماد (با برچسب قیمت)."""
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

    fig, axlist = mpf.plot(
        hist,
        type="candle",
        style=style,
        hlines=dict(hlines=levels, colors=["#C9973F"] * len(levels), linestyle="--", linewidths=1.2),
        title=f"{symbol} - Alert Levels",
        ylabel="Price",
        figsize=(9, 5),
        returnfig=True,
    )
    ax = axlist[0]
    for p in levels:
        ax.text(
            1.005, p, f"{p:g}",
            transform=ax.get_yaxis_transform(),
            color="#C9973F", fontsize=9, fontweight="bold",
            va="center", ha="left",
        )

    path = f"/tmp/{symbol}_chart.png"
    fig.savefig(path, dpi=150, facecolor="#10141A", bbox_inches="tight")
    return path


def send_telegram_alert(symbol, title, target_price, current_price, condition, all_prices):
    cond_text = (
        "به قیمت هدف رسید یا از آن بالاتر رفت"
        if condition == "gte"
        else "به قیمت هدف رسید یا از آن پایین‌تر آمد"
    )
    now_str = datetime.now(TEHRAN).strftime("%Y-%m-%d %H:%M")
    levels_text = "، ".join(f"{p:g}" for p in sorted(set(all_prices)))
    caption = (
        "🚨 هشدار قیمت سهام\n\n"
        f"نماد: {symbol}\n"
        f"شرکت: {title}\n"
        f"وضعیت: {cond_text}\n"
        f"قیمت هدف: {target_price}\n"
        f"قیمت فعلی: {current_price}\n"
        f"سطوح هشدار این نماد: {levels_text}\n"
        f"زمان: {now_str}"
    )
    chart_path = build_chart(symbol, all_prices)
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


def main():
    if not FORCE_CHECK and not in_market_hours():
        print("خارج از ساعات معاملاتی بورس؛ بررسی انجام نشد.")
        return

    if not BOT_TOKEN or not CHAT_ID:
        print("توکن بات یا آیدی چت تلگرام تنظیم نشده (Secrets را بررسی کنید).")
        return

    alerts = load_alerts()
    changed = False

    # تمام سطوح قیمتی هر نماد (برای رسم روی چارت) - شامل هشدارهای ارسال‌شده و فعال
    prices_by_symbol = {}
    for a in alerts:
        prices_by_symbol.setdefault(a["symbol"], []).append(float(a["targetPrice"]))

    for alert in alerts:
        if alert.get("triggered"):
            continue

        symbol = alert["symbol"]
        try:
            ticker = tse.Ticker(symbol)
            current_price = float(ticker.last_price)
            title = ticker.title or symbol
        except Exception as e:
            print(f"خطا در دریافت قیمت {symbol}: {e}")
            continue

        target_price = float(alert["targetPrice"])
        condition = alert.get("condition", "gte")
        hit = current_price >= target_price if condition == "gte" else current_price <= target_price

        if hit:
            try:
                all_prices = prices_by_symbol.get(symbol, [target_price])
                send_telegram_alert(symbol, title, target_price, current_price, condition, all_prices)
                alert["triggered"] = True
                alert["triggeredAt"] = datetime.now(TEHRAN).isoformat()
                alert["priceAtTrigger"] = current_price
                changed = True
                print(f"هشدار {symbol} ارسال شد.")
            except Exception as e:
                print(f"ارسال تلگرام برای {symbol} ناموفق بود: {e}")

    if changed:
        save_alerts(alerts)
        print("alerts.json به‌روزرسانی شد.")
    else:
        print("هیچ هشدار جدیدی فعال نشد.")


if __name__ == "__main__":
    main()
