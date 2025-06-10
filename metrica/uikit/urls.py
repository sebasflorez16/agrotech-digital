from django.urls import path

from .views import *

app_name="uikit"
urlpatterns = [
    #UI
    path("alerts", view=alerts_view, name="alerts"),
    path("avatar", view=avatar_view, name="avatar"),
    path("buttons", view=buttons_view, name="buttons"),
    path("badges", view=badges_view, name="badges"),
    path("cards", view=cards_view, name="cards"),
    path("carousels", view=carousels_view, name="carousels"),
    path("dropdowns", view=dropdowns_view, name="dropdowns"),
    path("grids", view=grids_view, name="grids"),
    path("images", view=images_view, name="images"),
    path("list", view=list_view, name="list"),
    path("modals", view=modals_view, name="modals"),
    path("navs", view=navs_view, name="navs"),
    path("navbar", view=navbar_view, name="navbar"),
    path("paginations", view=paginations_view, name="paginations"),
    path("popover", view=popover_view, name="popover"),
    path("progress", view=progress_view, name="progress"),
    path("spinners", view=spinners_view, name="spinners"),
    path("tabs", view=tabs_view, name="tabs"),
    path("typography", view=typography_view, name="typography"),
    path("videos", view=videos_view, name="videos"),

    #AdvanceUi
    path("animation", view=animation_view, name="animation"),
    path("clipboard", view=clipboard_view, name="clipboard"),
    path("dragula", view=dragula_view, name="dragula"),
    path("files", view=files_view, name="files"),
    path("highlight", view=highlight_view, name="highlight"),
    path("rangeslider", view=rangeslider_view, name="rangeslider"),
    path("ratings", view=ratings_view, name="ratings"),
    path("ratings", view=ratings_view, name="ratings"),
    path("ribbons", view=ribbons_view, name="ribbons"),
    path("sweetalerts", view=sweetalerts_view, name="sweetalerts"),
    path("toasts", view=toasts_view, name="toasts"),

    #forms
    path("formsElements", view=formsElements_view, name="formsElements"),
    path("formsAdvanced", view=formsAdvanced_view, name="formsAdvanced"),
    path("formsValidation", view=formsValidation_view, name="formsValidation"),
    path("formsWizard", view=formsWizard_view, name="formsWizard"),
    path("formsEditors", view=formsEditors_view, name="formsEditors"),
    path("formsUploads", view=formsUploads_view, name="formsUploads"),
    path("formsImgCrop", view=formsImgCrop_view, name="formsImgCrop"),

    #Charts
    path("chartsApex", view=chartsApex_view, name="chartsApex"),
    path("chartsJustgage", view=chartsJustgage_view, name="chartsJustgage"),
    path("chartsChartjs", view=chartsChartjs_view, name="chartsChartjs"),
    path("chartsToastUi", view=chartsToastUi_view, name="chartsToastUi"),

    #Tables
    path("tablesBasic", view=tablesBasic_view, name="tablesBasic"),
    path("tablesDatatable", view=tablesDatatable_view, name="tablesDatatable"),
    path("tablesEdittable", view=tablesEdittable_view, name="tablesEdittable"),

    #Icons
    path("iconsMaterialdesign", view=iconsMaterialdesign_view, name="iconsMaterialdesign"),
    path("iconsFontawesome", view=iconsFontawesome_view, name="iconsFontawesome"),
    path("iconsTabler", view=iconsTabler_view, name="iconsTabler"),
    path("iconsFeather", view=iconsFeather_view, name="iconsFeather"),

    #Maps
    path("mapsGoogle", view=mapsGoogle_view, name="mapsGoogle"),
    path("mapsLeaflet", view=mapsLeaflet_view, name="mapsLeaflet"),
    path("mapsVector", view=mapsVector_view, name="mapsVector"),

    #Email Templates
    path("emailBasic", view=emailBasic_view, name="emailBasic"),
    path("emailAlert", view=emailAlert_view, name="emailAlert"),
    path("emailBiiling", view=emailBiiling_view, name="emailBiiling"),
]