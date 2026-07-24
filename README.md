# incheonkirin.github.io

[Mingi Jeong](https://incheonkirin.github.io) — 비즈니스 문제를 기술 문제로 바꾸고, 모델 개발부터 운영과 조직 도입까지 책임하는 Applied Data Scientist의 기록.

- **Posts** · `content/posts/` — 운영·감사 맥락의 ML 글
- **Lab** · `content/lab/` — 실험·도구
- **Pulse** · `content/pulse/` — AI·데이터 관련 리서치 클리핑 (공개 선별)
- **Inbox** · `content/private/pulse-inbox/` — KIF/KIRI 자동 수집 (비공개)

## 로컬 미리보기

```bash
npm ci
npx quartz build --serve
```

Node 22+ 필요.

## Pulse 자동 수집 (선택)

`engine/` 크롤러는 `content/private/pulse-inbox/`에만 씁니다. 웹에 올릴 글은 `content/pulse/`로 수동 복사·선별합니다.

```bash
cd engine
pip install -r requirements.txt
python fetch.py && python render.py
```

## 배포

`main` push → GitHub Actions (`deploy-pages.yaml`) → GitHub Pages.
