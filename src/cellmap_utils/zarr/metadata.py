import zarr
import os
import numpy
from cellmap_utils.zarr.store import separate_store_path
from cellmap_utils.zarr.node import access_parent
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

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


def round_decimals(group : zarr.Group, decimals : int):
    """Round scale and translation metadata

    Args:
        group (zarr.Group): zarr group with ome-zarr metadata
        decimals (int): number of decimals to round
    """
    z_attrs = dict()
    z_attrs['multiscales'] = group.attrs['multiscales']

    # multiscale levels
    ms_levels = z_attrs['multiscales'][0]['datasets']
    for level in ms_levels:
        scale = level['coordinateTransformations'][0]['scale']
        translation = level['coordinateTransformations'][1]['translation']
        level['coordinateTransformations'][0]['scale'] = [round(sc, decimals) for sc in scale]
        level['coordinateTransformations'][1]['translation'] = [round(tr, decimals) for tr in translation]
    group.attrs['multiscales'] = z_attrs['multiscales']

def _read_multiscale_datasets(zg: zarr.Group):
    """Read and validate OME-NGFF multiscale dataset entries.

    Supports both OME-NGFF 0.4 (Zarr v2 stores) and OME-NGFF 0.5 (Zarr v3 stores,
    metadata nested under the "ome" key). Requires the optional 'zarr3' extra
    (ome-zarr-models).

    Args:
        zg (zarr.Group): zarr group with OME-NGFF multiscale metadata.

    Returns:
        A sequence of validated dataset entries, one per pyramid level. Each entry
        exposes a `.path` and a `.coordinateTransformations` attribute.
    """
    from ome_zarr_models import open_ome_zarr

    ome_group = open_ome_zarr(zg)
    multiscale_attrs = getattr(ome_group.attributes, "ome", ome_group.attributes)
    return multiscale_attrs.multiscales[0].datasets


def _read_multiscale_datasets_raw(zg: zarr.Group) -> list:
    """Best-effort read of multiscale dataset entries directly from zarr attrs, with no
    schema validation.

    Use this only as a fallback when `_read_multiscale_datasets` fails and some
    metadata is still preferable to an exception. It trusts the attrs to have the
    expected shape and does not check that the values it finds (scale, translation,
    units, etc.) are actually well-formed.

    Supports both the OME-NGFF 0.4 attrs layout (top-level "multiscales") and the
    0.5 layout ("ome" -> "multiscales").

    Args:
        zg (zarr.Group): zarr group to read.

    Returns:
        list: raw dataset entries (plain dicts), one per pyramid level.

    Raises:
        KeyError: if no recognizable "multiscales" structure is present at all.
    """
    attrs = dict(zg.attrs)
    multiscale_attrs = attrs.get("ome", attrs)
    return multiscale_attrs["multiscales"][0]["datasets"]


def _scale_and_translation(dataset) -> Tuple[list, list]:
    """Extract scale and translation from a multiscale dataset entry.

    Args:
        dataset: a dataset entry, either a validated object (from
            `_read_multiscale_datasets`) or a raw dict (from
            `_read_multiscale_datasets_raw`).

    Returns:
        Tuple[list, list]: (scale, translation)
    """
    if isinstance(dataset, dict):
        transforms = dataset["coordinateTransformations"]
        scale = next(t["scale"] for t in transforms if t["type"] == "scale")
        translation = next(t["translation"] for t in transforms if t["type"] == "translation")
        return scale, translation

    scale = next(t.scale for t in dataset.coordinateTransformations if t.type == "scale")
    translation = next(
        t.translation for t in dataset.coordinateTransformations if t.type == "translation"
    )
    return scale, translation


def get_s0_level(zg : zarr.Group, strict : bool = True) -> Tuple[list[float],list[float]]:
    """Read the base (s0) level's scale and translation.

    Supports both OME-NGFF 0.4 (Zarr v2 stores) and OME-NGFF 0.5 (Zarr v3 stores).
    Requires the optional 'zarr3' extra (ome-zarr-models).

    Args:
        zg (zarr.Group): zarr group with OME-NGFF multiscale metadata.
        strict (bool, optional): if True (default), require full OME-NGFF schema
            validation, and raise if it fails. If False, fall back to a best-effort,
            unvalidated read of the attrs when schema validation fails, instead of
            raising. Defaults to True.

    Returns:
        Tuple[list[float], list[float]]: (scale, translation) of the s0 level.
    """
    if strict:
        datasets = _read_multiscale_datasets(zg)
    else:
        try:
            datasets = _read_multiscale_datasets(zg)
        except RuntimeError:
            datasets = _read_multiscale_datasets_raw(zg)
    return _scale_and_translation(datasets[0])


def remove_checksum(path_to_arr: str):
    """Remove checksum parameter from zarr array metadata, to make it compatible with tensorstore.

    Args:
        path_to_arr (str): path to Zarr array
    """
    import json

    try:
        path_to_zarray = os.path.join(path_to_arr, '.zarray')
        with open(path_to_zarray, 'r+') as f:
            data = json.load(f)
            logger.info(f'old array metadata: {data}')
            try:
                del data['compressor']['checksum']
            except KeyError:
                logger.warning('No checksum found in compressor metadata')

        logger.info(f'new array metadata: {data}')
        with open(path_to_zarray, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=3)

        with open(path_to_zarray, 'r+') as f:
            data = json.load(f)

    except Exception as e:
        logger.error(f'FAILED to remove checksum in {path_to_zarray}: {e}')
        raise
