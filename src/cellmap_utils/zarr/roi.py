import zarr
from typing import Tuple
import ngff_zarr as nz
from cellmap_utils.zarr.metadata import get_s0_level
    
    
def get_matching_scale(dataset : zarr.Group,
                       roi : zarr.Group) -> Tuple[list[float], list[float]]:
    
    
    nz.validate(ngff_dict = dict(roi.attrs), version='0.4', model='image', strict=False)
    nz.validate(ngff_dict = dict(dataset.attrs), version='0.4', model='image', strict=False)
    s0_ds = dataset.attrs['multiscales'][0]['datasets'][0]['coordinateTransformations']
    
    for level in roi.attrs['multiscales'][0]['datasets']:
        scale = level['coordinateTransformations'][0]['scale']
        if scale==s0_ds[0]['scale']:
            offset = level['coordinateTransformations'][1]['translation']
            return (scale, offset)
    raise ValueError("Could not find ROI scale values that matches with s0 level of the dataset")


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

    