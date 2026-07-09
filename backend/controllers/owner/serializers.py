from .schemas import (
    MenuItemResponse,
    OwnerOrderCustomerResponse,
    OwnerOrderMenuItemResponse,
    OwnerOrderResponse,
    OwnerOrderRestaurantResponse,
    RestaurantResponse,
)


def restaurant_response(restaurant):
    return RestaurantResponse(
        id=restaurant.id,
        name=restaurant.name,
        description=restaurant.description,
    ).model_dump()


def menu_item_response(menu_item):
    return MenuItemResponse(
        id=menu_item.id,
        title=menu_item.title,
        name=menu_item.name,
        price=menu_item.price,
        description=menu_item.description,
        restaurant_id=menu_item.restaurant_id,
    ).model_dump()


def order_response(order):
    return OwnerOrderResponse(
        id=order.id,
        customer=OwnerOrderCustomerResponse(
            id=order.customer.id,
            username=order.customer.username,
            email=order.customer.email,
        ),
        restaurant=OwnerOrderRestaurantResponse(
            id=order.restaurant.id,
            name=order.restaurant.name,
        ),
        menu_item=OwnerOrderMenuItemResponse(
            id=order.menu_item.id,
            title=order.menu_item.title,
            name=order.menu_item.name,
        ),
        quantity=order.quantity,
        unit_price=order.unit_price,
        total_price=order.total_price,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )
