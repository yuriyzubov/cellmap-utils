import json

import pytest

from cellmap_utils.airtable.supabase.air_to_supabase import (
    _IDENTITY_TRANSFORM,
    _grid_from_transform,
    _mesh_name,
    _read_mesh_info,
    get_mesh_record,
)


class FakeTable:
    """Minimal stand-in for a pyairtable Table, just enough for get_mesh_record()."""

    def __init__(self, records):
        self._records = records
        self.formulas = []

    def all(self, formula=None):
        self.formulas.append(formula)
        return self._records


class FakeApi:
    def __init__(self, tables: dict):
        self._tables = tables

    def table(self, base_id, table_id):
        return self._tables[table_id]


@pytest.fixture
def airtable_env(monkeypatch):
    monkeypatch.setenv("AIRTABLE_BASE_ID", "baseXXXX")
    monkeypatch.setenv("IMAGE_TABLE_ID", "image_table")


@pytest.fixture
def mesh_dir(tmp_path):
    """Build a mesh folder that holds a neuroglancer info file."""

    def _make(transform, kind="segmentations", organelle="mito"):
        path = tmp_path / kind / organelle
        path.mkdir(parents=True)
        info = {"@type": "neuroglancer_multilod_draco", "transform": transform}
        (path / "info").write_text(json.dumps(info))
        return str(path)

    return _make


def test_mesh_name_segmentation():
    path = "s3://test-bucket/sample.zarr/segmentations/mito"
    assert _mesh_name(path) == "mito_seg"


def test_mesh_name_groundtruth():
    path = "s3://test-bucket/sample.zarr/groundtruth/mito"
    assert _mesh_name(path) == "mito_gt"


def test_mesh_name_ignores_trailing_slash():
    path = "s3://test-bucket/sample.zarr/segmentations/nuc/"
    assert _mesh_name(path) == "nuc_seg"


def test_mesh_name_rejects_unknown_path():
    with pytest.raises(ValueError, match="segmentations"):
        _mesh_name("s3://test-bucket/sample.zarr/image")


def test_read_mesh_info(mesh_dir):
    path = mesh_dir(_IDENTITY_TRANSFORM)
    info = _read_mesh_info(path)
    assert info["@type"] == "neuroglancer_multilod_draco"
    assert info["transform"] == _IDENTITY_TRANSFORM


def test_read_mesh_info_ignores_trailing_slash(mesh_dir):
    path = mesh_dir(_IDENTITY_TRANSFORM)
    assert _read_mesh_info(f"{path}/") == _read_mesh_info(path)


def test_grid_from_transform_reads_diagonal_and_last_column():
    # 4x3 row-major: scale sits on the diagonal, shift in the last column
    transform = [2, 0, 0, 10,
                 0, 3, 0, 20,
                 0, 0, 4, 30]

    scale, translation = _grid_from_transform(transform)

    # neuroglancer orders axes x, y, z; supabase wants z, y, x
    assert scale == [4, 3, 2]
    assert translation == [30, 20, 10]


def test_grid_from_identity_transform_has_no_scale_or_shift():
    scale, translation = _grid_from_transform(_IDENTITY_TRANSFORM)
    assert scale == [1, 1, 1]
    assert translation == [0, 0, 0]


def test_get_mesh_record_builds_supabase_record(airtable_env, mesh_dir):
    image_table = FakeTable(
        records=[{"id": "recIMG", "fields": {"name": "mito", "title": "Mitochondria segmentation"}}]
    )
    at_api = FakeApi({"image_table": image_table})
    mesh_path = mesh_dir(_IDENTITY_TRANSFORM)

    record = get_mesh_record(
        mesh_path=mesh_path,
        image_path="s3://test-bucket/sample.zarr/segmentations/mito",
        ds_name="my_dataset",
        at_api=at_api,
    )

    assert record.name == "mito_seg"
    assert record.description == "Mitochondria segmentation"
    assert record.url == mesh_path
    assert record.format == "neuroglancer_multilod_draco"
    assert record.grid_dims == ["z", "y", "x"]
    assert record.grid_scale == [1, 1, 1]
    assert record.grid_translation == [0, 0, 0]
    assert record.grid_units == ["nm", "nm", "nm"]
    assert record.dataset_name == "my_dataset"
    assert record.image_name == "mito"


def test_get_mesh_record_matches_image_on_location_s3(airtable_env, mesh_dir):
    image_path = "s3://test-bucket/sample.zarr/segmentations/mito"
    image_table = FakeTable(
        records=[{"id": "recIMG", "fields": {"name": "mito", "title": "Mitochondria segmentation"}}]
    )
    at_api = FakeApi({"image_table": image_table})

    get_mesh_record(
        mesh_path=mesh_dir(_IDENTITY_TRANSFORM),
        image_path=f"{image_path}/",
        ds_name="my_dataset",
        at_api=at_api,
    )

    # the image is looked up by its s3 location, with the trailing slash removed
    formula = str(image_table.formulas[0])
    assert "location_s3" in formula
    assert image_path in formula


def test_get_mesh_record_takes_grid_from_transform(airtable_env, mesh_dir):
    image_table = FakeTable(
        records=[{"id": "recIMG", "fields": {"name": "mito", "title": "Mitochondria segmentation"}}]
    )
    at_api = FakeApi({"image_table": image_table})
    transform = [8, 0, 0, 1,
                 0, 8, 0, 2,
                 0, 0, 8, 3]

    record = get_mesh_record(
        mesh_path=mesh_dir(transform),
        image_path="s3://test-bucket/sample.zarr/segmentations/mito",
        ds_name="my_dataset",
        at_api=at_api,
    )

    assert record.grid_scale == [8, 8, 8]
    assert record.grid_translation == [3, 2, 1]


def test_get_mesh_record_warns_when_transform_is_not_identity(
    airtable_env, mesh_dir, capsys
):
    image_table = FakeTable(
        records=[{"id": "recIMG", "fields": {"name": "mito", "title": "Mitochondria segmentation"}}]
    )
    at_api = FakeApi({"image_table": image_table})
    transform = [8, 0, 0, 1,
                 0, 8, 0, 2,
                 0, 0, 8, 3]

    get_mesh_record(
        mesh_path=mesh_dir(transform),
        image_path="s3://test-bucket/sample.zarr/segmentations/mito",
        ds_name="my_dataset",
        at_api=at_api,
    )

    assert "MESH TRANSFORM IS NOT THE IDENTITY" in capsys.readouterr().out


def test_get_mesh_record_is_quiet_for_identity_transform(
    airtable_env, mesh_dir, capsys
):
    image_table = FakeTable(
        records=[{"id": "recIMG", "fields": {"name": "mito", "title": "Mitochondria segmentation"}}]
    )
    at_api = FakeApi({"image_table": image_table})

    get_mesh_record(
        mesh_path=mesh_dir(_IDENTITY_TRANSFORM),
        image_path="s3://test-bucket/sample.zarr/segmentations/mito",
        ds_name="my_dataset",
        at_api=at_api,
    )

    assert "MESH TRANSFORM IS NOT THE IDENTITY" not in capsys.readouterr().out
