from pydantic import BaseModel

class SupaImageModel(BaseModel):
    source : dict | None
    name : str
    url : str
    description : str
    format : str
    display_settings : dict
    sample_type : str
    content_type : str
    dataset_name : str
    institution : str
    grid_dims : list[str]
    grid_scale : list[float]
    grid_translation : list[float]
    grid_units : list[str]
    grid_index_order : str
    stage : str
    image_stack : str
    doi : dict | None
class SupaImageAcquisitionModel(BaseModel):
    name : str
    institution : str
    start_date : str
    grid_axes: list[str]
    grid_spacing : list[float]
    grid_spacing_unit : str
    grid_dimensions : list[int]
    grid_dimensions_unit : str
class SupaSampleModel(BaseModel):
    name : str
    description : str
    protocol : str
    contributions : str
    subtype : list[str]  
    type : list[str]
class SupaDatasetModel(BaseModel):
    name : str
    description : str
    thumbnail_url : str
    stage : str
    publicaton : list[str]
    
class SupaPublicatioModel(BaseModel):
    doi : str