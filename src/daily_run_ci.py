"""
GitHub Actions용 자동화 파이프라인
1. 채널에서 최신 동영상 목록 가져오기
2. 새로운 동영상 감지
3. 자막 다운로드
4. Claude API로 요약
5. HTML 카드뉴스 재생성
6. 변경사항은 GitHub Actions가 커밋/push
"""
import json, subprocess, sys, os
from pathlib import Path
from datetime import datetime

# src/ 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from utils import BASE_DIR, SUBS_DIR, DATA_DIR, OUTPUT_DIR, load_summaries, save_summaries

CHANNEL_URL = "https://www.youtube.com/@차곡차곡투자연구소/videos"


def log(msg: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {msg}", flush=True)


def fetch_latest_videos(limit: int = 50) -> list:
    log("채널 동영상 목록 가져오는 중...")
    result = subprocess.run(
        _ytdlp_base_args() + [
            '--flat-playlist', '--dump-json',
            '--extractor-args', 'youtubetab:approximate_date',
            CHANNEL_URL,
        ],
        capture_output=True, timeout=120
    )
    lines = result.stdout.decode('utf-8', errors='replace').strip().split('\n')
    videos = []
    for line in lines:
        if not line.strip():
            continue
        try:
            d = json.loads(line)
            videos.append({
                'id': d.get('id', ''),
                'title': d.get('title', ''),
                'view_count': d.get('view_count'),
                'duration': d.get('duration'),
                'upload_date': d.get('upload_date'),
                'timestamp': d.get('timestamp'),
            })
        except:
            pass
    log(f"  → {len(videos)}개 동영상 확인")
    return videos


def find_new_videos(fetched: list) -> list:
    summaries = load_summaries()
    known_ids = set(summaries.keys())
    new_vids = [v for v in fetched if v['id'] not in known_ids]
    log(f"  → 신규 동영상: {len(new_vids)}개")
    return new_vids


def _ytdlp_base_args():
    """CI 환경(GitHub Actions)에서도 동작하도록 player client 및 쿠키 지정"""
    args = ['yt-dlp', '--extractor-args', 'youtube:player_client=android,ios,web']
    cookies = Path('/tmp/yt-cookies.txt')
    if cookies.exists() and cookies.stat().st_size > 100:
        args += ['--cookies', str(cookies)]
    return args


def download_subs_ytdlp(video_ids: list) -> list:
    """yt-dlp로 자막 다운로드 (언어 제한 없이 모든 자막 시도)"""
    urls = [f"https://www.youtube.com/watch?v={vid}" for vid in video_ids]
    cmd = _ytdlp_base_args() + [
        '--write-auto-sub', '--write-subs', '--all-subs',
        '--sub-format', 'srt/best',
        '--skip-download',
        '-o', f'{SUBS_DIR}/%(id)s',
    ] + urls
    result = subprocess.run(cmd, capture_output=True, timeout=300)
    stderr = result.stderr.decode('utf-8', errors='replace')
    if result.returncode != 0:
        log(f"  [WARN] yt-dlp: {stderr[-300:]}")

    # 다운로드된 파일 확인 (ko, ko-KR, en 등 언어 불문)
    found = []
    for vid in video_ids:
        srt_files = sorted(SUBS_DIR.glob(f"{vid}*.srt"))
        if srt_files:
            target = SUBS_DIR / f"{vid}.ko.srt"
            if not target.exists():
                srt_files[0].rename(target)
            found.append(vid)
    return found


def download_subs_api(video_ids: list) -> list:
    """youtube-transcript-api 폴백 (쿠키 지원, v0.6.x API)"""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        return []
    cookies = Path('/tmp/yt-cookies.txt')
    cookies_arg = str(cookies) if cookies.exists() and cookies.stat().st_size > 100 else None
    saved = []
    for vid in video_ids:
        try:
            parts = YouTubeTranscriptApi.get_transcript(vid, languages=['ko', 'en'], cookies=cookies_arg)
            text = '\n'.join(s['text'] for s in parts)
            srt_path = SUBS_DIR / f"{vid}.ko.srt"
            srt_path.write_text(text, encoding='utf-8')
            saved.append(vid)
        except Exception as e:
            log(f"  [WARN] transcript-api {vid}: {e}")
    return saved


def download_subs(video_ids: list) -> list:
    if not video_ids:
        return []
    log(f"자막 다운로드 중 ({len(video_ids)}개)...")
    downloaded = download_subs_ytdlp(video_ids)
    log(f"  → yt-dlp: {len(downloaded)}개")

    remaining = [v for v in video_ids if v not in downloaded]
    if remaining:
        log(f"  → transcript-api 폴백 ({len(remaining)}개)...")
        downloaded += download_subs_api(remaining)

    log(f"  → 자막 다운로드 완료: {len(downloaded)}개")
    return downloaded


def summarize_new(videos: list):
    from summarize import summarize_video
    summaries = load_summaries()
    new_count = 0
    for v in videos:
        vid = v['id']
        if vid in summaries:
            continue
        log(f"  요약: {v.get('title','')[:50]}")
        result = summarize_video(vid, v.get('title', ''), verbose=False)
        if result:
            summaries[vid] = result
            new_count += 1
            save_summaries(summaries)
    log(f"  → 요약 완료: {new_count}개 신규")
    return new_count


def run():
    log("=" * 50)
    log("차곡차곡 투자연구소 일일 업데이트 시작")
    log("=" * 50)

    # 1. 최신 목록 가져오기
    fetched = fetch_latest_videos()
    if not fetched:
        log("ERROR: 동영상 목록 가져오기 실패")
        return

    # 2. channel_videos.json 업데이트
    (DATA_DIR / 'channel_videos.json').write_text(
        json.dumps(fetched, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    # 3. 새 동영상 찾기
    new_vids = find_new_videos(fetched)

    if not new_vids:
        log("새로운 동영상 없음. HTML만 재생성합니다.")
    else:
        sub_ids = download_subs([v['id'] for v in new_vids])
        vids_with_subs = [v for v in new_vids if v['id'] in sub_ids]
        summarize_new(vids_with_subs)

    # 4. HTML 재생성 (최신 30개)
    log("HTML 카드뉴스 생성 중...")
    from generate_html import generate
    videos_sorted = sorted(
        [v for v in fetched if v.get('timestamp')],
        key=lambda x: x['timestamp'], reverse=True
    )[:30]
    summaries = load_summaries()
    generate(videos_sorted, summaries)

    log(f"완료!")


if __name__ == '__main__':
    run()
