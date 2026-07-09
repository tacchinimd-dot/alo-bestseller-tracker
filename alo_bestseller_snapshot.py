# -*- coding: utf-8 -*-
"""
Alo Yoga 베스트셀러 주간 스냅샷 수집기
======================================
목적: SS/FW 시즌 비교를 위해 베스트셀러 랭킹을 주기적으로 누적 수집
출력: alo_bestsellers_snapshots.csv (실행할 때마다 그날 스냅샷이 행으로 추가됨)

사용법:
    pip install requests playwright
    playwright install chromium        # 최초 1회만
    python alo_bestseller_snapshot.py

동작 방식:
    1) Shopify JSON 엔드포인트(/collections/{handle}/products.json) 우선 시도 — 가볍고 깔끔
    2) 429/차단 시 Playwright 실제 브라우저 렌더링으로 폴백
    3) 상품명 키워드로 SS성/FW성/시즌리스 자동 태깅
    4) 같은 날짜에 재실행하면 해당 날짜 데이터를 덮어씀 (중복 방지)
"""

import csv
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://www.aloyoga.com"

# 수집 대상 컬렉션. 핸들이 바뀌면 discover_collections()로 재확인 가능
COLLECTIONS = {
    "bestsellers": "W",        # 여성 베스트
    "mens-bestsellers": "M",   # 남성 베스트 (핸들이 다르면 아래 discover로 확인)
}

TOP_N = 50            # 컬렉션당 수집 상위 개수
OUT_CSV = Path(__file__).parent / "alo_bestsellers_snapshots.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html;q=0.9",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
}

# ── 시즌 태깅 키워드 (상품명/product_type 기준, 영문) ─────────────────
FW_KEYWORDS = [
    "hoodie", "sweatshirt", "sweatpant", "jogger", "jacket", "coat",
    "puffer", "sherpa", "fleece", "beanie", "half zip", "half-zip",
    "pullover", "cardigan", "sweater", "parka", "quilted", "velour",
    "thermal", "scarf", "glove", "mitten", "vest",
]
SS_KEYWORDS = [
    "bra", "tank", "short", "skirt", "skort", "dress", "swim", "bikini",
    "sleeveless", "visor", "tube top", "crop top", "tennis", "cami",
]
SEASONLESS_KEYWORDS = [
    "legging", "sock", "bag", "tote", "headband", "scrunchie", "mat",
    "bottle", "towel", "cap", "hat", "belt bag", "airlift", "airbrush",
    "tee", "t-shirt", "long sleeve", "onesie", "jumpsuit", "bodysuit",
]


def tag_season(title: str, product_type: str) -> str:
    text = f"{title} {product_type}".lower()
    # FW 우선 판정 (예: "fleece shorts" 같은 혼합 케이스는 FW 소재 우선)
    for kw in FW_KEYWORDS:
        if kw in text:
            return "FW"
    for kw in SS_KEYWORDS:
        if kw in text:
            return "SS"
    for kw in SEASONLESS_KEYWORDS:
        if kw in text:
            return "SEASONLESS"
    return "UNTAGGED"


def simplify_category(title: str, product_type: str) -> str:
    """대시보드 스택차트용 대분류"""
    text = f"{title} {product_type}".lower()
    rules = [
        ("OUTERWEAR", ["jacket", "coat", "puffer", "parka", "vest", "cardigan"]),
        ("FLEECE/KNIT", ["hoodie", "sweatshirt", "sweater", "sherpa", "fleece", "pullover", "half zip", "half-zip", "velour"]),
        ("BOTTOM-WARM", ["jogger", "sweatpant", "flare", "wide leg"]),
        ("LEGGING", ["legging", "airlift", "airbrush", "capri"]),
        ("BRA/TANK", ["bra", "tank", "cami", "tube top", "crop top", "bodysuit"]),
        ("SHORTS/SKIRT", ["short", "skirt", "skort", "tennis"]),
        ("DRESS/SWIM", ["dress", "swim", "bikini", "onesie", "jumpsuit"]),
        ("TOP", ["tee", "t-shirt", "long sleeve", "shirt", "top"]),
        ("ACC", ["sock", "bag", "tote", "headband", "scrunchie", "beanie", "cap", "hat", "mat", "bottle", "towel", "belt", "scarf", "glove"]),
    ]
    for cat, kws in rules:
        if any(kw in text for kw in kws):
            return cat
    return "ETC"


# ── 루트 1: Shopify JSON ────────────────────────────────────────────
def fetch_via_json(handle: str) -> list[dict] | None:
    url = f"{BASE_URL}/collections/{handle}/products.json"
    try:
        r = requests.get(url, headers=HEADERS, params={"limit": TOP_N}, timeout=20)
        if r.status_code != 200:
            print(f"  [JSON] {handle}: HTTP {r.status_code} → Playwright 폴백")
            return None
        products = r.json().get("products", [])
        if not products:
            print(f"  [JSON] {handle}: 상품 0개 → Playwright 폴백")
            return None
        rows = []
        for rank, p in enumerate(products[:TOP_N], start=1):
            variants = p.get("variants", [])
            prices = [float(v["price"]) for v in variants if v.get("price")]
            compare = [float(v["compare_at_price"]) for v in variants
                       if v.get("compare_at_price")]
            colors = {re.split(r"\s*/\s*", v.get("title", ""))[0]
                      for v in variants if v.get("title")}
            rows.append({
                "rank": rank,
                "title": p.get("title", ""),
                "product_type": p.get("product_type", ""),
                "handle": p.get("handle", ""),
                "price": min(prices) if prices else "",
                "compare_at_price": min(compare) if compare else "",
                "on_sale": bool(compare),
                "color_count": len(colors),
                "tags": ";".join(p.get("tags", []))[:200],
            })
        return rows
    except Exception as e:
        print(f"  [JSON] {handle}: 오류 {e} → Playwright 폴백")
        return None


# ── 루트 2: Playwright 폴백 ─────────────────────────────────────────
def fetch_via_playwright(handle: str) -> list[dict]:
    from playwright.sync_api import sync_playwright

    url = f"{BASE_URL}/collections/{handle}"
    rows = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(user_agent=HEADERS["User-Agent"],
                                locale="ko-KR")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        # 스크롤로 lazy-load 유도
        for _ in range(6):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(1200)

        # 우선 페이지 내 JSON(product grid state) 시도, 실패 시 DOM 파싱
        cards = page.query_selector_all(
            "[data-product-id], .product-tile, .product-card, li.grid__item"
        )
        rank = 0
        for card in cards:
            title_el = card.query_selector(
                "a[href*='/products/'] , .product-tile__name, .product-card__title"
            )
            if not title_el:
                continue
            title = (title_el.inner_text() or "").strip()
            if not title:
                continue
            href = ""
            link = card.query_selector("a[href*='/products/']")
            if link:
                href = link.get_attribute("href") or ""
            price_el = card.query_selector("[class*='price']")
            price_txt = (price_el.inner_text() if price_el else "").strip()
            price_match = re.search(r"[\d,.]+", price_txt.replace("₩", ""))
            rank += 1
            rows.append({
                "rank": rank,
                "title": title,
                "product_type": "",
                "handle": href.split("/products/")[-1].split("?")[0] if href else "",
                "price": price_match.group().replace(",", "") if price_match else "",
                "compare_at_price": "",
                "on_sale": "SALE" in price_txt.upper() or "%" in price_txt,
                "color_count": "",
                "tags": "",
            })
            if rank >= TOP_N:
                break
        browser.close()
    return rows


# ── 컬렉션 핸들 탐색 도우미 (핸들이 안 맞을 때 1회 실행) ──────────────
def discover_collections():
    url = f"{BASE_URL}/collections.json?limit=250"
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"collections.json 접근 불가 (HTTP {r.status_code})")
        return
    for c in r.json().get("collections", []):
        h = c.get("handle", "")
        if "best" in h or "top" in h:
            print(f"  {h}  ←  {c.get('title')}")


# ── 저장: 같은 날짜 데이터는 덮어쓰기 ────────────────────────────────
FIELDNAMES = [
    "snapshot_date", "gender", "collection", "rank", "title", "category",
    "season_tag", "product_type", "price", "compare_at_price", "on_sale",
    "color_count", "handle", "tags",
]


def save(all_rows: list[dict]):
    today = date.today().isoformat()
    existing = []
    if OUT_CSV.exists():
        with open(OUT_CSV, newline="", encoding="utf-8-sig") as f:
            existing = [r for r in csv.DictReader(f)
                        if r.get("snapshot_date") != today]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in existing + all_rows:
            w.writerow(r)
    print(f"\n저장 완료: {OUT_CSV}  (오늘 {len(all_rows)}행, 누적 {len(existing) + len(all_rows)}행)")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--discover":
        discover_collections()
        return

    today = date.today().isoformat()
    all_rows = []
    for handle, gender in COLLECTIONS.items():
        print(f"\n[{handle}] 수집 중...")
        rows = fetch_via_json(handle)
        if rows is None:
            rows = fetch_via_playwright(handle)
        for r in rows:
            r["snapshot_date"] = today
            r["gender"] = gender
            r["collection"] = handle
            r["season_tag"] = tag_season(r["title"], r["product_type"])
            r["category"] = simplify_category(r["title"], r["product_type"])
        print(f"  → {len(rows)}개 수집")
        all_rows.extend(rows)
        time.sleep(2)

    if not all_rows:
        print("수집 실패. python alo_bestseller_snapshot.py --discover 로 컬렉션 핸들을 확인해보세요.")
        return
    save(all_rows)

    # 간단 요약 출력
    from collections import Counter
    st = Counter(r["season_tag"] for r in all_rows)
    print(f"시즌 태그 분포: {dict(st)}")


if __name__ == "__main__":
    main()
