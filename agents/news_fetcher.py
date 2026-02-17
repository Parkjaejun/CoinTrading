# agents/news_fetcher.py
"""
암호화폐 뉴스 수집기

CryptoPanic API (무료)와 RSS 피드에서 최신 뉴스를 수집한다.
수집된 헤드라인은 LLM 감성 분석에 활용된다.
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from utils.logger import log_system, log_error

# RSS 파서 가용 여부
try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# RSS 피드 소스
RSS_FEEDS = [
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "category": "general",
    },
    {
        "name": "CoinTelegraph",
        "url": "https://cointelegraph.com/rss",
        "category": "general",
    },
]

# CryptoPanic API (무료 — auth_token 없이 사용 가능)
CRYPTOPANIC_API = "https://cryptopanic.com/api/free/v1/posts/"


class NewsFetcher:
    """암호화폐 뉴스 수집"""

    def __init__(self, cryptopanic_token: Optional[str] = None):
        """
        Args:
            cryptopanic_token: CryptoPanic API 토큰 (없으면 RSS만 사용)
        """
        self._cryptopanic_token = cryptopanic_token
        self._cache: List[Dict] = []
        self._last_fetch: Optional[datetime] = None
        self._cache_ttl = 300  # 5분 캐시

    def fetch_latest(self, limit: int = 10) -> List[Dict]:
        """
        최신 뉴스 수집

        Args:
            limit: 최대 뉴스 개수

        Returns:
            뉴스 딕셔너리 리스트
            [{"title": str, "source": str, "published": str, "url": str}, ...]
        """
        # 캐시 확인
        if self._last_fetch and self._cache:
            elapsed = (datetime.now() - self._last_fetch).total_seconds()
            if elapsed < self._cache_ttl:
                return self._cache[:limit]

        news = []

        # CryptoPanic API
        cryptopanic_news = self._fetch_cryptopanic()
        news.extend(cryptopanic_news)

        # RSS 피드
        rss_news = self._fetch_rss()
        news.extend(rss_news)

        # 시간순 정렬 (최신순)
        news.sort(key=lambda x: x.get("published", ""), reverse=True)

        # 캐시 갱신
        self._cache = news
        self._last_fetch = datetime.now()

        return news[:limit]

    def _fetch_cryptopanic(self) -> List[Dict]:
        """CryptoPanic API에서 뉴스 수집"""
        if not HAS_REQUESTS:
            return []

        try:
            params = {
                "currencies": "BTC",
                "kind": "news",
            }
            if self._cryptopanic_token:
                params["auth_token"] = self._cryptopanic_token

            response = requests.get(
                CRYPTOPANIC_API,
                params=params,
                timeout=10,
            )
            if response.status_code != 200:
                return []

            data = response.json()
            results = []
            for item in data.get("results", [])[:10]:
                results.append({
                    "title": item.get("title", ""),
                    "source": item.get("source", {}).get("title", "CryptoPanic"),
                    "published": item.get("published_at", ""),
                    "url": item.get("url", ""),
                })
            return results

        except Exception as e:
            log_error(f"[NewsFetcher] CryptoPanic 수집 실패: {e}")
            return []

    def _fetch_rss(self) -> List[Dict]:
        """RSS 피드에서 뉴스 수집"""
        if not HAS_FEEDPARSER:
            return []

        results = []
        for feed_info in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_info["url"])
                for entry in feed.entries[:5]:
                    results.append({
                        "title": entry.get("title", ""),
                        "source": feed_info["name"],
                        "published": entry.get("published", ""),
                        "url": entry.get("link", ""),
                    })
            except Exception as e:
                log_error(f"[NewsFetcher] RSS 수집 실패 ({feed_info['name']}): {e}")

        return results

    def get_sentiment_summary(self) -> str:
        """
        최근 뉴스 헤드라인 텍스트 반환 (LLM 분석용)

        Returns:
            뉴스 헤드라인 요약 문자열
        """
        news = self.fetch_latest(limit=10)
        if not news:
            return "최근 뉴스 없음"

        lines = []
        for i, item in enumerate(news, 1):
            source = item.get("source", "Unknown")
            title = item.get("title", "")
            lines.append(f"{i}. [{source}] {title}")

        return "\n".join(lines)
