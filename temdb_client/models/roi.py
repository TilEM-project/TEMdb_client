from typing import Dict, Optional, Union, List, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ROIBase(BaseModel):
    aperture_width_height: Optional[List[float]] = None
    aperture_centroid: Optional[List[float]] = None
    aperture_bounding_box: Optional[List[float]] = None
    aperture_image: Optional[str] = None
    optical_pixel_size: Optional[float] = None
    scale_y: Optional[float] = None
    barcode: Optional[Union[int, str]] = None
    rois: Optional[List[Any]] = None
    bucket: Optional[str] = None
    roi_mask: Optional[str] = None
    roi_mask_bucket: Optional[str] = None
    corners: Optional[Dict[str, Any]] = None
    corners_perpendicular: Optional[Dict[str, Any]] = None
    rule: Optional[str] = None
    edits: Optional[List[Any]] = None
    auto_roi: Optional[bool] = None
    roi_parameters: Optional[Dict[str, Any]] = None
    vertices: Optional[List] = None
    section_id: Optional[str] = None
    specimen_id: Optional[str] = None
    block_id: Optional[str] = None
    substrate_media_id: Optional[str] = None
    section_number: Optional[int] = None
    parent_roi_id: Optional[str] = None 
    cutting_session_id: Optional[str] = None
    roi_id: Optional[str] = None
    hierarchy_level: Optional[int] = None
    roi_number: Optional[int] = None

    class Config:
        extra = "allow"


class ROICreate(ROIBase):
    roi_number: int = Field(
        ..., description="Sequential number for this ROI within its parent context"
    )
    section_id: str = Field(...)
    specimen_id: str = Field(...)
    block_id: str = Field(...)
    substrate_media_id: str = Field(
        ..., description="Media ID of the substrate this section is placed on"
    )


class ROIUpdate(ROIBase):
    pass


class ROIResponse(ROIBase):
    roi_id: str = Field(..., description="Hierarchical ID of ROI")
    section_id: str = Field(...)
    cutting_session_id: str = Field(...)
    block_id: str = Field(...)
    specimen_id: str = Field(...)
    substrate_media_id: str = Field(..., description="Media ID of the substrate")
    hierarchy_level: int = Field(..., description="Depth level in ROI hierarchy")
    is_parent: bool = Field(
        default=False, description="Whether this ROI has child ROIs"
    )

    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ROIChildrenResponse(BaseModel):
    children: List[ROIResponse]
