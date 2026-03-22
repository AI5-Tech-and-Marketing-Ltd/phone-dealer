import time
import cloudinary
import cloudinary.utils
from django.conf import settings
from rest_framework import views, permissions, status
from rest_framework.response import Response
from .models import Product
from stores.models import Store

class CloudinarySignatureView(views.APIView):
    """Generate signature for Cloudinary signed uploads."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        upload_type = request.query_params.get('type', 'product')
        if upload_type == 'shop':
             preset = getattr(settings, 'CLOUDINARY_SHOP_PRESET', 'ml_default')
        else:
             preset = getattr(settings, 'CLOUDINARY_PRODUCT_PRESET', 'ml_default')
             
        timestamp = int(time.time())
        params = {
            "timestamp": timestamp,
            "upload_preset": preset
        }
        signature = cloudinary.utils.api_sign_request(
            params,
            settings.CLOUDINARY_STORAGE['API_SECRET']
        )
        return Response({
            "signature": signature,
            "timestamp": timestamp,
            "api_key": settings.CLOUDINARY_STORAGE['API_KEY'],
            "cloud_name": settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
            "upload_preset": params["upload_preset"]
        })

class SetImageUrlView(views.APIView):
    """Set the Cloudinary URL to a target model instance."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        target_type = request.data.get('type') # 'product' or 'store'
        target_id = request.data.get('id')
        url = request.data.get('url')

        if not all([target_type, target_id, url]):
             return Response({"error": "type, id, and url are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if target_type == 'product':
                obj = Product.objects.get(id=target_id, store__owner=request.user)
                obj.image = url
            elif target_type == 'store':
                obj = Store.objects.get(id=target_id, owner=request.user)
                obj.logo = url # or cover_image
            else:
                return Response({"error": "Invalid type."}, status=status.HTTP_400_BAD_REQUEST)
            
            obj.save()
            return Response({"message": f"Successfully updated {target_type} image."})
        except (Product.DoesNotExist, Store.DoesNotExist):
            return Response({"error": "Object not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
