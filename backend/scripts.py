from main import app
from factory import db
from models.menu_item import MenuItem
from models.restaurant import Restaurant
from models.order import Order

RESTAURANT_OWNER_ID = 4

menus = [
    {
        "title": "Entradas",
        "name": "Bruschetta",
        "description": "Pão italiano com tomate, manjericão e parmesão.",
        "price": 18.90,
    },
    {
        "title": "Entradas",
        "name": "Batata Frita",
        "description": "Batatas crocantes com molho especial.",
        "price": 16.00,
    },
    {
        "title": "Hambúrgueres",
        "name": "Cheeseburger",
        "description": "Pão brioche, carne 180g, queijo cheddar e molho da casa.",
        "price": 34.90,
    },
    {
        "title": "Hambúrgueres",
        "name": "Bacon Burger",
        "description": "Carne 180g, bacon crocante, cheddar e cebola caramelizada.",
        "price": 39.90,
    },
    {
        "title": "Pizzas",
        "name": "Margherita",
        "description": "Molho de tomate, mussarela, tomate e manjericão.",
        "price": 52.00,
    },
    {
        "title": "Bebidas",
        "name": "Refrigerante",
        "description": "Lata 350ml.",
        "price": 7.00,
    },
    {
        "title": "Bebidas",
        "name": "Suco Natural",
        "description": "Laranja, limão ou abacaxi.",
        "price": 10.00,
    },
    {
        "title": "Sobremesas",
        "name": "Brownie",
        "description": "Brownie com sorvete de creme.",
        "price": 19.90,
    },
]

with app.app_context():
    orders = [
        Order(
            customer_id=1,
            owner_id=1,
            restaurant_id=1,
            menu_item_id=2,
            quantity=2,
            unit_price=16.00,
            total_price=32.00
        ),
        Order(
            customer_id=1,
            owner_id=1,
            restaurant_id=1,
            menu_item_id=3,
            quantity=1,
            unit_price=34.90,
            total_price=34.90
        ),
    ]

    db.session.add_all(orders)
    db.session.commit()

    print("Pedidos criados com sucessos!")