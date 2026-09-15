import zarr
import copy
import logging
from typing import Tuple
from cellmap_utils.zarr.metadata import get_s0_level, _read_multiscale_datasets, _scale_and_translation

logger = logging.getLogger(__name__)


def get_matching_scale(dataset : zarr.Group,
                       roi : zarr.Group) -> Tuple[list[float], list[float]]:
    """Find the roi pyramid level whose scale matches the dataset's s0 scale.

    Supports both OME-NGFF 0.4 (Zarr v2 stores) and OME-NGFF 0.5 (Zarr v3 stores).
    Requires the optional 'zarr3' extra (ome-zarr-models).

    Args:
        dataset (zarr.Group): dataset zarr group with a multiscale pyramid.
        roi (zarr.Group): roi zarr group with a multiscale pyramid.

    Returns:
        Tuple[list[float], list[float]]: (matching roi scale, matching roi translation)
    """
    ds_scale, _ = get_s0_level(dataset)

    for level in _read_multiscale_datasets(roi):
        scale, translation = _scale_and_translation(level)
        if scale == ds_scale:
            return (scale, translation)
    raise ValueError("Could not find ROI scale values that matches with s0 level of the dataset")


def get_normalized_scale(reference : zarr.Group,
                          dataset : zarr.Group,
                          dataset_level : str = 's0') -> dict:
    """Correct a dataset's voxel size to match the reference pyramid level that has the same array shape.

    This is useful when a dataset (for example, a segmentation) was labeled with the wrong
    voxel size, but its array shape matches one of the levels of a trusted reference multiscale
    image. The scale of the matching reference level is treated as the correct voxel size for the
    dataset. The dataset's translation (offset) is not changed, because translation already stores
    an absolute physical position in nanometers, and does not depend on the scale label.

    Supports both OME-NGFF 0.4 (Zarr v2 stores) and OME-NGFF 0.5 (Zarr v3 stores).
    Requires the optional 'zarr3' extra (ome-zarr-models).

    Args:
        reference (zarr.Group): reference zarr group with a multiscale pyramid.
        dataset (zarr.Group): dataset zarr group to normalize, for example a segmentation.
        dataset_level (str, optional): path of the dataset level to normalize. Defaults to 's0'.

    Returns:
        dict: {'scale': matched reference scale, 'translation': dataset's own translation, unchanged}
    """

    ds_levels = {level.path: level for level in _read_multiscale_datasets(dataset)}
    if dataset_level not in ds_levels:
        raise ValueError(f"Dataset does not have a level named '{dataset_level}'")
    _, ds_translation = _scale_and_translation(ds_levels[dataset_level])

    ds_shape = list(dataset[dataset_level].shape)

    for level in _read_multiscale_datasets(reference):
        ref_shape = list(reference[level.path].shape)
        if ref_shape == ds_shape:
            matched_scale, _ = _scale_and_translation(level)
            return {'scale': matched_scale, 'translation': ds_translation}

    raise ValueError(
        f"Could not find a reference level with shape matching dataset level '{dataset_level}' shape {ds_shape}"
    )


def apply_normalized_scale(
    dataset: zarr.Group,
    dataset_level: str,
    normalized: dict,
    dry_run: bool = True,
) -> list:
    """Write a corrected scale into a dataset's OME-NGFF metadata.

    Use this after get_normalized_scale() to save its result. Only the scale
    for dataset_level changes. The translation already in the dataset's
    metadata is not touched.

    Supports both OME-NGFF 0.4 (top-level "multiscales" attrs key) and
    OME-NGFF 0.5 ("ome" -> "multiscales" attrs key).

    Args:
        dataset (zarr.Group): dataset zarr group to update.
        dataset_level (str): path of the level to update. Example: 's0'.
        normalized (dict): output of get_normalized_scale(). Must have a
            'scale' key.
        dry_run (bool, optional): if True (default), compute the updated
            metadata but do not write it to the group's attrs.

    Returns:
        list: the full 'multiscales' metadata that was written, or that
            would have been written if dry_run is True.

    Raises:
        ValueError: if dataset_level is not present in the dataset's
            metadata.
    """
    attrs = dict(dataset.attrs)
    is_v05 = "ome" in attrs
    root = attrs["ome"] if is_v05 else attrs
    multiscales = copy.deepcopy(root["multiscales"])

    ms_levels = multiscales[0]["datasets"]
    level_entry = next((lvl for lvl in ms_levels if lvl["path"] == dataset_level), None)
    if level_entry is None:
        raise ValueError(f"Dataset does not have a level named '{dataset_level}'")

    scale_transform = next(
        t for t in level_entry["coordinateTransformations"] if t["type"] == "scale"
    )
    scale_transform["scale"] = list(normalized["scale"])

    if dry_run:
        logger.info(
            f"[dry_run] would set scale for level '{dataset_level}' of "
            f"{dataset.path} to {normalized['scale']}"
        )
    elif is_v05:
        new_ome = copy.deepcopy(attrs["ome"])
        new_ome["multiscales"] = multiscales
        dataset.attrs["ome"] = new_ome
    else:
        dataset.attrs["multiscales"] = multiscales

    return multiscales


def recalibrate_offset(roi: zarr.Group, grid_spacing : list[float]) -> Tuple[list[float], list[float]]:
    """The offset of the roi at multiscale level with scale=grid_spacing must be divisible by grid_spacing.
        This method would recalibrate offset, if roi grid does not align with grid {scale : grid_spacing, translation : [0.0, 0.0, 0.0]}  

    Args:
        roi (zarr.Group): roi zarr group with multiscale pyramid 
        grid_spacing (list[float]): grid spacing, with assumption that translation=[0.0, 0.0, 0.0]

    Returns:
        Tuple[list[float], list[float]]: returns (ROI s0 scale, recalibrated offset)
    """
    
    roi_scale, roi_offset = get_s0_level(roi)

    # calculate log2(roi s0 level/grid_spacing), for transforming it to the dataset 
    from math import log2
    roi_level = [log2(float(roi_sc)/float(ds_sc)) for roi_sc, ds_sc in zip(roi_scale, grid_spacing)] 
    
    # calculate roi translation as if it was rescaled to scale=grid_spacing
    roi_tr_at_grid_spacing = [
            tr_n - sc_n *(0.5 - pow(2, -(l_n+1)))
            for (sc_n, tr_n, l_n) in zip(roi_scale, roi_offset, roi_level)
        ]
    
    # shift roi offset to align with grid spacing  
    tr_roi_at_s0_correct = [round(float(tr)/float(sc))*sc for sc, tr in zip(grid_spacing, roi_tr_at_grid_spacing)]
    tr_roi_sn_correct = [
        round((sc * (pow(2, level - 1) - 0.5)) + tr, 2)
        for (sc, tr, level) in zip(grid_spacing, tr_roi_at_s0_correct, roi_level)
    ]
    
    return {'scale': roi_scale, 'translation' : tr_roi_sn_correct}

    