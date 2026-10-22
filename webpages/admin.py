from django.contrib import admin
from django.contrib.auth.models import Group
from django.template.response import TemplateResponse
from django.db.models import Sum
from django.contrib import admin
from .models import TadimRandevusu
from django.contrib import admin
from .models import EkHizmet 

admin.site.register(EkHizmet)
# Karmaşık Gruplar menüsünü gizler
admin.site.unregister(Group)

from unfold.admin import ModelAdmin
from unfold.admin import TabularInline
from unfold.decorators import display

# --- 2FA (Karekod) Cihazını Panele Ekleme ---
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_totp.admin import TOTPDeviceAdmin

# Varsayılan tasarımı silip Unfold temamızı ekliyoruz
try:
    admin.site.unregister(TOTPDevice)
except admin.sites.NotRegistered:
    pass

@admin.register(TOTPDevice)
class CustomTOTPDeviceAdmin(TOTPDeviceAdmin, ModelAdmin):
    pass
# -------------------------------------------

from .models import (
    Hizmet, Firma, Paket, PaketTalebi, TeklifTalebi, Yorum,
    IletisimMesaji, EsnafBasvurusu,
    CateringTeklifi, CateringRezervasyonu, SistemLog,
    Siparis, FinansRaporu
)


@admin.register(Hizmet)
class HizmetAdmin(ModelAdmin):
    pass


@admin.register(Firma)
class FirmaAdmin(ModelAdmin):
    list_display = ('isim', 'sahibi', 'puan', 'sehir', 'aktif_mi_etiketi')
    list_filter = ('aktif_mi', 'sehir')

    @display(description="Siparişe Açık", boolean=True)
    def aktif_mi_etiketi(self, obj):
        return obj.aktif_mi


@admin.register(Paket)
class PaketAdmin(ModelAdmin):
    # YENİ: hedef_kitle_etiketi listeye eklendi
    list_display = ('isim', 'firma', 'hedef_kitle_etiketi', 'fiyat', 'hizmet', 'siparis_turu')
    # YENİ: hedef_kitle filtreye eklendi
    list_filter = ('hedef_kitle', 'hizmet', 'firma', 'siparis_turu')

    # YENİ: Unfold temasına uygun renkli rozetler eklendi
    @display(
        description="Hedef Kitle",
        label={
            "Kurumsal": "primary",  # Mavi
            "Bireysel": "success",  # Yeşil
            "Tumu": "info",         # Turkuaz
        }
    )
    def hedef_kitle_etiketi(self, obj):
        return obj.hedef_kitle

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(firma__sahibi=request.user)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(request.user, 'firma'):
            obj.firma = request.user.firma
        super().save_model(request, obj, form, change)


@admin.register(PaketTalebi)
class PaketTalebiAdmin(ModelAdmin):
    list_display = ('isim', 'paket', 'telefon', 'durum_etiketi', 'olusturulma_tarihi')
    list_filter = ('durum',)

    @display(
        description="Durum",
        label={
            "Bekliyor": "warning",
            "Ulaşıldı": "info",
            "Tamamlandı": "success",
            "İptal": "danger",
        }
    )
    def durum_etiketi(self, obj):
        return obj.durum


@admin.register(TeklifTalebi)
class TeklifTalebiAdmin(ModelAdmin):
    list_display = ('isim', 'telefon', 'etkinlik_tarihi', 'durum', 'olusturulma_tarihi')
    list_editable = ('durum',)
    list_filter = ('durum',)


@admin.register(Yorum)
class YorumAdmin(ModelAdmin):
    list_display = ('kullanici', 'paket', 'puan', 'olusturulma_tarihi')
    list_filter = ('puan',)


@admin.register(IletisimMesaji)
class IletisimMesajiAdmin(ModelAdmin):
    list_display = ('isim', 'konu', 'email', 'okundu_mu', 'tarih')
    list_filter = ('okundu_mu', 'tarih')
    search_fields = ('isim', 'email', 'konu')


@admin.register(EsnafBasvurusu)
class EsnafBasvurusuAdmin(ModelAdmin):
    list_display = ('firma_adi', 'ad_soyad', 'telefon', 'durum_etiketi', 'tarih')
    list_filter = ('durum', 'tarih')
    search_fields = ('firma_adi', 'ad_soyad')

    @display(
        description="Başvuru Durumu",
        label={
            "Bekliyor": "warning",
            "Onaylandı": "success",
            "Reddedildi": "danger",
        }
    )
    def durum_etiketi(self, obj):
        return obj.durum


@admin.register(CateringTeklifi)
class CateringTeklifiAdmin(ModelAdmin):
    list_display = ('talep', 'firma', 'toplam_tutar', 'durum_etiketi', 'gecerlilik_tarihi')
    list_filter = ('durum', 'firma')

    @display(
        description="Teklif Durumu",
        label={
            "BEKLIYOR": "warning",
            "KABUL": "success",
            "RED": "danger",
            "SURESI_DOLDU": "info",
        }
    )
    def durum_etiketi(self, obj):
        return obj.durum


@admin.register(CateringRezervasyonu)
class CateringRezervasyonuAdmin(ModelAdmin):
    list_display = ('teklif', 'olusturulma_tarihi')


@admin.register(SistemLog)
class SistemLogAdmin(ModelAdmin):
    list_display = ('kullanici', 'islem_detayi', 'tarih')
    list_filter = ('tarih',)
    search_fields = ('kullanici__username', 'islem_detayi')


@admin.register(FinansRaporu)
class FinansRaporuAdmin(ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        toplam_talep = PaketTalebi.objects.count()
        tamamlanan_talep = PaketTalebi.objects.filter(durum='Tamamlandı').count()
        
        ciro_query = Siparis.objects.filter(durum='TESLIM_EDILDI').aggregate(total=Sum('toplam_tutar'))
        toplam_ciro = ciro_query['total'] or 0

        aktif_firma = Firma.objects.filter(aktif_mi=True).count()
        toplam_paket = Paket.objects.count()

        context = dict(
            self.admin_site.each_context(request),
            title='YemekVar Finans ve Sistem Raporu',
            toplam_talep=toplam_talep,
            tamamlanan_talep=tamamlanan_talep,
            toplam_ciro=toplam_ciro,
            aktif_firma=aktif_firma,
            toplam_paket=toplam_paket,
        )
        return TemplateResponse(request, "admin/finans_paneli.html", context)

from .models import GenelTeklifTalebi

@admin.register(GenelTeklifTalebi)
class GenelTeklifTalebiAdmin(admin.ModelAdmin):
    list_display = ('isim', 'sehir', 'etkinlik_turu', 'kisi_sayisi', 'tarih', 'olusturulma_tarihi')
    list_filter = ('sehir', 'etkinlik_turu', 'olusturulma_tarihi')
    search_fields = ('isim', 'telefon', 'sehir')

@admin.register(TadimRandevusu)
class TadimRandevusuAdmin(admin.ModelAdmin):
    list_display = ('isim', 'sirket', 'telefon', 'paket', 'tarih', 'durum', 'olusturulma_tarihi')
    list_filter = ('durum', 'tarih')
    search_fields = ('isim', 'sirket', 'telefon')