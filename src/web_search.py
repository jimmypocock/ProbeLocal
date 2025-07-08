"""Web search functionality for Greg AI Playground"""
import logging
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, quote_plus
import hashlib
import json


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Represents a single search result"""
    title: str
    url: str
    snippet: str
    content: Optional[str] = None
    timestamp: datetime = None
    source: str = "web"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class WebSearcher:
    """Handles web search and content extraction"""
    
    def __init__(self, cache_ttl_minutes: int = 15):
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self.cache = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
    def search(self, query: str, num_results: int = 5) -> List[SearchResult]:
        """Search the web using DuckDuckGo HTML interface"""
        # Check cache first
        cache_key = self._get_cache_key(query, num_results)
        cached = self._get_from_cache(cache_key)
        if cached:
            logger.info(f"Returning cached results for: {query}")
            return cached
            
        try:
            # Use DuckDuckGo HTML search
            results = self._search_duckduckgo_html(query, num_results)
            
            # Cache results
            self._add_to_cache(cache_key, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {str(e)}")
            return []
            
    def _search_duckduckgo_html(self, query: str, num_results: int) -> List[SearchResult]:
        """Search using DuckDuckGo HTML interface"""
        encoded_query = quote_plus(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            # Find search results
            for i, result in enumerate(soup.find_all('div', class_='result__body')):
                if i >= num_results:
                    break
                    
                # Extract title
                title_elem = result.find('a', class_='result__a')
                if not title_elem:
                    continue
                    
                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')
                
                # Fix protocol-relative URLs from DuckDuckGo
                if url.startswith("//"):
                    url = "https:" + url
                
                # Extract snippet
                snippet_elem = result.find('a', class_='result__snippet')
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                
                if title and url:
                    results.append(SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet
                    ))
                    
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {str(e)}")
            return []
            
    def extract_content(self, url: str, max_length: int = 5000) -> Optional[str]:
        """Extract text content from a URL"""
        try:
            # Fix URLs that start with // (protocol-relative URLs)
            if url.startswith("//"):
                url = "https:" + url
            elif not url.startswith(("http://", "https://")):
                # Handle relative URLs or missing scheme
                logger.warning(f"Invalid URL format: {url}")
                return None
                
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Get text
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit length
            if len(text) > max_length:
                text = text[:max_length] + "..."
                
            return text
            
        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {str(e)}")
            return None
            
    def search_and_extract(self, query: str, num_results: int = 3) -> List[SearchResult]:
        """Search and extract content from top results"""
        results = self.search(query, num_results * 2)  # Get extra in case some fail
        
        extracted_count = 0
        for result in results:
            if extracted_count >= num_results:
                break
                
            content = self.extract_content(result.url)
            if content:
                result.content = content
                extracted_count += 1
                
        return results[:num_results]
        
    def _get_cache_key(self, query: str, num_results: int) -> str:
        """Generate cache key for a search query"""
        key_string = f"{query}:{num_results}"
        return hashlib.md5(key_string.encode()).hexdigest()
        
    def _get_from_cache(self, key: str) -> Optional[List[SearchResult]]:
        """Get results from cache if not expired"""
        if key in self.cache:
            cached_data = self.cache[key]
            if datetime.now() - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['results']
            else:
                del self.cache[key]
        return None
        
    def _add_to_cache(self, key: str, results: List[SearchResult]) -> None:
        """Add results to cache"""
        self.cache[key] = {
            'results': results,
            'timestamp': datetime.now()
        }
        
    def clear_cache(self) -> None:
        """Clear the cache"""
        self.cache.clear()
        
    def sanitize_content(self, content: str) -> str:
        """Sanitize web content for safety"""
        if not content:
            return ""
            
        # Remove potential script injections
        sanitized = content.replace('<script', '&lt;script')
        sanitized = sanitized.replace('</script>', '&lt;/script&gt;')
        
        # Remove other potentially harmful tags
        dangerous_tags = ['iframe', 'object', 'embed', 'form']
        for tag in dangerous_tags:
            sanitized = sanitized.replace(f'<{tag}', f'&lt;{tag}')
            
        return sanitized