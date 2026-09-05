"""
اسکریپت به‌روزرسانی فهرست کامل نمادهای بورس تهران (symbols.json).
هفته‌ای یک‌بار (یا با اجرای دستی) کل نام نمادها را از tsetmc می‌گیرد
تا اپ بتواند هنگام تایپ (مثلاً «شپ») همه نمادهای منطبق را پیشنهاد بدهد.
از تابع مستندشده و رسمی pytse_client استفاده می‌شود، نه حدس زدن اندپوینت داخلی.
"""

import json
import pytse_client as tse


def main():
    tickers = tse.download(symbols="all", write_to_csv=False)
    symbols = sorted(tickers.keys())
    with open("symbols.json", "w", encoding="utf-8") as f:
        json.dump(symbols, f, ensure_ascii=False)
    print(f"{len(symbols)} نماد ذخیره شد.")


if __name__ == "__main__":
    main()
