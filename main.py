
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Base, engine, get_db
from models import Product, Cart, CartItem, Order, OrderItem, Payment
from schemas import (
    ProductCreate, ProductUpdate, ProductOut,
    CartItemAdd, CartItemUpdate,
    OrderCreate, OrderOut, OrderStatusUpdate,
    PaymentCreate, PaymentOut
)
from crud import get_product_or_404, get_or_create_cart


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="E-Commerce Order Processing API",
    description="Product, cart, order, stock, payment and sales management API",
    version="1.0.0"
)


# PRODUCT MANAGEMENT

@app.post("/products", response_model=ProductOut, status_code=201, tags=["Products"])
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@app.get("/products", response_model=list[ProductOut], tags=["Products"])
def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    return db.query(Product).order_by(Product.id).offset(skip).limit(limit).all()


@app.get("/products/{product_id}", response_model=ProductOut, tags=["Products"])
def get_product(product_id: int, db: Session = Depends(get_db)):
    return get_product_or_404(db, product_id)

@app.get("/products/{product_id}/stock", tags=["Products"])
def check_product_stock(
    product_id: int,
    db: Session = Depends(get_db)
):
    product = get_product_or_404(db, product_id)

    return {
        "product_id": product.id,
        "product_name": product.name,
        "available_stock": product.stock_quantity,
        "in_stock": product.stock_quantity > 0
    }



@app.put("/products/{product_id}", response_model=ProductOut, tags=["Products"])
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db)
):
    product = get_product_or_404(db, product_id)
    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@app.delete("/products/{product_id}", tags=["Products"])
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = get_product_or_404(db, product_id)

    if db.query(CartItem).filter(CartItem.product_id == product_id).first():
        raise HTTPException(
            status_code=409,
            detail="Remove this product from carts before deleting it"
        )

    if db.query(OrderItem).filter(OrderItem.product_id == product_id).first():
        raise HTTPException(
            status_code=409,
            detail="Product has order history and cannot be deleted"
        )

    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}


# CART MANAGEMENT

def format_cart(cart, user_id):
    items = []
    total = 0.0

    for item in cart.items:
        subtotal = round(item.quantity * item.product.price, 2)
        total += subtotal
        items.append({
            "product_id": item.product.id,
            "product_name": item.product.name,
            "price": item.product.price,
            "quantity": item.quantity,
            "available_stock": item.product.stock_quantity,
            "subtotal": subtotal
        })

    return {
        "cart_id": cart.id,
        "user_id": user_id,
        "items": items,
        "total_amount": round(total, 2)
    }


@app.post("/cart/{user_id}/items", status_code=201, tags=["Cart"])
def add_to_cart(
    user_id: int,
    data: CartItemAdd,
    db: Session = Depends(get_db)
):
    if user_id <= 0:
        raise HTTPException(status_code=422, detail="user_id must be positive")

    product = get_product_or_404(db, data.product_id)

    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()

    item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product.id
    ).first()

    new_quantity = data.quantity + (item.quantity if item else 0)

    if new_quantity > product.stock_quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Only {product.stock_quantity} units are available"
        )

    if item:
        item.quantity = new_quantity
    else:
        db.add(CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=data.quantity
        ))

    db.commit()
    db.refresh(cart)
    return format_cart(cart, user_id)


@app.get("/cart/{user_id}", tags=["Cart"])
def view_cart(user_id: int, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()

    if cart is None:
        return {
            "cart_id": None,
            "user_id": user_id,
            "items": [],
            "total_amount": 0.0
        }

    return format_cart(cart, user_id)


@app.put("/cart/{user_id}/items/{product_id}", tags=["Cart"])
def update_cart_quantity(
    user_id: int,
    product_id: int,
    data: CartItemUpdate,
    db: Session = Depends(get_db)
):
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product_id
    ).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    product = get_product_or_404(db, product_id)

    if data.quantity > product.stock_quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Only {product.stock_quantity} units are available"
        )

    item.quantity = data.quantity
    db.commit()
    db.refresh(cart)
    return format_cart(cart, user_id)


@app.delete("/cart/{user_id}/items/{product_id}", tags=["Cart"])
def remove_cart_item(
    user_id: int,
    product_id: int,
    db: Session = Depends(get_db)
):
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    item = db.query(CartItem).filter(
        CartItem.cart_id == cart.id,
        CartItem.product_id == product_id
    ).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    db.delete(item)
    db.commit()
    db.refresh(cart)
    return format_cart(cart, user_id)


@app.delete("/cart/{user_id}", tags=["Cart"])
def clear_cart(user_id: int, db: Session = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.user_id == user_id).first()

    if cart is None:
        return {"message": "Cart is already empty"}

    for item in list(cart.items):
        db.delete(item)

    db.commit()
    return {"message": "Cart cleared successfully", "user_id": user_id}


# ORDER CREATION AND HISTORY

@app.post("/orders", response_model=OrderOut, status_code=201, tags=["Orders"])
def create_order(data: OrderCreate, db: Session = Depends(get_db)):
    try:
        cart = db.query(Cart).filter(
            Cart.user_id == data.user_id
        ).first()

        if cart is None or not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        cart_items = list(cart.items)
        total = 0.0

        for item in cart_items:
            product = get_product_or_404(db, item.product_id)

            if item.quantity > product.stock_quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {product.name}"
                )

            total += product.price * item.quantity

        order = Order(
            user_id=data.user_id,
            total_amount=round(total, 2),
            status="Pending"
        )
        db.add(order)
        db.flush()

        for item in cart_items:
            product = get_product_or_404(db, item.product_id)
            subtotal = round(product.price * item.quantity, 2)

            order.items.append(OrderItem(
                product_id=product.id,
                product_name=product.name,
                quantity=item.quantity,
                price_at_purchase=product.price,
                subtotal=subtotal
            ))

            product.stock_quantity -= item.quantity
            db.delete(item)

        db.commit()
        db.refresh(order)
        return order

    except Exception:
        db.rollback()
        raise


@app.get("/orders/my-orders", response_model=list[OrderOut], tags=["Orders"])
def get_my_orders(user_id: int = Query(..., gt=0), db: Session = Depends(get_db)):
    return db.query(Order).filter(
        Order.user_id == user_id
    ).order_by(Order.created_at.desc()).all()


@app.get("/orders", tags=["Orders"])
def search_orders(
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    user_id: Optional[int] = Query(None, gt=0),
    db: Session = Depends(get_db)
):
    allowed_statuses = {"Pending", "Confirmed", "Shipped", "Delivered", "Cancelled"}
    allowed_payments = {"Pending", "Successful", "Failed"}

    if status is not None and status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid order status")

    if payment_status is not None and payment_status not in allowed_payments:
        raise HTTPException(status_code=400, detail="Invalid payment status")

    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be before date_to")

    if min_amount is not None and max_amount is not None and min_amount > max_amount:
        raise HTTPException(status_code=400, detail="min_amount cannot exceed max_amount")

    query = db.query(Order)

    if payment_status is not None:
        query = query.join(Payment, Order.id == Payment.order_id)
        query = query.filter(Payment.payment_status == payment_status)

    if status is not None:
        query = query.filter(Order.status == status)
    if user_id is not None:
        query = query.filter(Order.user_id == user_id)
    if date_from is not None:
        query = query.filter(Order.created_at >= date_from)
    if date_to is not None:
        query = query.filter(Order.created_at <= date_to)
    if min_amount is not None:
        query = query.filter(Order.total_amount >= min_amount)
    if max_amount is not None:
        query = query.filter(Order.total_amount <= max_amount)

    orders = query.order_by(Order.created_at.desc()).all()

    return [
        {
            "id": order.id,
            "user_id": order.user_id,
            "created_at": order.created_at,
            "total_amount": order.total_amount,
            "status": order.status,
            "payment_status": (
                order.payment.payment_status if order.payment else "Not Paid"
            )
        }
        for order in orders
    ]


@app.get("/orders/{order_id}", response_model=OrderOut, tags=["Orders"])
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


# ORDER STATUS WORKFLOW AND STOCK RESTORATION

ALLOWED_TRANSITIONS = {
    "Pending": {"Confirmed", "Cancelled"},
    "Confirmed": {"Shipped", "Cancelled"},
    "Shipped": {"Delivered"},
    "Delivered": set(),
    "Cancelled": set()
}


@app.put("/orders/{order_id}/status", response_model=OrderOut, tags=["Orders"])
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db)
):
    try:
        order = db.query(Order).filter(Order.id == order_id).first()

        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")

        if data.status not in ALLOWED_TRANSITIONS[order.status]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot change order status from {order.status} to {data.status}"
            )

        if data.status == "Cancelled":
            for item in order.items:
                product = db.query(Product).filter(
                    Product.id == item.product_id
                ).first()

                if product is not None:
                    product.stock_quantity += item.quantity

        order.status = data.status
        db.commit()
        db.refresh(order)
        return order

    except Exception:
        db.rollback()
        raise


# PAYMENT SIMULATION

@app.post(
    "/orders/{order_id}/payment",
    response_model=PaymentOut,
    status_code=201,
    tags=["Payments"]
)
def process_payment(
    order_id: int,
    data: PaymentCreate,
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "Cancelled":
        raise HTTPException(
            status_code=400,
            detail="Payment is not allowed for a cancelled order"
        )

    payment = db.query(Payment).filter(
        Payment.order_id == order_id
    ).first()

    if payment is None:
        payment = Payment(
            order_id=order.id,
            amount=order.total_amount,
            payment_method=data.payment_method,
            payment_status=data.payment_status,
            payment_date=datetime.utcnow()
        )
        db.add(payment)
    else:
        payment.amount = order.total_amount
        payment.payment_method = data.payment_method
        payment.payment_status = data.payment_status
        payment.payment_date = datetime.utcnow()

    db.commit()
    db.refresh(payment)
    return payment


# SALES REPORT

@app.get("/reports/sales", tags=["Reports"])
def sales_report(db: Session = Depends(get_db)):
    total_orders = db.query(func.count(Order.id)).scalar() or 0

    total_cancelled = db.query(func.count(Order.id)).filter(
        Order.status == "Cancelled"
    ).scalar() or 0

    total_sales = db.query(
        func.coalesce(func.sum(Order.total_amount), 0.0)
    ).filter(Order.status != "Cancelled").scalar()

    successful_payments = db.query(func.count(Payment.id)).filter(
        Payment.payment_status == "Successful"
    ).scalar() or 0

    best_seller = (
        db.query(
            OrderItem.product_id,
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("units_sold")
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status != "Cancelled")
        .group_by(OrderItem.product_id, OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .first()
    )

    total_products_sold = (
        db.query(func.coalesce(func.sum(OrderItem.quantity), 0))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.status != "Cancelled")
        .scalar()
    )

    return {
        "total_orders": total_orders,
        "total_sales_amount": round(float(total_sales or 0), 2),
        "total_cancelled_orders": total_cancelled,
        "total_successful_payments": successful_payments,
        "best_selling_product": (
            {
                "product_id": best_seller.product_id,
                "product_name": best_seller.product_name,
                "units_sold": int(best_seller.units_sold)
            }
            if best_seller else None
        ),
        "total_products_sold": int(total_products_sold or 0)
    }


@app.get("/", tags=["General"])
def home():
    return {"message": "E-Commerce Order Processing API is running"}
