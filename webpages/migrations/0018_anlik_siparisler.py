# Generated manually for the split catering and instant-delivery flows.
from django.db import migrations, models
import django.db.models.deletion


def birlesik_sepet_kalemleri(apps, schema_editor):
    """Önceden oluşmuş yinelenen sepet kalemlerini kayıpsız birleştirir."""
    SepetElemani = apps.get_model('webpages', 'SepetElemani')
    for sepet_id, paket_id in SepetElemani.objects.values_list('sepet_id', 'paket_id').distinct():
        kalemler = list(SepetElemani.objects.filter(sepet_id=sepet_id, paket_id=paket_id).order_by('id'))
        if len(kalemler) > 1:
            ilk_kalem = kalemler[0]
            ilk_kalem.adet = sum(kalem.adet for kalem in kalemler)
            ilk_kalem.save(update_fields=['adet'])
            SepetElemani.objects.filter(id__in=[kalem.id for kalem in kalemler[1:]]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('webpages', '0017_esnafbasvurusu'),
    ]

    operations = [
        migrations.AddField(
            model_name='paket',
            name='siparis_turu',
            field=models.CharField(
                choices=[('ANLIK', 'Anlık teslimat'), ('CATERING', 'Catering / etkinlik talebi')],
                default='CATERING', max_length=10, verbose_name='Satış Türü',
            ),
        ),
        migrations.AlterField(
            model_name='paket',
            name='hizmet',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='paketler', to='webpages.hizmet', verbose_name='Hizmet Kategorisi'),
        ),
        migrations.RunPython(birlesik_sepet_kalemleri, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='sepetelemani',
            constraint=models.UniqueConstraint(fields=('sepet', 'paket'), name='tekil_sepet_paketi'),
        ),
        migrations.CreateModel(
            name='Siparis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('teslimat_adresi', models.TextField(verbose_name='Teslimat Adresi')),
                ('telefon', models.CharField(max_length=20, verbose_name='Telefon')),
                ('ara_toplam', models.DecimalField(decimal_places=2, max_digits=10)),
                ('teslimat_ucreti', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('toplam_tutar', models.DecimalField(decimal_places=2, max_digits=10)),
                ('durum', models.CharField(choices=[('ODEME_BEKLIYOR', 'Ödeme bekliyor'), ('ONAYLANDI', 'Onaylandı'), ('HAZIRLANIYOR', 'Hazırlanıyor'), ('YOLDA', 'Yolda'), ('TESLIM_EDILDI', 'Teslim edildi'), ('IPTAL', 'İptal edildi')], default='ODEME_BEKLIYOR', max_length=20)),
                ('olusturulma_tarihi', models.DateTimeField(auto_now_add=True)),
                ('guncellenme_tarihi', models.DateTimeField(auto_now=True)),
                ('firma', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='siparisler', to='webpages.firma')),
                ('kullanici', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='siparisler', to='auth.user')),
            ],
            options={'verbose_name': 'Sipariş', 'verbose_name_plural': 'Siparişler', 'ordering': ['-olusturulma_tarihi']},
        ),
        migrations.CreateModel(
            name='SiparisKalemi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('paket_adi', models.CharField(max_length=100)),
                ('birim_fiyat', models.DecimalField(decimal_places=2, max_digits=10)),
                ('adet', models.PositiveIntegerField(default=1)),
                ('paket', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='webpages.paket')),
                ('siparis', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kalemler', to='webpages.siparis')),
            ],
            options={'verbose_name': 'Sipariş Kalemi', 'verbose_name_plural': 'Sipariş Kalemleri'},
        ),
    ]
