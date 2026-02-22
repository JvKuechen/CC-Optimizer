# Delta Polling

**Source:** Discovered across multiple workspace audits

## When

Any system that periodically checks for new data -- email watchers, API pollers, file monitors, queue consumers.

## How

Track a high-water mark (timestamp, ID, or hash) and only process items newer than the mark.

```python
STATE_FILE = "last_check.json"

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {"last_id": None, "last_timestamp": None}

def save_state(state):
    json.dump(state, open(STATE_FILE, "w"))

def poll():
    state = load_state()
    new_items = fetch_since(state["last_timestamp"])
    for item in new_items:
        process(item)
    if new_items:
        state["last_timestamp"] = new_items[-1]["timestamp"]
        save_state(state)
```

## Rules

- State file must survive crashes (write atomically or use temp+rename)
- Handle clock skew: overlap by a small window and deduplicate
- Log each poll cycle (even empty ones) for debugging gaps
- First run (no state file) should NOT process all historical data -- set a reasonable starting point
