from typing import Tuple
from pyairtable import api
from pyairtable.formulas import match
from fibsem_tools import read
import os
import zarr

# upsert image record
from typing import Literal


def upsert_image(
    at_api: api,
    ds_name: str,
    image_name: str,
    image_path: str,
    image_title: str,
    image_type: Literal["human_segmentation", "em"],
    institution : str = "HHMI / Janelia Research Campus"
):
    """Upsert a record to airtable image table.

    Args:
        image_table (api.table.Table): image airtable object to create references.
        ds_name (str): name of the dataset.
        image_name (str): name of the image to upsert.
        image_path (str): image location.
        image_title (str): image title on openorganelle.com.
        image_type (Literal[&#39;human_segmentation&#39;, &#39;em&#39;]): image type
        collection_table (api.table.Table): collation airtable object to create references.
        fibsem_table (api.table.Table): fibsem_imaging airtable object to create references.
        annotation_table (api.table.Table): annotation airtable object to create references.

    Raises:
        ValueError: raise value error if multiple records with the same location and name are found in the image table.
    """
    
    image_table = at_api.table(os.environ['AIRTABLE_BASE_ID'], os.environ['IMAGE_TABLE_ID'])
    collection_table = at_api.table(os.environ['AIRTABLE_BASE_ID'], os.environ['COLLECTION_TABLE_ID'])
    fibsem_table = at_api.table(os.environ['AIRTABLE_BASE_ID'], os.environ['FIBSEM_TABLE_ID'])
    annotation_table = at_api.table(os.environ['AIRTABLE_BASE_ID'], os.environ['ANNOTATION_TABLE_ID'])
    institution_table = at_api.table(os.environ['AIRTABLE_BASE_ID'], os.environ['INSTITUTION_TABLE_ID'])
    
    existing_records = image_table.all(
        formula=match({"name": image_name, "location": image_path.rstrip("/")})
    )

    if image_type in ["human_segmentation", "ml_segmentation"]:
        value_type = "label"
    else:
        value_type = "scalar"

    input_zarr = read(image_path.rstrip("/"))
    if isinstance(input_zarr, zarr.Group):
        zg = input_zarr
        z_arr_name = "s0"
    else:
        zg_path, z_arr_name = os.path.split(image_path.rstrip("/"))
        zg = read(zg_path)

    scale = zg.attrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][0][
        "scale"
    ]
    offset = zg.attrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][1][
        "translation"
    ]
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
        "location": image_path.rstrip("/"),
        "format": "zarr",
        "title" : image_title,
        "institution" : [institution_table.all(formula=match({"name": institution}))[0]["id"]],
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
        "annotation": annotation,
    }

    if len(existing_records) > 2:
        raise ValueError("Multiple records with matching input image name found")

    if not existing_records:
        image_table.create(record_to_upsert)
    elif len(existing_records) == 1:
        image_table.update(existing_records[0]["id"], record_to_upsert)
