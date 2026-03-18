from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['price', 'daily_income', 'validity_period', 'created_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.action == 'list' and not self.request.user.is_staff:
            return Product.objects.filter(is_active=True)
        return super().get_queryset()

    @action(detail=False, methods=['get'])
    def active(self, request):
        products = Product.objects.filter(is_active=True)
        page = self.paginate_queryset(products)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def calculate_returns(self, request, pk=None):
        product = self.get_object()
        amount = request.query_params.get('amount', product.price)

        try:
            amount = float(amount)
        except ValueError:
            return Response({'error': 'Invalid amount'}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate returns based on amount
        ratio = amount / float(product.price)
        daily_return = float(product.daily_income) * ratio
        total_return = daily_return * product.validity_period

        return Response({
            'product_id': product.id,
            'product_name': product.name,
            'investment_amount': amount,
            'daily_return': round(daily_return, 2),
            'total_return': round(total_return, 2),
            'roi_percentage': round(((total_return - amount) / amount) * 100, 2),
            'validity_days': product.validity_period
        })