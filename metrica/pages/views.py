from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import TemplateView

class PagesView (LoginRequiredMixin, TemplateView):
    pass

# Create your views here.

profile_view = PagesView.as_view(template_name = "pages/profile.html")
tour_view = PagesView.as_view(template_name = "pages/tour.html")
timeline_view = PagesView.as_view(template_name = "pages/timeline.html")
treeview_view = PagesView.as_view(template_name = "pages/treeview.html")
starter_view = PagesView.as_view(template_name = "pages/starter.html")
pricing_view = PagesView.as_view(template_name = "pages/pricing.html")
blogs_view = PagesView.as_view(template_name = "pages/blogs.html")
faqs_view = PagesView.as_view(template_name = "pages/faq.html")
gallery_view = PagesView.as_view(template_name = "pages/gallery.html")