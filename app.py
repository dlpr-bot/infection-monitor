import streamlit as st
import pandas as pd
import plotly.express as px

import requests
import re

from wordcloud import WordCloud
import matplotlib.pyplot as plt

from datetime import date, timedelta

st.set_page_config(
    page_title="감염병 뉴스 모니터링",
    layout="wide"
)

CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]

def get_news(q, mx=1000):

    url = "https://naverapihub.apigw.ntruss.com/search/v1/news"

    hdr = {
        "X-NCP-APIGW-API-KEY-ID": CLIENT_ID,
        "X-NCP-APIGW-API-KEY": CLIENT_SECRET
    }

    items = []
    s = 1

    while s <= min(mx, 1000):

        try:

            r = requests.get(
                url,
                headers=hdr,
                params={
                    "query": q,
                    "display": 100,
                    "start": s,
                    "sort": "date",
                    "format": "json"
                },
                timeout=10
            )

            batch = r.json().get(
                "items",
                []
            )

            if not batch:
                break

            items.extend(batch)

            if len(batch) < 100:
                break

            s += 100

        except Exception:
            break

    return items

st.title("🦠 감염병 뉴스 모니터링 시스템")

from datetime import date, timedelta

st.subheader("🔍 검색 조건")

col1, col2, col3 = st.columns(3)

with col1:
    disease = st.selectbox(
        "감염병 선택",
        [
            "전체 감염병",
            "코로나19",
            "독감",
            "홍역",
            "노로바이러스",
            "엠폭스",
            "결핵",
            "말라리아"
        ]
    )

with col2:
    start_date = st.date_input(
        "시작일",
        date.today() - timedelta(days=7)
    )

with col3:
    end_date = st.date_input(
        "종료일",
        date.today()
    )

search = st.button("🔍 뉴스 수집")

if search:

    keyword = disease

    if disease == "전체 감염병":
        keyword = "감염병"

    news_data = get_news(keyword)

    filtered_news = []

    for article in news_data:

        article_date = pd.to_datetime(
            article["pubDate"]
        ).date()

        if start_date <= article_date <= end_date:

            filtered_news.append(article)

    st.session_state["news_data"] = filtered_news

c1, c2, c3, c4 = st.columns(4)

total_news = 0

if "news_data" in st.session_state:
    total_news = len(st.session_state["news_data"])

disease_types = 0

if "news_data" in st.session_state:

    disease_types = 0

c1.metric(
    "전체 기사",
    f"{total_news}건"
)

c2.metric(
    "감염병 종류",
    "-"
)

c3.metric(
    "위험 기사",
    "-"
)

c4.metric(
    "감염병 위험도",
    "-"
)

st.subheader("📈 일별 기사 발생 추이")

if "news_data" in st.session_state:

    daily_rows = []

    for article in st.session_state["news_data"]:

        dt = pd.to_datetime(
            article["pubDate"]
        )

        daily_rows.append(
            dt.strftime("%m/%d")
        )

    daily_df = (
        pd.Series(daily_rows)
        .value_counts()
        .sort_index()
        .reset_index()
    )

    daily_df.columns = ["일자","기사수"]

    fig = px.line(
        daily_df,
        x="일자",
        y="기사수",
        markers=True
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )


st.subheader("🦠 감염병 TOP10")

if "news_data" in st.session_state:

    disease_keywords = [
        "코로나",
        "독감",
        "인플루엔자",
        "홍역",
        "노로바이러스",
        "결핵",
        "말라리아",
        "엠폭스",
        "에볼라",
        "수족구"
    ]

    disease_count = {}

    for disease_name in disease_keywords:

        count = 0

        for article in st.session_state["news_data"]:

            text = (
                article["title"] +
                article["description"]
            )

            if disease_name in text:

                count += 1

        if count > 0:

            disease_count[disease_name] = count

    if disease_count:

        disease_df = pd.DataFrame(
            disease_count.items(),
            columns=["질병", "기사수"]
        ).sort_values(
            "기사수",
            ascending=False
        )
        disease_types = len(disease_count)

        fig2 = px.bar(
            disease_df,
            x="질병",
            y="기사수",
            color="기사수",
            text="기사수"
        )

        st.plotly_chart(
            fig2,
            width="stretch"
        )

    else:

        st.info("감염병 기사 없음")


st.subheader("🚦 감염병 위험 신호등")

RISK_WORDS = [
    "확산",
    "급증",
    "사망",
    "집단감염",
    "치명",
    "에볼라",
    "격리",
    "위험",
    "주의보",
    "감염",
    "전파"
]

risk_count = 0

if "news_data" in st.session_state:

    for article in st.session_state["news_data"]:

        txt = (
            article["title"] +
            article["description"]
        )

        if any(
            word in txt
            for word in RISK_WORDS
        ):
            risk_count += 1

if total_news > 0:

    risk_rate = (
        risk_count /
        total_news * 100
    )

else:

    risk_rate = 0

if risk_rate >= 60:

    signal = "🔴 위험"
    bg = "#f8d7da"

elif risk_rate >= 30:

    signal = "🟠 주의"
    bg = "#fff3cd"

else:

    signal = "🟢 안정"
    bg = "#d1e7dd"

st.markdown(
    f"""
    <div style="
    background:{bg};
    padding:30px;
    border-radius:10px;
    text-align:center;
    font-size:40px;
    font-weight:bold;
    ">
    {signal}
    <br>
    위험기사 {risk_count}건
    <br>
    위험비율 {risk_rate:.1f}%
    </div>
    """,
    unsafe_allow_html=True
)


st.subheader("🤖 AI 상황 요약")

top_disease = "-"

if "news_data" in st.session_state:

    disease_keywords = [
        "코로나",
        "독감",
        "인플루엔자",
        "홍역",
        "노로바이러스",
        "결핵",
        "말라리아",
        "엠폭스",
        "에볼라",
        "수족구"
    ]

    disease_count = {}

    for disease_name in disease_keywords:

        count = 0

        for article in st.session_state["news_data"]:

            txt = (
                article["title"] +
                article["description"]
            )

            if disease_name in txt:
                count += 1

        if count > 0:
            disease_count[disease_name] = count

    if len(disease_count) > 0:

        top_disease = max(
            disease_count,
            key=disease_count.get
        )

summary = f"""
최근 수집된 감염병 관련 뉴스는 총 {total_news}건이다.

가장 많이 언급된 질병은 {top_disease}이다.

위험 기사 수는 {risk_count}건이며
위험 비율은 {risk_rate:.1f}% 수준이다.

현재 감염병 위험도는
{signal} 단계로 판단된다.
"""

st.info(summary)

st.subheader("🚨 이상징후 감염병")

if len(disease_count) > 0:

    top3 = sorted(
        disease_count.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    for disease, cnt in top3:

        st.warning(
            f"{disease} 관련 기사 {cnt}건"
        )

st.subheader("✅ 대응 체크리스트")

st.checkbox("직원 마스크 착용 권고")
st.checkbox("손위생 점검 실시")
st.checkbox("발열환자 동선 확인")
st.checkbox("격리병실 운영상태 점검")
st.checkbox("예방접종 안내 공지")

st.subheader("☁️ 감염병 워드클라우드")

if "news_data" in st.session_state:

    text = " ".join([

        re.sub("<.*?>", "", article["title"]) + " " +
        re.sub("<.*?>", "", article["description"])

        for article in st.session_state["news_data"]

    ])

    STOPWORDS = [
        "감염병",
        "위한",
        "통해",
        "관련",
        "대응",
        "지원",
        "실시",
        "개최",
        "위해",
        "사업",
        "기사",
        "기자",
        "지역",
        "보건소",
        "병원",
        "정부",
        "국내",
        "올해",
        "이번",
        "지난",
        "대한",
        "있는",
        "있다",
        "한다",
        "밝혔다",
        "등",
        "및",
        "예방",
        "관리",
        "운영",
        "개최",
        "추진"
    ]

    for stop in STOPWORDS:
        text = text.replace(stop, "")

    wc = WordCloud(
        font_path="NanumGothic.ttf",
        width=1000,
        height=450,
        background_color="white",
        max_words=50,
        collocations=False
    ).generate(text)

    fig3, ax = plt.subplots(figsize=(12,6))

    ax.imshow(wc)

    ax.axis("off")

    st.pyplot(fig3)

st.subheader("🦠 감염병 정보센터")

info_df = pd.DataFrame({
    "질병": ["코로나19", "독감", "홍역", "노로바이러스", "엠폭스"],
    "잠복기": ["2~14일", "1~4일", "7~21일", "12~48시간", "5~21일"],
    "주요증상": ["발열, 기침", "고열, 근육통", "발열, 발진", "구토, 설사", "발열, 발진"],
    "전파방법": ["비말", "비말", "공기", "접촉", "접촉"],
    "위험국가": ["전세계", "전세계", "베트남·필리핀", "전세계", "콩고민주공화국"]
})

st.dataframe(
    info_df,
    use_container_width=True,
    hide_index=True
)

st.subheader("📰 전체 기사 리스트")

if "news_data" in st.session_state:

    rows = []

    disease_keywords = [
        "코로나",
        "독감",
        "인플루엔자",
        "홍역",
        "노로바이러스",
        "결핵",
        "말라리아",
        "엠폭스",
        "에볼라",
        "수족구"
    ]

    risk_words = [
        "확산",
        "급증",
        "사망",
        "집단감염",
        "치명",
        "에볼라",
        "격리",
        "위험",
        "주의보"
    ]

    for i, article in enumerate(
        st.session_state["news_data"],
        start=1
    ):

        title = re.sub(
            "<.*?>",
            "",
            article["title"]
        )

        desc = re.sub(
            "<.*?>",
            "",
            article["description"]
        )

        text = title + " " + desc

        disease_name = "-"

        for d in disease_keywords:

            if d in text:

                disease_name = d
                break

        risk = "🟢"

        if any(
            word in text
            for word in risk_words
        ):
            risk = "🔴"

        media = (
            article["link"]
            .replace("https://", "")
            .replace("http://", "")
            .split("/")[0]
        )

        rows.append({
            "No": i,
            "일자": article["pubDate"][:16],
            "매체명": media,
            "질병": disease_name,
            "위험도": risk,
            "헤드라인": title,
            "30자요약": desc[:50],
            "기사링크": article["link"]
        })

    article_df = pd.DataFrame(rows)

    st.dataframe(
        article_df,
        width="stretch",
        hide_index=True,
        column_config={
            "기사링크": st.column_config.LinkColumn(
                "기사보기"
            )
        }
    )
