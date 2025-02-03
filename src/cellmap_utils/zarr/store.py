import os


def separate_store_path(store, path):
    """
    sometimes you can pass a total os path to node, leading to
    an empty('') node.path attribute.
    the correct way is to separate path to container(.n5, .zarr)
    from path to array within a container.

    Args:
        store (string): path to store
        path (string): path array/group (.n5 or .zarr)

    Returns:
        (string, string): returns regularized store and group/array path
    """
    new_store, path_prefix = os.path.split(store)
    if ".zarr" in path_prefix:
        return store, path
    return separate_store_path(new_store, os.path.join(path_prefix, path))