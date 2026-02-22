# Config-Driven Generation

**Source:** Discovered across multiple workspace audits

## When

Projects that produce multiple output variants from similar logic -- reports for different instruments, templates for different clients, parsers for different file formats.

## How

Define a JSON/YAML config per variant. The generator reads config and produces output without variant-specific code.

```
configs/
  xrpd.json       # field mappings, layout, units for X-ray diffraction
  dsc.json         # field mappings, layout, units for calorimetry
  hplc.json        # field mappings, layout, units for chromatography

# Each config defines:
{
  "name": "XRPD",
  "fields": [
    {"source": "2theta", "label": "2-Theta", "unit": "degrees", "format": ".2f"},
    {"source": "intensity", "label": "Intensity", "unit": "counts", "format": ".0f"}
  ],
  "layout": "two-column",
  "template": "templates/analytical_report.docx"
}
```

Generator code reads config, never contains variant-specific logic:
```python
def generate_report(config_path, data_path):
    config = json.load(open(config_path))
    data = parse_data(data_path)
    for field in config["fields"]:
        # Generic field processing using config
```

## Rules

- Adding a new variant = adding a config file, not writing code
- Generator must handle missing fields gracefully (config may omit optional fields)
- Validate configs against a schema on load (fail fast on typos)
- Keep configs in a dedicated directory, not mixed with source code
