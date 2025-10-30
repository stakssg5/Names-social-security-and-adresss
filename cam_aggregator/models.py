from __future__ import annotations

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Text
from sqlalchemy.orm import relationship

from .db import Base


class Agency(Base):
    __tablename__ = "agencies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)

    cameras = relationship("Camera", back_populates="agency", cascade="all,delete-orphan")


class Camera(Base):
    __tablename__ = "cameras"
    __table_args__ = (
        UniqueConstraint("name", "agency_id", name="uq_camera_name_agency"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True, index=True)
    stream_url = Column(Text, nullable=False)
    stream_type = Column(String(32), nullable=False, default="hls")  # hls|mjpeg|image|iframe|other

    agency_id = Column(Integer, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    agency = relationship("Agency", back_populates="cameras")
