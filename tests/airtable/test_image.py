import pytest

from cellmap_utils.airtable.upsert import image as image_module
from cellmap_utils.airtable.upsert.image import _is_s3, _path_exists, upsert_image


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


S3_PATH = "s3://test-bucket/sample.zarr/image"


@pytest.fixture
def fake_tables():
    def _make(image_records=None):
        return {
            "image_table": FakeTable(records=image_records if image_records is not None else []),
            "collection_table": FakeTable(records=[{"id": "recCOLLECTION"}]),
            "fibsem_table": FakeTable(records=[{"id": "recFIBSEM"}]),
            "annotation_table": FakeTable(records=[{"id": "recANNOTATION"}]),
            "institution_table": FakeTable(records=[{"id": "recINSTITUTION"}]),
        }

    return _make


def test_is_s3():
    assert _is_s3("s3://bucket/key") is True
    assert _is_s3("/data/sample.zarr") is False


def test_path_exists_on_filesystem(tmp_path):
    present = tmp_path / "image.zarr"
    present.mkdir()
    assert _path_exists(str(present)) is True
    assert _path_exists(str(tmp_path / "missing.zarr")) is False


def test_path_exists_asks_fsspec_for_s3(monkeypatch):
    seen = {}

    class FakeFs:
        def exists(self, path):
            seen["path"] = path
            return True

    def fake_get_fs_token_paths(path):
        return FakeFs(), None, [path]

    import fsspec

    monkeypatch.setattr(fsspec, "get_fs_token_paths", fake_get_fs_token_paths)

    assert _path_exists(S3_PATH) is True
    assert seen["path"] == S3_PATH


def test_upsert_image_rejects_s3_in_image_path(airtable_env, fake_tables):
    with pytest.raises(ValueError, match="image_path_s3"):
        upsert_image(
            at_api=FakeApi(fake_tables()),
            ds_name="my_dataset",
            image_name="my_image",
            image_path=S3_PATH,
            image_title="My Image",
            image_type="em",
        )


def test_upsert_image_requires_at_least_one_path(airtable_env, fake_tables):
    with pytest.raises(ValueError, match="Pass image_path"):
        upsert_image(
            at_api=FakeApi(fake_tables()),
            ds_name="my_dataset",
            image_name="my_image",
            image_path=None,
            image_title="My Image",
            image_type="em",
        )


def test_upsert_image_records_both_copies(airtable_env, fake_tables, image_group_path, monkeypatch):
    # the s3 copy cannot be reached from a test, so report every path as present
    monkeypatch.setattr(image_module, "_path_exists", lambda path: True)
    tables = fake_tables()

    result = upsert_image(
        at_api=FakeApi(tables),
        ds_name="my_dataset",
        image_name="my_image",
        image_path=image_group_path,
        image_title="My Image",
        image_type="em",
        image_path_s3=S3_PATH,
    )

    assert result["fields"]["location"] == image_group_path
    assert result["fields"]["location_s3"] == S3_PATH


def test_upsert_image_reads_metadata_from_the_filesystem_copy(
    airtable_env, fake_tables, image_group_path, monkeypatch
):
    monkeypatch.setattr(image_module, "_path_exists", lambda path: True)
    seen = {}
    real_read = image_module._read_multiscale_group

    def spy(path):
        seen["path"] = path
        return real_read(path)

    monkeypatch.setattr(image_module, "_read_multiscale_group", spy)

    upsert_image(
        at_api=FakeApi(fake_tables()),
        ds_name="my_dataset",
        image_name="my_image",
        image_path=image_group_path,
        image_title="My Image",
        image_type="em",
        image_path_s3=S3_PATH,
    )

    # the filesystem copy reads faster, so it supplies the array metadata
    assert seen["path"] == image_group_path


def test_upsert_image_records_s3_copy_only(
    airtable_env, fake_tables, image_group_path, monkeypatch
):
    monkeypatch.setattr(image_module, "_path_exists", lambda path: True)
    seen = {}
    real_read = image_module._read_multiscale_group

    def fake_read(path):
        # the s3 copy cannot be opened from a test, so read the local fixture
        seen["path"] = path
        return real_read(image_group_path)

    monkeypatch.setattr(image_module, "_read_multiscale_group", fake_read)

    result = upsert_image(
        at_api=FakeApi(fake_tables()),
        ds_name="my_dataset",
        image_name="my_image",
        image_path=None,
        image_title="My Image",
        image_type="em",
        image_path_s3=S3_PATH,
    )

    assert "location" not in result["fields"]
    assert result["fields"]["location_s3"] == S3_PATH
    # with no filesystem copy, the metadata has to come from the s3 copy
    assert seen["path"] == S3_PATH


def test_upsert_image_skips_a_copy_that_is_absent(
    airtable_env, fake_tables, image_group_path, monkeypatch
):
    # the s3 copy is not there, the filesystem copy is
    monkeypatch.setattr(image_module, "_path_exists", lambda path: not _is_s3(path))

    result = upsert_image(
        at_api=FakeApi(fake_tables()),
        ds_name="my_dataset",
        image_name="my_image",
        image_path=image_group_path,
        image_title="My Image",
        image_type="em",
        image_path_s3=S3_PATH,
    )

    assert result["fields"]["location"] == image_group_path
    assert "location_s3" not in result["fields"]


def test_upsert_image_raises_when_no_copy_is_found(
    airtable_env, fake_tables, image_group_path, monkeypatch
):
    monkeypatch.setattr(image_module, "_path_exists", lambda path: False)

    with pytest.raises(ValueError, match="No copy found"):
        upsert_image(
            at_api=FakeApi(fake_tables()),
            ds_name="my_dataset",
            image_name="my_image",
            image_path=image_group_path,
            image_title="My Image",
            image_type="em",
            image_path_s3=S3_PATH,
        )
