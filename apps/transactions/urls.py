from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, PaymentMethodViewSet
from .admin_views import approve_transaction, reject_transaction

router = DefaultRouter()
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')

urlpatterns = [
    path('', include(router.urls)),
    # Admin action URLs
    path('admin/transactions/<uuid:transaction_id>/approve/', approve_transaction, name='admin-approve-transaction'),
    path('admin/transactions/<uuid:transaction_id>/reject/', reject_transaction, name='admin-reject-transaction'),
]