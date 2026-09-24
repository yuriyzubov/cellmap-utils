import copy

import pytest

from cellmap_utils.airtable.upsert.doi import upsert_doi

IMAGE_PATH = "/nrs/test/jrc_test.zarr/recon-1/labels/inference/segmentations/nuc"


class FakeTable:
    """Stand-in for a pyairtable Table that answers based on the formula it gets.

    A formula that matches no needle returns no records, so a lookup against
    the wrong field fails the test instead of quietly passing.
    """

    def __init__(self, matches=None, get_record=None):
        self._matches = matches or []
        self._get_record = get_record
        self.formulas = []
        self.created = []
        self.updated = []

    def all(self, formula=None):
        text = str(formula)
        self.formulas.append(text)
        for needle, records in self._matches:
            if needle in text:
                return copy.deepcopy(records)
        return []

    def get(self, record_id):
        return copy.deepcopy(self._get_record)

    def create(self, fields):
        record = {"id": "recNEWDOI", "fields": fields}
        self.created.append(record)
        return record

    def update(self, record_id, fields):
        record = {"id": record_id, "fields": fields}
        self.updated.append(record)
        return record


class FakeApi:
    def __init__(self, tables: dict):
        self._tables = tables

    def table(self, base_id, table_id):
        return self._tables[table_id]


@pytest.fixture
def airtable_env(monkeypatch):
    monkeypatch.setenv("AIRTABLE_BASE_ID", "baseXXXX")
    monkeypatch.setenv("IMAGE_TABLE_ID", "image_table")
    monkeypatch.setenv("DOI_TABLE_ID", "doi_table")
    monkeypatch.setenv("COLLECTION_TABLE_ID", "collection_table")


def make_image_record(**overrides):
    record = {
        "id": "recIMG",
        "fields": {
            "name": "nuc",
            # the image table's primary field, not the same as "name"
            "collection/name": "jrc_test/nuc",
            "title": "Nucleus segmentation",
            "image_type": "ml_segmentation",
            "collection": ["recCOLLECTION"],
            "location": IMAGE_PATH,
        },
    }
    record["fields"].update(overrides)
    return record


COLLECTION_RECORD = {
    "id": "recCOLLECTION",
    "fields": {"id": "jrc_test", "sample": ["recSAMPLE"]},
}


def build_api(image_record=None, doi_records=None, collection_record=None):
    image_record = image_record if image_record is not None else make_image_record()
    image_table = FakeTable(matches=[("{location}", [image_record])])
    doi_table = FakeTable(matches=[("jrc_test/nuc", doi_records or [])])
    collection_table = FakeTable(
        get_record=collection_record if collection_record is not None else COLLECTION_RECORD
    )
    tables = {
        "image_table": image_table,
        "doi_table": doi_table,
        "collection_table": collection_table,
    }
    return FakeApi(tables), tables


def test_upsert_doi_creates_record(airtable_env):
    at_api, tables = build_api()

    result = upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations")

    assert result["id"] == "recNEWDOI"
    fields = result["fields"]
    assert fields["image"] == ["recIMG"]
    assert fields["doi_name"] == "refined nucleus segmentations"
    assert fields["dataset"] == "jrc_test Nucleus segmentation"
    assert fields["collection"] == ["recCOLLECTION"]
    assert fields["sample"] == ["recSAMPLE"]
    assert len(tables["doi_table"].created) == 1
    assert len(tables["doi_table"].updated) == 0


def test_upsert_doi_updates_existing_record(airtable_env):
    existing = {"id": "recDOI", "fields": {"image": ["recIMG"]}}
    at_api, tables = build_api(doi_records=[existing])

    result = upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations")

    assert result["id"] == "recDOI"
    assert len(tables["doi_table"].updated) == 1
    assert len(tables["doi_table"].created) == 0


def test_upsert_doi_narrows_doi_lookup_on_image_primary_field(airtable_env):
    """A link field in a formula resolves to the primary field, not "name".

    The image table's primary field is "collection/name". Narrowing on "name"
    (here "nuc") finds nothing and silently duplicates the doi record.
    """
    existing = {"id": "recDOI", "fields": {"image": ["recIMG"]}}
    at_api, tables = build_api(doi_records=[existing])

    upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations")

    doi_formula = tables["doi_table"].formulas[0]
    assert "jrc_test/nuc" in doi_formula
    # the record was found, so this is an update rather than a duplicate
    assert len(tables["doi_table"].updated) == 1


def test_upsert_doi_ignores_doi_record_linked_to_another_image(airtable_env):
    other = {"id": "recOTHERDOI", "fields": {"image": ["recOTHERIMG"]}}
    at_api, tables = build_api(doi_records=[other])

    upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations")

    # narrowing matched by name, but the linked id did not, so create
    assert len(tables["doi_table"].created) == 1
    assert len(tables["doi_table"].updated) == 0


def test_upsert_doi_falls_back_to_location_s3(airtable_env):
    s3_path = "s3://bucket/jrc_test.zarr/recon-1/labels/inference/segmentations/nuc"
    image_record = make_image_record(location_s3=s3_path)
    image_table = FakeTable(matches=[("{location_s3}", [image_record])])
    doi_table = FakeTable(matches=[("jrc_test/nuc", [])])
    collection_table = FakeTable(get_record=COLLECTION_RECORD)
    at_api = FakeApi(
        {
            "image_table": image_table,
            "doi_table": doi_table,
            "collection_table": collection_table,
        }
    )

    result = upsert_doi(at_api, s3_path, "refined nucleus segmentations")

    assert result["fields"]["image"] == ["recIMG"]
    # the filesystem field was tried first, then the s3 field
    assert "{location}" in image_table.formulas[0]
    assert "{location_s3}" in image_table.formulas[1]


def test_upsert_doi_strips_trailing_slash(airtable_env):
    at_api, tables = build_api()

    upsert_doi(at_api, f"{IMAGE_PATH}/", "refined nucleus segmentations")

    assert f"{IMAGE_PATH}'" in tables["image_table"].formulas[0]


def test_upsert_doi_dry_run_does_not_write(airtable_env):
    at_api, tables = build_api()

    result = upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations", dry_run=True)

    assert result["id"] is None
    assert result["fields"]["dataset"] == "jrc_test Nucleus segmentation"
    assert len(tables["doi_table"].created) == 0
    assert len(tables["doi_table"].updated) == 0


def test_upsert_doi_rejects_human_segmentation(airtable_env):
    at_api, _ = build_api(image_record=make_image_record(image_type="human_segmentation"))

    with pytest.raises(ValueError, match="doi_crop"):
        upsert_doi(at_api, IMAGE_PATH, "manual nucleus segmentations")


def test_upsert_doi_raises_when_no_image_matches(airtable_env):
    image_table = FakeTable(matches=[])
    at_api = FakeApi(
        {
            "image_table": image_table,
            "doi_table": FakeTable(),
            "collection_table": FakeTable(get_record=COLLECTION_RECORD),
        }
    )

    with pytest.raises(ValueError, match="No image record found"):
        upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations")


def test_upsert_doi_raises_when_image_has_no_collection(airtable_env):
    image_record = make_image_record()
    del image_record["fields"]["collection"]
    at_api, _ = build_api(image_record=image_record)

    with pytest.raises(ValueError, match="no linked collection"):
        upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations")


def test_upsert_doi_sets_fibsem_imaging_for_raw_data(airtable_env):
    image_record = make_image_record(
        image_type="em",
        title="eFIB-SEM Data",
        fibsem_imaging=["recFIBSEM"],
    )
    at_api, _ = build_api(image_record=image_record)

    result = upsert_doi(at_api, IMAGE_PATH, "reconstructed FIB-SEM data")

    assert result["fields"]["fibsem_imaging"] == ["recFIBSEM"]


def test_upsert_doi_omits_fibsem_imaging_for_derived_images(airtable_env):
    image_record = make_image_record(fibsem_imaging=["recFIBSEM"])
    at_api, _ = build_api(image_record=image_record)

    result = upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations")

    # the image carries a fibsem link, but a segmentation must not pass it on
    assert "fibsem_imaging" not in result["fields"]


def test_upsert_doi_omits_sample_when_collection_has_none(airtable_env):
    at_api, _ = build_api(collection_record={"id": "recCOLLECTION", "fields": {"id": "jrc_test"}})

    result = upsert_doi(at_api, IMAGE_PATH, "refined nucleus segmentations")

    assert "sample" not in result["fields"]
