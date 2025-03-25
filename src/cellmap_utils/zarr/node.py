import zarr
from cellmap_utils.zarr.store import separate_store_path
import os
from fsspec import filesystem
from upath import UPath
import sys
from fibsem_tools import read


def access_parent(node: zarr.Group | zarr.Array):
    """
    Get the parent (zarr.Group) of an input zarr array(ds).


    Args:
        node (zarr.core.Array or zarr.hierarchy.Group): _description_

    Raises:
        RuntimeError: returned if the node array is in the parent group,
        or the group itself is the root group

    Returns:
        zarr.hierarchy.Group : parent group that contains input group/array
    """

    store_path, node_path = separate_store_path(node.store.path, node.path)
    if node_path == "":
        raise RuntimeError(
            f"{node.name} is in the root group of the {node.store.path} store."
        )
    else:
        return zarr.open(store=store_path, path=os.path.split(node_path)[0], mode="a")


def get_file_system(path):
    p = UPath(path)
    return filesystem(p.protocol, **p.storage_options)


def repair_zarr_branch(input_zarr_path: str):
    """A recursive methond that adds missing .zgroup file in any parent zarr group
       between input zarr group and root of the zarr container.

    Args:
        input_zarr_path (str): _description_
    """
    try:
        zarr_path = input_zarr_path.rstrip("/ ")  # remove unnecessary '/' and ' '
        fs = get_file_system(zarr_path)
        fs.exists(zarr_path)
    except:
        sys.exit("Path not found!")

    z_store, z_path = zarr_path.split(".zarr")

    try:
        read(zarr_path)
    except:
        print("not found, added .zgroup to: ", zarr_path)
        with fs.open(UPath(os.path.join(zarr_path, ".zgroup")), mode="w") as f:
            f.write(str({"zarr_format": 2}).replace("'", '"'))

    if z_path.lstrip("/ ").rstrip("/ ") != "":
        repair_zarr_branch(
            os.path.join(f"{z_store}.zarr", os.path.split(z_path)[0].lstrip("/"))
        )
