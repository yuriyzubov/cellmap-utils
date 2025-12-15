# Changelog

All notable changes to this project will be documented in this file.

## [0.0.33] - 2025-12-15

### Added
- New `get_contrast_values()` function in `cellmap_utils.image.info` module
  - Calculates min/max values and customizable percentiles for small numpy arrays
  - Includes dimension validation (arrays must have all dimensions < 256)
  - Configurable percentile ranges (default: 1st and 99th percentiles)
  - Returns dictionary with `min_val`, `max_val`, `percentile_low`, `percentile_high`

### Changed
- Updated package exports to include `get_contrast_values` function
- Enhanced documentation with airtable module overview

### Documentation
- Added comprehensive API documentation for image processing utilities
- Updated main package documentation structure