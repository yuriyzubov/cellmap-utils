import zarr
from typing import Optional
from cellmap_utils.zarr.metadata import get_s0_level
from cellmap_utils.zarr.roi import recalibrate_offset

def is_valid_ome(zg : zarr.Group, version : Optional[str] = None) -> bool:
    """Check whether a zarr group's OME-NGFF metadata validates, without raising.

    Supports both OME-NGFF 0.4 (Zarr v2 stores) and OME-NGFF 0.5 (Zarr v3 stores).
    Requires the optional 'zarr3' extra (ome-zarr-models).

    Args:
        zg (zarr.Group): the zarr group to check.
        version (str, optional): restrict the check to a specific OME-NGFF version
            ('0.4', '0.5', or '0.6'). Defaults to None, which tries every version.

    Returns:
        bool: True if the metadata validates against a known OME-NGFF model, False otherwise.
    """
    from ome_zarr_models import open_ome_zarr

    try:
        open_ome_zarr(zg, version=version)
        return True
    except RuntimeError:
        return False

def validate_ome(zg : zarr.Group):
    """Validate that a zarr group has well-formed OME-NGFF multiscale metadata.

    Supports both OME-NGFF 0.4 (Zarr v2 stores) and OME-NGFF 0.5 (Zarr v3 stores).
    Requires the optional 'zarr3' extra (ome-zarr-models). Raises if the metadata
    does not validate against any known OME-NGFF version. Use `is_valid_ome()`
    instead if you want a boolean result rather than an exception.

    Args:
        zg (zarr.Group): the input zarr group to validate.
    """
    from ome_zarr_models import open_ome_zarr

    open_ome_zarr(zg)
    
def validate_roi_offset(dataset : zarr.Group, roi : zarr.Group):
    
    validate_ome(dataset)
    validate_ome(roi)
    
    ds_scale, ds_offset = get_s0_level(dataset)
    roi_scale, roi_offset = get_s0_level(roi)
    correct_roi_s0_params = recalibrate_offset(roi, ds_scale)
    
    
    if not [round(tr,2) for tr in roi_offset]==correct_roi_s0_params['translation']:#all(list(map(float.is_integer, offset_unitless))):
        
        raise ValueError(f"""Offsets are not divisible by scales.\n
                         Incorrect translation: {roi_offset} \n
                         The correct translation for the roi (s0 level) to align with voxel grid: {correct_roi_s0_params['translation']}""")