import pytest

from cellmap_utils.zarr.roi import get_matching_scale, get_normalized_scale


def test_get_matching_scale_finds_roi_level_matching_dataset_s0(make_multiscale_group, ome_version):
    dataset = make_multiscale_group(
        voxel_sizes=[[4.0, 4.0, 4.0]],
        shapes=[(100, 100, 100)],
        translation=[0.0, 0.0, 0.0],
        name="dataset",
        ome_version=ome_version,
    )
    roi = make_multiscale_group(
        voxel_sizes=[[4.0, 4.0, 4.0], [8.0, 8.0, 8.0]],
        shapes=[(50, 50, 50), (25, 25, 25)],
        translation=[1.0, 2.0, 3.0],
        name="roi",
        ome_version=ome_version,
    )

    scale, translation = get_matching_scale(dataset, roi)

    assert scale == [4.0, 4.0, 4.0]
    assert translation == [1.0, 2.0, 3.0]


def test_get_matching_scale_no_match_raises(make_multiscale_group, ome_version):
    dataset = make_multiscale_group(
        voxel_sizes=[[4.0, 4.0, 4.0]],
        shapes=[(100, 100, 100)],
        translation=[0.0, 0.0, 0.0],
        name="dataset_no_match",
        ome_version=ome_version,
    )
    roi = make_multiscale_group(
        voxel_sizes=[[8.0, 8.0, 8.0]],
        shapes=[(25, 25, 25)],
        translation=[0.0, 0.0, 0.0],
        name="roi_no_match",
        ome_version=ome_version,
    )

    with pytest.raises(ValueError):
        get_matching_scale(dataset, roi)


@pytest.fixture
def reference(make_multiscale_group, ome_version):
    # s0: 6nm, 200^3 ; s1: 12nm, 100^3 (s1 covers the same physical extent as s0)
    return make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0], [12.0, 12.0, 12.0]],
        shapes=[(200, 200, 200), (100, 100, 100)],
        translation=[0.0, 0.0, 0.0],
        name="reference",
        ome_version=ome_version,
    )


def test_get_normalized_scale_matches_reference_level_by_shape(make_multiscale_group, reference, ome_version):
    # segmentation is only 100^3 voxels, but was labeled with the s0 (6nm) voxel size
    dataset = make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0]],
        shapes=[(100, 100, 100)],
        translation=[10.0, 20.0, 30.0],
        name="segmentation",
        ome_version=ome_version,
    )

    result = get_normalized_scale(reference, dataset)

    assert result["scale"] == [12.0, 12.0, 12.0]
    # translation is an absolute position in nanometers, so it must stay unchanged
    assert result["translation"] == [10.0, 20.0, 30.0]


def test_get_normalized_scale_uses_requested_dataset_level(make_multiscale_group, reference, ome_version):
    dataset = make_multiscale_group(
        voxel_sizes=[[3.0, 3.0, 3.0], [6.0, 6.0, 6.0]],
        shapes=[(400, 400, 400), (200, 200, 200)],
        translation=[0.0, 0.0, 0.0],
        name="segmentation_multilevel",
        ome_version=ome_version,
    )

    result = get_normalized_scale(reference, dataset, dataset_level="s1")

    assert result["scale"] == [6.0, 6.0, 6.0]


def test_get_normalized_scale_no_matching_shape_raises(make_multiscale_group, reference, ome_version):
    dataset = make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0]],
        shapes=[(37, 37, 37)],
        translation=[0.0, 0.0, 0.0],
        name="segmentation_no_match",
        ome_version=ome_version,
    )

    with pytest.raises(ValueError):
        get_normalized_scale(reference, dataset)


def test_get_normalized_scale_unknown_dataset_level_raises(make_multiscale_group, reference, ome_version):
    dataset = make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0]],
        shapes=[(100, 100, 100)],
        translation=[0.0, 0.0, 0.0],
        name="segmentation_unknown_level",
        ome_version=ome_version,
    )

    with pytest.raises(ValueError):
        get_normalized_scale(reference, dataset, dataset_level="s1")
