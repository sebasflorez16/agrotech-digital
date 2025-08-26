from django.http import JsonResponse
from django.views import View

class SimpleAnalyticsView(View):
    def get(self, request):
        return JsonResponse({
            "message": "Vista simple funciona!",
            "path": request.path,
            "method": request.method,
            "params": dict(request.GET),
            "view_id": request.GET.get('view_id'),
            "scene_date": request.GET.get('scene_date')
        })
