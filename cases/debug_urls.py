from django.urls import path
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from accounts.models import User


class UserListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        users = User.objects.all()
        return Response(
            [{"id": str(u.id), "username": u.username, "role": u.role} for u in users]
        )


urlpatterns = [path("users/all/", UserListView.as_view(), name="all-users")]
