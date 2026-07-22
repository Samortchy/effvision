from datetime import datetime
from sqlalchemy import DateTime, FetchedValue, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # Schema uses TEXT and TIMESTAMPTZ throughout; SQLAlchemy's defaults for
    # `str`/`datetime` would be VARCHAR and TIMESTAMP WITHOUT TIME ZONE.
    type_annotation_map = {
        str: Text,
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )

    # Maintained by the set_updated_at() trigger, not by the ORM.
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), server_onupdate=FetchedValue(), nullable=False
    )


class CreatedAtMixin:
    """Mixin for tables with only created_at (no updated_at trigger)."""
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
