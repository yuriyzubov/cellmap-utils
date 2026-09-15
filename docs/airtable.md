# Airtable Integration

This module provides utilities for working with Airtable databases and Supabase integration.

## Key Features

- **Record Management**: Upsert images and records
- **Dry Run**: `upsert_image()` and `upsert_record_scene_tables()` accept
  `dry_run=True` to preview the record(s) that would be created or updated,
  without writing to Airtable
- **Data Filtering**: Filter Airtable records based on criteria  
- **Supabase Integration**: Connect Airtable with Supabase databases

## Quick Start

```python
from cellmap_utils import upsert_image, filter_records

# Preview the record that would be created/updated, without writing it
preview = upsert_image(at_api, ds_name, image_name, image_path,
                        image_title, image_type, dry_run=True)

# Upsert an image record for real
upsert_image(at_api, ds_name, image_name, image_path, image_title, image_type)

# Filter records
filtered = filter_records(records, criteria)
```

## Detailed API Reference

For complete function documentation, see the [Airtable API Reference](api/api_airtable.md).