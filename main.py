import asyncio
import os
import httpx
from datetime import datetime, timedelta

# ── Cấu hình ──────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
# ──────────────────────────────────────────────────────

def get_reddit_posts():
    """Lấy bài từ các subreddit AI nổi tiếng"""
    subreddits = [
        "artificial",
        "MachineLearning", 
        "ChatGPT",
        "AIPromptProgramming",
    ]
    posts = []

    headers = {"User-Agent": "AIDigestBot/1.0"}

    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/search.json?q=tips+OR+guide+OR+tutorial&sort=top&t=week&limit=5"
            response = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
            data = response.json()

            for item in data["data"]["children"]:
                post = item["data"]
                # Chỉ lấy bài có nhiều upvote
                if post["score"] >= 100:
                    posts.append(
                        f"[Reddit r/{sub}] {post['title']} "
                        f"(👍 {post['score']}) - {post.get('selftext', '')[:200]}"
                    )
            print(f"[LOG] Reddit r/{sub}: lấy được {len(data['data']['children'])} bài")
        except Exception as e:
            print(f"[LOG] Lỗi Reddit r/{sub}: {e}")

    return posts

def get_hackernews_posts():
    """Lấy bài AI từ HackerNews"""
    posts = []
    try:
        # Tìm kiếm bài về AI trong 5 ngày gần nhất
        since_timestamp = int((datetime.utcnow() - timedelta(days=5)).timestamp())
        url = f"https://hn.algolia.com/api/v1/search?query=AI+tips+OR+AI+guide+OR+LLM&tags=story&numericFilters=created_at_i>{since_timestamp},points>50&hitsPerPage=10"

        response = httpx.get(url, timeout=15)
        data = response.json()

        for hit in data["hits"]:
            posts.append(
                f"[HackerNews] {hit['title']} "
                f"(👍 {hit.get('points', 0)}, 💬 {hit.get('num_comments', 0)} comments)"
            )
        print(f"[LOG] HackerNews: lấy được {len(data['hits'])} bài")
    except Exception as e:
        print(f"[LOG] Lỗi HackerNews: {e}")

    return posts

def summarize_with_gemini(posts):
    print(f"[LOG] Gửi {len(posts)} bài lên Gemini để tóm tắt...")
    content = "\n\n".join(posts)

    prompt = f"""Dưới đây là các bài viết về AI tips, guides và xu hướng AI mới nhất từ Reddit và HackerNews trong 5-7 ngày gần nhất.

Hãy tóm tắt thành một bản tin AI hữu ích bằng tiếng Việt với cấu trúc:
1. Các mẹo/hướng dẫn AI nổi bật nhất
2. Công cụ hoặc kỹ thuật AI đáng chú ý
3. Xu hướng đang được cộng đồng quan tâm

Dùng bullet points, ngôn ngữ dễ hiểu, thực tế và có thể áp dụng được.

NỘI DUNG:
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

def main():
    print("=" * 40)
    print(f"[LOG] Bắt đầu chạy lúc: {datetime.utcnow()}")
    print("=" * 40)

    # Thu thập từ cả 2 nguồn
    reddit_posts = get_reddit_posts()
    hn_posts = get_hackernews_posts()
    all_posts = reddit_posts + hn_posts

    print(f"[LOG] Tổng số bài thu thập: {len(all_posts)}")

    if not all_posts:
        print("[LOG] Không lấy được bài nào!")
        send_to_telegram("⚠️ Không lấy được nội dung từ Reddit và HackerNews.")
        return

    summary = summarize_with_gemini(all_posts)

    if not summary:
        send_to_telegram("⚠️ Gemini không trả về kết quả.")
        return

    today = datetime.utcnow().strftime("%d/%m/%Y")
    final_message = (
        f"🤖 *AI Tips & Trends tuần này*\n"
        f"📅 Cập nhật: {today}\n"
        f"📰 Nguồn: Reddit + HackerNews\n"
        f"{'─' * 25}\n\n"
        f"{summary}"
    )

    send_to_telegram(final_message)
    print("[LOG] Hoàn thành!")

if __name__ == "__main__":
    main()
