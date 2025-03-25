def filter_records(records, filter_field: str, filter_value: list[str] | str):
    """Custom method to filter records by a field value. all(formula=match({})) doesn't work when filtering by reference.

    Args:
        records (dict) : list of all records in a table. Not using table.all() within a method, since it slow to fetch all the records every time when a method is called.
        field (str): table field name
        field_value (list[str] | str): table field value

    Returns:
        list[dict]: return records with filter_value for filter_field field
    """

    matches = []
    for record in records:
        try:
            if isinstance(record["fields"][filter_field], list):
                cond = filter_value in record["fields"][filter_field]
            else:
                cond = record["fields"][filter_field] == filter_value
            if cond:
                matches.append(record)
        except:
            pass
    return matches
