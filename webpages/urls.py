from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('hizmet/<slug:slug>/', views.detay, name='detay'),
    path('teklif-al/<slug:paket_slug>/', views.teklif_al, name='teklif_al'),
    path('teklif-talebi-olustur/', views.teklif_talebi_olustur, name='teklif_talebi_olustur'),
    path('kayit/', views.kayit_ol, name='kayit'),
    path('giris/', views.giris_yap, name='giris'),
    path('arama/', views.arama_sonuclari, name='arama'),
    path('profil/', views.profil, name='profil'),
    path('yorum-yap/<slug:paket_slug>/', views.yorum_yap, name='yorum_yap'),
    path('hakkimizda/', views.hakkimizda, name='hakkimizda'),
    path('iletisim/', views.iletisim, name='iletisim'),
    path('panel/', views.firma_dashboard, name='firma_dashboard'),
    path('firmalar/', views.firmalar, name='firmalar'),
    path('hizli-teklif/', views.hizli_teklif, name='hizli_teklif'),
    
    # Karşılaştırma İşlemleri
    path('karsilastirmaya-ekle/<slug:paket_slug>/', views.karsilastirmaya_ekle, name='karsilastirmaya_ekle'),
    path('karsilastirma/', views.karsilastirma_goruntule, name='karsilastirma_goruntule'),
    path('karsilastirmadan-cikar/<slug:paket_slug>/', views.karsilastirmadan_cikar, name='karsilastirmadan_cikar'),
    
    # Sipariş İşlemleri
    path('dinamik-siparis/<slug:paket_slug>/', views.dinamik_siparis, name='dinamik_siparis'),
    
    # Durum Güncellemeleri ve Onaylar (Arka plan işlemi olduğu için ID kalır)
    path('talep-durum/<int:talep_id>/<str:yeni_durum>/', views.talep_durum_guncelle, name='talep_durum_guncelle'),
    path('siparis-durum/<int:siparis_id>/<str:yeni_durum>/', views.siparis_durum_guncelle, name='siparis_durum_guncelle'),
    path('catering-teklif/<int:teklif_id>/kabul/', views.catering_teklifi_kabul_et, name='catering_teklifi_kabul_et'),
    
    # Esnaf ve Çıkış
    path('is-ortagimiz-olun/', views.is_ortagimiz_olun, name='is_ortagimiz_olun'),
    path('cikis-yap/', views.cikis_yap, name='cikis_yap'),
    path('firma/<slug:slug>/', views.firma_detay, name='firma_detay'),
    path('sartlar-ve-kosullar/', views.sartlar_kosullar, name='sartlar_kosullar'),
    path('kvkk-aydinlatma/', views.kvkk_aydinlatma, name='kvkk_aydinlatma'),
    path('api/siparis-durum-guncelle/', views.siparis_durum_guncelle_api, name='siparis_durum_guncelle_api'),
    path('siparis/revize-et/<int:siparis_id>/', views.teklif_revize_et, name='teklif_revize_et'),
    path('revize-yanitla/<int:talep_id>/', views.musteri_revize_yanitla, name='musteri_revize_yanitla'),
    path('bireysel/', views.bireysel_abonelik, name='bireysel_abonelik'),
    path('abonelik-gun-atla/<int:talep_id>/', views.abonelik_gun_atla, name='abonelik_gun_atla'),
    path('api/siparis-durum-guncelle/', views.siparis_durum_guncelle_api, name='siparis_durum_guncelle_api'),
    path('teklif-revize-et/<int:siparis_id>/', views.teklif_revize_et, name='teklif_revize_et'),
    path('musteri-revize-yanitla/<int:talep_id>/', views.musteri_revize_yanitla, name='musteri_revize_yanitla'),
    path('karsilastirma/', views.karsilastirma, name='karsilastirma'),
    path('api/favori/<int:paket_id>/', views.favori_islemi, name='favori_islemi'),
    path('api/bildirimler/', views.canli_bildirim_getir, name='canli_bildirimler'),
]