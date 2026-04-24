import os
import httpx
from datetime import datetime

# ── Cấu hình ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
# ──────────────────────────────────────────────────────

def get_devto_posts():
    """Dev.to: nền tảng blog kỹ thuật, API hoàn toàn miễn phí"""
    posts = []
    tags = ["ai", "machinelearning", "llm", "chatgpt"]

    for tag in tags:
        try:
            url = f"https://dev.to/api/articles?tag={tag}&top=7&per_page=5"
            response = httpx.get(url, timeout=15)
            data = response.json()

            for article in data:
                posts.append(
                    f"[Dev.to] {article['title']} "
                    f"(❤️ {article.get('positive_reactions_count', 0)}) "
                    f"- {article.get('description', '')[:150]}"
                )
            print(f"[LOG] Dev.to #{tag}: {len(data)} bài")
        except Exception as e:
            print(f"[LOG] Lỗi Dev.to #{tag}: {e}")

    return posts

def get_hackernews_posts():
    """HackerNews: cộng đồng tech lớn, API chính thức miễn phí"""
    posts = []
    queries = ["artificial intelligence", "LLM", "ChatGPT", "AI agent"]

    for query in queries:
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={query}&tags=story&numericFilters=points>20&hitsPerPage=5"
            response = httpx.get(url, timeout=15)
            data = response.json()
            hits = data.get("hits", [])

            for hit in hits:
                posts.append(
                    f"[HackerNews] {hit['title']} "
                    f"(👍 {hit.get('points', 0)} points, "
                    f"💬 {hit.get('num_comments', 0)} comments)"
                )
            print(f"[LOG] HackerNews '{query}': {len(hits)} bài")
        except Exception as e:
            print(f"[LOG] Lỗi HackerNews '{query}': {e}")

    return posts

def summarize_with_gemini(posts):
    print(f"[LOG] Gửi {len(posts)} bài lên Gemini...")
    content = "\n\n".join(posts[:30])

    prompt = f"""Dưới đây là các bài viết về AI từ Dev.to và HackerNews trong tuần này.

Hãy tóm tắt thành bản tin AI hữu ích bằng tiếng Việt với cấu trúc rõ ràng:

🔥 *Xu hướng nổi bật*
(Những chủ đề AI được cộng đồng quan tâm nhất tuần này)

💡 *Tips & Tricks thực tế*
(Các mẹo, kỹ thuật có thể áp dụng ngay)

🛠 *Công cụ & Model đáng chú ý*
(Tool, framework, model mới được nhắc đến)

Dùng bullet points, ngôn ngữ dễ hiểu, súc tích, thực tế.

NỘI DUNG:
{content}"""

    try:
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={AIzaSyA-aZGI-U9XgGeN9EIpEH7aH8zMytC9ZgI}",
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
        print(f"[LOG] Telegram chunk {i+1}: ok={result.get('ok')} {result.get('description', '')}")

def main():
    print("=" * 40)
    print(f"[LOG] Bắt đầu chạy lúc: {datetime.utcnow()}")
    print("=" * 40)

    devto_posts = get_devto_posts()
    hn_posts = get_hackernews_posts()
    all_posts = devto_posts + hn_posts

    print(f"[LOG] Tổng bài thu thập: {len(all_posts)}")

    if not all_posts:
        send_to_telegram("⚠️ Không lấy được nội dung.")
        return

    summary = summarize_with_gemini(all_posts)

    if not summary:
        send_to_telegram("⚠️ Gemini không trả về kết quả.")
        return

    today = datetime.utcnow().strftime("%d/%m/%Y")
    final_message = (
        f"🤖 *AI Tips & Trends tuần này*\n"
        f"📅 Cập nhật: {today}\n"
        f"📰 Nguồn: Dev.to + HackerNews\n"
        f"{'─' * 25}\n\n"
        f"{summary}"
    )

    send_to_telegram(final_message)
    print("[LOG] Hoàn thành!")

if __name__ == "__main__":
    main()
