from pyairtable import api
from pyairtable.formulas import match
import os


def upsert_doi(
    at_api: api,
    image_path: str,
    doi_name: str,
    dry_run: bool = False,
) -> dict:
    """Upsert a record to airtable doi table, linked to an image record.

    Segmentation images (image_type "human_segmentation") do not belong in the
    doi table. They belong in the doi_crop table instead, so this method
    rejects them. Images with image_type "ml_segmentation" are still accepted
    here.

    The doi record's ``dataset`` field is set to ``"{collection id} {image
    title}"``, matching the naming convention already used for other doi
    records. The image's linked
    collection record is also set on the doi record's ``collection`` field,
    which drives several of the doi table's lookup fields. The collection's
    linked sample record, if any, is set on the doi record's ``sample`` field.
    When image_type is "em" (raw FIB-SEM data), the image's linked
    fibsem_imaging record is also carried forward onto the doi record's
    ``fibsem_imaging`` field. Derived images (predictions, segmentations) do
    not get this field set.

    Args:
        at_api (api): pyairtable Api object used to reach the base.
        image_path (str): filesystem path or s3:// path of the image record to
            link to the doi record. The image record's ``location`` or
            ``location_s3`` field must hold this exact path. Plain image
            names are not accepted here, because images in different
            datasets often share the same name.
        doi_name (str): value for the doi record's doi_name field.
        dry_run (bool, optional): if True, compute the record that would be
            created/updated, but do not call Airtable's create/update. Defaults
            to False.

    Raises:
        ValueError: raise value error if no image record matches image_path.
        ValueError: raise value error if multiple image records match image_path.
        ValueError: raise value error if the image's image_type is
            "human_segmentation".
        ValueError: raise value error if multiple doi records already link to
            the image.
        ValueError: raise value error if the image has no linked collection
            record.

    Returns:
        dict: the record that was upserted, in the same shape returned by
            pyairtable (``{'id': ..., 'fields': ...}``). When dry_run is True, no
            record is actually created/updated, so 'id' is None.
    """

    image_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["IMAGE_TABLE_ID"]
    )
    doi_table = at_api.table(os.environ["AIRTABLE_BASE_ID"], os.environ["DOI_TABLE_ID"])
    collection_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["COLLECTION_TABLE_ID"]
    )

    image_path = image_path.rstrip("/")
    image_records = image_table.all(
        formula=match({"location": image_path})
    ) or image_table.all(formula=match({"location_s3": image_path}))
    if not image_records:
        raise ValueError(f"No image record found with location {image_path!r}")
    if len(image_records) > 1:
        raise ValueError(f"Multiple image records found with location {image_path!r}")
    image_record = image_records[0]
    image_name = image_record["fields"]["name"]

    image_type = image_record["fields"].get("image_type")
    if image_type == "human_segmentation":
        raise ValueError(
            "image_type 'human_segmentation' belongs in the doi_crop table, "
            "not doi. Use a doi_crop upsert method instead."
        )

    # narrow by the image table's primary field value first (cheap), then
    # confirm by exact linked record id, because a link field compares
    # against the linked record's primary field rather than its name
    image_primary_value = image_record["fields"].get("collection/name", image_name)
    candidate_records = doi_table.all(formula=match({"image": image_primary_value}))
    existing_records = [
        record
        for record in candidate_records
        if image_record["id"] in record["fields"].get("image", [])
    ]
    if len(existing_records) > 1:
        raise ValueError(
            f"Multiple doi records already link to image {image_path!r}"
        )

    collection_ids = image_record["fields"].get("collection", [])
    if not collection_ids:
        raise ValueError(f"Image {image_path!r} has no linked collection record")
    collection_record = collection_table.get(collection_ids[0])
    ds_name = collection_record["fields"]["id"]
    title = image_record["fields"].get("title", "")
    dataset = f"{ds_name} {title}".strip()

    # a collection links to a single sample, but a sample can have several
    # collections, so this is a 1-to-many relationship from sample to collection
    sample_ids = collection_record["fields"].get("sample", [])
    if not sample_ids:
        print(f"No sample linked to collection {ds_name!r}")

    # only raw FIB-SEM data (image_type "em") carries its own fibsem_imaging
    # link forward onto the doi record; derived images (predictions,
    # segmentations) do not.
    fibsem_imaging_ids = []
    if image_type == "em":
        fibsem_imaging_ids = image_record["fields"].get("fibsem_imaging", [])
        if not fibsem_imaging_ids:
            print(f"No fibsem_imaging linked to image {image_path!r}")

    record_to_upsert = {
        "image": [image_record["id"]],
        "doi_name": doi_name,
        "dataset": dataset,
        "collection": [collection_ids[0]],
        **({"sample": sample_ids} if sample_ids else {}),
        **({"fibsem_imaging": fibsem_imaging_ids} if fibsem_imaging_ids else {}),
    }

    if dry_run:
        action = "update" if existing_records else "create"
        print(f"[dry_run] would {action} doi record: {record_to_upsert}")
        return {"id": None, "fields": record_to_upsert}

    if not existing_records:
        return doi_table.create(record_to_upsert)
    else:
        return doi_table.update(existing_records[0]["id"], record_to_upsert)
