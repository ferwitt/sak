# -*- coding: UTF-8 -*-

__author__ = "Fernando Witt"
__credits__ = ["Fernando Witt"]

__license__ = "MIT"
__maintainer__ = "Fernando Witt"
__email__ = "ferawitt@gmail.com"

import enum
from typing import Any, Dict

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import declarative_base, mapped_column

Base = declarative_base()

TABLES: Dict[str, Any] = {}


class SakTaskStatus(enum.Enum):
    PENDING = 1
    ABORTED = 2
    FAIL = 3
    SUCCESS = 4


SAK_TASK_DB = "sak_tasks"


class SakTaskDb(Base):  # type: ignore
    __tablename__ = SAK_TASK_DB
    __table_args__ = {"extend_existing": True}

    last_changed = mapped_column(String, index=True)

    key_hash = mapped_column(String(256), primary_key=True)
    namespace = mapped_column(String(64), index=True)

    status = mapped_column(Enum(SakTaskStatus), index=True)
    start_time = mapped_column(DateTime, index=True)
    end_time = mapped_column(DateTime, index=True)

    metadata_hash = mapped_column(String, index=False)


TABLES[SAK_TASK_DB] = SakTaskDb
