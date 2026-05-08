from django.contrib import admin
from .models import ProfilSekolah, Guru, Analisis, HasilAnalisis

admin.site.register(ProfilSekolah)
admin.site.register(Guru)
admin.site.register(Analisis)
admin.site.register(HasilAnalisis)