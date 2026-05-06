def map_intent(intent: str):
    parts = intent.split("_")

    if len(parts) == 2:
        return {
            "action": parts[0],
            "direction": parts[1]
        }

    return {
        "action": intent,
        "direction": None
    }