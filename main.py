import asyncio
import os
import httpx
from datetime import datetime, timedelta
from twscrape import API, gather

# ── Cấu hình ──────────────────────────────────────────
MAX_TWEETS = 20
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
X_USERNAME = os.environ["X_USERNAME"]
X_PASSWORD = os.environ["X_PASSWORD"]
X_EMAIL = os.environ["X_EMAIL"]

# Tự động tính ngày 5 ngày trước
since_date = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%d")
TOPIC = f"(AI tips OR AI guide OR AI tutorial) lang:en since:{since_date} min_faves:50"
# ──────────────────────────────────────────────────────

async def get_tweets(topic, limit):
    print(f"[LOG] Topic tìm kiếm: {topic}")

    api = API()

    try:
        await api.pool.add_account(X_USERNAME, X_PASSWORD, X_EMAIL, X_EMAIL)
        print("[LOG] Đã thêm account vào pool")
    except Exception as e:
        print(f"[LOG] Lỗi add account: {e}")
        return []

    try:
        await api.pool.login_all()
        print("[LOG] Login thành công")
    except Exception as e:
        print(f"[LOG] Lỗi login: {e}")
        return []

    try:
        tweets = await gather(api.search(topic, limit=limit))
        results = [
            f"@{t.user.username}: {t.rawContent}"
            for t in tweets
            if not t.rawContent.startswith("RT ")
        ]
        print(f"[LOG] Tìm được {len(results)} tweet")
        return results
    except Exception as e:
        print(f"[LOG] Lỗi khi tìm tweet: {e}")
        return []

def summarize_with_gemini(tweets):
    print(f"[LOG] Gửi {len(tweets)} tweet lên Gemini...")
    content = "\n\n".join(tweets)
    prompt = f"""Dưới đây là các tweet về AI tips và AI guides thú vị trong 5 ngày gần nhất.
Hãy tóm tắt những mẹo, hướng dẫn và thông tin hữu ích nhất bằng tiếng Việt.
Trình bày rõ ràng bằng bullet points, mỗi điểm giải thích ngắn gọn nhưng đủ ý.

TWEETS:
{content}"""

    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=30,
        )
        result = response.json()
        print(f"[LOG] Gemini status: {response.status_code}")

        if "candidates" not in result:
            print(f"[LOG] Gemini lỗi: {result}")
            return None

        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"[LOG] Lỗi Gemini: {e}")
        return None

def send_to_telegram(message):
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for i, chunk in enumerate(chunks):
        response = httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "Markdown",
            },
        )
        result = response.json()
        print(f"[LOG] Telegram chunk {i+1}: {result.get('ok')} - {result.get('description', '')}")

async def main():
    print("=" * 40)
    print(f"[LOG] Bắt đầu chạy lúc: {datetime.utcnow()}")
    print("=" * 40)

    tweets = await get_tweets(TOPIC, MAX_TWEETS)

    if not tweets:
        print("[LOG] Không có tweet → kiểm tra log bên trên để biết nguyên nhân")
        send_to_telegram("⚠️ Không tìm được tweet nào. Xem log GitHub Actions để biết chi tiết.")
        return

    summary = summarize_with_gemini(tweets)

    if not summary:
        send_to_telegram("⚠️ Gemini không trả về kết quả.")
        return

    today = datetime.utcnow().strftime("%d/%m/%Y")
    final_message = (
        f"🤖 *AI Tips & Guides hay nhất tuần*\n"
        f"📅 Cập nhật: {today}\n"
        f"{'─' * 25}\n\n"
        f"{summary}"
    )
    send_to_telegram(final_message)
    print("[LOG] Hoàn thành!")

if __name__ == "__main__":
    asyncio.run(main())
