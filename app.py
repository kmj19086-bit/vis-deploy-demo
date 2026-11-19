from pathlib import Path

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. 기본 설정 및 경로
HERE = Path(__file__).parent
COLORS = {"A": "#1f77b4", "B": "#ff7f0e"}

st.set_page_config(
    page_title="지점별 실적 비교 대시보드",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def load_data():
    df = pd.read_csv(HERE / "sales.csv")
    df["margin"] = (df["profit"] / df["sales"] * 100).round(1)
    return df


def korean_font():
    names = {f.name for f in fm.fontManager.ttflist}
    return next(
        (f for f in ["Pretendard", "Malgun Gothic", "AppleGothic", "NanumGothic"] if f in names),
        None,
    )


# 2. 헤더 영역
st.title("📊 어느 지점의 실적이 더 우수한가?")
st.caption("출처: 수업용 가상 데이터(sales.csv) · 2026년 1~12월 지점별 월 실적 · 금액 단위: 백만원")

try:
    data = load_data()
except FileNotFoundError:
    st.error("app.py와 같은 폴더에 sales.csv를 올려 주세요.")
    st.stop()

# 3. 사이드바 조회 조건
st.sidebar.header("🔎 조회 조건")
all_branches = sorted(data["branch"].unique().tolist())
branches = st.sidebar.multiselect("비교할 지점", all_branches, default=all_branches)

min_m, max_m = int(data["month"].min()), int(data["month"].max())
months = st.sidebar.slider("조회 월 범위", min_m, max_m, (min_m, max_m))

metric_label = st.sidebar.radio("핵심 분석 지표", ["매출", "영업이익"], horizontal=True)
metric = {"매출": "sales", "영업이익": "profit"}[metric_label]

show_avg_line = st.sidebar.checkbox("추이 차트에 전체 평균선 표시", value=True)

# 데이터 필터링
view = data.loc[
    data["branch"].isin(branches) & data["month"].between(months[0], months[1])
].copy()

if view.empty:
    st.warning("표시할 데이터가 없습니다. 사이드바에서 지점을 하나 이상 선택해 주세요.")
    st.stop()

# 4. 자동 인사이트 요약 배너
branch_summary = (
    view.groupby("branch", as_index=False)
    .agg(total_sales=("sales", "sum"), total_profit=("profit", "sum"), avg_metric=(metric, "mean"))
    .sort_values("total_sales" if metric == "sales" else "total_profit", ascending=False)
)
branch_summary["margin"] = branch_summary["total_profit"] / branch_summary["total_sales"] * 100

top_row = branch_summary.iloc[0]
top_branch = top_row["branch"]
top_val = top_row["total_sales"] if metric == "sales" else top_row["total_profit"]

if len(branch_summary) >= 2:
    second_row = branch_summary.iloc[1]
    second_val = second_row["total_sales"] if metric == "sales" else second_row["total_profit"]
    diff = top_val - second_val
    st.info(
        f"💡 **핵심 요약 ({months[0]}~{months[1]}월):** "
        f"**{top_branch}지점**의 누적 {metric_label}이 **{top_val:,.0f}백만원**으로 "
        f"{second_row['branch']}지점({second_val:,.0f}백만원)보다 **{diff:,.0f}백만원** 앞섭니다."
    )
else:
    st.info(
        f"💡 **핵심 요약 ({months[0]}~{months[1]}월):** "
        f"**{top_branch}지점**의 누적 {metric_label}은 **{top_val:,.0f}백만원**, "
        f"평균 영업이익률은 **{top_row['margin']:.1f}%**입니다."
    )

# 5. 상단 KPI 카드 (4열 구성)
total_sales = view["sales"].sum()
total_profit = view["profit"].sum()
total_margin = (total_profit / total_sales * 100) if total_sales else 0
best_month_row = view.loc[view[metric].idxmax()]

c1, c2, c3, c4 = st.columns(4)
c1.metric("선택 기간 총 매출", f"{total_sales:,.0f} 백만원", f"월평균 {view['sales'].mean():,.1f}")
c2.metric("선택 기간 총 영업이익", f"{total_profit:,.0f} 백만원", f"월평균 {view['profit'].mean():,.1f}")
c3.metric("기간 통합 영업이익률", f"{total_margin:.1f} %", f"관측치 {len(view)}건")
c4.metric(
    f"최고 {metric_label} 기록",
    f"{best_month_row[metric]:,.0f} 백만원",
    f"{int(best_month_row['month'])}월 · {best_month_row['branch']}지점",
)

st.divider()

# 6. 탭 기반 시각화 대시보드
tab1, tab2, tab3 = st.tabs(["📈 월별 추이 및 기간 합계", "💰 수익성 및 비중 분석", "📋 상세 데이터 및 요약표"])

with tab1:
    col_left, col_right = st.columns([3, 2])

    with col_left:
        trend = px.line(
            view.sort_values(["branch", "month"]),
            x="month",
            y=metric,
            color="branch",
            markers=True,
            color_discrete_map=COLORS,
            title=f"월별 {metric_label} 추이",
            labels={"month": "월", metric: f"{metric_label} (백만원)", "branch": "지점"},
            hover_data={"sales": ":,.0f", "profit": ":,.0f", "margin": ":.1f"},
        )
        trend.update_traces(line=dict(width=3), marker=dict(size=8))
        trend.update_xaxes(dtick=1)
        trend.update_yaxes(rangemode="tozero")

        if show_avg_line:
            avg_val = view[metric].mean()
            trend.add_hline(
                y=avg_val,
                line_dash="dot",
                line_color="gray",
                annotation_text=f"전체 평균 ({avg_val:,.1f})",
                annotation_position="top left",
            )

        st.plotly_chart(trend, use_container_width=True)

    with col_right:
        kfont = korean_font()
        totals = view.groupby("branch", as_index=False)[metric].sum()

        with plt.rc_context({"font.family": kfont or "DejaVu Sans", "axes.unicode_minus": False}):
            static_fig, ax = plt.subplots(figsize=(5.5, 4.2))
            bars = ax.bar(
                totals["branch"],
                totals[metric],
                color=[COLORS.get(b, "#333333") for b in totals["branch"]],
                width=0.5,
            )
            ax.bar_label(bars, fmt="%.0f", padding=4, fontweight="bold")
            if kfont:
                ax.set(title=f"지점별 기간 {metric_label} 합계", xlabel="지점", ylabel=f"{metric_label} (백만원)")
            else:
                ax.set(title=f"Period Total ({metric})", xlabel="Branch", ylabel=f"{metric} (M KRW)")
            ax.set_ylim(0, max(totals[metric].max() * 1.22, 1))
            ax.grid(axis="y", linestyle="--", alpha=0.4)
            ax.spines[["top", "right"]].set_visible(False)
            static_fig.tight_layout()

        st.pyplot(static_fig, use_container_width=True)
        plt.close(static_fig)

        if not kfont:
            st.caption("※ 배포 서버에 한글 글꼴이 없어 우측 정적 차트 라벨은 영어로 표시됩니다.")

with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        margin_fig = px.bar(
            branch_summary,
            x="branch",
            y="margin",
            color="branch",
            text="margin",
            color_discrete_map=COLORS,
            title="지점별 기간 영업이익률 비교 (%)",
            labels={"branch": "지점", "margin": "영업이익률 (%)"},
        )
        margin_fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        margin_fig.update_layout(showlegend=False)
        margin_fig.update_yaxes(range=[0, max(branch_summary["margin"].max() * 1.25, 10)])
        st.plotly_chart(margin_fig, use_container_width=True)

    with col_b:
        margin_trend = px.line(
            view.sort_values(["branch", "month"]),
            x="month",
            y="margin",
            color="branch",
            markers=True,
            color_discrete_map=COLORS,
            title="월별 영업이익률(%) 변화 추이",
            labels={"month": "월", "margin": "영업이익률 (%)", "branch": "지점"},
        )
        margin_trend.update_traces(line=dict(width=2.5), marker=dict(size=7))
        margin_trend.update_xaxes(dtick=1)
        margin_trend.update_yaxes(rangemode="tozero")
        st.plotly_chart(margin_trend, use_container_width=True)

with tab3:
    st.markdown("#### 지점별 요약 통계")
    summary_display = branch_summary.rename(
        columns={
            "branch": "지점",
            "total_sales": "누적 매출(백만원)",
            "total_profit": "누적 영업이익(백만원)",
            "avg_metric": f"월평균 {metric_label}(백만원)",
            "margin": "영업이익률(%)",
        }
    )
    st.dataframe(
        summary_display.style.format(
            {
                "누적 매출(백만원)": "{:,.0f}",
                "누적 영업이익(백만원)": "{:,.0f}",
                f"월평균 {metric_label}(백만원)": "{:,.1f}",
                "영업이익률(%)": "{:.1f}%",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("#### 필터링된 원본 데이터")
    display_view = view.rename(
        columns={"branch": "지점", "month": "월", "sales": "매출(백만원)", "profit": "영업이익(백만원)", "margin": "영업이익률(%)"}
    )
    st.dataframe(display_view, hide_index=True, use_container_width=True)

    st.download_button(
        "📥 현재 조회 결과 CSV 다운로드",
        data=view.to_csv(index=False).encode("utf-8-sig"),
        file_name="selected_sales.csv",
        mime="text/csv",
    )

st.caption("※ 본 대시보드는 제공된 수치의 기술적 비교를 목적으로 하며, 실적 변화의 외부 원인은 별도 분석이 필요합니다.")