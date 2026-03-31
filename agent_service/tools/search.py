from duckduckgo_search import DDGS

def web_search(query: str) -> dict:
    """
    Search the web using DuckDuckGo.

    Returns top 3 results in a simple message + raw results.
    """

    try: 
        #  Create DDGS client and search
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        
        #nothing found
        if not results:
            return {
                "success": False,
                "message": "No search results found."
            }
        
        #Build a readble message
        lines =  []
        for item in results:
            title = item.get("title", "No title")
            body = item.get("body", "")
            href = item.get("href", "")
            lines.append(f"- {title}: {body} ({href})")

        return {
            "success": True,
            "results": results,
            "message": "Top search results:\n" + "\n".join(lines)
        }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"Search failed: {e}"
        }