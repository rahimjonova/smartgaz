from fastapi import APIRouter

from app.api.v1.endpoints import admin, orders, routes, tracking, users

api_router = APIRouter()
api_router.include_router(users.router)
api_router.include_router(orders.router)
api_router.include_router(tracking.router)
api_router.include_router(routes.router)
api_router.include_router(admin.router)
