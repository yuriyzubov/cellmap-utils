# Airtable Integration

This module provides utilities for working with Airtable databases and Supabase integration.

## Key Features

- **Record Management**: Upsert images and records
- **Data Filtering**: Filter Airtable records based on criteria  
- **Supabase Integration**: Connect Airtable with Supabase databases

## Quick Start

```python
from cellmap_utils import upsert_image, filter_records
from cellmap_utils.airtable import get_dataset_full

# Upsert an image record
upsert_image(image_data)

# Filter records
filtered = filter_records(records, criteria)
```

## Detailed API Reference

For complete function documentation, see the [Airtable API Reference](api/api_airtable.md).