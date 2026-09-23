from typing import Tuple
from pyairtable import api
from pyairtable.formulas import match
import os
import zarr

from cellmap_utils.zarr.metadata import get_s0_level

# upsert image record
from typing import Literal

# Zarr metadata file names that sometimes end up on the tail of a discovered
# path (e.g. when paths come from a glob for "zarr.json"/".zarray"/".zgroup").
_ZARR_METADATA_FILENAMES = {"zarr.json", ".zarray", ".zgroup", ".zattrs"}


def _read_multiscale_group(image_path: str) -> Tuple[zarr.Group, str]:
    """Open an OME-NGFF Zarr group and figure out which array holds the base (s0) scale.

    Args:
        image_path (str): path to either the multiscale group or one of its arrays.
            A trailing Zarr metadata filename (e.g. "zarr.json") is stripped
            off if present, since it points at a file, not a group/array root.

    Returns:
        Tuple[zarr.Group, str]: the multiscale group, and the name of the array to read.
    """
    if os.path.basename(image_path) in _ZARR_METADATA_FILENAMES:
        image_path = os.path.dirname(image_path)

    node = zarr.open(image_path, mode="r")
    if isinstance(node, zarr.Group):
        return node, "s0"

    group_path, array_name = os.path.split(image_path)
    return zarr.open_group(group_path, mode="r"), array_name


def _is_s3(path: str) -> bool:
    return path.startswith("s3://")


def _path_exists(path: str) -> bool:
    """Check whether a copy of the image is present at ``path``.

    Args:
        path (str): a filesystem path, or an ``s3://`` path.

    Returns:
        bool: True if something is present at ``path``.
    """
    if _is_s3(path):
        import fsspec

        fs, _, paths = fsspec.get_fs_token_paths(path)
        return fs.exists(paths[0])

    return os.path.exists(path)


def upsert_image(
    at_api: api,
    ds_name: str,
    image_name: str,
    image_path: str | None,
    image_title: str,
    image_type: Literal["human_segmentation", "em"],
    institution: str = "HHMI / Janelia Research Campus",
    challenge : bool = False,
    dry_run : bool = False,
    image_path_s3: str | None = None,
) -> dict:
    """Upsert a record to airtable image table.

    An image can have a filesystem copy, an S3 copy, or both. Each copy that is
    present gets its own field: ``location`` for the filesystem copy, and
    ``location_s3`` for the S3 copy. A copy that is absent leaves its field
    unset. The array metadata comes from the filesystem copy when it exists,
    because that copy reads faster.

    Args:
        image_table (api.table.Table): image airtable object to create references.
        ds_name (str): name of the dataset.
        image_name (str): name of the image to upsert.
        image_path (str | None): filesystem path of the image. Pass None if the
            image has no filesystem copy. An ``s3://`` path is not accepted here.
        image_title (str): image title on openorganelle.com.
        image_type (Literal[&#39;human_segmentation&#39;, &#39;em&#39;]): image type
        collection_table (api.table.Table): collation airtable object to create references.
        fibsem_table (api.table.Table): fibsem_imaging airtable object to create references.
        annotation_table (api.table.Table): annotation airtable object to create references.
        dry_run (bool, optional): if True, compute the record that would be
            created/updated, but do not call Airtable's create/update. Defaults
            to False.
        image_path_s3 (str | None, optional): ``s3://`` path of the image. Pass
            None if the image has no S3 copy. Defaults to None.

    Raises:
        ValueError: raise value error if image_path holds an s3:// path.
        ValueError: raise value error if neither path holds a copy of the image.
        ValueError: raise value error if multiple records with the same location and name are found in the image table.

    Returns:
        dict: the record that was upserted, in the same shape returned by
            pyairtable (``{'id': ..., 'fields': ...}``). When dry_run is True, no
            record is actually created/updated, so 'id' is None.
    """

    if image_path is not None and _is_s3(image_path):
        raise ValueError(
            "image_path must be a filesystem path. "
            "Pass an s3:// path in image_path_s3."
        )

    if image_path is None and image_path_s3 is None:
        raise ValueError("Pass image_path, image_path_s3, or both.")

    locations = {}
    for field, path in (("location", image_path), ("location_s3", image_path_s3)):
        if path is None:
            continue
        path = path.rstrip("/")
        if _path_exists(path):
            locations[field] = path
        else:
            print(f"No copy found at {path}")

    if not locations:
        raise ValueError("No copy found at the given paths.")

    metadata_path = locations.get("location", locations.get("location_s3"))

    image_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["IMAGE_TABLE_ID"]
    )
    collection_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["COLLECTION_TABLE_ID"]
    )
    fibsem_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["FIBSEM_TABLE_ID"]
    )
    annotation_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["ANNOTATION_TABLE_ID"]
    )
    institution_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["INSTITUTION_TABLE_ID"]
    )

    # a record already in airtable can carry only one of the two locations
    existing_records = []
    seen_ids = set()
    for field, path in locations.items():
        for record in image_table.all(formula=match({"name": image_name, field: path})):
            if record["id"] not in seen_ids:
                seen_ids.add(record["id"])
                existing_records.append(record)

    if image_type in ["human_segmentation", "ml_segmentation"]:
        value_type = "label"
    else:
        value_type = "scalar"

    zg, z_arr_name = _read_multiscale_group(metadata_path)
    scale, offset = get_s0_level(zg)
    shape = zg[z_arr_name].shape

    try:
        fibsem_imaging = [fibsem_table.all(formula=match({"name": ds_name}))[0]["id"]]
    except:
        fibsem_imaging = []

    try:
        annotation = [
            annotation_table.all(formula=match({"name": image_name}))[0]["id"]
        ]
    except:
        annotation = []

    record_to_upsert = {
        "name": image_name,
        "collection": [collection_table.all(formula=match({"id": ds_name}))[0]["id"]],
        **locations,
        "format": "zarr",
        "title": image_title,
        "institution": [
            institution_table.all(formula=match({"name": institution}))[0]["id"]
        ],
        "image_type": image_type,
        "value_type": value_type,
        "size_x_pix": shape[2],
        "size_y_pix": shape[1],
        "size_z_pix": shape[0],
        "resolution_x_nm": scale[2],
        "resolution_y_nm": scale[1],
        "resolution_z_nm": scale[0],
        "offset_x_nm": offset[2],
        "offset_y_nm": offset[1],
        "offset_z_nm": offset[0],
        "fibsem_imaging": fibsem_imaging,
        "challenge" : challenge,
        "annotation": annotation,
    }

    if len(existing_records) > 2:
        raise ValueError("Multiple records with matching input image name found")

    if dry_run:
        action = "update" if existing_records else "create"
        print(f"[dry_run] would {action} image record: {record_to_upsert}")
        return {"id": None, "fields": record_to_upsert}

    if not existing_records:
        return image_table.create(record_to_upsert)
    elif len(existing_records) == 1:
        return image_table.update(existing_records[0]["id"], record_to_upsert)
