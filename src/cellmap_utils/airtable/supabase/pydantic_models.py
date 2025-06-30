from pydantic import BaseModel


class SupaImageModel(BaseModel):
    source: dict | None
    name: str
    url: str
    description: str
    format: str
    display_settings: dict
    sample_type: str
    content_type: str
    dataset_name: str
    institution: str
    grid_dims: list[str]
    grid_scale: list[float]
    grid_translation: list[float]
    grid_units: list[str]
    grid_index_order: str
    stage: str
    image_stack: str
    #doi: dict | None


class SupaImageAcquisitionModel(BaseModel):
    name: str
    institution: str
    start_date: str
    grid_axes: list[str]
    grid_spacing: list[float]
    grid_spacing_unit: str
    grid_dimensions: list[int]
    grid_dimensions_unit: str

class SupaSampleModel(BaseModel):
    name: str 
    description: str | None 
    protocol: str | None
    contributions: str | None
    organism : list[str] | None
    strain: list[str] | None
    subtype: list[str] | None
    type: list[str] | None
    institution: list[str] | None
    origin_species : list[str] | None
    treatment : list[str] | None
    
    @classmethod
    def from_airt_sample_record(cls, ds_name, institution, sample_record):
        fields = sample_record["fields"]
        return cls(
            name=ds_name,
            institution=institution,
            description=fields.get("description"),
            protocol=fields.get("protocol"),
            contributions=fields.get("contributions"),
            organism=fields.get("origin_species"),
            treatment=fields.get("treatment"),
            strain=fields.get("strain"),
            type=fields.get("type"),
            subtype=fields.get("subtype"),
            origin_species=fields.get("origin_species"),
        )

class SupaPublicationModel(BaseModel):
    url: str
    name : str
    pub_type: str

class SupaDatasetModel(BaseModel):
    name: str
    description: str
    thumbnail_url: str
    stage: str
    publications: list[SupaPublicationModel]