"""
Claude API를 사용해 동영상 자막을 요약하고 카드뉴스 데이터를 생성
"""
import os, json
from pathlib import Path
from anthropic import Anthropic
from utils import SUBS_DIR, DATA_DIR, BASE_DIR, parse_srt, load_summaries, save_summaries

# .env 파일에서 API 키 로드
_env = BASE_DIR / '.env'
if _env.exists():
    for line in _env.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            os.environ[k.strip()] = v.strip()

client = Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용

SUMMARY_PROMPT = """당신은 투자 콘텐츠 분석 전문가입니다.
아래는 투자 유튜브 채널 '차곡차곡 투자연구소'의 동영상 스크립트입니다.
이 내용을 모바일 캐러셀 스토리보드 형식으로 구조화해주세요.

스크립트:
{transcript}

다음 JSON 형식으로만 응답하세요 (다른 텍스트 없이):
{{
  "headline": "핵심 메시지 한 줄 (최대 30자)",
  "stocks": ["언급된 종목/ETF명 (있는 경우만)"],
  "sentiment": "bullish 또는 bearish 또는 neutral",
  "category": "국내주식 또는 미국주식 또는 ETF 또는 부동산 또는 거시경제 또는 기타",
  "tags": ["태그1", "태그2", "태그3"],
  "slides": [
    {{
      "title": "슬라이드 제목 (10자 내외)",
      "content": "이 슬라이드의 핵심 내용을 3-5문장으로 상세히 설명. 구체적인 수치, 사례, 비교를 포함할 것.",
      "highlight": "이 슬라이드의 핵심 인사이트 한두 문장 (강조 박스에 표시됨)",
      "icon": "관련 이모지 하나"
    }}
  ]
}}

slides는 4-6개로 구성하세요:
- 슬라이드 1: 현재 상황/배경 — 왜 지금 이 종목/주제인가, 현재 주가나 시장 상황
- 슬라이드 2-4: 핵심 분석 포인트 — 각 슬라이드는 하나의 주제에 집중, 수치/근거 포함
- 마지막 슬라이드: 투자 시사점 또는 결론 — 실제 투자 판단에 도움이 되는 내용"""


def summarize_video(video_id: str, title: str, verbose: bool = True) -> dict | None:
    """단일 동영상 자막 요약"""
    srt_path = SUBS_DIR / f"{video_id}.ko.srt"
    if not srt_path.exists():
        srt_path = SUBS_DIR / f"{video_id}.en.srt"
    if not srt_path.exists():
        if verbose:
            print(f"  [SKIP] 자막 없음: {video_id}")
        return None

    transcript = parse_srt(srt_path)
    if len(transcript) < 100:
        if verbose:
            print(f"  [SKIP] 자막 너무 짧음: {video_id}")
        return None

    # 너무 긴 경우 잘라내기 (API 비용 절감)
    max_chars = 8000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + '...(이하 생략)'

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": SUMMARY_PROMPT.format(transcript=transcript)
            }]
        )
        raw = response.content[0].text.strip()
        # JSON 파싱 — 코드블록 제거
        if '```' in raw:
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        raw = raw.strip()
        result = json.loads(raw)
        if verbose:
            print(f"  [OK] {title[:50]}")
        return result
    except Exception as e:
        print(f"  [ERROR] {video_id}: {e}")
        return None


def run_summarize(videos: list, force: bool = False):
    """여러 동영상 일괄 요약"""
    summaries = load_summaries()
    new_count = 0

    for v in videos:
        vid = v['id']
        if not force and vid in summaries:
            continue
        print(f"요약 중: {v.get('title','')[:55]}")
        result = summarize_video(vid, v.get('title', ''))
        if result:
            summaries[vid] = result
            new_count += 1
            # 중간 저장
            save_summaries(summaries)

    print(f"\n완료: {new_count}개 새로 요약, 총 {len(summaries)}개")
    return summaries


if __name__ == '__main__':
    from utils import load_channel_videos
    from datetime import datetime

    videos = load_channel_videos()
    videos_sorted = sorted(
        [v for v in videos if v.get('timestamp')],
        key=lambda x: x['timestamp'], reverse=True
    )[:30]

    run_summarize(videos_sorted)
