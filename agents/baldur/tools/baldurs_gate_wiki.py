import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BaldursGateWikiManager:
    def __init__(self):
        self.base_url = "https://bg3.wiki"
        self.search_url = "https://bg3.wiki/w/index.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    async def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        try:
            if not query:
                return {"success": False, "error": "Query parameter is required"}
            
            search_params = {'search': query, 'title': 'Special:Search', 'go': 'Go'}
            response = self.session.get(self.search_url, params=search_params)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            search_results = []
            result_links = soup.find_all('a', href=True)
            
            for link in result_links:
                href = link.get('href')
                if href and '/wiki/' in href and not href.startswith('http'):
                    title = link.get_text(strip=True)
                    if title and len(title) > 2:
                        full_url = urljoin(self.base_url, href)
                        search_results.append({'title': title, 'url': full_url})
                        if len(search_results) >= limit:
                            break
            
            if search_results:
                detailed_results = []
                for result in search_results[:limit]:
                    try:
                        page_response = self.session.get(result['url'])
                        page_response.raise_for_status()
                        page_soup = BeautifulSoup(page_response.content, 'html.parser')
                        
                        content_div = page_soup.find('div', {'id': 'mw-content-text'})
                        if content_div:
                            first_p = content_div.find('p')
                            summary = first_p.get_text(strip=True) if first_p else "No summary available"
                            summary = summary[:500] + "..." if len(summary) > 500 else summary
                            
                            categories = []
                            category_links = page_soup.find_all('a', href=lambda x: x and 'Category:' in x)
                            for cat_link in category_links[:5]:
                                cat_name = cat_link.get_text(strip=True)
                                if cat_name:
                                    categories.append(cat_name)
                            
                            detailed_results.append({
                                "title": result['title'],
                                "url": result['url'],
                                "summary": summary,
                                "categories": categories,
                                "content_length": len(content_div.get_text()) if content_div else 0
                            })
                        else:
                            detailed_results.append({
                                "title": result['title'],
                                "url": result['url'],
                                "summary": "Content could not be retrieved",
                                "categories": [],
                                "content_length": 0
                            })
                    except Exception as e:
                        logger.warning(f"Could not get details for {result['title']}: {e}")
                        detailed_results.append({
                            "title": result['title'],
                            "url": result['url'],
                            "summary": "Details could not be retrieved",
                            "categories": [],
                            "content_length": 0
                        })
                
                return {
                    "success": True,
                    "results": detailed_results,
                    "query": query,
                    "total_found": len(search_results),
                    "results_returned": len(detailed_results)
                }
            else:
                return {"success": False, "message": "No results found", "query": query}
        except Exception as e:
            logger.error(f"Error searching Baldur's Gate Wiki: {e}")
            return {"success": False, "error": str(e), "query": query}

_manager = BaldursGateWikiManager()

async def baldurs_gate_wiki(**kwargs) -> Dict[str, Any]:
    """Search the Baldur's Gate 3 Wiki for information."""
    query: str = kwargs.get("query", "")
    limit: int = kwargs.get("limit", 5)
    return await _manager.search(query, limit)
