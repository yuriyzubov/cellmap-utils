# Zarr Utilities

This module provides comprehensive utilities for working with Zarr arrays, OME-NGFF metadata, and data validation.

## Key Features

- **Metadata Management**: Handle multiscale and single-scale metadata
- **OME-NGFF Support**: Full OME-NGFF specification compliance, both 0.4
  (Zarr v2) and 0.5 (Zarr v3) stores, via `ome-zarr-models`
- **Validation**: Validate ROI offsets and array structures; `is_valid_ome()`
  for a non-raising check
- **Scale Normalization**: Correct a mislabeled dataset voxel size against a
  trusted reference pyramid with `get_normalized_scale()` and
  `apply_normalized_scale()`
- **Store Operations**: Advanced Zarr store path handling
- **Dry Run**: Most metadata-writing functions accept `dry_run=True` to
  preview a change without writing it

## Quick Start

```python
from cellmap_utils import get_multiscale_metadata, validate_ome
from cellmap_utils.zarr import get_matching_scale, get_normalized_scale, apply_normalized_scale

# Get metadata
metadata = get_multiscale_metadata(voxel_size=[1.0, 1.0, 1.0],
                                  translation=[0.0, 0.0, 0.0],
                                   levels=3)

# Validate OME-NGFF compliance
is_valid = validate_ome(zarr_group)

# Correct a dataset's voxel size against a trusted reference, then preview the write
normalized = get_normalized_scale(reference_group, dataset_group)
apply_normalized_scale(dataset_group, "s0", normalized, dry_run=True)
```

## Detailed API Reference

For complete function documentation, see the [Zarr API Reference](api/api_zarr.md).