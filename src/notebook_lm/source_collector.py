"""
ソース収集モジュール
NotebookLMを使用したソース記事の自動収集
"""
import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

# 基本的なロガー設定（loguruの代替）
from core.utils.logger import logger

from config.settings import settings

@dataclass
class SourceInfo:
    """ソース情報"""
    url: str
    title: str
    content_preview: str
    relevance_score: float
    reliability_score: float
    source_type: str  # "news", "article", "academic", "blog"

class SourceCollector:
    """ソース収集クラス"""
    
    def __init__(self):
        self.max_sources = settings.NOTEBOOK_LM_SETTINGS["max_sources"]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    async def collect_sources(
        self, 
        topic: str, 
        urls: Optional[List[str]] = None
    ) -> List[SourceInfo]:
        """
        ソースを収集する
        
        Args:
            topic: 調査トピック
            urls: 指定されたURL一覧
            
        Returns:
            List[SourceInfo]: 収集されたソース一覧
        """
        logger.info(f"ソース収集開始: {topic}")
        
        sources = []
        
        # 指定されたURLがある場合は優先的に処理
        if urls:
            logger.info(f"指定URL処理: {len(urls)}件")
            for url in urls:
                source = await self._process_url(url, topic)
                if source:
                    sources.append(source)
        
        # 不足分を自動検索で補完
        remaining_count = self.max_sources - len(sources)
        if remaining_count > 0:
            logger.info(f"自動検索実行: {remaining_count}件")
            auto_sources = await self._search_sources(topic, remaining_count)
            sources.extend(auto_sources)
        
        # 品質でソート
        sources.sort(key=lambda x: (x.reliability_score + x.relevance_score) / 2, reverse=True)
        
        logger.info(f"ソース収集完了: {len(sources)}件")
        return sources[:self.max_sources]
    
    async def _process_url(self, url: str, topic: str) -> Optional[SourceInfo]:
        """
        指定されたURLを処理してソース情報を生成
        
        Args:
            url: 処理するURL
            topic: 関連トピック
            
        Returns:
            Optional[SourceInfo]: ソース情報（取得失敗時はNone）
        """
        try:
            logger.debug(f"URL処理開始: {url}")
            
            # コンテンツ取得
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # HTMLパース
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトル抽出
            title = self._extract_title(soup)
            
            # コンテンツプレビュー抽出
            content_preview = self._extract_content_preview(soup)
            
            # 関連性スコア計算
            relevance_score = self._calculate_relevance(title, content_preview, topic)
            
            # 信頼性スコア計算
            reliability_score = self._calculate_reliability(url, soup)
            
            # ソースタイプ判定
            source_type = self._determine_source_type(url, soup)
            
            return SourceInfo(
                url=url,
                title=title,
                content_preview=content_preview,
                relevance_score=relevance_score,
                reliability_score=reliability_score,
                source_type=source_type
            )
            
        except Exception as e:
            logger.warning(f"URL処理失敗: {url} - {str(e)}")
            return None
    
    async def _search_sources(self, topic: str, count: int) -> List[SourceInfo]:
        """
        トピックに基づいてソースを自動検索
        
        Args:
            topic: 検索トピック
            count: 取得する件数
            
        Returns:
            List[SourceInfo]: 検索されたソース一覧
        """
        # 実際の実装では、NotebookLMのAPIまたはWeb検索APIを使用
        # ここではプレースホルダー実装
        logger.info(f"自動検索: {topic} ({count}件)")
        
        # TODO: 実際の検索API実装
        # - Google Search API
        # - Bing Search API
        # - ニュースAPI等を使用
        
        return []
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """HTMLからタイトルを抽出"""
        # title タグ
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # h1 タグ
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        
        # og:title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            return og_title.get('content', '').strip()
        
        return "タイトル不明"
    
    def _extract_content_preview(self, soup: BeautifulSoup) -> str:
        """HTMLからコンテンツプレビューを抽出"""
        # meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
        
        # og:description
        og_desc = soup.find('meta', property='og:description')
        if og_desc:
            return og_desc.get('content', '').strip()
        
        # 本文の最初の部分を抽出
        content_tags = soup.find_all(['p', 'div'], class_=lambda x: x and any(
            keyword in x.lower() for keyword in ['content', 'article', 'text', 'body']
        ))
        
        if content_tags:
            text = ' '.join([tag.get_text().strip() for tag in content_tags[:3]])
            return text[:500] + "..." if len(text) > 500 else text
        
        return "プレビュー不明"
    
    def _calculate_relevance(self, title: str, content: str, topic: str) -> float:
        """関連性スコアを計算"""
        # 簡単なキーワードマッチング実装
        # 実際の実装では、より高度なNLP手法を使用
        
        text = (title + " " + content).lower()
        topic_words = topic.lower().split()
        
        matches = sum(1 for word in topic_words if word in text)
        return min(matches / len(topic_words), 1.0)
    
    def _calculate_reliability(self, url: str, soup: BeautifulSoup) -> float:
        """信頼性スコアを計算"""
        score = 0.5  # ベーススコア
        
        # ドメインベースの信頼性
        domain = url.split('/')[2].lower()
        
        # 信頼できるニュースサイト
        trusted_domains = [
            'nikkei.com', 'asahi.com', 'mainichi.jp', 'yomiuri.co.jp',
            'nhk.or.jp', 'reuters.com', 'bbc.com', 'cnn.com'
        ]
        
        if any(trusted in domain for trusted in trusted_domains):
            score += 0.3
        
        # HTTPS使用
        if url.startswith('https'):
            score += 0.1
        
        # 記事の構造
        if soup.find('article') or soup.find('time') or soup.find('author'):
            score += 0.1
        
        return min(score, 1.0)
    
    def _determine_source_type(self, url: str, soup: BeautifulSoup) -> str:
        """ソースタイプを判定"""
        domain = url.split('/')[2].lower()
        
        # ニュースサイト
        news_indicators = ['news', 'nikkei', 'asahi', 'mainichi', 'yomiuri', 'nhk']
        if any(indicator in domain for indicator in news_indicators):
            return "news"
        
        # 学術サイト
        academic_indicators = ['edu', 'ac.jp', 'scholar', 'researchgate']
        if any(indicator in domain for indicator in academic_indicators):
            return "academic"
        
        # ブログ
        blog_indicators = ['blog', 'wordpress', 'medium', 'note']
        if any(indicator in domain for indicator in blog_indicators):
            return "blog"
        
        return "article"
    
    def save_sources_info(self, sources: List[SourceInfo], output_path: Path):
        """ソース情報をファイルに保存"""
        import json
        
        sources_data = [
            {
                "url": source.url,
                "title": source.title,
                "content_preview": source.content_preview,
                "relevance_score": source.relevance_score,
                "reliability_score": source.reliability_score,
                "source_type": source.source_type
            }
            for source in sources
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sources_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"ソース情報保存完了: {output_path}")
