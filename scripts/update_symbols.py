"""
اسکریپت به‌روزرسانی فهرست کامل نمادهای بورس تهران (symbols.json).
هفته‌ای یک‌بار (یا با اجرای دستی) نام همه نمادها را از دیده‌بان بازار (market watch)
tsetmc می‌گیرد تا اپ بتواند هنگام تایپ (مثلاً «شپ») همه نمادهای منطبق را پیشنهاد بدهد.

نکته: از get_stats استفاده می‌شود که یک اسنپ‌شات سبک و یکجا از همه نمادهاست،
نه tse.download(symbols="all") که تاریخچه کامل قیمت هر نماد را جدا دانلود می‌کند
و به همین دلیل بسیار کند است (می‌تواند ساعت‌ها طول بکشد و در GitHub Actions تایم‌اوت شود).
"""

import json
from pytse_client import get_stats


def main():
    stats = get_stats(to_csv=False)
    symbols = sorted(set(stats["symbol"].dropna().astype(str)))
    with open("symbols.json", "w", encoding="utf-8") as f:
        json.dump(symbols, f, ensure_ascii=False)
    print(f"{len(symbols)} نماد ذخیره شد.")


if __name__ == "__main__":
    main()
