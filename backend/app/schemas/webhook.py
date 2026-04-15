"""Webhook schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class WebhookCreate(BaseModel):
    """Schema for creating a webhook."""

    name: str = Field(..., min_length=1, max_length=255)
    url: HttpUrl
    events: list[str] = Field(..., min_length=1)
    description: str | None = None


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook."""

    name: str | None = Field(None, min_length=1, max_length=255)
    url: HttpUrl | None = None
    events: list[str] | None = Field(None, min_length=1)
    is_active: bool | None = None
    description: str | None = None


class WebhookRead(BaseModel):
    """Schema for reading a webhook."""

    id: UUID
    name: str
    url: str
    events: list[str]
    is_active: bool
    description: str | None
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryRead(BaseModel):
    """Schema for reading a webhook delivery."""

    id: UUID
    webhook_id: UUID
    event_type: str
    response_status: int | None
    error_message: str | None
    attempt_count: int
    success: bool
    created_at: datetime
    delivered_at: datetime | None


class WebhookListResponse(BaseModel):
    """Response for list of webhooks."""

    items: list[WebhookRead]
    total: int


class WebhookDeliveryListResponse(BaseModel):
    """Response for list of webhook deliveries."""

    items: list[WebhookDeliveryRead]
    total: int


class WebhookTestResponse(BaseModel):
    """Response for webhook test."""

    success: bool
    status_code: int | None
    message: str


class WebhookSecretResponse(BaseModel):
    """Response for secret regeneration."""

    secret: str
