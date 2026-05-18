"""
URL configuration for smpn2nagrak project.
"""

from django.contrib import admin
from django.urls import path

from django.conf import settings
from django.conf.urls.static import static

from website import views

urlpatterns = [

    # =========================
    # ADMIN
    # =========================

    path(
        'admin/',
        admin.site.urls
    ),

    # =========================
    # WEBSITE
    # =========================

    path(
        '',
        views.home,
        name='home'
    ),

    path(
        'profil/',
        views.profil,
        name='profil'
    ),

    path(
        'guru/',
        views.guru_list,
        name='guru'
    ),

    # =========================
    # ANALISIS
    # =========================

    path(
        'analisis/upload/',
        views.upload_analisis,
        name='upload_analisis'
    ),

    path(
        'analisis/hasil/<int:analisis_id>/',
        views.hasil_analisis,
        name='hasil_analisis'
    ),

    # =========================
    # RIWAYAT ANALISIS
    # =========================

    path(
        'analisis/riwayat/',
        views.riwayat_analisis,
        name='riwayat_analisis'
    ),

    # =========================
    # DATA SISWA
    # =========================

    path(
        'analisis/data-siswa/',
        views.data_siswa,
        name='data_siswa'
    ),

    # =========================
    # DETAIL SISWA
    # =========================

    path(
        'analisis/siswa/<str:nis>/',
        views.detail_siswa,
        name='detail_siswa'
    ),

    # =========================
    # EXPORT EXCEL
    # =========================

    path(
        'analisis/export-excel/',
        views.export_excel,
        name='export_excel'
    ),

]

if settings.DEBUG:

    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )