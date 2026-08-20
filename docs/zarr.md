# Zarr Utilities

This module provides comprehensive utilities for working with Zarr arrays, OME-NGFF metadata, and data validation.

## Key Features

- **Metadata Management**: Handle multiscale and single-scale metadata
- **OME-NGFF Support**: Full OME-NGFF specification compliance
- **Validation**: Validate ROI offsets and array structures
- **Store Operations**: Advanced Zarr store path handling

## Quick Start

```python
from cellmap_utils import get_multiscale_metadata, validate_ome
from cellmap_utils.zarr import get_matching_scale

# Get metadata
metadata = get_multiscale_metadata(voxel_size=[1.0, 1.0, 1.0],
                                  translation=[0.0, 0.0, 0.0],
                                   levels=3)

# Validate OME-NGFF compliance
is_valid = validate_ome(zarr_group)
```

## Detailed API Reference

For complete function documentation, see the [Zarr API Reference](api/api_zarr.md).