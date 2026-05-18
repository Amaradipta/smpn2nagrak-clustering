from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Avg
from django.http import HttpResponse

from .models import ProfilSekolah, Guru, Analisis, HasilAnalisis

import pandas as pd
import json

from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import davies_bouldin_score

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt

from scipy.cluster.hierarchy import linkage, dendrogram

import io
import base64


# =========================
# HOME
# =========================

def home(request):

    return render(
        request,
        'home.html'
    )


# =========================
# PROFIL SEKOLAH
# =========================

def profil(request):

    profil = ProfilSekolah.objects.first()

    return render(
        request,
        'profil.html',
        {
            'profil': profil
        }
    )


# =========================
# DATA GURU
# =========================

def guru_list(request):

    guru = Guru.objects.all()

    return render(
        request,
        'guru.html',
        {
            'guru': guru
        }
    )


# =========================
# UPLOAD ANALISIS
# =========================

def upload_analisis(request):

    if request.method == 'POST':

        file = request.FILES['file']

        tahun_ajaran = request.POST['tahun_ajaran']

        semester = request.POST['semester']

        jenjang = request.POST['jenjang']

        # =========================
        # VALIDASI DUPLIKAT
        # =========================

        cek_analisis = Analisis.objects.filter(
            tahun_ajaran=tahun_ajaran,
            semester=semester,
            jenjang=jenjang
        ).first()

        if cek_analisis:

            messages.error(
                request,
                f'Analisis Tahun Ajaran {tahun_ajaran} Semester {semester} sudah tersedia.'
            )

            return redirect(
                'upload_analisis'
            )

        # =========================
        # SIMPAN ANALISIS
        # =========================

        analisis = Analisis.objects.create(
            tahun_ajaran=tahun_ajaran,
            semester=semester,
            jenjang = jenjang
        )

        # =========================
        # BACA FILE EXCEL
        # =========================

        excel_file = pd.ExcelFile(file)

        semua_data = []

        for sheet in excel_file.sheet_names:

            df_sheet = pd.read_excel(
                excel_file,
                sheet_name=sheet
            )

            # Tambahkan nama kelas
            df_sheet['Kelas'] = sheet

            semua_data.append(df_sheet)

        # =========================
        # GABUNGKAN SEMUA SHEET
        # =========================

        df = pd.concat(
            semua_data,
            ignore_index=True
        )

        # =========================
        # HAPUS DATA KOSONG
        # =========================

        df = df.dropna(
            subset=['Nama']
        )

        # =========================
        # HITUNG AVG
        # =========================

        mapel = [
            'PABP',
            'PP',
            'INDO',
            'MAT',
            'IPA',
            'IPS',
            'ING',
            'SB',
            'PJOK',
            'INFO',
            'SUNDA',
            'PRAKARYA'
        ]

        df['AVG'] = (
            df[mapel]
            .mean(axis=1)
            .round(2)
        )

        # =========================
        # KOLOM CLUSTER & RISIKO
        # =========================

        df['cluster'] = None

        df['risiko'] = None

        dbi_list = []

        # =========================
        # PROSES PER KELAS
        # =========================

        for kelas in df['Kelas'].unique():

            df_kelas = df[
                df['Kelas'] == kelas
            ].copy()

            # =========================
            # MINIMAL DATA
            # =========================

            if len(df_kelas) < 4:

                df.loc[
                    df['Kelas'] == kelas,
                    'cluster'
                ] = -1

                df.loc[
                    df['Kelas'] == kelas,
                    'risiko'
                ] = 'Data Tidak Cukup'

                continue

            # =========================
            # FITUR CLUSTERING
            # =========================

            fitur = df_kelas[[
                'AVG',
                'ABSEN',
                'EKSTRAKURIKULER'
            ]]

            # =========================
            # NORMALISASI
            # =========================

            scaler = MinMaxScaler()

            fitur_scaled = scaler.fit_transform(
                fitur
            )

            # =========================
            # AGGLOMERATIVE CLUSTERING
            # =========================

            model = AgglomerativeClustering(
                n_clusters=4,
                linkage='ward'
            )

            cluster = model.fit_predict(
                fitur_scaled
            )

            # =========================
            # HITUNG DBI
            # =========================

            dbi = davies_bouldin_score(
                fitur_scaled,
                cluster
            )

            dbi_list.append(dbi)

            # =========================
            # SIMPAN CLUSTER
            # =========================

            df.loc[
                df['Kelas'] == kelas,
                'cluster'
            ] = cluster

            # =========================
            # DATA NORMALISASI
            # =========================

            df_scaled = pd.DataFrame(
                fitur_scaled,
                columns=[
                    'AVG',
                    'ABSEN',
                    'EKSTRAKURIKULER'
                ]
            )

            df_scaled['cluster'] = cluster

            # =========================
            # SKOR CLUSTER
            # =========================

            df_scaled['SKOR_CLUSTER'] = (
                df_scaled[
                    [
                        'AVG',
                        'ABSEN',
                        'EKSTRAKURIKULER'
                    ]
                ].mean(axis=1)
            )

            # =========================
            # RATA-RATA CLUSTER
            # =========================

            rata_cluster = (
                df_scaled
                .groupby('cluster')['SKOR_CLUSTER']
                .mean()
                .sort_values(ascending=False)
            )

            urutan_cluster = list(
                rata_cluster.index
            )

            # =========================
            # MAPPING RISIKO
            # =========================

            mapping_risiko = {}

            if len(urutan_cluster) == 4:

                mapping_risiko[
                    urutan_cluster[0]
                ] = 'Tidak Berisiko'

                mapping_risiko[
                    urutan_cluster[1]
                ] = 'Rendah'

                mapping_risiko[
                    urutan_cluster[2]
                ] = 'Sedang'

                mapping_risiko[
                    urutan_cluster[3]
                ] = 'Tinggi'

            # =========================
            # LABEL RISIKO
            # =========================

            df.loc[
                df['Kelas'] == kelas,
                'risiko'
            ] = df.loc[
                df['Kelas'] == kelas,
                'cluster'
            ].map(mapping_risiko)

        # =========================
        # RATA-RATA DBI
        # =========================

        if dbi_list:

            dbi_avg = (
                sum(dbi_list)
                / len(dbi_list)
            )

        else:

            dbi_avg = 0

        analisis.dbi = round(
            dbi_avg,
            4
        )

        analisis.save()

        # =========================
        # SIMPAN KE DATABASE
        # =========================

        for _, row in df.iterrows():

            HasilAnalisis.objects.create(
                analisis=analisis,
                nis=row['No Induk'],
                nama=row['Nama'],
                kelas=row['Kelas'],
                nilai_rata_rata=row['AVG'],
                persentase_kehadiran=row['ABSEN'],
                skor_ekstrakurikuler=row['EKSTRAKURIKULER'],
                cluster=row['cluster'],
                risiko=row['risiko']
            )

        messages.success(
            request,
            'Analisis berhasil dilakukan.'
        )

        return redirect(
            'hasil_analisis',
            analisis_id=analisis.id
        )

    return render(
        request,
        'upload_analisis.html'
    )


# =========================
# HASIL ANALISIS
# =========================

def hasil_analisis(request, analisis_id):

    analisis = get_object_or_404(
        Analisis,
        id=analisis_id
    )

    dbi = analisis.dbi

    kelas_filter = request.GET.get(
        'kelas'
    )

    data = HasilAnalisis.objects.filter(
        analisis=analisis
    )

    if kelas_filter:

        data = data.filter(
            kelas=kelas_filter
        )

    # =========================
    # RINGKASAN RISIKO
    # =========================

    total_siswa = data.count()

    jumlah_risiko = (
        data
        .values('risiko')
        .annotate(
            jumlah=Count('id')
        )
    )

    tidak_berisiko = 0
    risiko_rendah = 0
    risiko_sedang = 0
    risiko_tinggi = 0

    for r in jumlah_risiko:

        if r['risiko'] == 'Tidak Berisiko':

            tidak_berisiko = r['jumlah']

        elif r['risiko'] == 'Rendah':

            risiko_rendah = r['jumlah']

        elif r['risiko'] == 'Sedang':

            risiko_sedang = r['jumlah']

        elif r['risiko'] == 'Tinggi':

            risiko_tinggi = r['jumlah']

    # =========================
    # STATISTIK CLUSTER
    # =========================

    statistik_cluster = (
        data
        .values(
            'kelas',
            'cluster',
            'risiko'
        )
        .annotate(
            jumlah=Count('id'),
            rata_nilai=Avg('nilai_rata_rata'),
            rata_kehadiran=Avg('persentase_kehadiran'),
            rata_ekstra=Avg('skor_ekstrakurikuler')
        )
        .order_by(
            'kelas',
            'cluster'
        )
    )

    # =========================
    # DISTRIBUSI RISIKO
    # =========================

    distribusi = (
        data
        .values('risiko')
        .annotate(
            jumlah=Count('id')
        )
    )

    label_chart = []
    data_chart = []
    warna_chart = []

    for d in distribusi:

        label_chart.append(
            d['risiko']
        )

        data_chart.append(
            d['jumlah']
        )

        if d['risiko'] == 'Tidak Berisiko':

            warna_chart.append(
                'rgba(34,197,94,0.7)'
            )

        elif d['risiko'] == 'Rendah':

            warna_chart.append(
                'rgba(132,204,22,0.7)'
            )

        elif d['risiko'] == 'Sedang':

            warna_chart.append(
                'rgba(250,204,21,0.7)'
            )

        elif d['risiko'] == 'Tinggi':

            warna_chart.append(
                'rgba(239,68,68,0.7)'
            )

        else:

            warna_chart.append(
                'rgba(100,116,139,0.7)'
            )

    label_chart_json = json.dumps(
        label_chart
    )

    data_chart_json = json.dumps(
        data_chart
    )

    warna_chart_json = json.dumps(
        warna_chart
    )

    # =========================
    # BUBBLE SCATTER PLOT
    # =========================

    scatter_data = []

    for siswa in data:

        warna = 'rgba(100,116,139,0.7)'

        # warna berdasarkan risiko
        if siswa.risiko == 'Tidak Berisiko':

            warna = 'rgba(34,197,94,0.7)'

        elif siswa.risiko == 'Rendah':

            warna = 'rgba(132,204,22,0.7)'

        elif siswa.risiko == 'Sedang':

            warna = 'rgba(250,204,21,0.7)'

        elif siswa.risiko == 'Tinggi':

            warna = 'rgba(239,68,68,0.7)'
            
        # ukuran bubble diperkecil
        ukuran = (
            float(siswa.skor_ekstrakurikuler) * 2.5
        )

        scatter_data.append({

            'x': float(
                siswa.nilai_rata_rata
            ),

            'y': float(
                siswa.persentase_kehadiran
            ),

            'r': ukuran,

            'label': siswa.nama,

            'kelas': siswa.kelas,

            'risiko': siswa.risiko,

            'cluster': siswa.cluster,

            'ekstra': siswa.skor_ekstrakurikuler,

            'backgroundColor': warna

        })

    scatter_data_json = json.dumps(
        scatter_data
    )

    # =========================
    # DENDROGRAM
    # =========================

    fitur_dendrogram = list(

        data.values_list(
            'nilai_rata_rata',
            'persentase_kehadiran',
            'skor_ekstrakurikuler'
        )

    )

    linked = linkage(
        fitur_dendrogram,
        method='ward'
    )

    plt.figure(
        figsize=(10, 5)
    )

    dendrogram(
        linked,
        truncate_mode='lastp',
        p=20
    )

    plt.title(
        'Dendrogram Agglomerative Hierarchical Clustering'
    )

    plt.xlabel(
        'Data Siswa'
    )

    plt.ylabel(
        'Jarak Euclidean'
    )

    buffer = io.BytesIO()

    plt.savefig(
        buffer,
        format='png',
        bbox_inches='tight'
    )

    buffer.seek(0)

    image_png = buffer.getvalue()

    buffer.close()

    grafik_dendrogram = base64.b64encode(
        image_png
    ).decode('utf-8')

    plt.close()

    # =========================
    # INSIGHT DASHBOARD
    # =========================

    insight_dashboard = None

    jumlah_risiko_dashboard = {

        'Tidak Berisiko': tidak_berisiko,

        'Rendah': risiko_rendah,

        'Sedang': risiko_sedang,

        'Tinggi': risiko_tinggi

    }

    kategori_terbanyak = max(
        jumlah_risiko_dashboard,
        key=jumlah_risiko_dashboard.get
    )

    jumlah_terbanyak = jumlah_risiko_dashboard[
        kategori_terbanyak
    ]

    if kategori_terbanyak == 'Tidak Berisiko':

        insight_dashboard = (
            f'Mayoritas siswa berada pada kategori '
            f'{kategori_terbanyak} '
            f'dengan total {jumlah_terbanyak} siswa.'
        )

    elif kategori_terbanyak == 'Rendah':

        insight_dashboard = (
            f'Sebagian besar siswa berada pada '
            f'kategori risiko rendah sebanyak '
            f'{jumlah_terbanyak} siswa.'
        )

    elif kategori_terbanyak == 'Sedang':

        insight_dashboard = (
            f'Kategori risiko sedang mendominasi '
            f'dengan jumlah {jumlah_terbanyak} siswa.'
        )

    elif kategori_terbanyak == 'Tinggi':

        insight_dashboard = (
            f'Perlu perhatian lebih lanjut karena '
            f'kategori risiko tinggi mendominasi '
            f'dengan total {jumlah_terbanyak} siswa.'
        )

    # =========================
    # FILTER KELAS
    # =========================

    daftar_kelas = (
        HasilAnalisis.objects
        .filter(
            analisis=analisis
        )
        .values_list(
            'kelas',
            flat=True
        )
        .distinct()
    )

    return render(
        request,
        'hasil_analisis.html',
        {
            'analisis': analisis,
            'data': data,
            'kelas_filter': kelas_filter,
            'daftar_kelas': daftar_kelas,
            'statistik_cluster': statistik_cluster,
            'total_siswa': total_siswa,
            'tidak_berisiko': tidak_berisiko,
            'risiko_rendah': risiko_rendah,
            'risiko_sedang': risiko_sedang,
            'risiko_tinggi': risiko_tinggi,
            'label_chart': label_chart_json,
            'data_chart': data_chart_json,
            'warna_chart': warna_chart_json,
            'scatter_data': scatter_data_json,
            'grafik_dendrogram': grafik_dendrogram,
            'dbi': dbi,
            'insight_dashboard': insight_dashboard,
        }
    )


# =========================
# RIWAYAT ANALISIS
# =========================

def riwayat_analisis(request):

    analisis = (
        Analisis.objects
        .all()
        .order_by('-id')
    )

    return render(
        request,
        'riwayat_analisis.html',
        {
            'analisis': analisis
        }
    )


# =========================
# DATA SISWA
# =========================

def data_siswa(request):

    data = HasilAnalisis.objects.all()

    # FILTER KELAS
    kelas = request.GET.get('kelas')

    if kelas:

        data = data.filter(
            kelas=kelas
        )

    # FILTER RISIKO
    risiko = request.GET.get('risiko')

    if risiko:

        data = data.filter(
            risiko=risiko
        )

    # SEARCH NAMA
    search = request.GET.get('search')

    if search:

        data = data.filter(
            nama__icontains=search
        )

    # ORDER
    data = data.order_by(
        'kelas',
        'nama'
    )

    daftar_kelas = (
        HasilAnalisis.objects
        .values_list(
            'kelas',
            flat=True
        )
        .distinct()
    )

    daftar_risiko = (
        HasilAnalisis.objects
        .values_list(
            'risiko',
            flat=True
        )
        .distinct()
    )

    return render(
        request,
        'data_siswa.html',
        {
            'data': data,
            'daftar_kelas': daftar_kelas,
            'daftar_risiko': daftar_risiko,
            'kelas_selected': kelas,
            'risiko_selected': risiko,
            'search': search
        }
    )

# =========================
# DETAIL SISWA
# =========================

def detail_siswa(request, nis):

    siswa = (
        HasilAnalisis.objects
        .filter(
            nis=nis
        )
        .order_by(
            'analisis__tahun_ajaran',
            'analisis__semester'
        )
    )

    if not siswa.exists():

        messages.error(
            request,
            'Data siswa tidak ditemukan.'
        )

        return redirect(
            'data_siswa'
        )

    siswa_terbaru = siswa.last()

    # =========================
    # DATA GRAFIK
    # =========================

    label_semester = []

    data_avg = []

    data_kehadiran = []

    data_ekstra = []

    for item in siswa:

        label_semester.append(
            f"{item.analisis.tahun_ajaran} - Semester {item.analisis.semester}"
        )

        data_avg.append(
            float(item.nilai_rata_rata)
        )

        data_kehadiran.append(
            float(item.persentase_kehadiran)
        )

        data_ekstra.append(
            float(item.skor_ekstrakurikuler)
        )

    # =========================
    # INSIGHT PERFORMA
    # =========================

    insight = None

    if siswa.count() >= 2:

        sebelumnya = siswa[
            siswa.count() - 2
        ]

        sekarang = siswa.last()

        # =========================
        # PERUBAHAN AVG
        # =========================

        if (
            sekarang.nilai_rata_rata >
            sebelumnya.nilai_rata_rata
        ):

            insight_avg = (
                'Nilai rata-rata siswa mengalami peningkatan.'
            )

        elif (
            sekarang.nilai_rata_rata <
            sebelumnya.nilai_rata_rata
        ):

            insight_avg = (
                'Nilai rata-rata siswa mengalami penurunan.'
            )

        else:

            insight_avg = (
                'Nilai rata-rata siswa cenderung stabil.'
            )

        # =========================
        # PERUBAHAN RISIKO
        # =========================

        if (
            sekarang.risiko ==
            sebelumnya.risiko
        ):

            insight_risiko = (
                f'Kategori risiko akademik tetap pada tingkat {sekarang.risiko}.'
            )

        else:

            insight_risiko = (
                f'Kategori risiko akademik berubah dari '
                f'{sebelumnya.risiko} menjadi '
                f'{sekarang.risiko}.'
            )

        # =========================
        # GABUNGKAN INSIGHT
        # =========================

        insight = (
            insight_avg
            + ' ' +
            insight_risiko
        )

    context = {

        'siswa': siswa,

        'siswa_terbaru': siswa_terbaru,

        'label_semester': json.dumps(
            label_semester
        ),

        'data_avg': json.dumps(
            data_avg
        ),

        'data_kehadiran': json.dumps(
            data_kehadiran
        ),

        'data_ekstra': json.dumps(
            data_ekstra
        ),

        'insight': insight

    }

    return render(
        request,
        'detail_siswa.html',
        context
    )

# =========================
# EXPORT EXCEL
# =========================

def export_excel(request):

    data = HasilAnalisis.objects.all()

    # =========================
    # FILTER KELAS
    # =========================

    kelas = request.GET.get('kelas')

    if kelas and kelas != 'None':

        data = data.filter(
            kelas=kelas
        )

    # =========================
    # FILTER RISIKO
    # =========================

    risiko = request.GET.get('risiko')

    if risiko and risiko != 'None':

        data = data.filter(
            risiko=risiko
        )

    # =========================
    # SEARCH NAMA
    # =========================

    search = request.GET.get('search')

    if search and search != 'None':

        data = data.filter(
            nama__icontains=search
        )

    # =========================
    # JIKA DATA KOSONG
    # =========================

    if not data.exists():

        messages.error(
            request,
            'Data tidak ditemukan untuk diexport.'
        )

        return redirect(
            'data_siswa'
        )

    # =========================
    # DATAFRAME
    # =========================

    df = pd.DataFrame(
        list(
            data.values(
                'nis',
                'nama',
                'kelas',
                'nilai_rata_rata',
                'persentase_kehadiran',
                'skor_ekstrakurikuler',
                'cluster',
                'risiko'
            )
        )
    )

    # =========================
    # UBAH NAMA KOLOM
    # =========================

    df.columns = [
        'No Induk',
        'Nama',
        'Kelas',
        'AVG',
        'ABSEN',
        'EKSTRAKURIKULER',
        'Cluster',
        'Risiko'
    ]

    # =========================
    # RESPONSE EXCEL
    # =========================

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    nama_file = 'hasil_analisis'

    if kelas and kelas != 'None':

        nama_file += f'_{kelas}'

    if risiko and risiko != 'None':

        nama_file += f'_{risiko}'

    nama_file += '.xlsx'

    response[
        'Content-Disposition'
    ] = (
        f'attachment; filename={nama_file}'
    )

    # =========================
    # EXPORT EXCEL
    # =========================

    with pd.ExcelWriter(
        response,
        engine='openpyxl'
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name='Hasil Analisis'
        )

    return response