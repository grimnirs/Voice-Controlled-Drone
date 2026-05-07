def map_intent(intent: str):
    parts = intent.split("_")

    if len(parts) == 2:
        action = parts[0]
        direction = parts[1]
        return action, direction
        # return {
        #     "action": parts[0],
        #     "direction": parts[1]
        # }

    action = parts[0]
    direction = None
    return action, direction
    # return {
    #     "action": intent,
    #     "direction": None
    # }