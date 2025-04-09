from pyairtable import api

# from dotenv import load_dotenv
import os
from pyairtable.formulas import match
from datetime import datetime

from .pydantic_models import (
    SupaDatasetModel,
    SupaImageAcquisitionModel,
    SupaImageModel,
    SupaPublicationModel,
    SupaSampleModel,
)


def get_image_record(image_path: str, ds_name: str, at_api: api):
    """Read an image record from airtable and return supabase image, dataset, sample, and acquisition records.

    Args:
        image_path (str): path to dataset used as a filter parameter for airtable image table records
        at_api (api): airtable api instance

    Returns:
        dict: returns a dictionary of records, with pydantic models for supabase table records as values.
    """

    # image table (switch between prod and test bases in .env)
    image_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["IMAGE_TABLE_ID"]
    )
    fibsem_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["FIBSEM_TABLE_ID"]
    )
    institution_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["INSTITUTION_TABLE_ID"]
    )

    image_record = image_table.all(formula=match({"location": image_path.rstrip("/")}))[0]
    
    name = image_record["fields"]["name"]
    display_settings = {
        "invertLUT": False,
        "contrastLimits": {"end": 255, "max": 255, "min": 0, "start": 0},
    }

    content_type_mapping = {
        "em": "em",
        "ml_segmentation": "segmentation",
        "human_segmentation": "segmentation",
    }
    content_type = content_type_mapping[image_record["fields"]["image_type"]]

    source = None
    try:

        fibsem_record = fibsem_table.get(image_record["fields"]["fibsem_imaging"][0])
        if image_record["fields"]["image_type"] == "em":
            display_settings["color"] = "white"

            format_string = "%Y-%m-%d"
            source = {
                "bias_V": fibsem_record["fields"]["bias_v"],
                "scan_hz": fibsem_record["fields"]["scan_rate_mhz"],
                "current_nA": fibsem_record["fields"]["imaging_current_nA"],
                "duration_days": (
                    datetime.strptime(
                        fibsem_record["fields"]["stop_date"], format_string
                    ).date()
                    - datetime.strptime(
                        fibsem_record["fields"]["start_date"], format_string
                    ).date()
                ).days,
                "landing_energy_eV": fibsem_record["fields"]["primary_energy_ev"],
            }
    except:
        print("NO FIBSEM RECORD", ds_name)

    if image_record["fields"]["image_type"] == "em":
        pub_name = "Reconstructed FIB-SEM data"
    else:
        pub_name = "Segmentations"

    print(image_record)
    supa_image = SupaImageModel(
        source=source,
        name=name,
        url=image_path,
        description=image_record["fields"]["title"],
        format="zarr",
        display_settings=display_settings,
        sample_type=image_record["fields"]["value_type"],
        content_type=content_type,
        dataset_name=ds_name,
        institution=institution_table.get( image_record['fields']['institution'][0])['fields']['name'],
        grid_dims=["z", "y", "x"],
        grid_scale=[
            image_record["fields"][f"resolution_{_}_nm"] for _ in ["z", "y", "x"]
        ],
        grid_translation=[0.0, 0.0, 0.0],
        # [
        #     image_record["fields"][f"offset_{_}_nm"] for _ in ["z", "y", "x"]
        # ],
        grid_units=["nm", "nm", "nm"],
        grid_index_order="C",
        stage="dev",
        image_stack=f"{ds_name}_groundtruth",
        #doi={"url": image_record["fields"]["doi_link_dataset"][0], "name": pub_name},
    )

    return supa_image


def get_img_acq_record(ds_name: str, at_api: api):

    fibsem_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["FIBSEM_TABLE_ID"]
    )
    fibsem_record = fibsem_table.all(formula=match({"name": ds_name}))[0]

    sample_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["SAMPLE_TABLE_ID"]
    )
    #sample_record = sample_table.all(formula=match({"name": ds_name}))[0]

    image_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["IMAGE_TABLE_ID"]
    )
    image_record = image_table.get(fibsem_record["fields"]["images"][0])
    supa_acquisition = SupaImageAcquisitionModel(
        name=ds_name,
        institution="HHMI/Janelia",#sample_record["fields"]["institution"],
        start_date=fibsem_record["fields"]["start_date"],
        grid_axes=["z", "y", "x"],
        grid_spacing=[
            fibsem_record["fields"][f"resolution_{_}_nm"] for _ in ["z", "y", "x"]
        ],
        grid_spacing_unit="nm",
        grid_dimensions=[
            image_record["fields"][f"size_{_}_pix"] for _ in ["z", "y", "x"]
        ],
        grid_dimensions_unit="nm",
    )

    return supa_acquisition


def get_sample_record(ds_name: str, at_api: api):

    collection_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["COLLECTION_TABLE_ID"]
    )
    collection_record = collection_table.all(formula=match({"id": ds_name}))[0]

    sample_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["SAMPLE_TABLE_ID"]
    )
    sample_record = sample_table.get(collection_record["fields"]["sample"][0])

    supa_sample = SupaSampleModel(
        name=ds_name,
        description=sample_record["fields"]["description"],
        protocol=sample_record["fields"]["description"],
        contributions=sample_record["fields"]["contributions"],
        type=sample_record["fields"]["type"],
        subtype=sample_record["fields"]["subtype"],
    )
    return supa_sample


def get_dataset_record(ds_name: str, at_api: api):

    collection_table = at_api.table(
        os.environ["AIRTABLE_BASE_ID"], os.environ["COLLECTION_TABLE_ID"]
    )
    sample_table = at_api.table(os.environ["AIRTABLE_BASE_ID"], os.environ["COLLECTION_TABLE_ID"])
    publication_table = at_api.table(os.environ["AIRTABLE_BASE_ID"], os.environ["PUBLICATION_TABLE_ID"])
    doi_table = at_api.table(os.environ["AIRTABLE_BASE_ID"], os.environ["DOI_TABLE_ID"])
    
    
    collection_record = collection_table.all(formula=match({"id": ds_name}))[0]
    sample_record = sample_table.get(collection_record['fields']['sample'][0])
    
    pubs = []
    for doi_id in sample_record['fields']['doi']:
        doi_record = doi_table.get(doi_id)
        supa_doi = SupaPublicationModel(
            name=doi_record['fields']['doi_name'],
            url = doi_record['fields']['doi_link_dataset'],
            pub_type = 'doi',
        )
        pubs.append(supa_doi)
    print(pubs)
    supa_dataset = SupaDatasetModel(
        name=ds_name,
        description=collection_record["fields"]["description"],
        thumbnail_url=f"s3://janelia-cosem-datasets/{ds_name}/thumbnail.jpg",
        stage="dev",
        publications=pubs,
    )
    return supa_dataset


def get_dataset_full(img_path: str, ds_name: str, at_api: api):

    return {
        "image": get_image_record(img_path, ds_name, at_api),
        "image_acquisition": get_img_acq_record(ds_name, at_api),
        "sample": get_sample_record(ds_name, at_api),
        "dataset": get_dataset_record(ds_name, at_api),
    }
