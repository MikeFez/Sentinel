import feedparser
from typing import List, Dict, Any
from datetime import datetime
import logging
import urllib.parse

logger = logging.getLogger(__name__)


class NewsService:
    """Service for fetching news articles using Google News RSS"""

    @staticmethod
    def get_news(query: str, max_articles: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch news articles from Google News RSS for a given query.

        Args:
            query: Search query (company name, ticker, etc.)
            max_articles: Maximum number of articles to return

        Returns:
            List of news articles with title, url, date, and source
        """
        try:
            # Construct Google News RSS URL
            encoded_query = urllib.parse.quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            # Parse the RSS feed
            feed = feedparser.parse(rss_url)

            articles = []
            for entry in feed.entries[:max_articles]:
                # Extract source from title (Google News format: "Title - Source")
                title = entry.get("title", "")
                source = None
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    source = parts[1]

                # Parse publication date
                published = entry.get("published")
                date_str = None
                if published:
                    try:
                        parsed_date = datetime.strptime(
                            published, "%a, %d %b %Y %H:%M:%S %Z"
                        )
                        date_str = parsed_date.isoformat()
                    except:
                        date_str = published

                articles.append(
                    {
                        "title": title,
                        "url": entry.get("link", ""),
                        "date": date_str,
                        "source": source,
                    }
                )

            logger.info(f"Fetched {len(articles)} articles for query: {query}")
            return articles

        except Exception as e:
            logger.error(f"Error fetching news for query '{query}': {str(e)}")
            return []
