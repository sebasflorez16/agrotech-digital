from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin

from django.views.generic import TemplateView

# Create your views here.

class UikitView(LoginRequiredMixin, TemplateView):
    pass
#Ui 
alerts_view = UikitView.as_view(template_name = "uikit/ui-elements/alerts.html")
avatar_view = UikitView.as_view(template_name = "uikit/ui-elements/avatar.html")
buttons_view = UikitView.as_view(template_name = "uikit/ui-elements/buttons.html")
badges_view = UikitView.as_view(template_name = "uikit/ui-elements/badges.html")
cards_view = UikitView.as_view(template_name = "uikit/ui-elements/cards.html")
carousels_view = UikitView.as_view(template_name = "uikit/ui-elements/carousels.html")
dropdowns_view = UikitView.as_view(template_name = "uikit/ui-elements/dropdowns.html")
grids_view = UikitView.as_view(template_name = "uikit/ui-elements/grids.html")
images_view = UikitView.as_view(template_name = "uikit/ui-elements/images.html")
list_view = UikitView.as_view(template_name = "uikit/ui-elements/list.html")
modals_view = UikitView.as_view(template_name = "uikit/ui-elements/modals.html")
navs_view = UikitView.as_view(template_name = "uikit/ui-elements/navs.html")
navbar_view = UikitView.as_view(template_name = "uikit/ui-elements/navbar.html")
paginations_view = UikitView.as_view(template_name = "uikit/ui-elements/paginations.html")
popover_view = UikitView.as_view(template_name = "uikit/ui-elements/popover-tooltips.html")
progress_view = UikitView.as_view(template_name = "uikit/ui-elements/progress.html")
spinners_view = UikitView.as_view(template_name = "uikit/ui-elements/spinners.html")
tabs_view = UikitView.as_view(template_name = "uikit/ui-elements/tabs-accordions.html")
typography_view = UikitView.as_view(template_name = "uikit/ui-elements/typography.html")
videos_view = UikitView.as_view(template_name = "uikit/ui-elements/videos.html")

#Advance UI
animation_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-animation.html")
clipboard_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-clipboard.html")
dragula_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-dragula.html")
files_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-files.html")
highlight_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-highlight.html")
rangeslider_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-rangeslider.html")
ratings_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-ratings.html")
ribbons_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-ribbons.html")
sweetalerts_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-sweetalerts.html")
toasts_view = UikitView.as_view(template_name = "uikit/advanced-ui/advanced-toasts.html")

#Forms
formsElements_view = UikitView.as_view(template_name = "uikit/forms/forms-elements.html")
formsAdvanced_view = UikitView.as_view(template_name = "uikit/forms/forms-advanced.html")
formsValidation_view = UikitView.as_view(template_name = "uikit/forms/forms-validation.html")
formsWizard_view = UikitView.as_view(template_name = "uikit/forms/forms-wizard.html")
formsEditors_view = UikitView.as_view(template_name = "uikit/forms/forms-editors.html")
formsUploads_view = UikitView.as_view(template_name = "uikit/forms/forms-uploads.html")
formsImgCrop_view = UikitView.as_view(template_name = "uikit/forms/forms-img-crop.html")

#Charts
chartsApex_view = UikitView.as_view(template_name = "uikit/charts/charts-apex.html")
chartsJustgage_view = UikitView.as_view(template_name = "uikit/charts/charts-justgage.html")
chartsChartjs_view = UikitView.as_view(template_name = "uikit/charts/charts-chartjs.html")
chartsToastUi_view = UikitView.as_view(template_name = "uikit/charts/charts-toast-ui.html")

#Tables
tablesBasic_view = UikitView.as_view(template_name = "uikit/tables/tables-basic.html")
tablesDatatable_view = UikitView.as_view(template_name = "uikit/tables/tables-datatable.html")
tablesEdittable_view = UikitView.as_view(template_name = "uikit/tables/tables-editable.html")

#Icons
iconsMaterialdesign_view = UikitView.as_view(template_name = "uikit/icons/icons-materialdesign.html")
iconsFontawesome_view = UikitView.as_view(template_name = "uikit/icons/icons-fontawesome.html")
iconsTabler_view = UikitView.as_view(template_name = "uikit/icons/icons-tabler.html")
iconsFeather_view = UikitView.as_view(template_name = "uikit/icons/icons-feather.html")

#Maps
mapsGoogle_view = UikitView.as_view(template_name = "uikit/maps/maps-google.html")
mapsLeaflet_view = UikitView.as_view(template_name = "uikit/maps/maps-leaflet.html")
mapsVector_view = UikitView.as_view(template_name = "uikit/maps/maps-vector.html")

#Email
emailBasic_view = UikitView.as_view(template_name = "uikit/email/email-templates-basic.html")
emailAlert_view = UikitView.as_view(template_name = "uikit/email/email-templates-alert.html")
emailBiiling_view = UikitView.as_view(template_name = "uikit/email/email-templates-billing.html")