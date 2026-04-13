import anthropic
import datetime
import os
import random
import time
import glob
import requests

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
pexels_key = os.environ.get("PEXELS_API_KEY")

CATEGORIES = {
    "스포츠뉴스": [
        "손흥민 최근 경기 활약 분석",
        "KBO 리그 최신 순위와 주요 경기",
        "NBA 플레이오프 주요 경기 정리",
        "K리그 최신 이슈와 이적 소식",
        "EPL 주요 경기 결과 분석",
        "한국 배구 V리그 최신 소식",
        "UFC 최신 경기와 한국 선수 동향",
        "한국 야구 국가대표 소식",
    ],
    "스포츠정보": [
        "축구 포지션별 역할 정리",
        "헬스 초보자를 위한 운동 루틴",
        "수영 자유형 자세 교정법",
        "골프 입문자 스윙 가이드",
        "마라톤 준비하는 방법",
        "배드민턴 서브 기초",
        "등산 장비 선택 가이드",
        "자전거 올바른 자세와 안전 수칙",
    ],
    "스포츠소식": [
        "2026년 국내 생활체육대회 일정",
        "전국체육대회 참가 신청 방법",
        "지역 스포츠 센터 무료 강습 안내",
        "국내 마라톤 대회 일정",
        "생활체육 동호회 지원 정책",
        "스포츠 용품 할인 행사 정보",
    ],
    "스포츠이야기": [
        "처음 축구를 시작했던 날",
        "동네 야구팀에서 배운 팀워크",
        "마라톤 완주 후 느낀 것들",
        "스포츠가 일상을 바꾼 이야기",
        "운동으로 극복한 슬럼프",
        "동호회에서 만난 인연들",
        "운동이 정신 건강에 미치는 영향",
    ],
}

TOPIC_SEARCH = {
    "손흥민": "soccer player kicking ball",
    "KBO": "baseball game stadium",
    "NBA": "basketball game court",
    "K리그": "soccer match stadium korea",
    "EPL": "football match premier league",
    "배구": "volleyball game",
    "UFC": "martial arts fighter",
    "야구": "baseball pitcher",
    "축구 포지션": "soccer tactics team",
    "헬스": "gym fitness workout",
    "수영": "swimming pool athlete",
    "골프": "golf course swing",
    "마라톤": "marathon running road",
    "배드민턴": "badminton court player",
    "등산": "hiking mountain trail",
    "자전거": "cycling road bike",
    "생활체육": "community sports event",
    "전국체육대회": "sports competition athletes",
    "스포츠 센터": "sports center indoor facility",
    "동호회": "sports team friends",
    "스포츠 용품": "sports equipment gear",
}

CATEGORY_ICONS = {
    "스포츠뉴스": "⚡",
    "스포츠정보": "📋",
    "스포츠소식": "📢",
    "스포츠이야기": "💬",
}

CATEGORY_CLASS = {
    "스포츠뉴스": "cat-news",
    "스포츠정보": "cat-info",
    "스포츠소식": "cat-info",
    "스포츠이야기": "cat-story",
}


def get_pexels_image(topic, category):
    if not pexels_key:
        return None, None

    query = "sports athlete"
    for key, val in TOPIC_SEARCH.items():
        if key in topic:
            query = val
            break

    try:
        headers = {"Authorization": pexels_key}
        url = "https://api.pexels.com/v1/search?query=" + query + "&per_page=10&orientation=landscape"
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        photos = data.get("photos", [])
        if not photos:
            return None, None
        photo = random.choice(photos[:5])
        img_url = photo["src"]["large"]
        photographer = photo["photographer"]
        return img_url, photographer
    except Exception as e:
        print("Pexels 이미지 실패: " + str(e))
        return None, None


def get_existing_titles():
    titles = set()
    for filepath in glob.glob("_posts/*.md"):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("title:"):
                    title = line.replace("title:", "").strip().strip('"')
                    words = [w for w in title.split() if len(w) >= 4]
                    for w in words:
                        titles.add(w.lower())
    return titles


def is_duplicate(topic, existing):
    words = [w for w in topic.split() if len(w) >= 4]
    for w in words:
        if w.lower() in existing:
            return True
    return False


def generate_post(category, topic, date_str, img_url, photographer):
    img_block = ""
    if img_url:
        img_block = "\n\n![" + topic + "](" + img_url + ")\n*© " + photographer + " / Pexels*\n\n"

    prompt = (
        "아래 조건으로 스포츠 블로그 글을 작성해.\n\n"
        "주제: " + topic + "\n"
        "카테고리: " + category + "\n\n"
        "출력 형식 (반드시 아래 형식 그대로):\n"
        "---\n"
        "layout: post\n"
        "title: \"제목\"\n"
        "date: " + date_str + "\n"
        "description: \"한 줄 요약\"\n"
        "category: " + category + "\n"
        "category_class: " + CATEGORY_CLASS[category] + "\n"
        "---\n\n"
        + img_block +
        "(본문)\n\n"
        "작성 규칙:\n"
        "- 글자 수 1000자 이상\n"
        "- 소제목(##) 3개 이상\n"
        "- 정제된 문체. 과장하거나 오버하지 말 것\n"
        "- 독자에게 실질적으로 유익한 내용\n"
        "- 이모지 사용 금지\n"
        "- 첫 문장부터 본론으로 바로 들어갈 것\n"
        "- 맨 앞 --- 부터 시작. 앞에 다른 텍스트 없이 바로 시작"
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
all_cats = list(CATEGORIES.keys())
selected_cats = [all_cats[i % len(all_cats)] for i in range(count)]

for i, category in enumerate(selected_cats):
    topics = CATEGORIES[category]
    unique = [t for t in topics if not is_duplicate(t, existing)]
    topic = random.choice(unique if unique else topics)

    print("[" + str(i+1) + "/" + str(count) + "] " + category + " - " + topic)

    img_url, photographer = get_pexels_image(topic, category)
    print("이미지: " + (img_url[:50] + "..." if img_url else "없음"))

    content = generate_post(category, topic, date_str, img_url, photographer)

    slug = topic[:30].replace(" ", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    filename = "_posts/" + date_str + "-" + slug + ".md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    print("완료: " + filename)
    if i < len(selected_cats) - 1:
        time.sleep(2)

print("모든 글 생성 완료!")
