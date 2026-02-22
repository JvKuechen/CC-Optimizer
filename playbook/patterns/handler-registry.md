# Handler Registry

**Source:** Discovered across multiple workspace audits

## When

Projects that route different input types to specific processors -- file format parsers, API endpoint handlers, command dispatchers.

## How

A registry maps input patterns to handler functions. New handlers are added by registering, not by modifying routing logic.

```python
# Registry pattern
HANDLERS = {
    "xrpd": XRPDHandler,
    "dsc": DSCHandler,
    "hplc": HPLCHandler,
}

def get_handler(filename):
    """Route to handler based on filename patterns."""
    for key, handler_cls in HANDLERS.items():
        if handler_cls.can_handle(filename):
            return handler_cls()
    raise ValueError(f"No handler for {filename}")
```

Each handler implements a common interface:
```python
class BaseHandler:
    @staticmethod
    def can_handle(filename: str) -> bool:
        """Return True if this handler can process the given file."""
        ...

    def parse(self, filepath: str) -> dict:
        """Parse the file and return structured data."""
        ...
```

## Rules

- Adding a new handler = one new class + one registry entry
- `can_handle` must be deterministic (filename/extension check, not content sniffing)
- When multiple handlers match, use specificity order (most specific first)
- Document the registry in CLAUDE.md as a handler table
