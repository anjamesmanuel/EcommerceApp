from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
import models

# ✅ Create tables in ecommerce.db
Base.metadata.create_all(bind=engine)

app = FastAPI(title="E-commerce API")

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# GET API: All items / Item by ID
# ============================================================
@app.get("/items")
def get_items(db: Session = Depends(get_db)):
    return db.query(models.Product).all()

@app.get("/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(models.Product).filter(models.Product.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


# ============================================================
# GET API: All sales transactions (Orders)
# ============================================================
@app.get("/sales")
def get_sales(db: Session = Depends(get_db)):
    return db.query(models.PaymentOrder).all()


# ============================================================
# POST API: Add an order (purchase)
# ============================================================
@app.post("/orders")
def add_order(order: dict, db: Session = Depends(get_db)):
    new_order = models.PaymentOrder(
        user_id=order.get("user_id"),
        full_name=order["full_name"],
        email=order["email"],
        shipping_address=order["shipping_address"],
        amount_paid=order["amount_paid"]
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Add order items
    items = order.get("items", [])
    for item in items:
        order_item = models.OrderItem(
            order_id=new_order.id,
            product_id=item["product_id"],
            user_id=order.get("user_id"),
            quantity=item["quantity"],
            price=item["price"]
        )
        db.add(order_item)
    db.commit()

    return {"message": "Order created", "order_id": new_order.id}


# ============================================================
# PUT API: Update an order (quantity, status)
# ============================================================
@app.put("/orders/{order_id}")
def update_order(order_id: int, update_data: dict, db: Session = Depends(get_db)):
    order = db.query(models.PaymentOrder).filter(models.PaymentOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update status fields
    if "shipped" in update_data:
        order.shipped = update_data["shipped"]
    if "date_shipped" in update_data:
        order.date_shipped = update_data["date_shipped"]

    # Update quantities in OrderItem
    if "items" in update_data:
        for item in update_data["items"]:
            order_item = db.query(models.OrderItem).filter(
                models.OrderItem.order_id == order_id,
                models.OrderItem.product_id == item["product_id"]
            ).first()
            if order_item:
                order_item.quantity = item["quantity"]
                order_item.price = item["price"]

    db.commit()
    db.refresh(order)
    return {"message": "Order updated", "order": order}


# ============================================================
# DELETE API: Delete an order
# ============================================================
@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.PaymentOrder).filter(models.PaymentOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return {"message": "Order deleted successfully"}

# ============================================================
# SEED API: Insert sample orders + order items
# ============================================================
@app.post("/seed-orders")
def seed_orders(db: Session = Depends(get_db)):
    # 1. Find sample products
    laptop = db.query(models.Product).filter(models.Product.name == "Laptop").first()
    smartphone = db.query(models.Product).filter(models.Product.name == "Smartphone").first()
    headphones = db.query(models.Product).filter(models.Product.name == "Headphones").first()

    if not (laptop and smartphone and headphones):
        return {"error": "Please run /seed first to insert products"}

    # 2. Create a sample order
    order1 = models.PaymentOrder(
        user_id=1,   # assuming user_id 1 exists (or set to None if no auth yet)
        full_name="John Doe",
        email="john@example.com",
        shipping_address="123 Main St, Manila",
        amount_paid=77500,  # total of Laptop + Smartphone
        shipped=False
    )

    order2 = models.PaymentOrder(
        user_id=1,
        full_name="Jane Smith",
        email="jane@example.com",
        shipping_address="456 Elm St, Cebu",
        amount_paid=2500,   # just headphones
        shipped=True
    )

    db.add(order1)
    db.add(order2)
    db.commit()

    # 3. Add items to the orders
    order_item1 = models.OrderItem(
        order_id=order1.id,
        product_id=laptop.id,
        user_id=1,
        quantity=1,
        price=laptop.price
    )

    order_item2 = models.OrderItem(
        order_id=order1.id,
        product_id=smartphone.id,
        user_id=1,
        quantity=1,
        price=smartphone.price
    )

    order_item3 = models.OrderItem(
        order_id=order2.id,
        product_id=headphones.id,
        user_id=1,
        quantity=1,
        price=headphones.sale_price
    )

    db.add_all([order_item1, order_item2, order_item3])
    db.commit()

    return {"message": "Sample orders and order items seeded successfully"}
