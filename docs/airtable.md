# Airtable Integration

This module provides utilities for working with Airtable databases and Supabase integration.

## Key Features

- **Record Management**: Upsert images, doi records, and scene records
- **Filesystem and S3 copies**: `upsert_image()` takes `image_path` for a
  filesystem copy and `image_path_s3` for an S3 copy. Pass one or both. Each
  copy present fills its own field (`location`, `location_s3`); a copy that is
  absent leaves its field unset
- **Dry Run**: `upsert_image()`, `upsert_doi()`, and
  `upsert_record_scene_tables()` accept `dry_run=True` to preview the
  record(s) that would be created or updated, without writing to Airtable
- **Data Filtering**: Filter Airtable records based on criteria  
- **Supabase Integration**: Connect Airtable with Supabase databases

## Quick Start

```python
from cellmap_utils import upsert_image, upsert_doi, filter_records

# Preview the record that would be created/updated, without writing it
preview = upsert_image(at_api, ds_name, image_name, image_path,
                        image_title, image_type, dry_run=True)

# Upsert an image record for real
upsert_image(at_api, ds_name, image_name, image_path, image_title, image_type)

# Record both a filesystem copy and an S3 copy of the same image
upsert_image(at_api, ds_name, image_name, image_path, image_title, image_type,
             image_path_s3="s3://my-bucket/sample.zarr/image")

# Upsert a doi record, linked to the image at this path
upsert_doi(at_api, image_path, "refined nucleus segmentations")

# Filter records
filtered = filter_records(records, criteria)
```

## DOI Records

`upsert_doi()` links an image to a record in the `doi` table. The image is
found by its `location` or `location_s3` path, not by its name, because image
names such as `nuc` repeat across many datasets.

The function fills `dataset` (as `"{collection id} {image title}"`), and links
`collection` and `sample` from the image's collection record. It links
`fibsem_imaging` only for raw FIB-SEM data (`image_type` `"em"`).

Segmentation crops (`image_type` `"human_segmentation"`) belong in the
separate `doi_crop` table, so `upsert_doi()` rejects them.

## Supabase Records

`get_mesh_record()` reads a neuroglancer precomputed mesh volume and its
Airtable image record, and returns a `SupaMeshModel`:

```python
from cellmap_utils import get_mesh_record

mesh = get_mesh_record(mesh_path, image_path, ds_name, at_api)
```

The grid scale and the grid shift come from the `transform` in the mesh `info`
file, not from a fixed value. The image record is matched on its `location_s3`
field. A mesh whose transform is not the identity prints a warning, because
such a mesh does not sit on the image.

## Detailed API Reference

For complete function documentation, see the [Airtable API Reference](api/api_airtable.md).