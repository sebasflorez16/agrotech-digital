from rest_framework import serializers
from django.contrib.auth import get_user_model

class UserProfileUtilSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'email', 'name', 'last_name', 'is_active', 'is_staff', "image"]
