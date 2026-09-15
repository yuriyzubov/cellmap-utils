import pytest
import zarr

AXES = "zyx"


@pytest.fixture(params=["0.4", "0.5"])
def ome_version(request):
    return request.param


@pytest.fixture
def make_multiscale_group(tmp_path):
    """Factory fixture that builds a disk-backed OME-NGFF multiscale zarr group.

    ome_zarr_models validates against real, disk-backed stores; an in-memory
    zarr.group() is not reliably discoverable by open_ome_zarr().
    """

    def _make(voxel_sizes, shapes, translation, name="test", ome_version="0.4"):
        """Build a disk-backed OME-NGFF multiscale zarr group for testing.

        Args:
            voxel_sizes (list[list[float]]): one voxel size (scale) per pyramid level.
            shapes (list[tuple[int, int, int]]): one array shape per pyramid level.
            translation (list[float]): translation (offset), shared by all levels.
            name (str, optional): name of the multiscale set. Defaults to "test".
            ome_version (str, optional): "0.4" (Zarr v2 store) or "0.5" (Zarr v3 store,
                metadata nested under "ome"). Defaults to "0.4".
        """
        zarr_format = 2 if ome_version == "0.4" else 3
        store_path = tmp_path / f"{name}_{ome_version}_{len(shapes)}.zarr"
        group = zarr.open_group(str(store_path), mode="w", zarr_format=zarr_format)

        datasets = []
        for level, (voxel_size, shape) in enumerate(zip(voxel_sizes, shapes)):
            path = f"s{level}"
            if ome_version == "0.4":
                group.create_array(path, shape=shape, dtype="uint8")
            else:
                # OME-NGFF 0.5 (Zarr v3) requires dimension_names matching the axes.
                group.create_array(path, shape=shape, dtype="uint8", dimension_names=list(AXES))
            datasets.append(
                {
                    "coordinateTransformations": [
                        {"type": "scale", "scale": [float(v) for v in voxel_size]},
                        {"type": "translation", "translation": [float(t) for t in translation]},
                    ],
                    "path": path,
                }
            )

        multiscales = [
            {
                "axes": [{"name": axis, "type": "space", "unit": "nanometer"} for axis in AXES],
                "coordinateTransformations": [{"scale": [1.0, 1.0, 1.0], "type": "scale"}],
                "datasets": datasets,
                "name": name,
            }
        ]
        if ome_version == "0.4":
            multiscales[0]["version"] = "0.4"
            group.attrs["multiscales"] = multiscales
        else:
            group.attrs["ome"] = {"version": "0.5", "multiscales": multiscales}

        # re-open read/write, so tests can still tweak attrs afterwards if needed
        return zarr.open_group(str(store_path), mode="a")

    return _make
