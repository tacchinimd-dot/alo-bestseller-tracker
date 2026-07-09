# Alo Yoga 베스트셀러 주간 스냅샷 트래커

Alo Yoga(Shopify) 여성/남성 베스트셀러 랭킹을 **매주 자동 수집**하여
SS/FW 시즌 비교용 데이터를 `alo_bestsellers_snapshots.csv` 에 누적합니다.

## 동작 방식
- **실행 주기**: 매주 월요일 09:00 KST (GitHub Actions cron, UTC 월 00:00)
- **수집 대상**: `bestsellers`(여성, W), `mens-bestsellers`(남성, M) 각 TOP 50
- **수집 루트**: Shopify `products.json` 우선 → 차단 시 Playwright(Chromium) 폴백
- **태깅**: 상품명 키워드로 `season_tag`(FW / SS / SEASONLESS / UNTAGGED) + `category` 자동 분류
- **누적**: 실행 날짜(`snapshot_date`)를 한 세트로 추가. 같은 날 재실행 시 해당 날짜만 덮어씀(중복 방지)
- **자동 커밋**: 워크플로가 갱신된 CSV를 저장소에 self-commit

## 수동 실행
GitHub 저장소 → **Actions** 탭 → *Weekly Alo Bestseller Snapshot* → **Run workflow**
또는 CLI:
```bash
gh workflow run "Weekly Alo Bestseller Snapshot"
gh run watch
```

## CSV 스키마 (`alo_bestsellers_snapshots.csv`)
`snapshot_date, gender, collection, rank, title, category, season_tag, product_type,
price, compare_at_price, on_sale, color_count, handle, tags`

## 로컬 실행 (선택)
```bash
pip install -r requirements.txt
playwright install chromium   # 폴백용, 최초 1회
python alo_bestseller_snapshot.py
```
컬렉션 핸들 확인: `python alo_bestseller_snapshot.py --discover`
