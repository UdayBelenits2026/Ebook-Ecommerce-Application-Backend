from sqlalchemy import inspect
from typing import Any, Dict, List


def orm_to_dict(instance: Any) -> Dict[str, Any]:
    """Return a plain dict of column attributes for a SQLAlchemy ORM instance."""
    return {c.key: getattr(instance, c.key) for c in inspect(instance.__class__).mapper.column_attrs}


def orm_list_to_dicts(instances: List[Any]) -> List[Dict[str, Any]]:
    return [orm_to_dict(instance) for instance in instances]