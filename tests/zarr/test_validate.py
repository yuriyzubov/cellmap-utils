import pytest

from cellmap_utils.zarr.validate import is_valid_ome, validate_ome, validate_roi_offset


def test_is_valid_ome_true_for_well_formed_metadata(make_multiscale_group, ome_version):
    group = make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0]],
        shapes=[(100, 100, 100)],
        translation=[0.0, 0.0, 0.0],
        name="valid",
        ome_version=ome_version,
    )

    assert is_valid_ome(group) is True
    # validate_ome() must not raise on the same well-formed metadata
    validate_ome(group)


def test_is_valid_ome_false_for_malformed_metadata(make_multiscale_group, ome_version):
    group = make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0]],
        shapes=[(100, 100, 100)],
        translation=[0.0, 0.0, 0.0],
        name="malformed",
        ome_version=ome_version,
    )

    # break the metadata: "multiscales" must be a list of objects, not a string
    if ome_version == "0.4":
        group.attrs["multiscales"] = "not-a-valid-multiscales-entry"
    else:
        group.attrs["ome"] = {"version": "0.5", "multiscales": "not-a-valid-multiscales-entry"}

    assert is_valid_ome(group) is False
    with pytest.raises(RuntimeError):
        validate_ome(group)


def test_validate_roi_offset_aligned_does_not_raise(make_multiscale_group, ome_version):
    dataset = make_multiscale_group(
        voxel_sizes=[[4.0, 4.0, 4.0]],
        shapes=[(100, 100, 100)],
        translation=[0.0, 0.0, 0.0],
        name="dataset_aligned",
        ome_version=ome_version,
    )
    roi = make_multiscale_group(
        voxel_sizes=[[4.0, 4.0, 4.0]],
        shapes=[(50, 50, 50)],
        translation=[0.0, 0.0, 0.0],
        name="roi_aligned",
        ome_version=ome_version,
    )

    validate_roi_offset(dataset, roi)


def test_validate_roi_offset_misaligned_raises(make_multiscale_group, ome_version):
    dataset = make_multiscale_group(
        voxel_sizes=[[4.0, 4.0, 4.0]],
        shapes=[(100, 100, 100)],
        translation=[0.0, 0.0, 0.0],
        name="dataset_misaligned",
        ome_version=ome_version,
    )
    roi = make_multiscale_group(
        voxel_sizes=[[4.0, 4.0, 4.0]],
        shapes=[(50, 50, 50)],
        translation=[1.3, 1.3, 1.3],
        name="roi_misaligned",
        ome_version=ome_version,
    )

    with pytest.raises(ValueError):
        validate_roi_offset(dataset, roi)
