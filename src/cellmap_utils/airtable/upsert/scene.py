from typing import Tuple
from pyairtable import api
from pyairtable.formulas import match


def upsert_record_scene_tables(
    scene_table: api.table.Table,
    scene_to_image_table: api.table.Table,
    image_table: api.table.Table,
    image_location: str,
    scene_data: dict = {},
    scene_to_image_data: dict = {},
) -> Tuple[dict]:
    """This method upserts records into scene and scene_to_image table at the same time.

    Args:
        scene_table (pyairtable.api.table.Table): output table to upsert
        scene_to_image_table (pyairtable.api.table.Table): output table to upsert
        image_table (pyairtable.api.table.Table): input table from where the record is being taken
        image_location (str): provides value for location filter paramater for the image record
        scene_update (dict): custom data to upsert into "scene" table
        scene_to_image_update (dict): custom data to upsert in "scene_to_image" table

    Returns:
        Tuple[dict]: output records that were upserted
    """

    # fetch a record from image table:
    image_records = image_table.all(formula=match({"location": image_location}))
    if len(image_records) > 1:
        raise ValueError(
            "Multiple images with the same path are found in airtable image table. Only one record should exist!"
        )
    else:
        image_airt = image_records[0]

    scene_to_image_ids = {}
    scene_ids = {}

    scene_to_image_insert = {
        "image": [image_airt["id"]],
        "contrast_start": 0,
        "contrast_stop": 255,
        "color": "white",
    }
    # update if input data for an upsert record exists
    scene_to_image_insert = {
        key: scene_to_image_data.get(key, val)
        for key, val in scene_to_image_insert.items()
    }

    location = image_airt["fields"]["location"]
    print(location)

    # define whether update or create a record in the scene_to_image table by looking at the value from 'location_web' column
    existing_record_scene_to_image = scene_to_image_table.first(
        formula=match({"location_web": location})
    )

    # add records to scene_to_image table
    if existing_record_scene_to_image == None:
        scene_to_image_ids[location] = scene_to_image_table.create(
            scene_to_image_insert
        )
    else:
        scene_to_image_ids[location] = scene_to_image_table.update(
            existing_record_scene_to_image["id"], scene_to_image_insert
        )

    # add record to scene table
    # define whether update or create a record in the scene table by looking at the value from 'scene_to_image' column
    if existing_record_scene_to_image:
        existing_record_scene = scene_table.first(
            formula=match(
                {"scene_to_image": existing_record_scene_to_image["fields"]["name"]}
            )
        )
    else:
        existing_record_scene = None

    scene_insert = {
        "name": "Default view",
        "scene_to_image": [scene_to_image_ids[location]["id"]],
        "description": "The default view of the data.",
        "crossection_scale": 10.0,
        "projection_scale": 1000.0,
    }
    # update if input data for an upsert record exists
    scene_insert = {key: scene_data.get(key, val) for key, val in scene_insert.items()}

    if existing_record_scene == None:
        scene_ids[location] = scene_table.create(scene_insert)
    else:
        scene_ids[location] = scene_table.update(
            existing_record_scene["id"], scene_insert
        )

    return (scene_to_image_ids, scene_ids)
