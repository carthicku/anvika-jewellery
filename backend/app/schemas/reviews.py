"""Product review requests/responses. Only approved reviews are public."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Page, StrictIn

ReviewStatus = Literal["pending", "approved", "rejected"]


class ReviewOut(BaseModel):
    id: str
    rating: int
    title: str
    body: str
    author_name: str
    verified_purchase: bool
    created_at: datetime


class ReviewSummaryOut(BaseModel):
    count: int
    # One decimal place as a string ("4.5"); null when there are no approved reviews.
    average: str | None


class ProductReviewsOut(BaseModel):
    summary: ReviewSummaryOut
    reviews: Page[ReviewOut]


class MyReviewOut(BaseModel):
    rating: int
    title: str
    body: str
    status: ReviewStatus
    status_label: str
    updated_at: datetime


class MyReviewStateOut(BaseModel):
    can_review: bool
    review: MyReviewOut | None


class ReviewIn(StrictIn):
    rating: int = Field(ge=1, le=5)
    title: str = Field(min_length=3, max_length=120)
    body: str = Field(min_length=20, max_length=2000)


class AdminReviewOut(BaseModel):
    id: str
    product_name: str
    product_slug: str
    rating: int
    title: str
    body: str
    author_name: str
    customer_email: str
    verified_purchase: bool
    status: ReviewStatus
    moderation_note: str | None
    created_at: datetime
    updated_at: datetime


class ModerateReviewIn(StrictIn):
    decision: Literal["approve", "reject"]
    note: str = Field(default="", max_length=300)
