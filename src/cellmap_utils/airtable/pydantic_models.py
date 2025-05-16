from pydantic import BaseModel
from typing import Dict, Any


def generate_pydantic_model(data: Dict[str, Any], model_name: str ) -> type[BaseModel]:
    """
    Generates a Pydantic model class dynamically from a dictionary.

    Args:
        data: A dictionary representing the structure of the model.
        model_name: The name of the generated Pydantic model class.

    Returns:
        A Pydantic model class.
    """

    fields = {}
    for key, value in data.items():
        fields[key] = (type(value), ...)

    model_class = type(model_name, (BaseModel,), fields)
    return model_class

