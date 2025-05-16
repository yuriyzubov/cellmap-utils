import zarr
import ngff_zarr as nz
from cellmap_utils.zarr.metadata import get_s0_level
from cellmap_utils.zarr.roi import recalibrate_offset

def validate_ome(zg : zarr.Group):
    """thin wrapper method for ngff_zarr.validate. 

    Args:
        zg (zarr.Group): the input zarr group with a json schema to validate.
    """
    nz.validate(ngff_dict = dict(zg.attrs), version='0.4', model='image', strict=False)
    
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