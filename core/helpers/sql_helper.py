def filter_valid_update_clauses(data: dict, id: int) -> tuple[str, dict]:
    """Filter valid update clauses"""
    set_clause = ", ".join(f"{col} = :{col}" for col in data)
    params = {**data, "id": id}
    return set_clause, params


def filter_valid_insert_clauses(data: dict) -> tuple[str, dict]:
    """Filter valid insert clauses"""
    columns = ", ".join(data.keys())
    placeholders = ", ".join(f":{col}" for col in data)
    return columns, placeholders
