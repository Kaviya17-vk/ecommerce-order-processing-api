
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    description: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    category: Optional[str] = Field(None, min_length=1, max_length=100)
    price: Optional[float] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    description: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    name: str
    category: str
    price: float
    stock_quantity: int
    description: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartItemAdd(BaseModel):
    product_id: int = Field(..., gt=0)
    quantity: int = Field(..., gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    user_id: int = Field(..., gt=0)


class OrderItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    price_at_purchase: float
    subtotal: float

    model_config = ConfigDict(from_attributes=True)


class PaymentOut(BaseModel):
    id: int
    order_id: int
    amount: float
    payment_method: str
    payment_status: str
    payment_date: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderOut(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: str
    created_at: datetime
    items: list[OrderItemOut]
    payment: Optional[PaymentOut] = None

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    status: Literal[
        "Pending",
        "Confirmed",
        "Shipped",
        "Delivered",
        "Cancelled"
    ]


class PaymentCreate(BaseModel):
    payment_method: Literal[
        "UPI",
        "Card",
        "Net Banking",
        "Cash on Delivery"
    ]
    payment_status: Literal[
        "Pending",
        "Successful",
        "Failed"
    ] = "Successful"
