from django.urls import path

from .views import profile_view, tour_view, timeline_view, treeview_view, starter_view, pricing_view, blogs_view, faqs_view, gallery_view
 
app_name = "pages" 
urlpatterns = [
  path("profile", view=profile_view, name="profile"),
  path("tour", view=tour_view, name="tour"),
  path("timeline", view=timeline_view, name="timeline"),
  path("treeview", view=treeview_view, name="treeview"),
  path("starter", view=starter_view, name="starter"),
  path("pricing", view=pricing_view, name="pricing"),
  path("blogs", view=blogs_view, name="blogs"),
  path("faqs", view=faqs_view, name="faqs"),
  path("gallery", view=gallery_view, name="gallery")
]