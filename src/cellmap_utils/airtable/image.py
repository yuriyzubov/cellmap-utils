from typing import Tuple
from pyairtable import api
from pyairtable.formulas import match
from fibsem_tools import read
import os
import zarr

# upsert image record
from typing import Literal
def upsert_image( image_table : api.table.Table,
                 ds_name : str,
                 image_name : str,
                 image_path : str,
                 image_type : Literal['human_segmentation', 'em'],
                 collection_table : api.table.Table,
                 fibsem_table : api.table.Table,
                 annotation_table : api.table.Table
                 ):
    
    existing_records = image_table.all(formula = match({'name' : image_name, 'location' : image_path.rstrip('/')}))
    
    if image_type == 'human_segmentation':
            value_type = 'label'
    else: 
        value_type = 'scalar'
    
    input_zarr = read(image_path.rstrip('/'))
    if isinstance(input_zarr, zarr.Group):
        zg = input_zarr
        z_arr_name = 's0'
    else:
        zg_path, z_arr_name = os.path.split(image_path.rstrip('/'))
        zg = read(zg_path)    
        
    
    scale = zg.attrs['multiscales'][0]['datasets'][0]['coordinateTransformations'][0]['scale']
    offset = zg.attrs['multiscales'][0]['datasets'][0]['coordinateTransformations'][1]['translation']
    shape  = zg[z_arr_name].shape
    
    try:
        fibsem_imaging = [fibsem_table.all(formula = match({'name' : ds_name}))[0]['id']]
    except:
        fibsem_imaging = []
     
    try:   
        annotation = [annotation_table.all(formula = match({'name' : image_name}))[0]['id']]
    except:
        annotation = []
    
    record_to_upsert = {    'name' : image_name,
                            'collection' : [collection_table.all(formula = match({'id' : ds_name}))[0]['id']],
                            'location' : image_path.rstrip('/'),
                            'format' : 'zarr',
                            'image_type' : image_type,
                            'value_type' : value_type,
                            'size_x_pix' : shape[2],
                            'size_y_pix' : shape[1],
                            'size_z_pix' : shape[0],
                            'resolution_x_nm' : scale[2],
                            'resolution_y_nm' : scale[1],
                            'resolution_z_nm' : scale[0],
                            'offset_x_nm' : offset[2],
                            'offset_y_nm' : offset[1],
                            'offset_z_nm' : offset[0],
                            'fibsem_imaging' : fibsem_imaging,
                            'annotation' : annotation
                            }
    
    
    if len(existing_records) > 2:
        raise ValueError('Multiple records with matching input image name found')
    
    if not existing_records:
        image_table.create(record_to_upsert)
    elif len(existing_records) == 1:
        image_table.update(existing_records[0]['id'], record_to_upsert)
        
        
