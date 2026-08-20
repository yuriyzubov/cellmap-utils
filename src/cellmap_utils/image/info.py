import zarr
import numpy as np
from typing import Dict, Union


def get_contrast_values(arr: np.ndarray,
                        percentile_low: float = 1.0,
                        percentile_high: float = 99.0) -> Dict[str, float]:
    """
    Calculate contrast values (min, max, and percentiles) for a small numpy array.
    
    Args:
        arr: Input numpy array
        percentile_low: Lower percentile to calculate (default: 1.0)
        percentile_high: Upper percentile to calculate (default: 99.0)
        
    Returns:
        Dictionary containing:
        - percentile_low: Lower percentile value
        - percentile_high: Upper percentile value
        
    Raises:
        ValueError: If any dimension of the array is >= 256
    """
    # Check that each dimension is smaller than 256
    for i, dim_size in enumerate(arr.shape):
        if dim_size >= 256:
            raise ValueError(
                f"Array dimension {i} has size {dim_size} which is >= 256. "
                f"Please resample the input numpy array to have all dimensions < 256."
            )
    
    # Calculate actual min/max
    min_val = float(arr.min())
    max_val = float(arr.max())
    
    # Calculate specified percentiles
    p_low, p_high = np.percentile(arr, [percentile_low, percentile_high])
    
    return {
        'percentile_low': float(p_low),
        'percentile_high': float(p_high)
    }