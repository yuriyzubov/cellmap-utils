# Changelog

All notable changes to this project will be documented in this file.

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