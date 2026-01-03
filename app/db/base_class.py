# app/db/base_class.py
from typing import Any
from sqlalchemy.ext.declarative import as_declarative, declared_attr

@as_declarative()
class Base:
    id: Any
    __name__: str
    
    # 自動將 class name 轉為小寫作為 table name
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()