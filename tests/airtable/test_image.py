import pytest

from cellmap_utils.airtable.upsert.image import upsert_image


class FakeTable:
    """Minimal stand-in for a pyairtable Table, just enough for upsert_image()."""

    def __init__(self, records=None):
        self._records = records if records is not None else [{"id": "recEXISTING"}]
        self.created = []
        self.updated = []

    def all(self, formula=None):
        return self._records

    def create(self, fields):
        record = {"id": "recNEW", "fields": fields}
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
    monkeypatch.setenv("COLLECTION_TABLE_ID", "collection_table")
    monkeypatch.setenv("FIBSEM_TABLE_ID", "fibsem_table")
    monkeypatch.setenv("ANNOTATION_TABLE_ID", "annotation_table")
    monkeypatch.setenv("INSTITUTION_TABLE_ID", "institution_table")


@pytest.fixture
def image_group_path(tmp_path):
    import zarr

    store_path = tmp_path / "image.zarr"
    group = zarr.open_group(str(store_path), mode="w", zarr_format=2)
    group.create_array("s0", shape=(10, 20, 30), dtype="uint8")
    group.attrs["multiscales"] = [
        {
            "axes": [{"name": axis, "type": "space", "unit": "nanometer"} for axis in "zyx"],
            "coordinateTransformations": [{"scale": [1.0, 1.0, 1.0], "type": "scale"}],
            "datasets": [
                {
                    "coordinateTransformations": [
                        {"type": "scale", "scale": [6.0, 6.0, 6.0]},
                        {"type": "translation", "translation": [1.0, 2.0, 3.0]},
                    ],
                    "path": "s0",
                }
            ],
            "name": "image",
            "version": "0.4",
        }
    ]
    return str(store_path)


def test_upsert_image_creates_new_record(airtable_env, image_group_path):
    image_table = FakeTable(records=[])  # no existing record -> create path
    tables = {
        "image_table": image_table,
        "collection_table": FakeTable(records=[{"id": "recCOLLECTION"}]),
        "fibsem_table": FakeTable(records=[{"id": "recFIBSEM"}]),
        "annotation_table": FakeTable(records=[{"id": "recANNOTATION"}]),
        "institution_table": FakeTable(records=[{"id": "recINSTITUTION"}]),
    }
    at_api = FakeApi(tables)

    result = upsert_image(
        at_api=at_api,
        ds_name="my_dataset",
        image_name="my_image",
        image_path=image_group_path,
        image_title="My Image",
        image_type="em",
    )

    assert result["id"] == "recNEW"
    fields = result["fields"]
    assert fields["size_z_pix"] == 10
    assert fields["size_y_pix"] == 20
    assert fields["size_x_pix"] == 30
    assert fields["resolution_z_nm"] == 6.0
    assert fields["offset_z_nm"] == 1.0
    assert len(image_table.created) == 1
    assert len(image_table.updated) == 0


def test_upsert_image_updates_existing_record(airtable_env, image_group_path):
    image_table = FakeTable(records=[{"id": "recEXISTING"}])
    tables = {
        "image_table": image_table,
        "collection_table": FakeTable(records=[{"id": "recCOLLECTION"}]),
        "fibsem_table": FakeTable(records=[{"id": "recFIBSEM"}]),
        "annotation_table": FakeTable(records=[{"id": "recANNOTATION"}]),
        "institution_table": FakeTable(records=[{"id": "recINSTITUTION"}]),
    }
    at_api = FakeApi(tables)

    result = upsert_image(
        at_api=at_api,
        ds_name="my_dataset",
        image_name="my_image",
        image_path=image_group_path,
        image_title="My Image",
        image_type="em",
    )

    assert result["id"] == "recEXISTING"
    assert len(image_table.updated) == 1
    assert len(image_table.created) == 0


def test_upsert_image_dry_run_does_not_write(airtable_env, image_group_path):
    image_table = FakeTable(records=[])
    tables = {
        "image_table": image_table,
        "collection_table": FakeTable(records=[{"id": "recCOLLECTION"}]),
        "fibsem_table": FakeTable(records=[{"id": "recFIBSEM"}]),
        "annotation_table": FakeTable(records=[{"id": "recANNOTATION"}]),
        "institution_table": FakeTable(records=[{"id": "recINSTITUTION"}]),
    }
    at_api = FakeApi(tables)

    result = upsert_image(
        at_api=at_api,
        ds_name="my_dataset",
        image_name="my_image",
        image_path=image_group_path,
        image_title="My Image",
        image_type="em",
        dry_run=True,
    )

    assert result["id"] is None
    assert result["fields"]["size_z_pix"] == 10
    assert len(image_table.created) == 0
    assert len(image_table.updated) == 0
