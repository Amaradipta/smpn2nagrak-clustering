from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Avg
from .models import ProfilSekolah, Guru, Analisis, HasilAnalisis

import pandas as pd
import json
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import davies_bouldin_score


def home(request):
    return render(request, 'home.html')


def profil(request):
    profil = ProfilSekolah.objects.first()
    return render(request, 'profil.html', {'profil': profil})


def guru_list(request):
    guru = Guru.objects.all()
    return render(request, 'guru.html', {'guru': guru})


def upload_analisis(request):
    if request.method == 'POST':
        file = request.FILES['file']
        tahun_ajaran = request.POST['tahun_ajaran']
        semester = request.POST['semester']

        analisis = Analisis.objects.create(
            tahun_ajaran=tahun_ajaran,
            semester=semester
        )

        df = pd.read_excel(file)

        df['cluster'] = None
        df['risiko'] = None

        dbi_list = []  # 🔥 penampung DBI

        for kelas in df['Kelas'].unique():

            df_kelas = df[df['Kelas'] == kelas]

            # Validasi minimal 3 siswa
            if len(df_kelas) < 3:
                df.loc[df['Kelas'] == kelas, 'cluster'] = -1
                df.loc[df['Kelas'] == kelas, 'risiko'] = 'Data Tidak Cukup'
                continue

            fitur = df_kelas[[
                'Nilai_Rata_Rata',
                'Persentase_Kehadiran',
                'Skor_Ekstrakurikuler'
            ]]

            # Normalisasi MinMax
            scaler = MinMaxScaler()
            fitur_scaled = scaler.fit_transform(fitur)

            # Clustering
            model = AgglomerativeClustering(n_clusters=3, linkage='ward')
            cluster = model.fit_predict(fitur_scaled)

            # Evaluasi DBI
            dbi = davies_bouldin_score(fitur_scaled, cluster)
            dbi_list.append(dbi)

            df.loc[df['Kelas'] == kelas, 'cluster'] = cluster

            # Mapping risiko
            df_kelas = df[df['Kelas'] == kelas]

            rata_cluster = (
                df_kelas.groupby('cluster')['Nilai_Rata_Rata']
                .mean()
                .sort_values(ascending=False)
            )

            urutan_cluster = list(rata_cluster.index)

            mapping_risiko = {}

            if len(urutan_cluster) == 3:
                mapping_risiko[urutan_cluster[0]] = 'Tidak Berisiko'
                mapping_risiko[urutan_cluster[1]] = 'Berisiko Sedang'
                mapping_risiko[urutan_cluster[2]] = 'Berisiko Tinggi'

            df.loc[df['Kelas'] == kelas, 'risiko'] = \
                df.loc[df['Kelas'] == kelas, 'cluster'].map(mapping_risiko)

        # Rata-rata DBI
        if dbi_list:
            dbi_avg = sum(dbi_list) / len(dbi_list)
        else:
            dbi_avg = 0

        # Simpan DBI ke session
        request.session['dbi'] = round(dbi_avg, 4)

        # Simpan ke database
        for _, row in df.iterrows():
            HasilAnalisis.objects.create(
                analisis=analisis,
                nis=row['NIS'],
                nama=row['Nama'],
                kelas=row['Kelas'],
                nilai_rata_rata=row['Nilai_Rata_Rata'],
                persentase_kehadiran=row['Persentase_Kehadiran'],
                skor_ekstrakurikuler=row['Skor_Ekstrakurikuler'],
                cluster=row['cluster'],
                risiko=row['risiko']
            )

        messages.success(request, "Analisis berhasil dilakukan.")
        return redirect('hasil_analisis', analisis_id=analisis.id)

    return render(request, 'upload_analisis.html')


def hasil_analisis(request, analisis_id):
    analisis = get_object_or_404(Analisis, id=analisis_id)

    # 🔥 Ambil DBI
    dbi = request.session.get('dbi', None)

    kelas_filter = request.GET.get('kelas')

    data = HasilAnalisis.objects.filter(analisis=analisis)

    if kelas_filter:
        data = data.filter(kelas=kelas_filter)

    # Ringkasan
    total_siswa = data.count()

    jumlah_risiko = (
        data
        .values('risiko')
        .annotate(jumlah=Count('id'))
    )

    tidak_berisiko = 0
    risiko_sedang = 0
    risiko_tinggi = 0

    for r in jumlah_risiko:
        if r['risiko'] == 'Tidak Berisiko':
            tidak_berisiko = r['jumlah']
        elif r['risiko'] == 'Berisiko Sedang':
            risiko_sedang = r['jumlah']
        elif r['risiko'] == 'Berisiko Tinggi':
            risiko_tinggi = r['jumlah']

    # Statistik cluster
    statistik_cluster = (
        data
        .values('kelas', 'cluster', 'risiko')
        .annotate(
            jumlah=Count('id'),
            rata_nilai=Avg('nilai_rata_rata'),
            rata_kehadiran=Avg('persentase_kehadiran'),
            rata_ekstra=Avg('skor_ekstrakurikuler')
        )
        .order_by('kelas', 'cluster')
    )

    # Grafik
    distribusi = (
        data
        .values('risiko')
        .annotate(jumlah=Count('id'))
    )

    label_chart = []
    data_chart = []
    warna_chart = []

    for d in distribusi:
        label_chart.append(d['risiko'])
        data_chart.append(d['jumlah'])

        if d['risiko'] == 'Tidak Berisiko':
            warna_chart.append('#16a34a')
        elif d['risiko'] == 'Berisiko Sedang':
            warna_chart.append('#facc15')
        elif d['risiko'] == 'Berisiko Tinggi':
            warna_chart.append('#dc2626')
        else:
            warna_chart.append('#64748b')

    label_chart_json = json.dumps(label_chart)
    data_chart_json = json.dumps(data_chart)
    warna_chart_json = json.dumps(warna_chart)

    daftar_kelas = (
        HasilAnalisis.objects
        .filter(analisis=analisis)
        .values_list('kelas', flat=True)
        .distinct()
    )

    return render(request, 'hasil_analisis.html', {
        'analisis': analisis,
        'data': data,
        'kelas_filter': kelas_filter,
        'daftar_kelas': daftar_kelas,
        'statistik_cluster': statistik_cluster,
        'total_siswa': total_siswa,
        'tidak_berisiko': tidak_berisiko,
        'risiko_sedang': risiko_sedang,
        'risiko_tinggi': risiko_tinggi,
        'label_chart': label_chart_json,
        'data_chart': data_chart_json,
        'warna_chart': warna_chart_json,
        'dbi': dbi  # 🔥 tampilkan DBI
    })