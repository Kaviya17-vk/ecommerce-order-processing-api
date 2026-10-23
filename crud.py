
from fastapi import HTTPException
from sqlalchemy.orm import Session

from models import Cart, Product


def get_product_or_404(db: Session, product_id: int):
    product = db.query(Product).filter(
        Product.id == product_id
    ).first()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


def get_or_create_cart(db: Session, user_id: int):
    cart = db.query(Cart).filter(
        Cart.user_id == user_id
    ).first()

    if cart is None:
        cart = Cart(user_id=user_id)
        db.add(cart)
        db.flush()

    return cart
