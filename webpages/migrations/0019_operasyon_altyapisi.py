from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [('webpages', '0018_anlik_siparisler')]

    operations = [
        migrations.AddField(
            model_name='firma', name='aktif_mi',
            field=models.BooleanField(default=True, verbose_name='Siparişe Açık mı?'),
        ),
        migrations.CreateModel(
            name='TeslimatAdresi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('baslik', models.CharField(default='Ev', max_length=50)),
                ('sehir', models.CharField(max_length=50)),
                ('ilce', models.CharField(max_length=50)),
                ('mahalle', models.CharField(max_length=100)),
                ('acik_adres', models.TextField()),
                ('teslimat_notu', models.CharField(blank=True, max_length=255)),
                ('varsayilan_mi', models.BooleanField(default=False)),
                ('kullanici', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teslimat_adresleri', to='auth.user')),
            ],
            options={'verbose_name': 'Teslimat Adresi', 'verbose_name_plural': 'Teslimat Adresleri'},
        ),
        migrations.CreateModel(
            name='CateringTeklifi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('toplam_tutar', models.DecimalField(decimal_places=2, max_digits=10)),
                ('menu_detayi', models.TextField()),
                ('gecerlilik_tarihi', models.DateField()),
                ('durum', models.CharField(choices=[('BEKLIYOR', 'Müşteri onayı bekleniyor'), ('KABUL', 'Kabul edildi'), ('RED', 'Reddedildi'), ('SURESI_DOLDU', 'Süresi doldu')], default='BEKLIYOR', max_length=15)),
                ('olusturulma_tarihi', models.DateTimeField(auto_now_add=True)),
                ('firma', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='catering_teklifleri', to='webpages.firma')),
                ('talep', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teklifler', to='webpages.pakettalebi')),
            ],
            options={'verbose_name': 'Catering Teklifi', 'verbose_name_plural': 'Catering Teklifleri'},
        ),
        migrations.CreateModel(
            name='CateringRezervasyonu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('olusturulma_tarihi', models.DateTimeField(auto_now_add=True)),
                ('notlar', models.TextField(blank=True)),
                ('teklif', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='rezervasyon', to='webpages.cateringteklifi')),
            ],
            options={'verbose_name': 'Catering Rezervasyonu', 'verbose_name_plural': 'Catering Rezervasyonları'},
        ),
    ]
