from datetime import datetime

def create_analytics_document(
    category: str,
    state: str,
    income: str,
    ration: str
):
    return {
        "category": category,
        "state": state,
        "income": income,
        "ration": ration,
        "timestamp": datetime.utcnow()
    }