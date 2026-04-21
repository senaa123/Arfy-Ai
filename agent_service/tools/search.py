from ddgs import DDGS


def web_search(query: str) -> dict:
    """
    Search the web using DDGS.

    Returns top 3 results in a simple message + raw results.
    """
    clean_query = query.strip()
    if not clean_query:
        return {
            "success": False,
            "message": "Search query was empty.",
        }

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(clean_query, max_results=3))

        if not results:
            return {
                "success": False,
                "message": "No search results found.",
            }

        summary_lines = []
        for item in results:
            title = item.get("title", "No title")
            body = item.get("body", "")
            href = item.get("href", "")
            summary_lines.append(f"- {title}: {body} ({href})")

        return {
            "success": True,
            "results": results,
            "message": "Top search results:\n" + "\n".join(summary_lines),
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Search failed: {e}",
        }
