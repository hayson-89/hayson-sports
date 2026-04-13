import anthropic
import datetime
import os
import random
import time
import glob
import requests
import urllib.request
import urllib.parse

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
pexels_key = os.environ.get("PEXELS_API_KEY")

CATEGORY_CLASS = {
    "스포츠뉴스": "cat-news",
    "스포츠정보": "cat-info",
    "스포츠소식": "cat-info",
    "스포츠이야기": "cat-story",
}

TOPIC_SEARCH = {
    "손흥민": "soccer player kicking ball",
    "KBO": "baseball game stadium",
    "NBA": "basketball game court",
    "K리그": "soccer match stadium",
    "EPL": "football premier league",
    "배구": "volleyball game",
    "UFC": "martial arts fighter",
    "야구": "baseball pitcher",
    "축구": "soccer football match",
    "농구": "basketball court player",
    "골프": "golf course swing",
    "마라톤": "marathon running road",
    "수영": "swimming pool athlete",
    "테니스": "tennis court player",
    "배드민턴": "badminton player court",
    "복싱": "boxing ring fighter",
    "격투기": "martial arts combat",
    "헬스": "gym fitness workout",
    "등산": "hiking mountain trail",
    "자전거": "cycling road bike",
}

FALLBACK_TOPICS = {
    "스포츠뉴스": [
        "손흥민 최근 경기 활약 분석",
        "KBO 리그 최신 순위와 주요 경기",
        "NBA 플레이오프 주요 경기 정리",
        "K리그 최신 이슈와 이적 소식",
        "EPL 주요 경기 결과 분석",
        "한국 배구 V리그 최신 소식",
    ],
    "스포츠정보": [
        "헬스 초보자를 위한 운동 루틴",
        "마라톤 준비하는 방법",
        "수영 자유형 자세 교정법",
        "골프 입문자 스윙 가이드",
        "등산 장비 선택 가이드",
        "자전거 올바른 자세와 안전 수칙",
    ],
    "스포츠소식": [
        "2026년 국내 생활체육대회 일정",
        "전국체육대회 참가 신청 방법",
        "국내 마라톤 대회 일정",
        "생활체육 동호회 지원 정책",
    ],
    "스포츠이야기": [
        "마라톤 완주 후 느낀 것들",
        "스포츠가 일상을 바꾼 이야기",
        "운동으로 극복한 슬럼프",
        "운동이 정신 건강에 미치는 영향",
    ],
}


def get_google_news():
    news_items = []
    feeds = [
        "https://news.google.com/rss/search?q=스포츠&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=축구+야구+농구&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=손흥민+KBO+NBA&hl=ko&gl=KR&ceid=KR:ko",
    ]
    for feed_url in feeds:
        try:
            req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                content = res.read().decode("utf-8")
            start = 0
            while True:
                s = content.find("<title>", start)
                if s == -1:
                    break
                e = content.find("</title>", s)
                title = content[s+7:e].strip()
                title = title.replace("<![CDATA[", "").replace("]]>", "").strip()
                if (len(title) > 8
                        and "Google" not in title
                        and "뉴스" not in title[:3]
                        and title not in [n["title"] for n in news_items]):
                    news_items.append({"title": title})
                start = e + 1
            time.sleep(0.5)
        except Exception as e:
            print("뉴스 수집 실패: " + str(e))
    print("뉴스 수집: " + str(len(news_items)) + "개")
    return news_items


def classify_news(news_items):
    classified = {k: [] for k in FALLBACK_TOPICS}
    news_kw = ["경기", "승리", "패배", "골", "득점", "우승", "선수", "리그",
               "축구", "야구", "농구", "배구", "골프", "테니스", "UFC", "올림픽"]
    info_kw = ["방법", "가이드", "팁", "기초", "훈련", "운동법", "기술"]
    notice_kw = ["대회", "일정", "신청", "행사", "개막", "폐막", "개최", "참가"]
    for item in news_items:
        t = item["title"]
        if any(k in t for k in info_kw):
            classified["스포츠정보"].append(t)
        elif any(k in t for k in notice_kw):
            classified["스포츠소식"].append(t)
        elif any(k in t for k in news_kw):
            classified["스포츠뉴스"].append(t)
    return classified


def get_pexels_image(topic):
    if not pexels_key:
        return None, None, None
    query = "sports athlete competition"
    for key, val in TOPIC_SEARCH.items():
        if key in topic:
            query = val
            break
    try:
        headers = {"Authorization": pexels_key}
        url = ("https://api.pexels.com/v1/search?query="
               + urllib.parse.quote(query)
               + "&per_page=10&orientation=landscape")
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        photos = data.get("photos", [])
        if not photos:
            return None, None, None
        photo = random.choice(photos[:5])
        return photo["src"]["large"], photo["src"]["medium"], photo["photographer"]
    except Exception as e:
        print("Pexels 실패: " + str(e))
        return None, None, None


def get_existing_titles():
    titles = set()
    for filepath in glob.glob("_posts/*.md"):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("title:"):
                    title = line.replace("title:", "").strip().strip('"')
                    for w in title.split():
                        if len(w) >= 4:
                            titles.add(w.lower())
    return titles


def is_duplicate(topic, existing):
    for w in topic.split():
        if len(w) >= 4 and w.lower() in existing:
            return True
    return False


def generate_post(category, topic, date_str, img_large, img_medium, photographer, is_news=False):
    img_block = ""
    if img_large:
        img_block = "\n\n![" + topic + "](" + img_large + ")\n*© " + photographer + " / Pexels*\n\n"

    if is_news:
        subject = ("이 글은 오늘 실제 뉴스 헤드라인을 바탕으로 작성해.\n"
                   "헤드라인: '" + topic + "'\n"
                   "배경 설명, 의미 분석, 향후 전망을 담아서 써줘.\n")
    else:
        subject = "주제: " + topic + "\n"

    thumbnail_line = ("thumbnail: \"" + img_medium + "\"\n") if img_medium else ""

    prompt = (
        "스포츠 블로그 글을 작성해.\n\n"
        + subject +
        "카테고리: " + category + "\n\n"
        "출력 형식 (반드시 아래 형식 그대로 출력):\n"
        "---\n"
        "layout: post\n"
        "title: \"제목\"\n"
        "date: " + date_str + "\n"
        "description: \"한 줄 요약 (60자 이내)\"\n"
        "category: " + category + "\n"
        "category_class: " + CATEGORY_CLASS[category] + "\n"
        + thumbnail_line +
        "---\n\n"
        + img_block +
        "(본문)\n\n"
        "작성 규칙:\n"
        "- 글자 수 1000자 이상\n"
        "- 소제목(##) 3개 이상\n"
        "- 정제된 문체. 과장하거나 오버하지 말 것\n"
        "- 독자에게 실질적으로 유익한 내용 위주\n"
        "- 이모지 사용 금지\n"
        "- 첫 문장부터 본론으로 바로 시작\n"
        "- 맨 앞 --- 부터 시작. 앞에 다른 텍스트 절대 없이"
    )

    msg = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


# 메인
count = int(os.environ.get("POST_COUNT", "2"))
today = datetime.date.today()
date_str = today.strftime("%Y-%m-%d")
os.makedirs("_posts", exist_ok=True)

existing = get_existing_titles()

print("최신 뉴스 수집 중...")
news_items = get_google_news()
classified_news = classify_news(news_items)

all_cats = list(FALLBACK_TOPICS.keys())
posts_to_generate = []

for i in range(count):
    category = all_cats[i % len(all_cats)]
    is_news = False
    news_topics = classified_news.get(category, [])
    unique_news = [t for t in news_topics if not is_duplicate(t, existing)]
    if unique_news:
        topic = unique_news[0]
        is_news = True
        print("뉴스 기반: " + topic[:40])
    else:
        fallbacks = FALLBACK_TOPICS[category]
        unique_fb = [t for t in fallbacks if not is_duplicate(t, existing)]
        topic = random.choice(unique_fb if unique_fb else fallbacks)
        print("기본 주제: " + topic[:40])
    posts_to_generate.append({"category": category, "topic": topic, "is_news": is_news})

for i, post_info in enumerate(posts_to_generate):
    category = post_info["category"]
    topic = post_info["topic"]
    is_news = post_info["is_news"]

    print("[" + str(i+1) + "/" + str(count) + "] " + category + " - " + topic[:30])

    img_large, img_medium, photographer = get_pexels_image(topic)
    print("이미지: " + (img_large[:50] + "..." if img_large else "없음"))

    content = generate_post(category, topic, date_str, img_large, img_medium, photographer, is_news)

    slug = topic[:30].replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    suffix = "" if i == 0 else "-" + str(i+1)
    filename = "_posts/" + date_str + suffix + "-" + slug + ".md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print("저장: " + filename)
    if i < len(posts_to_generate) - 1:
        time.sleep(2)

print("모든 글 생성 완료!")
