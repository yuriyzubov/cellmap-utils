# Changelog

All notable changes to this project will be documented in this file.

## [0.0.35] - 2026-09-24

### 🎉 New Features
- **Airtable**: Added `upsert_doi()`, which upserts a record in the `doi`
  table and links it to an image record. Finds the image by its storage
  path, fills the dataset name, and links the related records. Supports
  `dry_run`.
- **Supabase Integration**: Added `get_mesh_record()` and `SupaMeshModel`,
  which build a Supabase record for a neuroglancer precomputed mesh volume.
  The grid scale and shift come from the mesh metadata rather than a fixed
  value.

### 🔧 Enhanced Features
- **Airtable**: `upsert_image()` accepts `image_path_s3`, so an image can
  have a filesystem copy, an S3 copy, or both. Each copy that is present
  fills its own location field; a copy that is absent leaves its field
  unset. Array metadata is read from the filesystem copy when it exists.

### 🧪 Testing / CI
- Added 30 tests covering `upsert_doi()`, the S3 paths in `upsert_image()`,
  and the mesh helpers. The suite is now 65 tests.

### 📦 Package Management
- Exported `upsert_doi` and `get_mesh_record` at the package level.
- Documented the new functions on the airtable page, and added the doi
  module to the API reference.
- Version bump from 0.0.34 to 0.0.35.

## [0.0.34] - 2026-09-15

### 🎉 New Features
- **Zarr**: Added `get_normalized_scale()` and `apply_normalized_scale()` to
  correct a mislabeled dataset voxel size against a trusted reference
  pyramid, matched by array shape.
- **Zarr**: Added `is_valid_ome()`, a non-raising counterpart to
  `validate_ome()`.
- **Dry-run support**: Added a `dry_run` option to `upsert_image()`,
  `upsert_record_scene_tables()`, `insert_omero_metadata()`,
  `ome_ngff_only()`, `round_decimals()`, `remove_checksum()`, and
  `repair_zarr_branch()`. Each now previews its change and returns what
  was (or would be) written, without requiring a real write.

### 🔧 Enhanced Features
- **OME-NGFF**: Migrated metadata reading/validation from `ngff_zarr` (an
  undeclared dependency) to `ome-zarr-models`, adding support for OME-NGFF
  0.5 (Zarr v3) alongside 0.4. Affects `get_s0_level()`,
  `get_matching_scale()`, and `validate_ome()`.
- **Airtable**: `upsert_image()` now reads OME-NGFF metadata via the shared
  `get_s0_level()` helper instead of a local, unvalidated attrs read.
- **Supabase Integration**: Use `doi_link_dataset_crop` (not
  `doi_link_dataset`) for human_segmentation images; pull dataset
  publications from the collection record and the description from the
  sample record.

### 🐛 Bug Fixes
- Fixed `round_decimals()` writing through to the underlying store during
  `dry_run` (now deep-copies metadata before mutating it).
- Fixed `round_decimals` being listed in the package's `__all__` but never
  actually imported, so `from cellmap_utils import round_decimals` was
  broken.

### 🧪 Testing / CI
- Added 35 tests across the airtable and zarr modules, plus shared
  `make_multiscale_group` / `ome_version` test fixtures.
- Added a GitHub Actions workflow that runs `pytest` on every push/PR to
  `main`.

### 📦 Package Management
- Dropped the unused `fibsem_tools` dependency and `fibsem` optional group.
- Tightened `requires-python` to `>=3.11`.
- Exported `get_normalized_scale`, `apply_normalized_scale`,
  `is_valid_ome`, and `recalibrate_offset` at the package level.
- Version bump from 0.0.33 to 0.0.34.

## [0.0.33] - 2025-12-15

### 🎉 New Features
- **Image Processing**: Added `get_contrast_values()` function in `cellmap_utils.image.info` module
  - Calculates min/max values and customizable percentiles for small numpy arrays
  - Built-in dimension validation (all dimensions must be < 256)  
  - Configurable percentile ranges (default: 1-99%)
  - Returns dictionary with `percentile_low`, `percentile_high` values
  - Optimized for small arrays, not distributed processing

### � Documentation
- Added changelog documentation
- Updated documentation webpage files  
- Enhanced API documentation structure
- Added comprehensive module overview pages

###  Package Management
- Updated package exports to include new `get_contrast_values` function
- Version bump from 0.0.32 to 0.0.33

### 🔄 Usage Example
```python
from cellmap_utils import get_contrast_values

# Calculate contrast values with custom percentiles
contrast_data = get_contrast_values(array, percentile_low=5.0, percentile_high=95.0)
print(f"Contrast range: {contrast_data['percentile_low']} - {contrast_data['percentile_high']}")
```

## [0.0.32] - 2025-12-15

### 🔧 Enhanced Features
- **Supabase Integration**: Enhanced sample record handling
  - Modified `get_sample_record()` method to include more fields
  - Updated `SupaSampleModel` with improved data mapping
  - Added classmethod to map data from Airtable sample records to Supabase
  - Fixed data template changes for Supabase image and dataset tables

- **Zarr Compatibility**: Improved TensorStore integration
  - Added `remove_checksum` function to make ZarrV2 arrays compatible with TensorStore
  - Enhanced metadata handling for better cross-platform compatibility

### 🐛 Bug Fixes
- Fixed typos in Supabase integration code
- Corrected data insertion templates for Supabase tables

### 📚 Documentation
- Modified documentation structure