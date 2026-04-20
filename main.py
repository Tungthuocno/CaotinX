import asyncio
import os
import httpx
from twscrape import API, gather
from twscrape.logger import set_log_level

# ── Cấu hình ──────────────────────────────────────────
TOPIC = "AI agent 2025"          # Chủ đề muốn theo dõi
MAX_TWEETS = 20                   # Số tweet thu thập mỗi lần chạy
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
X_USERNAME = os.environ["X_USERNAME"]
X_PASSWORD = os.environ["X_PASSWORD"]
X_EMAIL = os.environ["X_EMAIL"]
# ──────────────────────────────────────────────────────

async def get_tweets(topic: str, limit: int) -> list[str]:
    api = API()
    await api.pool.add_account(X_USERNAME, X_PASSWORD, X_EMAIL, X_EMAIL)
    await api.pool.login_all()

    tweets = await gather(api.search(topic, limit=limit))
    return [
        f"@{t.user.username}: {t.rawContent}"
        for t in tweets
        if not t.rawContent.startswith("RT ")  # Bỏ retweet
    ]

def summarize_with_gemini(tweets: list[str], topic: str) -> str:
    content = "\n\n".join(tweets)
    prompt = f"""Dưới đây là {len(tweets)} tweet về chủ đề "{topic}".
Hãy tóm tắt các điểm nổi bật, xu hướng chính và thông tin đáng chú ý nhất bằng tiếng Việt.
Trình bày rõ ràng, súc tích, dùng bullet points.

TWEETS:
{content}"""

    response = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=30,
    )
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]

def send_to_telegram(message: str, topic: str):
    header = f"🔍 *Tóm tắt về: {topic}*\n{'─' * 30}\n\n"
    full_message = header + message
    
    # Telegram giới hạn 4096 ký tự/tin nhắn
    chunks = [full_message[i:i+4000] for i in range(0, len(full_message), 4000)]
    
    for chunk in chunks:
        httpx.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "Markdown",
            },
        )

async def main():
    print(f"Đang thu thập tweet về: {TOPIC}")
    tweets = await get_tweets(TOPIC, MAX_TWEETS)
    
    if not tweets:
        print("Không tìm thấy tweet nào.")
        return
    
    print(f"Thu thập được {len(tweets)} tweet. Đang tóm tắt...")
    summary = summarize_with_gemini(tweets, TOPIC)
    
    print("Gửi vào Telegram...")
    send_to_telegram(summary, TOPIC)
    print("Hoàn thành!")

if __name__ == "__main__":
    asyncio.run(main())