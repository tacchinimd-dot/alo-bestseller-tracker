# Alo Yoga 베스트셀러 주간 스냅샷 트래커

Alo Yoga(Shopify) 여성/남성 베스트셀러 랭킹을 **매주 자동 수집**하여
SS/FW 시즌 비교용 데이터를 `alo_bestsellers_snapshots.csv` 에 누적하고,
**라이브 대시보드**로 팀에 공유합니다.

## 📊 라이브 대시보드 (팀 공유용)

**https://tacchinimd-dot.github.io/alo-bestseller-tracker/**

- 이 URL을 **새로고침**하면 그 시점까지 누적된 최신 데이터가 반영됩니다 (CSV를 실시간 fetch).
- 매주 월요일 자동 수집 → 봇이 CSV 커밋 → GitHub Pages 자동 재배포 → 팀이 새로고침하면 최신 데이터.
- 포함: 누적 현황 · 시즌 전환 추이 · FW 상품 증가 곡선 · 신규 진입/이탈 · 시즌 구성 · 베스트셀러 이미지 갤러리.

## 동작 방식
- **실행 주기**: 매주 월요일 09:00 KST (GitHub Actions cron, UTC 월 00:00)
- **수집 대상**: `bestsellers`(여성, W), `mens-bestsellers`(남성, M) 각 TOP 50
- **수집 루트**: Shopify `products.json` 우선 → 차단 시 Playwright(Chromium) 폴백
- **태깅**: 상품명 키워드로 `season_tag`(FW / SS / SEASONLESS / UNTAGGED) + `category` 자동 분류
- **이미지**: `products.json` 의 공식 상품 이미지 URL(`image` 컬럼)도 함께 수집
- **누적**: 실행 날짜(`snapshot_date`)를 한 세트로 추가. 같은 날 재실행 시 해당 날짜만 덮어씀(중복 방지)
- **자동 커밋**: 워크플로가 갱신된 CSV를 저장소에 self-commit → Pages 자동 갱신

## 수동 실행
GitHub 저장소 → **Actions** 탭 → *Weekly Alo Bestseller Snapshot* → **Run workflow**
또는 CLI:
```bash
gh workflow run "Weekly Alo Bestseller Snapshot"
gh run watch
```

## CSV 스키마 (`alo_bestsellers_snapshots.csv`)
`snapshot_date, gender, collection, rank, title, category, season_tag, product_type,
price, compare_at_price, on_sale, color_count, image, handle, tags`

## 파일 구성
- `index.html` — 라이브 대시보드(GitHub Pages 진입점, CSV 실시간 로드)
- `alo_bestseller_snapshot.py` — 수집 스크립트
- `.github/workflows/weekly-snapshot.yml` — 주간 자동 수집 + CSV self-commit

## 로컬 실행 (선택)
```bash
pip install -r requirements.txt
playwright install chromium   # 폴백용, 최초 1회
python alo_bestseller_snapshot.py
```
> 대시보드는 GitHub Pages(같은 사이트의 CSV) 환경에서 동작합니다. 로컬 `index.html` 을 `file://` 로 직접 열면
> 브라우저 보안정책으로 CSV를 읽지 못하므로, 배포 URL로 접속하거나 로컬 웹서버로 열어주세요.
