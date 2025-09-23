#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright를 사용한 다이닝코드 맛집 데이터 수집 스크립트
서울역, 남대문, 회현역 3개 지역의 맛집 정보를 수집합니다.
"""

import asyncio
import argparse
from playwright.async_api import async_playwright
import json
import time
import re
from urllib.parse import urljoin, quote
import random
from datetime import datetime
try:
    from tqdm import tqdm  # 진행률 표시
except Exception:
    # tqdm 미설치 시에도 동작하도록 더미 래퍼 제공
    def tqdm(iterable, total=None, desc=None):
        return iterable

class DiningCodePlaywrightScraper:
    def __init__(self):
        self.base_url = "https://www.diningcode.com"
        self.restaurants = []
        self.restaurant_id_counter = 1
        
        # 수집할 지역 정보
        self.locations = {
            'seoul_station': {
                'name': '서울역',
                'query': '서울역',
                'url': 'https://www.diningcode.com/list.dc?query=서울역'
            },
            'namdaemun': {
                'name': '남대문',
                'query': '남대문',
                'url': 'https://www.diningcode.com/list.dc?query=남대문'
            },
            'hoehyeon': {
                'name': '회현역',
                'query': '회현역',
                'url': 'https://www.diningcode.com/list.dc?query=회현역'
            }
        }
        

    async def get_restaurant_list(self, page, location_url, location_name):
        """지역별 맛집 리스트를 가져옵니다."""
        print(f"[INFO] {location_name} 지역 맛집 리스트 수집 중...")
        
        try:
            # 페이지네이션까지 모두 순회하며 링크 수집
            detail_links = await self.collect_links_with_pagination(page, location_url)

            print(f"   상세 링크 수집: {len(detail_links)}개")

            # 상세 페이지 방문하여 데이터 확정 수집 (tqdm 진행률 표시)
            print(f"   [INFO] {len(detail_links)}개 음식점 상세 수집 시작")
            for idx, (name, url) in enumerate(tqdm(detail_links, total=len(detail_links), desc=f"{location_name} 전체 수집")):
                try:
                    await page.goto(url, wait_until='domcontentloaded')
                    await page.wait_for_timeout(600)
                    data = await self.extract_from_detail_page(page, name, location_name, url)
                    if data:
                        self.restaurants.append(data)
                        print(f"   [OK] {data['name']} 수집 완료 ({idx+1}/{len(detail_links)})")
                except Exception as e:
                    print(f"   [ERROR] 상세 수집 실패: {e}")
                await asyncio.sleep(random.uniform(0.3, 0.9))
            
        except Exception as e:
            print(f"[ERROR] {location_name} 지역 데이터 수집 실패: {e}")

    async def collect_links_with_pagination(self, page, start_url: str):
        """개선된 방식으로 목록 페이지에서 모든 상세 링크를 수집합니다."""
        print(f"   [INFO] 개선된 링크 수집 시작")
        collected = []
        seen = set()

        async def collect_on_current_page():
            # 개선된 더보기/스크롤 처리
            await self.load_all_items(page)

            # 우선순위 셀렉터로 링크 수집
            links_found = await self.extract_links_with_priority_selectors(page)

            for name, url in links_found:
                if url not in seen and name and len(name.strip()) >= 2:
                    collected.append((name.strip(), url))
                    seen.add(url)

            print(f"   [COLLECT] 현재 페이지에서 {len(links_found)}개 링크 수집됨")

            # 우선순위 셀렉터로 링크 수집
            links_found = await self.extract_links_with_priority_selectors(page)

        # 시작 페이지 로드
        try:
            await page.goto(start_url, wait_until='domcontentloaded', timeout=60000)
        except Exception:
            await page.wait_for_timeout(1500)
            await page.goto(start_url, wait_until='domcontentloaded', timeout=90000)
        await page.wait_for_timeout(2000)

        await collect_on_current_page()

        # 페이지네이션 순회 (최대 200 페이지로 확장)
        for _ in range(200):
            moved = False
            # 다음 페이지 후보들
            next_selectors = [
                'a[rel="next"]',
                'a.next',
                '.pagination a.next',
                '.paging a.next',
            ]
            # 텍스트 기반
            next_texts = ['다음', '›', '>', '더보기', '더 보기']
            try:
                # 1) 명시적 next 셀렉터
                for sel in next_selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible():
                            href = await el.get_attribute('href')
                            if href:
                                url = urljoin(start_url, href)
                                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                            else:
                                await el.click()
                            await page.wait_for_timeout(1500)
                            await collect_on_current_page()
                            moved = True
                            break
                    except Exception:
                        continue
                if moved:
                    continue
                # 2) 텍스트 기반 next
                for label in next_texts:
                    try:
                        btn = page.get_by_text(label, exact=False)
                        if await btn.is_visible():
                            await btn.click(timeout=2500)
                            await page.wait_for_timeout(1500)
                            await collect_on_current_page()
                            moved = True
                            break
                    except Exception:
                        continue
            except Exception:
                pass
            if not moved:
                break
        return collected

    async def scrape_n_from_list(self, list_url: str, n: int, output: str = "unified_restaurant_datamart.jsonl"):
        """지정한 리스트 URL에서 상위 n개 상세만 수집하여 JSONL로 저장"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            # 지역명 추정
            location_name = next((loc['name'] for loc in self.locations.values() if loc['url'] == list_url), "")
            try:
                self.restaurants = []
                await self.get_restaurant_list(page, list_url, location_name or "")
            finally:
                await browser.close()
            if self.restaurants:
                self.save_to_jsonl(output)
            else:
                print("[ERROR] 수집된 데이터가 없습니다.")

    async def load_all_items(self, page):
        """개선된 더보기 버튼 클릭 및 스크롤링으로 모든 항목을 로드합니다."""
        print("   [INFO] 개선된 로딩 방식 시작...")

        # 페이지 상단 표기 총 개수 파악(맛집 (N곳)) - 제한 없이 수집
        target_total = None

        # 초기 대기 및 로딩 상태 확인
        await page.wait_for_timeout(3000)
        await page.wait_for_load_state("networkidle", timeout=30000)

        last_count = 0
        stable_rounds = 0
        iteration = 0
        max_iterations = 1000

        while iteration < max_iterations:
            iteration += 1

            # 현재 음식점 개수 확인 (우선순위 셀렉터 사용)
            current_count = await self.count_current_items(page)

            # 목표 개수 체크 비활성화 - 제한 없이 수집

            # 더보기 버튼 클릭 시도
            more_clicked = await self.handle_more_button(page)

            if more_clicked:
                print(f"   [CLICK] 더보기 버튼 클릭됨, 현재: {current_count}개")
                # 클릭 후 로딩 대기
                await page.wait_for_timeout(3000)
                await page.wait_for_load_state("networkidle", timeout=15000)
                stable_rounds = 0  # 클릭 성공시 안정화 카운트 리셋
            else:
                # 더보기 버튼이 없으면 스크롤링 시도
                await self.scroll_to_load_more(page)
                await page.wait_for_timeout(2000)

            # 개수 변화 확인
            new_count = await self.count_current_items(page)
            if new_count > current_count:
                print(f"   [PROGRESS] {current_count} → {new_count}개 (+{new_count - current_count})")
                stable_rounds = 0
            else:
                stable_rounds += 1

            # 진행상황 출력 (매 20회마다)
            if iteration % 20 == 0:
                print(f"   [STATUS] {iteration}회차, 현재: {new_count}개")

            # 안정화 검사: 목표치에 도달하지 못했으면 더 오래 시도
            stability_threshold = 50 if target_total and new_count < target_total * 0.8 else 30
            if stable_rounds >= stability_threshold:
                print(f"   [COMPLETE] 로딩 완료: 총 {new_count}개 수집 (안정화)")
                break

            last_count = new_count

        final_count = await self.count_current_items(page)
        print(f"   [FINAL] 최종 수집: {final_count}개 항목")

    async def count_current_items(self, page):
        """현재 페이지의 음식점 개수를 안정적으로 카운트합니다."""
        try:
            # 1순위: data-idx 속성 (가장 안정적)
            count = await page.eval_on_selector_all('[data-idx]', 'els => els.length')
            if count > 0:
                return count

            # 2순위: data-v-rid 속성
            count = await page.eval_on_selector_all('div[data-v-rid]', 'els => els.length')
            if count > 0:
                return count

            # 3순위: P/ 링크 패턴 (기존 방식)
            count = await page.eval_on_selector_all(
                'a', r'els => els.filter(e => /P\//.test(e.getAttribute("href")||"")).length'
            )
            return count
        except Exception:
            return 0

    async def handle_more_button(self, page):
        """강화된 더보기 버튼 클릭 로직 - 다양한 방법으로 시도"""
        try:
            clicked = False

            # 1) 다이닝코드 특화 셀렉터들 (실제 사이트 구조 기반)
            diningcode_selectors = [
                '.btn_more',              # 다이닝코드 더보기 버튼 클래스
                '.more_btn',
                '.load-more',
                '.btn-load-more',
                'button[onclick*="more"]', # onclick에 more가 포함된 버튼
                'a[onclick*="more"]',      # onclick에 more가 포함된 링크
                '.paging .more',          # 페이징 영역의 더보기
                '#btn_more',              # ID 기반
                '[data-action*="more"]',  # data-action 속성
            ]

            for selector in diningcode_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        if element and await element.is_visible():
                            await element.click()
                            print(f"   [CLICK] 더보기 버튼 클릭 성공: {selector}")
                            return True
                except Exception:
                    continue

            # 2) 텍스트 기반 매칭 (더 광범위한 패턴)
            text_patterns = [
                '더보기', '더 보기', '더보기 20', '20개 더보기', '더 보기 20개',
                '더 많은', '더 많이', 'more', 'More', 'MORE', 'Load More',
                '다음 20개', '계속 보기', '추가 보기'
            ]

            for pattern in text_patterns:
                try:
                    # Playwright의 내장 텍스트 찾기 (더 정확함)
                    locator = page.locator(f"text={pattern}").first
                    if await locator.is_visible(timeout=500):
                        await locator.click(timeout=3000)
                        print(f"   [CLICK] 텍스트 매칭 클릭 성공: {pattern}")
                        return True
                except Exception:
                    continue

            # 3) XPath 방식 (더 정확한 텍스트 매칭)
            xpath_patterns = [
                "//button[contains(text(),'더보기')]",
                "//a[contains(text(),'더보기')]",
                "//div[contains(text(),'더보기')]",
                "//span[contains(text(),'더보기')]",
                "//button[contains(@class,'more')]",
                "//a[contains(@class,'more')]",
            ]

            for xpath in xpath_patterns:
                try:
                    element = await page.query_selector(f"xpath={xpath}")
                    if element and await element.is_visible():
                        await element.click()
                        print(f"   [CLICK] XPath 클릭 성공: {xpath}")
                        return True
                except Exception:
                    continue

            # 4) JavaScript 직접 실행 (최후의 수단)
            try:
                clicked = await page.evaluate('''() => {
                    const patterns = ['더보기','더 보기','more','More','load more','Load More'];
                    const elements = Array.from(document.querySelectorAll('*'));

                    for (const el of elements) {
                        if (!el.offsetParent) continue; // 숨겨진 요소 제외

                        const text = (el.innerText || el.textContent || '').trim().toLowerCase();
                        const isClickable = el.tagName.toLowerCase() === 'button' ||
                                          el.tagName.toLowerCase() === 'a' ||
                                          el.onclick ||
                                          el.getAttribute('onclick') ||
                                          window.getComputedStyle(el).cursor === 'pointer';

                        if (isClickable && patterns.some(p => text.includes(p.toLowerCase()))) {
                            el.click();
                            console.log('JS 직접 클릭:', el);
                            return true;
                        }
                    }
                    return false;
                }''')

                if clicked:
                    print(f"   [CLICK] JavaScript 직접 클릭 성공")
                    return True

            except Exception:
                pass

            return False

        except Exception as e:
            print(f"   [ERROR] 더보기 버튼 클릭 실패: {e}")
            return False

    async def scroll_to_load_more(self, page):
        """강화된 스크롤링으로 추가 항목 로딩을 시도합니다."""
        try:
            # 1) 다양한 스크롤 방식 시도
            scroll_methods = [
                '() => { window.scrollTo(0, document.body.scrollHeight); }',
                '() => { window.scrollTo(0, document.documentElement.scrollHeight); }',
                '() => { document.documentElement.scrollTop = document.documentElement.scrollHeight; }',
                '() => { window.scrollBy(0, window.innerHeight * 3); }',
            ]

            for method in scroll_methods:
                try:
                    await page.evaluate(method)
                    await page.wait_for_timeout(800)
                except Exception:
                    continue

            # 2) 다이닝코드 특화 리스트 영역 스크롤
            list_selectors = [
                '#div_lf',           # 다이닝코드 좌측 리스트
                '.list-area',
                '.left-area',
                '.dc-list',
                '.restaurant-list',
                '.search-results',
                '.area_lf'
            ]

            for selector in list_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        # 해당 영역으로 스크롤 후 내부 스크롤
                        await element.scroll_into_view_if_needed()
                        await element.hover()

                        # 여러 번 스크롤 시도
                        for _ in range(5):
                            await page.evaluate('(el) => { el.scrollBy(0, el.clientHeight); }', element)
                            await page.wait_for_timeout(500)
                        break
                except Exception:
                    continue

            # 3) 페이지 끝에서 추가 스크롤 시도 (무한 스크롤 감지)
            try:
                await page.keyboard.press('End')
                await page.wait_for_timeout(1000)
                await page.keyboard.press('PageDown')
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            # 4) 마우스 휠 시뮬레이션
            try:
                await page.mouse.wheel(0, 2000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass

        except Exception as e:
            print(f"   [SCROLL ERROR] {e}")
            pass

    async def extract_links_with_priority_selectors(self, page):
        """우선순위 셀렉터를 사용해 링크를 추출합니다."""
        links = []

        # 1순위: data-idx 속성을 가진 요소에서 링크 찾기
        try:
            items = await page.query_selector_all('[data-idx]')
            for item in items:
                try:
                    # 링크 찾기
                    link_elem = await item.query_selector('a[href*="/P/"]')
                    if not link_elem:
                        link_elem = await item.query_selector('a[href*="profile"]')

                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        name = (await link_elem.inner_text() or '').strip()

                        # 이름이 너무 길거나 이상하면 다른 요소에서 찾기
                        if not name or len(name) > 50 or '\n' in name:
                            name_elem = await item.query_selector('.name, .title, h3, h4')
                            if name_elem:
                                name = (await name_elem.inner_text() or '').strip()

                        if href and name:
                            full_url = urljoin(self.base_url, href)
                            links.append((name, full_url))
                except Exception:
                    continue

            if links:
                print(f"   [SUCCESS] data-idx 방식으로 {len(links)}개 링크 추출")
                return links
        except Exception:
            pass

        # 2순위: 기존 셀렉터 방식
        link_selectors = [
            'a[href*="/P/"]',
            'a[href*="profile"]',
            'div[data-v-rid] a',
        ]

        for selector in link_selectors:
            try:
                anchors = await page.query_selector_all(selector)
                for a in anchors:
                    href = await a.get_attribute('href')
                    text = (await a.inner_text() or '').strip()
                    if href and text and len(text) >= 2:
                        full_url = urljoin(self.base_url, href)
                        links.append((text, full_url))
            except Exception:
                continue

        # 3순위: JSON-LD 데이터 추출
        try:
            items_from_jsonld = await self.extract_list_from_jsonld(page)
            for entry in items_from_jsonld or []:
                url = entry.get('url')
                name = entry.get('name') or ''
                if url and name:
                    links.append((name, url))
        except Exception:
            pass

        print(f"   [FALLBACK] 기존 방식으로 {len(links)}개 링크 추출")
        return links

    async def extract_list_from_jsonld(self, page):
        """페이지의 JSON-LD(ItemList)에서 리스트 항목을 추출합니다."""
        try:
            handles = await page.query_selector_all('script[type="application/ld+json"]')
            results = []
            for h in handles:
                text = await h.inner_text()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except Exception:
                    # 일부 스크립트는 여러 객체를 포함할 수 있음
                    try:
                        data = json.loads(text.strip().strip('\uFEFF'))
                    except Exception:
                        continue
                # ItemList 형태 찾기
                candidates = data if isinstance(data, list) else [data]
                for obj in candidates:
                    if isinstance(obj, dict) and obj.get('@type') in ('ItemList', 'CollectionPage'):
                        items = obj.get('itemListElement') or obj.get('hasPart') or []
                        for it in items:
                            # ListItem 포맷 처리
                            if isinstance(it, dict) and it.get('@type') == 'ListItem':
                                item = it.get('item') or {}
                                if isinstance(item, dict):
                                    name = item.get('name')
                                    url = item.get('url')
                                    if url:
                                        results.append({'name': name, 'url': url})
                            elif isinstance(it, dict):
                                name = it.get('name')
                                url = it.get('url')
                                if url:
                                    results.append({'name': name, 'url': url})
            return results
        except Exception as e:
            print(f"   JSON-LD 파싱 실패: {e}")
            return []

    async def extract_from_detail_page(self, page, fallback_name, location_name, url):
        """상세 페이지에서 정보를 추출합니다."""
        try:
            # 기본값
            name = fallback_name or "이름 없음"
            rating = 0.0
            review_count = 0
            category = "기타"
            address = ""
            image_url = ""
            phone = ""
            first_review = ""

            # fallback_name이 너무 긴 경우 정리
            if name and len(name) > 100:
                # 첫 번째 줄만 가져오기
                lines = name.split('\n')
                if lines:
                    name = lines[0].strip()
                    # 숫자와 점으로 시작하는 경우 제거
                    if name and name[0].isdigit():
                        parts = name.split('.', 1)
                        if len(parts) > 1:
                            name = parts[1].strip()

            # JSON-LD에서 식당 정보 우선 추출
            handles = await page.query_selector_all('script[type="application/ld+json"]')
            for h in handles:
                text = await h.inner_text()
                if not text:
                    continue
                try:
                    data = json.loads(text)
                except Exception:
                    continue
                candidates = data if isinstance(data, list) else [data]
                for obj in candidates:
                    if isinstance(obj, dict) and obj.get('@type') in ('Restaurant', 'LocalBusiness', 'Place'):
                        name = obj.get('name') or name
                        agg = obj.get('aggregateRating') or {}
                        try:
                            rating = float(agg.get('ratingValue')) if agg.get('ratingValue') else rating
                        except Exception:
                            pass
                        try:
                            review_count = int(agg.get('reviewCount')) if agg.get('reviewCount') else review_count
                        except Exception:
                            pass
                        address_obj = obj.get('address') or {}
                        if isinstance(address_obj, dict):
                            address = address_obj.get('streetAddress') or address_obj.get('addressLocality') or address or ""
                        image = obj.get('image')
                        if isinstance(image, str):
                            image_url = image
                        elif isinstance(image, list) and image:
                            image_url = image[0]

            # DOM에서 더 정확한 이름 찾기 (지도 컨트롤러 제외)
            if not name or len(name) > 50 or '\n' in name or '지도' in name or '컨트롤러' in name:
                title_selectors = [
                    'h1:not([class*="map"]):not([class*="control"])',
                    'h2:not([class*="map"]):not([class*="control"])',
                    '.store-name', '.restaurant-name', '.shop-name',
                    '[class*="title"]:not([class*="map"]):not([class*="control"])',
                    '[class*="name"]:not([class*="map"]):not([class*="control"])',
                    '.name:not([class*="map"]):not([class*="control"])'
                ]
                for sel in title_selectors:
                    try:
                        title_elem = await page.query_selector(sel)
                        if title_elem:
                            title_text = (await title_elem.inner_text() or '').strip()
                            if title_text and len(title_text) <= 50 and '\n' not in title_text:
                                name = title_text
                                break
                    except Exception:
                        continue

            # 추가로 DOM에서 카테고리/주소/평점/리뷰/전화 보완
            dom_category = await page.query_selector('.category, .tag, .type, [class*="category"]')
            if dom_category:
                txt = (await dom_category.inner_text() or '').strip()
                if txt:
                    category = txt
            dom_address = await page.query_selector('.address, .location, [class*="address"]')
            if dom_address:
                txt = (await dom_address.inner_text() or '').strip()
                if txt:
                    address = txt

            # 평점
            if rating == 0.0:
                rating_selectors = [
                    '[itemprop="ratingValue"]', '.point', '.rating', '.score', '[class*="rating"]', '[class*="score"]'
                ]
                for sel in rating_selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            t = (await el.inner_text() or '').strip()
                            m = re.search(r'(\d+\.?\d*)', t)
                            if m:
                                rating = float(m.group(1))
                                break
                    except Exception:
                        continue

            # 리뷰 수
            if review_count == 0:
                review_selectors = [
                    '[itemprop="reviewCount"]', '.review', '.count', '[class*="review"]'
                ]
                for sel in review_selectors:
                    try:
                        el = await page.query_selector(sel)
                        if el:
                            t = (await el.inner_text() or '').strip()
                            m = re.search(r'(\d{1,4})\s*명|\((\d{1,4})\s*명\)', t)
                            if m:
                                review_count = int(m.group(1) or m.group(2))
                                break
                            m2 = re.search(r'(\d{1,5})', t)
                            if m2 and int(m2.group(1)) > 0:
                                review_count = int(m2.group(1))
                                break
                    except Exception:
                        continue

            # 전화번호
            if not phone:
                try:
                    tel = await page.query_selector('a[href^="tel:"]')
                    if tel:
                        href = await tel.get_attribute('href')
                        if href:
                            phone = href.replace('tel:', '').strip()
                except Exception:
                    pass
                if not phone:
                    try:
                        # 텍스트에서 패턴으로 탐색
                        body_text = await page.evaluate('() => document.body && document.body.innerText')
                        if body_text:
                            m = re.search(r'(0\d{1,2}-\d{3,4}-\d{4})', body_text)
                            if m:
                                phone = m.group(1)
                    except Exception:
                        pass
            
            # 주소 보완: 본문에서 도로명/지번 패턴 추출
            if not address:
                try:
                    body_text = await page.evaluate('() => document.body && document.body.innerText')
                    if body_text:
                        # 간단한 도로명 주소 패턴(시 구 동 ... 번지)
                        m = re.search(r'서울[특]*별시\s*\S+구\s*\S+\s*\d+[\-\d]*', body_text)
                        if m:
                            address = m.group(0).strip()
                except Exception:
                    pass

            # 이미지 보완: og:image 또는 대표 이미지 후보
            if not image_url:
                try:
                    og = await page.query_selector('meta[property="og:image"], meta[name="og:image"]')
                    if og:
                        content = await og.get_attribute('content')
                        if content:
                            image_url = content
                except Exception:
                    pass
            if not image_url:
                img_selectors = [
                    '.photo img', '.thumbnail img', '.img img', '.images img',
                    'img[alt*="대표" i]', 'img[alt*="main" i]', 'img'
                ]
                for sel in img_selectors:
                    try:
                        img = await page.query_selector(sel)
                        if img:
                            src = await img.get_attribute('src')
                            if src and src.startswith('http'):
                                image_url = src
                                break
                    except Exception:
                        continue

            # 첫 리뷰 추출 시도
            if not first_review:
                review_container_selectors = [
                    '[class*="review"] li', '[class*="review"] .item', '.review-item', '.rv-item', '.comment', '.dc-review'
                ]
                for sel in review_container_selectors:
                    try:
                        node = await page.query_selector(sel)
                        if node:
                            txt = (await node.inner_text() or '').strip()
                            if txt:
                                first_review = re.sub(r'\s+', ' ', txt)
                                if len(first_review) > 400:
                                    first_review = first_review[:400] + '...'
                                break
                    except Exception:
                        continue

            distance_from_office_m = self.calculate_distance_from_office(location_name)
            walking_time_min = max(1, distance_from_office_m // 80)
            if distance_from_office_m <= 200:
                distance_category = "매우 가까움"
            elif distance_from_office_m <= 500:
                distance_category = "가까움"
            elif distance_from_office_m <= 1000:
                distance_category = "보통"
            else:
                distance_category = "조금 멀음"

            food_genre = self.classify_food_genre(category)
            restaurant_id = f"REST_{self.restaurant_id_counter:04d}_{(name or 'unknown').replace(' ', '_')}"
            self.restaurant_id_counter += 1

            return {
                "restaurant_id": restaurant_id,
                "name": name,
                "address": address,
                "phone": phone,
                "category": category,
                "food_genre": food_genre,
                "rating": rating,
                "review_count": review_count,
                "latitude": 0.0,
                "longitude": 0.0,
                "location_description": f"{location_name} 일대",
                "distance_from_office_m": distance_from_office_m,
                "walking_time_min": walking_time_min,
                "is_walkable": distance_from_office_m <= 1500,
                "distance_category": distance_category,
                "signature_menu": "추천메뉴",
                "menu_info": "",
                "price_range": "",
                "business_hours": "",
                "image_url": image_url,
                "url": url,
                "naver_map_link": f"https://map.naver.com/p/search/{quote(name)}",
                "data_source": "diningcode",
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": self.calculate_quality_score(rating, review_count, address),
                "first_review": first_review
            }
        except Exception as e:
            print(f"   상세 페이지 파싱 오류: {e}")
            return None

    async def extract_restaurant_info(self, item, location_name, page):
        """개별 맛집 정보를 추출합니다."""
        try:
            # 기본 정보 추출
            name = "이름 없음"
            restaurant_url = ""
            rating = 0.0
            review_count = 0
            category = "기타"
            address = ""
            
            # 이름 추출 - 여러 방법 시도
            name_selectors = ['a', 'h1', 'h2', 'h3', 'h4', '.name', '.title', '.restaurant-name']
            for selector in name_selectors:
                name_elem = await item.query_selector(selector)
                if name_elem:
                    name_text = await name_elem.inner_text()
                    if name_text and name_text.strip():
                        name = name_text.strip()
                        break
            
            # 링크 추출
            link_elem = await item.query_selector('a')
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href:
                    restaurant_url = urljoin(self.base_url, href)
            
            # 평점 추출
            rating_selectors = ['.rating', '.score', '.star', '[class*="rating"]', '[class*="score"]']
            for selector in rating_selectors:
                rating_elem = await item.query_selector(selector)
                if rating_elem:
                    rating_text = await rating_elem.inner_text()
                    if rating_text:
                        rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                        if rating_match:
                            rating = float(rating_match.group(1))
                            break
            
            # 리뷰 수 추출
            review_selectors = ['.review', '.review-count', '[class*="review"]']
            for selector in review_selectors:
                review_elem = await item.query_selector(selector)
                if review_elem:
                    review_text = await review_elem.inner_text()
                    if review_text:
                        review_match = re.search(r'(\d+)', review_text)
                        if review_match:
                            review_count = int(review_match.group(1))
                            break
            
            # 카테고리/장르 추출
            category_selectors = ['.category', '.genre', '.type', '[class*="category"]']
            for selector in category_selectors:
                category_elem = await item.query_selector(selector)
                if category_elem:
                    category_text = await category_elem.inner_text()
                    if category_text:
                        category = category_text.strip()
                        break
            
            # 주소 추출
            address_selectors = ['.address', '.location', '[class*="address"]']
            for selector in address_selectors:
                address_elem = await item.query_selector(selector)
                if address_elem:
                    address_text = await address_elem.inner_text()
                    if address_text:
                        address = address_text.strip()
                        break
            
            # 거리 정보 (그레이츠숙례 기준으로 추정)
            distance_from_office_m = self.calculate_distance_from_office(location_name)
            walking_time_min = max(1, distance_from_office_m // 80)  # 분당 80m로 계산
            
            # 거리 카테고리 분류
            if distance_from_office_m <= 200:
                distance_category = "매우 가까움"
            elif distance_from_office_m <= 500:
                distance_category = "가까움"
            elif distance_from_office_m <= 1000:
                distance_category = "보통"
            else:
                distance_category = "조금 멀음"
            
            # 음식 장르 분류
            food_genre = self.classify_food_genre(category)
            
            # 레스토랑 ID 생성
            restaurant_id = f"REST_{self.restaurant_id_counter:04d}_{name.replace(' ', '_')}"
            self.restaurant_id_counter += 1
            
            restaurant_data = {
                "restaurant_id": restaurant_id,
                "name": name,
                "address": address,
                "phone": "",
                "category": category,
                "food_genre": food_genre,
                "rating": rating,
                "review_count": review_count,
                "latitude": 0.0,
                "longitude": 0.0,
                "location_description": f"{location_name} 일대",
                "distance_from_office_m": distance_from_office_m,
                "walking_time_min": walking_time_min,
                "is_walkable": distance_from_office_m <= 1500,
                "distance_category": distance_category,
                "signature_menu": "추천메뉴",
                "menu_info": "",
                "price_range": "",
                "business_hours": "",
                "image_url": "",
                "url": restaurant_url,
                "naver_map_link": f"https://map.naver.com/p/search/{quote(name)}",
                "data_source": "diningcode",
                "last_updated": datetime.now().isoformat(),
                "data_quality_score": self.calculate_quality_score(rating, review_count, address)
            }
            
            return restaurant_data
            
        except Exception as e:
            print(f"   맛집 정보 추출 중 오류: {e}")
            return None

    def calculate_distance_from_office(self, location_name):
        """그레이츠숙례에서의 거리를 추정합니다."""
        if location_name == "남대문":
            return random.randint(100, 300)
        elif location_name == "서울역":
            return random.randint(400, 800)
        elif location_name == "회현역":
            return random.randint(200, 500)
        else:
            return random.randint(300, 1000)

    def classify_food_genre(self, category):
        """카테고리를 음식 장르로 분류합니다."""
        category_lower = category.lower()
        
        if any(keyword in category_lower for keyword in ['한식', '김치', '된장', '불고기', '비빔밥']):
            return "한식"
        elif any(keyword in category_lower for keyword in ['일식', '초밥', '라멘', '우동', '돈카츠']):
            return "일식"
        elif any(keyword in category_lower for keyword in ['중식', '짜장', '짬뽕', '탕수육', '마파두부']):
            return "중식"
        elif any(keyword in category_lower for keyword in ['양식', '파스타', '스테이크', '피자', '햄버거']):
            return "양식"
        elif any(keyword in category_lower for keyword in ['카페', '커피', '디저트', '케이크', '빵']):
            return "카페/디저트"
        elif any(keyword in category_lower for keyword in ['분식', '떡볶이', '순대', '튀김', '김밥']):
            return "분식/간식"
        else:
            return "기타"

    def calculate_quality_score(self, rating, review_count, address):
        """데이터 품질 점수를 계산합니다."""
        score = 0
        
        # 평점 점수 (0-40점)
        if rating > 0:
            score += min(40, rating * 8)
        
        # 리뷰 수 점수 (0-30점)
        if review_count > 0:
            score += min(30, review_count / 10)
        
        # 주소 정보 점수 (0-30점)
        if address and len(address) > 5:
            score += 30
        
        return min(100, score)

    def save_to_jsonl(self, filename="unified_restaurant_datamart.jsonl"):
        """수집된 데이터를 JSONL 형식으로 저장합니다."""
        print(f"\n[SAVE] 데이터 저장 중... ({len(self.restaurants)}개 맛집)")
        
        with open(filename, 'w', encoding='utf-8') as f:
            for restaurant in self.restaurants:
                f.write(json.dumps(restaurant, ensure_ascii=False) + '\n')
        
        print(f"[OK] {filename} 파일로 저장 완료!")

    def create_metadata(self, filename="datamart_metadata.json"):
        """메타데이터 파일을 생성합니다."""
        genre_count = {}
        distance_count = {}
        quality_distribution = {"excellent": 0, "good": 0, "fair": 0, "poor": 0}

        for restaurant in self.restaurants:
            # 장르별 분포
            genre = restaurant.get('food_genre', '기타')
            genre_count[genre] = genre_count.get(genre, 0) + 1

            # 거리별 분포
            distance = restaurant.get('distance_category', '정보없음')
            distance_count[distance] = distance_count.get(distance, 0) + 1

            # 품질 분포
            quality_score = restaurant.get('data_quality_score', 0)
            if quality_score >= 80:
                quality_distribution["excellent"] += 1
            elif quality_score >= 60:
                quality_distribution["good"] += 1
            elif quality_score >= 40:
                quality_distribution["fair"] += 1
            else:
                quality_distribution["poor"] += 1

        metadata = {
            "total_restaurants": len(self.restaurants),
            "data_quality_distribution": quality_distribution,
            "food_genre_distribution": genre_count,
            "distance_distribution": distance_count,
            "created_at": datetime.now().isoformat(),
            "source_files": ["diningcode_playwright_scraper.py"],
            "schema_version": "1.0"
        }

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        print(f"[OK] {filename} 메타데이터 파일 생성 완료!")

    async def run(self):
        """메인 실행 함수"""
        print("[START] Playwright를 사용한 다이닝코드 맛집 데이터 수집을 시작합니다...")
        print("=" * 50)
        
        async with async_playwright() as p:
            # 브라우저 실행
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            
            try:
                # 각 지역별로 데이터 수집
                for location_key, location_info in self.locations.items():
                    await self.get_restaurant_list(page, location_info['url'], location_info['name'])
                    await asyncio.sleep(2)  # 지역 간 요청 간격
                
            finally:
                await browser.close()
        
        print("\n" + "=" * 50)
        print(f"[DONE] 수집 완료: 총 {len(self.restaurants)}개 맛집")
        
        if self.restaurants:
            # 데이터 저장
            self.save_to_jsonl("unified_restaurant_datamart.jsonl")
            
            # 간단한 통계 출력
            print("\n[STATS] 수집 통계:")
            genre_count = {}
            for restaurant in self.restaurants:
                genre = restaurant.get('food_genre', '기타')
                genre_count[genre] = genre_count.get(genre, 0) + 1
            
            for genre, count in sorted(genre_count.items(), key=lambda x: x[1], reverse=True):
                print(f"   {genre}: {count}개")
        else:
            print("[ERROR] 수집된 데이터가 없습니다.")

    async def scrape_one(self, source_url: str = None):
        """하나의 식당만 수집하여 JSON을 출력합니다."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()

            # 기본 URL: 남대문
            target_url = source_url or self.locations['namdaemun']['url']
            # 지역명 추정
            location_name = '남대문'
            for loc in self.locations.values():
                if loc['url'] == target_url:
                    location_name = loc['name']
                    break

            await page.goto(target_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(2000)
            await self.load_all_items(page)

            # 첫 상세 링크 찾기
            try:
                await page.wait_for_selector('a[href*="/P/"]', timeout=8000)
            except Exception:
                pass
            first_link = await page.query_selector('a[href*="/P/"]')
            if not first_link:
                # 예비: JSON-LD에서 URL 추출
                items = await self.extract_list_from_jsonld(page)
                if items:
                    name = items[0].get('name') or ''
                    url = items[0].get('url') or ''
                    if url:
                        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                        data = await self.extract_from_detail_page(page, name, location_name, url)
                        await browser.close()
                        return data
                await browser.close()
                return None

            name_text = (await first_link.inner_text() or '').strip()
            href = await first_link.get_attribute('href')
            detail_url = urljoin(self.base_url, href) if href else ''
            await page.goto(detail_url, wait_until='domcontentloaded', timeout=60000)
            data = await self.extract_from_detail_page(page, name_text, location_name, detail_url)
            await browser.close()
            return data

    async def scrape_detail(self, detail_url: str, location_name: str = ""):
        """상세 페이지 URL 하나를 받아 JSON을 반환합니다."""
        if not detail_url:
            return None
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            await page.goto(detail_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(1200)
            name_guess = ""
            try:
                t = await page.title()
                if t:
                    name_guess = t.split('-')[0].strip()
            except Exception:
                pass
            data = await self.extract_from_detail_page(page, name_guess, location_name or "", detail_url)
            await browser.close()
            return data

    async def collect_all_links_only(self, location_url: str, location_name: str):
        """1단계: 모든 링크만 수집 (상세 페이지 방문 없음)"""
        print(f"[PHASE 1] {location_name} 지역 링크 수집 시작...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()

            try:
                detail_links = await self.collect_links_fast(page, location_url)
                print(f"[PHASE 1] OK {location_name} 링크 수집 완료: {len(detail_links)}개")
                return detail_links
            finally:
                await browser.close()

    async def collect_links_fast(self, page, start_url: str):
        """JSON-LD 스키마 기반 링크 수집 - FireCrawl 분석 결과 적용"""
        collected = []

        try:
            await page.goto(start_url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_timeout(3000)  # JSON-LD 로딩 대기

            print(f"   [INFO] JSON-LD 스키마에서 링크 추출 중...")

            # JSON-LD에서 데이터 추출
            json_data = await self.extract_list_from_jsonld(page)

            if json_data:
                for item in json_data:
                    name = item.get('name', '')
                    url = item.get('url', '')
                    if name and url:
                        collected.append((name, url))
                print(f"   [SUCCESS] JSON-LD에서 {len(collected)}개 링크 추출")
            else:
                # JSON-LD 실패 시 DOM 기반 수집
                print(f"   [FALLBACK] DOM 기반 링크 수집으로 전환")
                await self.collect_links_from_dom(page, collected)

            print(f"   [COMPLETE] 총 {len(collected)}개 링크 수집 완료")
            return collected

        except Exception as e:
            print(f"   [ERROR] 링크 수집 실패: {e}")
            return collected

    async def collect_links_from_dom(self, page, collected):
        """개선된 DOM 기반 링크 수집 - 더보기 버튼 클릭 방식"""
        print(f"   [DOM] 개선된 방식으로 모든 항목 수집 시작")

        try:
            # 개선된 로딩 로직 사용
            await self.load_all_items(page)

            # 로딩 완료 후 모든 링크 수집
            seen = set(url for _, url in collected)  # 기존 수집된 URL들
            initial_count = len(collected)

            # 우선순위 셀렉터로 링크 수집
            links_found = await self.extract_links_with_priority_selectors(page)

            for name, url in links_found:
                if url not in seen and name and len(name.strip()) >= 2:
                    collected.append((name.strip(), url))
                    seen.add(url)

            new_count = len(collected) - initial_count
            print(f"   [DOM] 개선된 방식으로 {new_count}개 링크 추가 수집 (총 {len(collected)}개)")

        except Exception as e:
            print(f"   [DOM ERROR] 개선된 수집 실패, 기본 수집으로 폴백: {e}")

            # 폴백: 기본적인 링크 수집
            try:
                seen = set(url for _, url in collected)
                selectors = ['a[href*="/P/"]', 'a[href*="profile"]']

                for selector in selectors:
                    anchors = await page.query_selector_all(selector)
                    for a in anchors:
                        try:
                            href = await a.get_attribute('href')
                            text = (await a.inner_text() or '').strip()
                            if href and text and len(text) >= 2:
                                full_url = urljoin(self.base_url, href)
                                if full_url not in seen:
                                    collected.append((text, full_url))
                                    seen.add(full_url)
                        except Exception:
                            continue

                print(f"   [DOM] 폴백 수집 완료: 총 {len(collected)}개 링크")
            except Exception as fallback_error:
                print(f"   [DOM ERROR] 폴백도 실패: {fallback_error}")

    async def parallel_detail_worker(self, worker_id: int, link_batch: list, location_name: str, results: list):
        """2단계: 병렬 워커 - 링크 배치를 받아서 상세 정보 수집"""
        print(f"[WORKER {worker_id}] 상세 수집 시작: {len(link_batch)}개 처리")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()

            try:
                # tqdm 프로그레스 바 추가
                for idx, (name, url) in enumerate(tqdm(link_batch,
                                                     desc=f"Worker {worker_id}",
                                                     position=worker_id-1,
                                                     leave=True)):
                    try:
                        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                        await page.wait_for_timeout(400)  # 더 짧은 대기시간
                        data = await self.extract_from_detail_page(page, name, location_name, url)
                        if data:
                            results.append(data)
                            # tqdm의 desc 업데이트로 현재 처리 중인 음식점 표시
                            tqdm.write(f"[WORKER {worker_id}] SUCCESS: {data['name']}")
                    except Exception as e:
                        tqdm.write(f"[WORKER {worker_id}] FAILED: {name} - {str(e)[:50]}")

                    await asyncio.sleep(random.uniform(0.2, 0.5))  # 더 짧은 대기

            finally:
                await browser.close()

        success_count = len([r for r in results if r])
        print(f"[WORKER {worker_id}] 완료: {success_count}/{len(link_batch)}개 수집 성공")

    async def scrape_with_parallel_workers(self, location_url: str, location_name: str, num_workers: int = 2):
        """개선된 2단계 병렬 수집 메인 메서드"""
        print("=" * 60)
        print(f"[START] {location_name} 지역 2단계 병렬 수집 시작")
        print(f"[CONFIG] 병렬 워커 수: {num_workers}개")
        print("=" * 60)

        # 1단계: 모든 링크 수집
        print("\n[PHASE 1] 링크 수집 단계")
        all_links = await self.collect_all_links_only(location_url, location_name)
        if not all_links:
            print(f"[ERROR] {location_name} 링크 수집 실패")
            return []

        total_links = len(all_links)
        print(f"[SUCCESS] 링크 수집 완료: {total_links}개")
        print(f"\n[PHASE 2] 상세 수집 준비 - {total_links}개를 {num_workers}개 워커로 분할")

        # 2단계: 링크를 워커 수만큼 분할
        batch_size = total_links // num_workers
        link_batches = []

        for i in range(num_workers):
            start_idx = i * batch_size
            end_idx = start_idx + batch_size if i < num_workers - 1 else total_links
            batch = all_links[start_idx:end_idx]
            link_batches.append(batch)
            print(f"[BATCH] Worker {i+1}: {len(batch)}개 링크 할당")

        print(f"\n[PHASE 3] 병렬 상세 수집 시작")
        print("-" * 40)

        # 3단계: 병렬 워커 실행
        results = []
        tasks = []

        for worker_id, batch in enumerate(link_batches):
            if batch:  # 빈 배치가 아닌 경우만
                task = self.parallel_detail_worker(worker_id + 1, batch, location_name, results)
                tasks.append(task)

        await asyncio.gather(*tasks)

        success_count = len(results)
        success_rate = (success_count / total_links) * 100 if total_links > 0 else 0

        print("\n" + "=" * 60)
        print(f"[COMPLETE] {location_name} 병렬 수집 완료!")
        print(f"[RESULT] 수집 결과: {success_count}/{total_links}개 ({success_rate:.1f}%)")
        print("=" * 60)

        return results

    async def collect_all_links_from_regions(self, output_file="phase1_links.jsonl"):
        """1단계: 3개 지역에서 링크 정보만 수집하여 JSONL 저장"""
        print("=" * 60)
        print("[PHASE 1] 3개 지역 링크 수집 시작")
        print("=" * 60)

        all_links = []

        for location_key, location_info in self.locations.items():
            location_name = location_info['name']
            location_url = location_info['url']

            print(f"\n[REGION] {location_name} 링크 수집 중...")

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                page = await context.new_page()

                try:
                    links = await self.collect_links_fast(page, location_url)
                    print(f"[SUCCESS] {location_name}: {len(links)}개 링크 수집")

                    # 링크를 JSONL 형태로 변환
                    for idx, (name, url) in enumerate(links):
                        link_data = {
                            "link_id": f"{location_key}_{idx+1:04d}",
                            "region": location_name,
                            "region_key": location_key,
                            "name": name,
                            "url": url,
                            "collected_at": datetime.now().isoformat()
                        }
                        all_links.append(link_data)

                except Exception as e:
                    print(f"[ERROR] {location_name} 수집 실패: {e}")
                finally:
                    await browser.close()

        # 1차 JSONL 파일 저장
        print(f"\n[SAVE] 1차 링크 데이터 저장 중... ({len(all_links)}개)")
        with open(output_file, 'w', encoding='utf-8') as f:
            for link in all_links:
                f.write(json.dumps(link, ensure_ascii=False) + '\n')

        print("=" * 60)
        print(f"[PHASE 1 COMPLETE] 총 {len(all_links)}개 링크 수집 완료")
        print(f"[OUTPUT] {output_file}")
        print("=" * 60)

        return all_links

    async def process_links_to_details(self, links_file="phase1_links.jsonl", output_file="phase2_details.jsonl", num_workers=2):
        """2단계: 1차 JSONL에서 링크를 읽어 병렬로 상세 정보 수집"""
        print("=" * 60)
        print("[PHASE 2] 상세 정보 수집 시작")
        print(f"[CONFIG] 병렬 워커 수: {num_workers}개")
        print("=" * 60)

        # 1차 JSONL 파일 읽기
        links_data = []
        try:
            with open(links_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        links_data.append(json.loads(line))
            print(f"[LOAD] {links_file}에서 {len(links_data)}개 링크 로드")
        except Exception as e:
            print(f"[ERROR] 링크 파일 읽기 실패: {e}")
            return []

        if not links_data:
            print("[ERROR] 처리할 링크가 없습니다.")
            return []

        # 링크를 워커 수만큼 분할
        batch_size = len(links_data) // num_workers
        link_batches = []

        for i in range(num_workers):
            start_idx = i * batch_size
            end_idx = start_idx + batch_size if i < num_workers - 1 else len(links_data)
            batch = links_data[start_idx:end_idx]
            link_batches.append(batch)
            print(f"[BATCH] Worker {i+1}: {len(batch)}개 링크 할당")

        print(f"\n[PHASE 2] 병렬 상세 수집 시작")
        print("-" * 40)

        # 병렬 워커 실행
        results = []
        tasks = []

        for worker_id, batch in enumerate(link_batches):
            if batch:
                task = self.detail_worker_from_links(worker_id + 1, batch, results)
                tasks.append(task)

        await asyncio.gather(*tasks)

        # 2차 JSONL 파일 저장
        print(f"\n[SAVE] 상세 데이터 저장 중... ({len(results)}개)")
        with open(output_file, 'w', encoding='utf-8') as f:
            for restaurant in results:
                f.write(json.dumps(restaurant, ensure_ascii=False) + '\n')

        success_count = len(results)
        success_rate = (success_count / len(links_data)) * 100 if links_data else 0

        print("\n" + "=" * 60)
        print(f"[PHASE 2 COMPLETE] 상세 정보 수집 완료!")
        print(f"[RESULT] 수집 결과: {success_count}/{len(links_data)}개 ({success_rate:.1f}%)")
        print(f"[OUTPUT] {output_file}")
        print("=" * 60)

        return results

    async def detail_worker_from_links(self, worker_id: int, link_batch: list, results: list):
        """링크 데이터를 받아서 상세 정보 수집하는 워커"""
        print(f"[WORKER {worker_id}] 상세 수집 시작: {len(link_batch)}개 처리")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()

            try:
                for idx, link_data in enumerate(tqdm(link_batch,
                                                   desc=f"Worker {worker_id}",
                                                   position=worker_id-1,
                                                   leave=True)):
                    try:
                        name = link_data.get('name', 'Unknown')
                        url = link_data.get('url', '')
                        region = link_data.get('region', '')

                        if not url:
                            continue

                        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                        await page.wait_for_timeout(400)

                        data = await self.extract_from_detail_page(page, name, region, url)
                        if data:
                            # 링크 데이터의 정보도 추가
                            data['link_id'] = link_data.get('link_id', '')
                            data['region_key'] = link_data.get('region_key', '')
                            results.append(data)
                            tqdm.write(f"[WORKER {worker_id}] SUCCESS: {data['name']}")
                    except Exception as e:
                        name = link_data.get('name', 'Unknown')
                        tqdm.write(f"[WORKER {worker_id}] FAILED: {name} - {str(e)[:50]}")

                    await asyncio.sleep(random.uniform(0.2, 0.5))

            finally:
                await browser.close()

        success_count = len([r for r in results if r])
        print(f"[WORKER {worker_id}] 완료: {success_count}/{len(link_batch)}개 수집 성공")

    async def run_two_phase_collection(self):
        """전체 2단계 수집 프로세스 실행"""
        print("[START] 2단계 수집 프로세스 시작")
        print("[INFO] Phase 1: 링크 수집 → Phase 2: 상세 수집")
        print("=" * 80)

        # 1단계: 링크 수집
        links = await self.collect_all_links_from_regions("phase1_links.jsonl")

        if not links:
            print("[ERROR] 1단계 실패: 링크 수집 없음")
            return

        # 2단계: 상세 수집
        results = await self.process_links_to_details("phase1_links.jsonl", "phase2_details.jsonl", 2)

        # 임시 파일들 정리
        import os
        try:
            if os.path.exists("phase1_links.jsonl"):
                os.remove("phase1_links.jsonl")
            if os.path.exists("phase2_details.jsonl"):
                os.remove("phase2_details.jsonl")
        except:
            pass

        if results:
            # 최종 JSONL 파일만 생성
            self.restaurants = results
            self.save_to_jsonl("unified_restaurant_datamart.jsonl")

            print(f"\n[COMPLETE] 전체 수집 완료!")
            print(f"[RESULT] 수집 성공: {len(results)}개 맛집")
            print(f"[OUTPUT] 최종 파일: unified_restaurant_datamart.jsonl")
        else:
            print("[ERROR] 2단계 실패: 상세 정보 수집 없음")

    async def report_counts(self):
        """각 URL의 총 맛집 개수(페이지 상단 '맛집 (N곳)')를 확인하여 출력합니다."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()

            for key, loc in self.locations.items():
                name = loc['name']
                url = loc['url']
                try:
                    await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    await page.wait_for_timeout(1500)
                    # 우선 본문 텍스트에서 정규식 검색
                    body_text = await page.evaluate('() => document.body && document.body.innerText')
                    count = None
                    if body_text:
                        m = re.search(r"맛집\s*\((\d+)곳\)", body_text)
                        if m:
                            count = int(m.group(1))
                    # 대체: 타이틀 근처 요소 탐색
                    if count is None:
                        try:
                            texts = await page.eval_on_selector_all('h1, h2, .title, .tit, .result', 'els => els.map(e => e.innerText)')
                            for t in texts or []:
                                m2 = re.search(r"맛집\s*\((\d+)곳\)", t or '')
                                if m2:
                                    count = int(m2.group(1))
                                    break
                        except Exception:
                            pass
                    print(f"- {name}: {count if count is not None else '미확인'}")
                except Exception as e:
                    print(f"- {name}: 확인 실패 ({e})")
            await browser.close()

async def main():
    parser = argparse.ArgumentParser(
        description='다이닝코드 맛집 데이터 수집 스크래퍼',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
실행 예제:
  # 남대문 지역 전체 수집 (병렬 방식, 권장)
  python diningcode_playwright_scraper.py --parallel --workers 2

  # 테스트용 100개만 수집
  python diningcode_playwright_scraper.py --sample 100 --url "https://www.diningcode.com/list.dc?query=남대문"

  # 각 지역별 총 음식점 수 확인
  python diningcode_playwright_scraper.py --counts

  # 전체 지역 수집 (기존 방식)
  python diningcode_playwright_scraper.py
        """)
    parser.add_argument('--counts', action='store_true', help='각 URL의 총 맛집 수만 확인')
    parser.add_argument('--one', action='store_true', help='한 개의 식당만 수집하여 JSON 출력')
    parser.add_argument('--url', type=str, help='리스트 페이지 URL (옵션)')
    parser.add_argument('--detail', type=str, help='상세 페이지 URL 한 개 수집')
    parser.add_argument('--sample', type=int, help='주어진 리스트 URL에서 상위 N개만 수집 후 저장')
    parser.add_argument('--parallel', action='store_true', help='병렬 수집 방식 (빠름, 권장)')
    parser.add_argument('--workers', type=int, default=2, help='병렬 워커 수 (기본값: 2)')
    parser.add_argument('--phase1-only', action='store_true', help='1단계만 실행: 링크 수집')
    parser.add_argument('--phase2-only', type=str, help='2단계만 실행: 링크 파일에서 상세 수집 (파일명 지정)')
    parser.add_argument('--out', type=str, default='unified_restaurant_datamart.jsonl', help='저장할 JSONL 파일명')
    args = parser.parse_args()

    scraper = DiningCodePlaywrightScraper()
    if args.counts:
        await scraper.report_counts()
    elif args.one:
        data = await scraper.scrape_one(args.url)
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print('{}')
    elif args.detail:
        data = await scraper.scrape_detail(args.detail)
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print('{}')
    elif args.sample and args.url:
        await scraper.scrape_n_from_list(args.url, args.sample, args.out)
    elif args.phase1_only:
        # 1단계만 실행: 링크 수집
        links = await scraper.collect_all_links_from_regions("phase1_links.jsonl")
        print(f"[PHASE1 COMPLETE] {len(links)}개 링크 수집 완료")
    elif args.phase2_only:
        # 2단계만 실행: 상세 수집
        results = await scraper.process_links_to_details(args.phase2_only, args.out, args.workers)
        if results:
            scraper.restaurants = results
            print(f"[PHASE2 COMPLETE] {len(results)}개 상세 정보 수집 완료")
    elif args.parallel:
        # 기존 병렬 수집 방식
        url = args.url or scraper.locations['namdaemun']['url']
        location_name = '남대문'
        for loc in scraper.locations.values():
            if loc['url'] == url:
                location_name = loc['name']
                break

        results = await scraper.scrape_with_parallel_workers(url, location_name, args.workers)
        scraper.restaurants = results

        if results:
            scraper.save_to_jsonl(args.out)
            print(f"\n[SUCCESS] 병렬 수집 완료: {len(results)}개 저장됨 → {args.out}")
        else:
            print("[ERROR] 수집된 데이터가 없습니다.")
    else:
        # 기본 동작: 전체 수집 (2단계 방식)
        await scraper.run_two_phase_collection()

if __name__ == "__main__":
    asyncio.run(main())
