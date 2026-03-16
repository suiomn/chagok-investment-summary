"""공통 유틸리티 함수 (GitHub Actions CI용)"""
import re, json, os
from pathlib import Path

# 레포 루트 기준 경로 (src/ 의 상위 = 레포 루트)
BASE_DIR = Path(__file__).parent.parent
SUBS_DIR = BASE_DIR / 'tmp_subs'   # 임시 디렉토리 (커밋 안 함)
DATA_DIR = BASE_DIR / 'data'
OUTPUT_DIR = BASE_DIR              # index.html은 레포 루트에 생성

for d in [SUBS_DIR, DATA_DIR, OUTPUT_DIR]:
    d.mkdir(exist_ok=True)


def parse_srt(srt_path: Path) -> str:
    """SRT 파일을 읽어 중복 제거된 순수 텍스트로 반환"""
    text = srt_path.read_text(encoding='utf-8', errors='replace')
    # 타임코드와 인덱스 번호 제거
    text = re.sub(r'^\d+\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', '', text)
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    # 빈 줄 정리
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # 연속 중복 제거 (YouTube 자동 자막은 겹치는 구간이 많음)
    deduped = []
    prev = ''
    for line in lines:
        if line != prev:
            deduped.append(line)
        prev = line
    return ' '.join(deduped)


def load_summaries() -> dict:
    """저장된 요약 데이터 로드"""
    path = DATA_DIR / 'summaries.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return {}


def save_summaries(data: dict):
    """요약 데이터 저장"""
    path = DATA_DIR / 'summaries.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def load_channel_videos() -> list:
    """채널 비디오 메타데이터 로드"""
    path = DATA_DIR / 'channel_videos.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    return []
