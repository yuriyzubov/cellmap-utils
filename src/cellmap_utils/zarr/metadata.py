import zarr
import os
import numpy
from cellmap_utils.zarr.store import separate_store_path
from cellmap_utils.zarr.node import access_parent


def insert_omero_metadata(
    src: str,
    window_max: int = None,
    window_min: int = None,
    window_start: int = None,
    window_end: int = None,
    id: int = None,
    name: str = None,
):
    """
    Insert or update missing omero transitional metadata into .zattrs metadata of parent group for the input zarr array.


    Args:
        src (str): Path to Zarr array.
        window_max (int, optional): Max view window value. Defaults to None.
        window_min (int, optional): Min view window value. Defaults to None.
        window_start (int, optional): Contrast min value. Defaults to None.
        window_end (int, optional): Contrast max value. Defaults to None.
        id (int, optional): Defaults to None.
        name (str, optional): Name of the dataset. Defaults to None.
    """

    store_path, zarr_path = separate_store_path(src, "")

    z_store = zarr.NestedDirectoryStore(store_path)
    z_arr = zarr.open(store=z_store, path=zarr_path, mode="a")

    parent_group = access_parent(z_arr)

    if window_max == None:
        window_max = numpy.iinfo(z_arr.dtype).max
    if window_min == None:
        window_min = numpy.iinfo(z_arr.dtype).min

    omero = dict()
    omero["id"] = 1 if id == None else id
    omero["name"] = (
        os.path.basename(z_store.path.rstrip("/")).split(".")[0]
        if name == None
        else name
    )
    omero["version"] = "0.4"
    omero["channels"] = [
        {
            "active": True,
            "coefficient": 1,
            "color": "FFFFFF",
            "inverted": False,
            "label": parent_group.path.split("/")[-1],
            "window": {
                "end": window_max if window_end == None else window_end,
                "max": window_max,
                "min": window_min,
                "start": window_min if window_start == None else window_start,
            },
        }
    ]
    omero["rdefs"] = {
        "defaultT": 0,
        "defaultZ": int(z_arr.shape[0] / 2),
        "model": "greyscale",
    }
    parent_group.attrs["omero"] = omero


def get_single_scale_metadata(
    ds_name: str,
    voxel_size: list[float],
    translation: list[float],
    name: str,
    units: str = "nanometer",
    axes: list[str] = ["z", "y", "x"],
):
    """Returns multiscales ngff metadata with a single level.

    Args:
        ds_name (str): name of the dataset that contains the data.
        voxel_size (list[float]): scale. Example: [1.0, 1.0, 1.0]
        translation (list[float]): offset. Example: [0.0, 0.0, 0.0]
        name (str): Name of a multiscale set.
        units (str, optional): Physical units. Defaults to 'nanometer'.
        axes (list[str], optional): Axes labeling. Defaults to ['z', 'y', 'x'].

    Returns:
        _type_: _description_
    """
    z_attrs: dict = {"multiscales": [{}]}
    z_attrs["multiscales"][0]["axes"] = [
        {"name": axis, "type": "space", "unit": units} for axis in axes
    ]
    z_attrs["multiscales"][0]["coordinateTransformations"] = [
        {"scale": [1.0, 1.0, 1.0], "type": "scale"}
    ]
    z_attrs["multiscales"][0]["datasets"] = [
        {
            "coordinateTransformations": [
                {"scale": [float(item) for item in voxel_size], "type": "scale"},
                {"translation": translation, "type": "translation"},
            ],
            "path": ds_name,
        }
    ]

    z_attrs["multiscales"][0]["name"] = name
    z_attrs["multiscales"][0]["version"] = "0.4"

    return z_attrs


def get_multiscale_metadata(
    voxel_size: list[float],
    translation: list[float],
    levels: int,
    units: str = "nanometer",
    axes: list[str] = ["z", "y", "x"],
    name: str = "",
):
    """Generates a multiscale metadata from specified voxel size, offset and multi-scale pyramid levels.

    Args:
        voxel_size (list[float]): physical size of the voxel
        translation (list[float]): physical translation of the center of the voxel.
        levels (int): how many levels are present in the multis-scale pyramid.
        units (str, optional): Physical units. Defaults to 'nanometer'.
        axes (list[str], optional): Axis order. Defaults to ['z', 'y', 'x'].
        name (str, optional): Name of the dataset that would utilize multi-scale metadata. Defaults to ''.

    Returns:
        _type_: _description_
    """

    multsc = get_single_scale_metadata("s0", voxel_size, translation, name, units, axes)

    z_attrs = multsc
    base_scale = z_attrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][
        0
    ]["scale"]
    base_trans = z_attrs["multiscales"][0]["datasets"][0]["coordinateTransformations"][
        1
    ]["translation"]
    num_levels = levels
    for level in range(1, num_levels + 1):
        # print(f'{level=}')

        sn = [float(dim * pow(2, level)) for dim in base_scale]
        trn = [
            (dim * (pow(2, level - 1) - 0.5)) + tr
            for (dim, tr) in zip(base_scale, base_trans)
        ]

        z_attrs["multiscales"][0]["datasets"].append(
            {
                "coordinateTransformations": [
                    {"type": "scale", "scale": sn},
                    {"type": "translation", "translation": trn},
                ],
                "path": f"s{level}",
            }
        )

    return z_attrs


def ome_ngff_only(zg: zarr.Group):
    """Delete all attrs from .zattrs that are not part of the OME-NGFF Zarr spec and CellMap metadata.

    Args:
        zg (zarr.Group): zarr group that contains multiscale metadata.
    """
    to_keep = [
        "multiscales",
        "cellmap",
        "omero",
        "bioformats2raw.layout",
        "labels",
        "well",
        "plate",
    ]
    to_delete_attrs = [attr for attr in list(zg.attrs) if attr not in to_keep]

    for attr_name in to_delete_attrs:
        zg.attrs.__delitem__(attr_name)
