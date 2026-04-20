import asyncio
import os
import httpx
from twscrape import API, gather

TOPIC = "AI agent 2025"
MAX_TWEETS = 20
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
X_USERNAME = os.environ["X_USERNAME"]
X_PASSWORD = os.environ["X_PASSWORD"]
X_EMAIL = os.environ["X_EMAIL"]

async def get_tweets(topic, limit):
    api = API()
    await api.pool.add_account(X_USERNAME, X_PASSWORD, X_EMAIL, X_EMAIL)
    await api.pool.login_all()
    tweets = await gather(api.search(topic, limit=limit))
    results = [
        f"@{t.user.username}: {t.rawContent}"
        for t in tweets
        if not t.rawContent.startswith("RT ")
    ]
    print(f"[LOG] Tìm được {len(results)} tweet cho chủ đề: {topic}")
    return results

def summarize_with_gemini(tweets, topic):
    print(f"[LOG] Đang gửi {len(tweets)} tweet lên Gemini...")
    content = "\n\n".join(tweets)
    prompt = f"""Dưới đây là {len(tweets)} tweet về chủ đề "{topic}".
Tóm tắt các điểm nổi bật bằng tiếng Việt, dùng bullet points, súc tích.

TWEETS:
{content}"""

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

def send_to_telegram(message):
    print(f"[LOG] Đang gửi tin nhắn tới Telegram...")
    print(f"[LOG] Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"[LOG] Độ dài tin nhắn: {len(message)} ký tự")

    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    print(f"[LOG] Số chunks cần gửi: {len(chunks)}")

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
        print(f"[LOG] Chunk {i+1} - Status: {response.status_code}")
        print(f"[LOG] Chunk {i+1} - Response: {result}")

async def main():
    print("=" * 40)
    print(f"[LOG] Bắt đầu chạy - Chủ đề: {TOPIC}")
    print("=" * 40)

    tweets = await get_tweets(TOPIC, MAX_TWEETS)

    if not tweets:
        print("[LOG] Không tìm được tweet nào → Dừng lại")
        # Gửi thông báo test thẳng vào Telegram để kiểm tra kết nối
        send_to_telegram("⚠️ Test kết nối Telegram: Không tìm được tweet nào!")
        return

    summary = summarize_with_gemini(tweets, TOPIC)

    if not summary:
        print("[LOG] Gemini không trả về kết quả → Dừng lại")
        send_to_telegram("⚠️ Test kết nối Telegram: Gemini lỗi!")
        return

    final_message = f"🔍 *Tóm tắt về: {TOPIC}*\n{'─' * 25}\n\n{summary}"
    send_to_telegram(final_message)
    print("[LOG] Hoàn thành!")

if __name__ == "__main__":
    asyncio.run(main())
