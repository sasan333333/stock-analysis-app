"""
اسکریپت به‌روزرسانی فهرست کامل نمادهای بورس تهران (symbols.json).
به‌جای گرفتن این لیست از اینترنت (که یا خیلی کند است یا به سرورهای
از‌کارافتاده مثل old.tsetmc.com می‌خورد)، از فایل symbols.json که
خودِ کتابخانه‌ی pytse_client به‌صورت آماده و داخلی همراه خودش دارد
استفاده می‌کنیم. این فایل نیازی به اتصال شبکه ندارد و فوری خوانده می‌شود.
"""

import inspect
import json
import os

import pytse_client

FALLBACK_SYMBOLS = [
    "فولاد", "فملی", "خودرو", "خساپا", "شپنا", "شستا", "فارس", "وبملت",
    "وتجارت", "وبصادر", "رمپنا", "کگل", "کچاد", "شبندر", "اخابر", "همراه",
    "وغدیر", "پترول", "شتران", "وپارس",
]


def find_bundled_symbols():
    package_dir = os.path.dirname(inspect.getfile(pytse_client))
    for root, _dirs, files in os.walk(package_dir):
        for fn in files:
            if fn.lower() in ("symbols.json", "symbols_name.json", "symbols_names.json"):
                path = os.path.join(root, fn)
                try:
                    with open(path, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue
                if isinstance(data, dict) and data:
                    return sorted(str(k) for k in data.keys())
                if isinstance(data, list) and data:
                    return sorted(set(str(x) for x in data))
    return None


def main():
    symbols = find_bundled_symbols()
    if not symbols:
        print("فایل نمادهای داخلی پیدا نشد؛ از فهرست پیش‌فرض استفاده می‌شود.")
        symbols = FALLBACK_SYMBOLS

    with open("symbols.json", "w", encoding="utf-8") as f:
        json.dump(symbols, f, ensure_ascii=False)
    print(f"{len(symbols)} نماد ذخیره شد.")


if __name__ == "__main__":
    main()
