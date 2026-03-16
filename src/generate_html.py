"""
요약 데이터를 캐러셀 카드뉴스 HTML로 변환 (모바일 반응형, 슬라이드 스토리보드)
"""
import json
from pathlib import Path
from datetime import datetime
from utils import DATA_DIR, OUTPUT_DIR, load_summaries, load_channel_videos

CATEGORY_COLOR = {
    '국내주식':  '#6c63ff',
    '미국주식':  '#4ecdc4',
    'ETF':       '#ffd93d',
    '부동산':    '#f97316',
    '거시경제':  '#a855f7',
    '기타':      '#64748b',
}

SENTIMENT_ICON = {
    'bullish': ('📈', '#22c55e'),
    'bearish': ('📉', '#ef4444'),
    'neutral': ('➡️', '#94a3b8'),
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>차곡차곡 투자연구소 | 동영상 요약</title>

  <!-- PWA -->
  <link rel="manifest" href="manifest.json">
  <meta name="theme-color" content="#0f1117">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="차곡투자">
  <link rel="apple-touch-icon" href="icon-192.png">
  <link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
  <style>
    :root {{
      --bg: #0a0c10;
      --card: #13161f;
      --card2: #1a1d2a;
      --border: #22263a;
      --text: #e8eaf0;
      --muted: #7a7f96;
      --radius: 18px;
      --accent: #6c63ff;
    }}
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      font-family: -apple-system, 'Segoe UI', 'Apple SD Gothic Neo', sans-serif;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
    }}

    /* ── Header ── */
    .header {{
      position: sticky; top: 0; z-index: 100;
      background: rgba(10,12,16,0.92);
      backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border);
      padding: 0.85rem 1.2rem;
      display: flex; align-items: center; gap: 0.8rem;
    }}
    .header-logo {{
      width: 28px; height: 28px; border-radius: 8px;
      background: linear-gradient(135deg, #6c63ff, #4ecdc4);
      display: flex; align-items: center; justify-content: center;
      font-size: 0.9rem; flex-shrink: 0;
    }}
    .header-text {{ flex: 1; min-width: 0; }}
    .header-title {{ font-size: 0.95rem; font-weight: 700; line-height: 1; }}
    .header-sub {{ font-size: 0.7rem; color: var(--muted); margin-top: 0.15rem; }}
    .updated {{ font-size: 0.7rem; color: var(--muted); white-space: nowrap; flex-shrink: 0; }}

    /* ── Filters ── */
    .filters {{
      padding: 0.75rem 1rem;
      display: flex; gap: 0.5rem;
      overflow-x: auto; scrollbar-width: none;
      -webkit-overflow-scrolling: touch;
    }}
    .filters::-webkit-scrollbar {{ display: none; }}
    .filter-btn {{
      flex-shrink: 0; padding: 0.35rem 0.85rem; border-radius: 20px;
      border: 1px solid var(--border); background: var(--card2);
      color: var(--muted); font-size: 0.78rem; font-weight: 500;
      cursor: pointer; transition: all .18s; white-space: nowrap;
    }}
    .filter-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 700; }}
    .filter-btn:not(.active):hover {{ border-color: var(--accent); color: var(--accent); }}

    /* ── Cards grid ── */
    .cards {{
      padding: 0.5rem 1rem 3rem;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
      gap: 1.2rem;
    }}
    @media (max-width: 500px) {{
      .cards {{ grid-template-columns: 1fr; padding: 0.5rem 0.75rem 4rem; gap: 1rem; }}
    }}

    /* ── Card ── */
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      display: flex; flex-direction: column;
    }}

    /* Thumbnail */
    .thumb-wrap {{
      position: relative; width: 100%; aspect-ratio: 16/9;
      overflow: hidden; background: #1a1d2a;
    }}
    .thumb-wrap img {{
      width: 100%; height: 100%; object-fit: cover; display: block;
    }}
    .thumb-overlay {{
      position: absolute; inset: 0;
      background: linear-gradient(to bottom,rgba(0,0,0,0.08) 0%,rgba(0,0,0,0.04) 40%,rgba(0,0,0,0.72) 78%,rgba(0,0,0,0.92) 100%);
    }}
    .thumb-badges {{
      position: absolute; top: 0.7rem; left: 0.7rem;
      display: flex; gap: 0.4rem; align-items: center;
    }}
    .cat-badge {{
      font-size: 0.65rem; font-weight: 700;
      padding: 0.2rem 0.6rem; border-radius: 20px; color: #fff;
      backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
      border: 1px solid rgba(255,255,255,0.2);
    }}
    .sent-badge {{
      font-size: 0.72rem; padding: 0.18rem 0.5rem; border-radius: 20px;
      background: rgba(0,0,0,0.55); backdrop-filter: blur(4px);
      border: 1px solid rgba(255,255,255,0.15); font-weight: 600;
    }}
    .thumb-bottom {{
      position: absolute; bottom: 0; left: 0; right: 0;
      padding: 0.4rem 0.8rem 0.65rem;
    }}
    .thumb-headline {{
      font-size: 0.95rem; font-weight: 800; line-height: 1.3; color: #fff;
      text-shadow: 0 1px 4px rgba(0,0,0,0.9);
      display: -webkit-box; -webkit-line-clamp: 2;
      -webkit-box-orient: vertical; overflow: hidden;
    }}
    .thumb-date {{ font-size: 0.65rem; color: rgba(255,255,255,0.55); margin-top: 0.15rem; }}

    /* ── Carousel slides ── */
    .slides-outer {{ position: relative; overflow: hidden; }}
    .slides-track {{
      display: flex;
      transition: transform 0.32s cubic-bezier(0.4,0,0.2,1);
      will-change: transform;
    }}
    .slide {{
      min-width: 100%; padding: 1rem 1.1rem;
      display: flex; flex-direction: column; gap: 0.6rem;
    }}
    .slide-header {{
      display: flex; align-items: center; gap: 0.6rem;
    }}
    .slide-icon {{
      width: 36px; height: 36px; border-radius: 10px; flex-shrink: 0;
      background: rgba(108,99,255,0.15); border: 1px solid rgba(108,99,255,0.3);
      display: flex; align-items: center; justify-content: center; font-size: 1.1rem;
    }}
    .slide-title {{ font-size: 0.92rem; font-weight: 800; line-height: 1.3; }}
    .slide-num {{ margin-left: auto; font-size: 0.65rem; color: var(--muted); flex-shrink: 0; }}
    .slide-content {{ font-size: 0.84rem; line-height: 1.72; color: #b8bcd4; }}
    .slide-highlight {{
      background: rgba(108,99,255,0.08);
      border: 1px solid rgba(108,99,255,0.2);
      border-left: 3px solid var(--accent);
      border-radius: 8px; padding: 0.6rem 0.75rem;
      font-size: 0.8rem; color: #c4c0ff; line-height: 1.55;
    }}
    .slide-tags {{ display: flex; flex-wrap: wrap; gap: 0.35rem; padding-top: 0.2rem; }}

    /* Dots + nav */
    .slide-nav {{
      display: flex; align-items: center; gap: 0.5rem;
      padding: 0.45rem 0.8rem 0.7rem;
    }}
    .dots-wrap {{ flex: 1; display: flex; gap: 0.4rem; align-items: center; justify-content: center; }}
    .dot {{
      width: 6px; height: 6px; border-radius: 50%;
      background: var(--border); transition: all .2s; cursor: pointer;
    }}
    .dot.active {{ background: var(--accent); width: 18px; border-radius: 3px; }}
    .nav-btn {{
      width: 28px; height: 28px; border-radius: 50%;
      background: var(--card2); border: 1px solid var(--border);
      color: var(--muted); display: flex; align-items: center; justify-content: center;
      cursor: pointer; font-size: 0.75rem; transition: all .18s; flex-shrink: 0;
      user-select: none;
    }}
    .nav-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
    .nav-btn:disabled {{ opacity: 0.25; cursor: default; pointer-events: none; }}

    /* Tags */
    .stock-tag {{
      font-size: 0.72rem; font-weight: 700; padding: 0.22rem 0.6rem;
      border-radius: 8px; background: rgba(78,205,196,0.12);
      border: 1px solid rgba(78,205,196,0.35); color: #4ecdc4;
    }}
    .tag {{
      font-size: 0.7rem; padding: 0.2rem 0.55rem; border-radius: 8px;
      background: var(--card2); border: 1px solid var(--border); color: var(--muted);
    }}

    /* CTA */
    .card-cta {{
      display: flex; align-items: center; justify-content: center; gap: 0.4rem;
      padding: 0.65rem; border-top: 1px solid var(--border);
      font-size: 0.8rem; font-weight: 600; color: var(--muted);
      text-decoration: none; transition: background .18s, color .18s;
    }}
    .card-cta:hover {{ background: rgba(108,99,255,0.1); color: var(--accent); }}
    .play-icon {{
      width: 22px; height: 22px; border-radius: 50%;
      background: rgba(255,0,0,0.15); border: 1px solid rgba(255,0,0,0.3);
      display: flex; align-items: center; justify-content: center;
      font-size: 0.6rem; color: #ff4444;
    }}

    .empty {{ text-align: center; color: var(--muted); padding: 3rem; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <div class="header">
    <div class="header-logo">📊</div>
    <div class="header-text">
      <div class="header-title">차곡차곡 투자연구소</div>
      <div class="header-sub">동영상 AI 요약 카드뉴스</div>
    </div>
    <div class="updated">🕐 {updated}</div>
  </div>

  <div class="filters" id="filters">
    <button class="filter-btn active" data-cat="전체">전체 {total}</button>
    {filter_buttons}
  </div>

  <div class="cards" id="cards">
    {cards_html}
  </div>

  <script>
    // ── 카테고리 필터 ──
    const allCards = document.querySelectorAll('.card[data-cat]');
    document.querySelectorAll('.filter-btn').forEach(btn => {{
      btn.addEventListener('click', () => {{
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const cat = btn.dataset.cat;
        let visible = 0;
        allCards.forEach(c => {{
          const show = cat === '전체' || c.dataset.cat === cat;
          c.style.display = show ? '' : 'none';
          if (show) visible++;
        }});
        const empty = document.querySelector('.empty');
        if (empty) empty.style.display = visible === 0 ? '' : 'none';
      }});
    }});

    // ── 캐러셀 ──
    function initCarousel(card) {{
      const track = card.querySelector('.slides-track');
      const slides = card.querySelectorAll('.slide');
      const dots = card.querySelectorAll('.dot');
      const prevBtn = card.querySelector('.nav-prev');
      const nextBtn = card.querySelector('.nav-next');
      const total = slides.length;
      let idx = 0;

      function update() {{
        track.style.transform = `translateX(-${{idx * 100}}%)`;
        dots.forEach((d, i) => d.classList.toggle('active', i === idx));
        if (prevBtn) prevBtn.disabled = idx === 0;
        if (nextBtn) nextBtn.disabled = idx === total - 1;
      }}

      if (prevBtn) prevBtn.addEventListener('click', e => {{ e.stopPropagation(); idx = Math.max(0, idx-1); update(); }});
      if (nextBtn) nextBtn.addEventListener('click', e => {{ e.stopPropagation(); idx = Math.min(total-1, idx+1); update(); }});
      dots.forEach((d, i) => d.addEventListener('click', e => {{ e.stopPropagation(); idx = i; update(); }}));

      // 터치 스와이프
      let startX = 0;
      card.addEventListener('touchstart', e => {{ startX = e.touches[0].clientX; }}, {{passive: true}});
      card.addEventListener('touchend', e => {{
        const dx = e.changedTouches[0].clientX - startX;
        if (Math.abs(dx) > 40) {{ idx = dx < 0 ? Math.min(total-1, idx+1) : Math.max(0, idx-1); update(); }}
      }}, {{passive: true}});

      update();
    }}

    document.querySelectorAll('.card[data-cat]').forEach(initCarousel);

    // ── PWA 서비스워커 ──
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register('./sw.js', {{scope: './'}}).catch(() => {{}});
    }}
  </script>
</body>
</html>
"""

CARD_TEMPLATE = """
<div class="card" data-cat="{category}">
  <a href="https://youtube.com/watch?v={video_id}" target="_blank" style="display:contents">
  <div class="thumb-wrap">
    <img src="https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
         onerror="this.src='https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'"
         alt="{headline}" loading="lazy">
    <div class="thumb-overlay"></div>
    <div class="thumb-badges">
      <span class="cat-badge" style="background:{cat_color}">{category}</span>
      <span class="sent-badge" style="color:{sent_color}">{sent_icon}</span>
    </div>
    <div class="thumb-bottom">
      <div class="thumb-headline">{headline}</div>
      <div class="thumb-date">{date}</div>
    </div>
  </div>
  </a>
  <div class="slides-outer">
    <div class="slides-track">
      {slides_html}
    </div>
  </div>
  <div class="slide-nav">
    <button class="nav-btn nav-prev">‹</button>
    <div class="dots-wrap">{dots_html}</div>
    <button class="nav-btn nav-next">›</button>
  </div>
  <a class="card-cta" href="https://youtube.com/watch?v={video_id}" target="_blank">
    <span class="play-icon">▶</span> 원본 영상 보기
  </a>
</div>
"""

SLIDE_TEMPLATE = """
      <div class="slide">
        <div class="slide-header">
          <div class="slide-icon">{icon}</div>
          <div class="slide-title">{title}</div>
          <div class="slide-num">{num} / {total}</div>
        </div>
        <div class="slide-content">{content}</div>
        {highlight_html}
      </div>"""

SLIDE_LAST_TEMPLATE = """
      <div class="slide">
        <div class="slide-header">
          <div class="slide-icon">{icon}</div>
          <div class="slide-title">{title}</div>
          <div class="slide-num">{num} / {total}</div>
        </div>
        <div class="slide-content">{content}</div>
        {highlight_html}
        <div class="slide-tags">{stocks_html}{tags_html}</div>
      </div>"""


def _build_fallback_slides(s: dict) -> list:
    """구 포맷(key_points) 데이터를 slides로 변환 (하위 호환)"""
    slides = []
    summary = s.get('summary', '')
    if summary:
        slides.append({'icon': '📌', 'title': '핵심 요약', 'content': summary, 'highlight': ''})
    for i, kp in enumerate(s.get('key_points', [])[:4]):
        icons = ['🔍', '💡', '⚠️', '📊']
        slides.append({'icon': icons[i % len(icons)], 'title': f'포인트 {i+1}', 'content': kp, 'highlight': ''})
    if not slides:
        slides.append({'icon': '📄', 'title': '내용', 'content': '요약 데이터가 없습니다.', 'highlight': ''})
    return slides


def generate(videos: list, summaries: dict, output_path: Path = None):
    if output_path is None:
        output_path = OUTPUT_DIR / 'index.html'

    meta = {v['id']: v for v in videos}

    ordered = []
    for vid, s in summaries.items():
        if vid in meta:
            ordered.append((meta[vid], s))
    ordered.sort(key=lambda x: x[0].get('timestamp', 0), reverse=True)

    from collections import Counter
    cat_counts = Counter(s.get('category', '기타') for _, s in ordered)

    filter_buttons = '\n    '.join(
        f'<button class="filter-btn" data-cat="{cat}">{cat} {cnt}</button>'
        for cat, cnt in sorted(cat_counts.items())
    )

    cards_parts = []
    for v, s in ordered:
        cat = s.get('category', '기타')
        cat_color = CATEGORY_COLOR.get(cat, '#64748b')
        sent = s.get('sentiment', 'neutral')
        sent_icon, sent_color = SENTIMENT_ICON.get(sent, ('➡️', '#94a3b8'))

        # slides 또는 fallback
        slides = s.get('slides') or _build_fallback_slides(s)
        total = len(slides)

        stocks_html = ' '.join(
            f'<span class="stock-tag">{st}</span>' for st in s.get('stocks', [])[:4]
        )
        tags_html = ' '.join(
            f'<span class="tag">#{t}</span>' for t in s.get('tags', [])[:3]
        )

        slides_html_parts = []
        for i, sl in enumerate(slides):
            highlight_html = (
                f'<div class="slide-highlight">{sl["highlight"]}</div>'
                if sl.get('highlight') else ''
            )
            is_last = (i == total - 1)
            tpl = SLIDE_LAST_TEMPLATE if is_last else SLIDE_TEMPLATE
            slides_html_parts.append(tpl.format(
                icon=sl.get('icon', '📌'),
                title=sl.get('title', ''),
                content=sl.get('content', ''),
                highlight_html=highlight_html,
                num=i + 1,
                total=total,
                stocks_html=stocks_html if is_last else '',
                tags_html=tags_html if is_last else '',
            ))

        dots_html = ''.join(
            f'<div class="dot{"  active" if i == 0 else ""}"></div>'
            for i in range(total)
        )

        date_str = v.get('date', v.get('upload_date', ''))
        if len(date_str) == 8:
            date_str = f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:]}"

        card = CARD_TEMPLATE.format(
            video_id=v['id'],
            category=cat,
            cat_color=cat_color,
            date=date_str,
            headline=s.get('headline', ''),
            sent_icon=sent_icon,
            sent_color=sent_color,
            slides_html=''.join(slides_html_parts),
            dots_html=dots_html,
        )
        cards_parts.append(card)

    html = HTML_TEMPLATE.format(
        updated=datetime.now().strftime('%Y.%m.%d %H:%M'),
        total=len(ordered),
        filter_buttons=filter_buttons,
        cards_html='\n'.join(cards_parts) if cards_parts
                   else '<div class="empty">요약된 동영상이 없습니다</div>',
    )

    output_path.write_text(html, encoding='utf-8')
    print(f"HTML 생성 완료: {output_path} ({len(ordered)}개 카드)")
    return output_path


if __name__ == '__main__':
    from utils import load_channel_videos
    videos = load_channel_videos()
    summaries = load_summaries()
    generate(videos, summaries)
