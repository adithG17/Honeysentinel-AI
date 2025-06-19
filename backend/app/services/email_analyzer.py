def analyze_email(content: str) -> float:
    # Dummy logic for email analysis
    if "click here" in content.lower() or "urgent" in content.lower():
        return 0.85  # High risk
    return 0.2  # Low risk
