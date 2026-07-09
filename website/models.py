from django.db import models

class ProfilSekolah(models.Model):
    nama_sekolah = models.CharField(max_length=200)
    alamat = models.TextField()
    visi = models.TextField()
    misi = models.TextField()
    deskripsi = models.TextField()

    class Meta:
        verbose_name = "Profil Sekolah"
        verbose_name_plural = "Profil Sekolah"

    def __str__(self):
        return self.nama_sekolah


class Guru(models.Model):
    nama = models.CharField(max_length=200)
    jabatan = models.CharField(max_length=200)
    foto = models.ImageField(upload_to='guru/', null=True, blank=True)

    class Meta:
        verbose_name = "Data Guru"
        verbose_name_plural = "Data Guru"

    def __str__(self):
        return self.nama

class Analisis(models.Model):

    tahun_ajaran = models.CharField(
        max_length=20
    )

    semester = models.IntegerField()

    jenjang = models.CharField(
        max_length=10
    )

    tanggal_analisis = models.DateTimeField(
        auto_now_add=True
    )

    silhouette = models.FloatField(
        null=True,
        blank=True
    )

    chi = models.FloatField(
        null=True,
        blank=True
    )

    dbi = models.FloatField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Batch Analisis"
        verbose_name_plural = "Batch Analisis"

    def __str__(self):

        return (
            f"Kelas {self.jenjang} - "
            f"{self.tahun_ajaran} "
            f"Semester {self.semester}"
        )


class HasilAnalisis(models.Model):

    analisis = models.ForeignKey(
        Analisis,
        on_delete=models.CASCADE
    )

    nis = models.CharField(max_length=50)

    nama = models.CharField(max_length=200)

    kelas = models.CharField(max_length=20)

    nilai_rata_rata = models.FloatField()

    persentase_kehadiran = models.FloatField()

    skor_ekstrakurikuler = models.IntegerField()

    cluster = models.IntegerField(
        null=True,
        blank=True
    )

    risiko = models.CharField(
        max_length=50,
        null=True,
        blank=True
    )

    class Meta:

        verbose_name = "Hasil Analisis Siswa"

        verbose_name_plural = "Hasil Analisis Siswa"

    def __str__(self):

        return f"{self.nama} ({self.kelas})"