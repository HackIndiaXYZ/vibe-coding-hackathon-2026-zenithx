def create_scheme_document(
    name: str,
    category: str,
    state: str,
    description: str,
    eligibility: str
):
    return {
        "name": name,
        "category": category,
        "state": state,
        "description": description,
        "eligibility": eligibility
    }