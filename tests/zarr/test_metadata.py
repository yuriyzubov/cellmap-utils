import pytest

from cellmap_utils.zarr.metadata import get_s0_level


def _corrupt_axes(group, ome_version):
    """Break schema validity (an extra, unexpected axis entry) while keeping
    datasets/coordinateTransformations intact, so a raw, unvalidated read can still
    recover scale and translation."""
    extra_axis = {"name": "c", "type": "channel"}
    if ome_version == "0.4":
        multiscales = group.attrs["multiscales"]
        multiscales[0]["axes"].append(extra_axis)
        group.attrs["multiscales"] = multiscales
    else:
        ome = group.attrs["ome"]
        ome["multiscales"][0]["axes"].append(extra_axis)
        group.attrs["ome"] = ome


def test_get_s0_level_strict_raises_on_malformed_metadata(make_multiscale_group, ome_version):
    group = make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0]],
        shapes=[(100, 100, 100)],
        translation=[10.0, 20.0, 30.0],
        name="malformed_strict",
        ome_version=ome_version,
    )
    _corrupt_axes(group, ome_version)

    with pytest.raises(RuntimeError):
        get_s0_level(group, strict=True)


def test_get_s0_level_lenient_still_returns_scale_and_translation(make_multiscale_group, ome_version):
    group = make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0]],
        shapes=[(100, 100, 100)],
        translation=[10.0, 20.0, 30.0],
        name="malformed_lenient",
        ome_version=ome_version,
    )
    _corrupt_axes(group, ome_version)

    scale, translation = get_s0_level(group, strict=False)

    assert scale == [6.0, 6.0, 6.0]
    assert translation == [10.0, 20.0, 30.0]


def test_get_s0_level_lenient_matches_strict_on_well_formed_metadata(make_multiscale_group, ome_version):
    group = make_multiscale_group(
        voxel_sizes=[[6.0, 6.0, 6.0]],
        shapes=[(100, 100, 100)],
        translation=[10.0, 20.0, 30.0],
        name="well_formed",
        ome_version=ome_version,
    )

    assert get_s0_level(group, strict=True) == get_s0_level(group, strict=False)
