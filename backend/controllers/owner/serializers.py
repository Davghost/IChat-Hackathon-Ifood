from .schemas import (
    OwnerOrderContextResponse,
    OwnerOrderCourierResponse,
    OwnerOrderCustomerResponse,
    OwnerOrderLocationResponse,
    OwnerOrderResponse,
    OwnerOrderRouteResponse,
)


def order_response(order):
    return OwnerOrderResponse(
        id=order["id"],
        order_id=order["order_id"],
        customer=OwnerOrderCustomerResponse(
            name=order["customer_name"],
            email=order["customer_email"],
        ),
        courier=OwnerOrderCourierResponse(
            name=order["courier_name"],
            vehicle=order["courier_vehicle"],
        ),
        route=OwnerOrderRouteResponse(
            restaurant=OwnerOrderLocationResponse(
                lat=order["restaurant_lat"],
                lng=order["restaurant_lng"],
            ),
            customer=OwnerOrderLocationResponse(
                lat=order["customer_lat"],
                lng=order["customer_lng"],
            ),
        ),
        context=OwnerOrderContextResponse(
            weather=order["weather"],
            traffic_level=order["traffic_level"],
            restaurant_busy_level=order["restaurant_busy_level"],
            app_version=order["app_version"],
        ),
        delivery_neighborhood=order["delivery_neighborhood"],
        main_dish=order["main_dish"],
        quantity=order["quantity"],
        order_price=order["order_price"],
        total_price=order["total_price"],
        status=order["status"],
        order_time=order["order_time"],
        updated_at=order["updated_at"],
        payload=order["payload"],
    )
