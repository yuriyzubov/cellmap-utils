import pytest

from cellmap_utils.zarr.roi import get_matching_scale


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
