from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
import uuid


# 1. Hizmet / Kategori Modeli
class Hizmet(models.Model):
    baslik = models.CharField(max_length=100, verbose_name="Hizmet Başlığı")
    emoji = models.CharField(max_length=10, blank=True, null=True, verbose_name="Emoji")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    resim = models.ImageField(upload_to='hizmetler/', null=True, blank=True, verbose_name="Görsel")
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True, verbose_name="SEO URL")

    class Meta:
        verbose_name = "Hizmet"
        verbose_name_plural = "Hizmetler"

    def __str__(self):
        return self.baslik

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.baslik)}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)



# YENİ: Ek Hizmet Modeli
class EkHizmet(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Ek Hizmet (Örn: Garson)")
    fiyat = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Sabit bir fiyatı varsa girin, yoksa 0 bırakın.")

    class Meta:
        verbose_name = "Ek Hizmet"
        verbose_name_plural = "Ek Hizmetler"

    def __str__(self):
        return self.isim


# 2. Firma Modeli
class Firma(models.Model):
    sahibi = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='firma', verbose_name="Firma Sahibi")
    isim = models.CharField(max_length=100, verbose_name="Firma İsmi")
    puan = models.DecimalField(max_digits=3, decimal_places=1, default=5.0, verbose_name="Puan")
    logo = models.ImageField(upload_to='firmalar/', null=True, blank=True, verbose_name="Logo")
    
    # ZORUNLU ALANLAR
    sehir = models.CharField(max_length=50, verbose_name="Şehir") 
    telefon = models.CharField(max_length=15, verbose_name="Telefon Numarası")
    email = models.EmailField(max_length=255, verbose_name="E-Posta Adresi")
    adres = models.TextField(verbose_name="Açık Adres")
    
    aktif_mi = models.BooleanField(default=True, verbose_name="Siparişe Açık mı?")
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True, verbose_name="SEO URL")
    super_esnaf = models.BooleanField(default=False, verbose_name="Süper Esnaf Rozeti")
    one_cikan = models.BooleanField(default=False, verbose_name="Öne Çıkan Firma")
    
    # B2B BAŞARI METRİKLERİ
    teslimat_basarisi = models.IntegerField(default=98, verbose_name="Zamanında Teslimat Oranı (%)")
    hijyen_uyumu = models.IntegerField(default=100, verbose_name="Hijyen Uyumu (%)")
    tecrube_yili = models.IntegerField(default=10, verbose_name="Sektör Tecrübesi (Yıl)")

    class Meta:
        verbose_name = "Firma"
        verbose_name_plural = "Firmalar"

    def __str__(self):
        return self.isim
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.isim)}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


# 3. Paket Modeli
class Paket(models.Model):
    SIPARIS_TURU_SECENEKLERI = (
        ('ANLIK', 'Anlık teslimat'),
        ('CATERING', 'Catering / etkinlik talebi'),
    )
    # YENİ EKLENEN: Bireysel / Kurumsal Ayrımı
    HEDEF_KITLE_SECENEKLERI = [
        ('Kurumsal', 'Sadece Kurumsal (B2B)'),
        ('Bireysel', 'Sadece Bireysel (B2C)'),
        ('Tumu', 'Hem Kurumsal Hem Bireysel')
    ]
    hedef_kitle = models.CharField(max_length=15, choices=HEDEF_KITLE_SECENEKLERI, default='Kurumsal', verbose_name="Hedef Kitle")
    
    firma = models.ForeignKey(Firma, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Firma")
    hizmet = models.ForeignKey(Hizmet, on_delete=models.CASCADE, related_name='paketler', verbose_name="Hizmet Kategorisi")
    isim = models.CharField(max_length=100, verbose_name="Paket İsmi")
    aciklama = models.TextField(verbose_name="Açıklama")
    fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Fiyat (₺)")
    resim = models.ImageField(upload_to='paketler/', null=True, blank=True, verbose_name="Görsel")
    min_kisi_sayisi = models.IntegerField(default=1, verbose_name="Min. Kişi Sayısı")
    abonelik_mi = models.BooleanField(default=False, verbose_name="Abonelik mi?")
    
    # YENİ EKLENEN: Abonelik Uygunluk Durumu
    abonelik_uygun_mu = models.BooleanField(default=False, verbose_name="Aylık/Haftalık Aboneliğe Uygun Mu?")
    
    max_iskonto_orani = models.IntegerField(default=0, help_text="Yüzde olarak maksimum indirim oranı (Örn: 25). İndirim yoksa 0 bırakın.", verbose_name="Maks. İskonto Oranı (%)")
    siparis_turu = models.CharField(max_length=10, choices=SIPARIS_TURU_SECENEKLERI, default='CATERING', verbose_name="Satış Türü")
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True, verbose_name="SEO URL")

    class Meta:
        verbose_name = "Paket"
        verbose_name_plural = "Paketler"

    def __str__(self):
        return f"{self.isim} - {self.fiyat} ₺"

    @property
    def ortalama_puan(self):
        yorumlar = self.yorumlar.all()
        if yorumlar:
            return round(sum(yorum.puan for yorum in yorumlar) / len(yorumlar), 1)
        return 0

    @property
    def yorum_sayisi(self):
        return self.yorumlar.count()
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{slugify(self.isim)}-{uuid.uuid4().hex[:6]}"
        super().save(*args, **kwargs)


class PaketTalebi(models.Model):
    DURUM_SECENEKLERI = [
        ('Bekliyor', 'Bekliyor'),
        ('Hazırlanıyor', 'Hazırlanıyor'),
        ('Aktif', 'Abonelik Aktif'), # YENİ: Abonelikler için
        ('Tamamlandı', 'Tamamlandı'),
        ('Reddedildi', 'Reddedildi'),
        ('Revize Edildi', 'Revize Edildi'), 
    ]

    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Kullanıcı")
    paket = models.ForeignKey(Paket, on_delete=models.CASCADE, related_name='talepler', verbose_name="Paket")
    isim = models.CharField(max_length=100, verbose_name="Ad Soyad")
    telefon = models.CharField(max_length=15, verbose_name="Telefon")
    kisi_sayisi = models.IntegerField(default=1, verbose_name="Kişi Sayısı")
    etkinlik_tarihi = models.DateField(null=True, blank=True, verbose_name="Etkinlik/Başlangıç Tarihi")
    mesaj = models.TextField(blank=True, null=True, verbose_name="Müşteri Notu")
    
    # Ek Hizmetler ve Teslimat Seçenekleri
    secilen_ek_hizmetler = models.ManyToManyField(EkHizmet, blank=True, verbose_name="İstenen Ek Hizmetler")
    TESLIMAT_SEKLI_SECENEKLERI = [
        ('Sıcak', 'Sıcak Teslimat'),
        ('Soğuk', 'Soğuk Teslimat (Isıtılmaya Hazır)'),
    ]
    teslimat_sekli = models.CharField(max_length=15, choices=TESLIMAT_SEKLI_SECENEKLERI, null=True, blank=True, verbose_name="Teslimat Şekli")
    
    # YENİ EKLENEN/DÜZENLENEN: ABONELİK TAKİP ALANLARI
    abonelik_suresi = models.IntegerField(null=True, blank=True, verbose_name="Toplam Abonelik Süresi (Gün)")
    kalan_abonelik_gunu = models.IntegerField(null=True, blank=True, verbose_name="Kalan Gün Sayısı")
    son_teslimat_tarihi = models.DateField(null=True, blank=True, verbose_name="Son Teslim Edilen Tarih")
    
    # Pazarlık ve Kanban alanları
    durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='Bekliyor', verbose_name="Durum")
    revize_fiyat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Revize Fiyat (₺)")
    revize_notu = models.TextField(blank=True, null=True, verbose_name="Firma Revize Notu")
    
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    class Meta:
        verbose_name = "Paket Talebi"
        verbose_name_plural = "Paket Talepleri"

    def __str__(self):
        return f"{self.isim} - {self.paket.isim} ({self.durum})"
        
    def save(self, *args, **kwargs):
        # Abonelik oluşturulurken kalan gün sayısı, toplam süreye eşit başlar
        if self.abonelik_suresi and self.kalan_abonelik_gunu is None:
            self.kalan_abonelik_gunu = self.abonelik_suresi
            
        # Kalan gün sıfırlanırsa aboneliği tamamlandı olarak işaretle
        if self.abonelik_suresi and self.kalan_abonelik_gunu is not None and self.kalan_abonelik_gunu <= 0:
            self.durum = 'Tamamlandı'
            self.kalan_abonelik_gunu = 0
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Paket Talebi"
        verbose_name_plural = "Paket Talepleri"

    def __str__(self):
        return f"{self.isim} - {self.paket.isim} ({self.durum})"


# 5. Teklif Talebi Modeli
class TeklifTalebi(models.Model):
    DURUM_SECENEKLERI = (
        ('Bekliyor', 'Bekliyor'),
        ('Arandı', 'Müşteri Arandı'),
        ('Onaylandı', 'Onaylandı'),
        ('İptal', 'İptal Edildi'),
    )

    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Kullanıcı")
    isim = models.CharField(max_length=100, verbose_name="Ad Soyad")
    telefon = models.CharField(max_length=15, verbose_name="Telefon")
    etkinlik_tarihi = models.DateField(verbose_name="Etkinlik Tarihi")
    kisi_sayisi = models.IntegerField(verbose_name="Kişi Sayısı")
    mesaj = models.TextField(blank=True, null=True, verbose_name="Mesaj")
    durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='Bekliyor', verbose_name="Durum")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")

    class Meta:
        verbose_name = "Teklif Talebi"
        verbose_name_plural = "Teklif Talepleri"

    def __str__(self):
        return f"{self.isim} - {self.durum}"


# 6. Müşteri Yorum Sistemi
class Yorum(models.Model):
    paket = models.ForeignKey(Paket, on_delete=models.CASCADE, related_name='yorumlar', verbose_name="Paket")
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Kullanıcı")
    puan = models.IntegerField(choices=[(i, i) for i in range(1, 6)], default=5, verbose_name="Puan")
    yorum_metni = models.TextField(verbose_name="Yorum Metni")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Oluşturulma Tarihi")
    dogrulanmis_musteri = models.BooleanField(default=False, verbose_name="Doğrulanmış Müşteri")

    class Meta:
        verbose_name = "Yorum"
        verbose_name_plural = "Yorumlar"

    def __str__(self):
        return f"{self.kullanici.username} - {self.paket.isim} ({self.puan}/5)"


# 7. İletişim Mesajı Modeli
class IletisimMesaji(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Ad Soyad")
    email = models.EmailField(verbose_name="E-Posta")
    konu = models.CharField(max_length=200, verbose_name="Konu")
    mesaj = models.TextField(verbose_name="Mesaj")
    okundu_mu = models.BooleanField(default=False, verbose_name="Okundu mu?")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "İletişim Mesajı"
        verbose_name_plural = "İletişim Mesajları"

    def __str__(self):
        return f"{self.isim} - {self.konu}"


class Siparis(models.Model):
    DURUM_SECENEKLERI = (
        ('ODEME_BEKLIYOR', 'Ödeme bekliyor'),
        ('ONAYLANDI', 'Onaylandı'),
        ('HAZIRLANIYOR', 'Hazırlanıyor'),
        ('YOLDA', 'Yolda'),
        ('TESLIM_EDILDI', 'Teslim edildi'),
        ('IPTAL', 'İptal edildi'),
    )

    kullanici = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='siparisler')
    firma = models.ForeignKey(Firma, on_delete=models.SET_NULL, null=True, blank=True, related_name='siparisler')
    teslimat_adresi = models.TextField(verbose_name="Teslimat Adresi")
    telefon = models.CharField(max_length=20, verbose_name="Telefon")
    ara_toplam = models.DecimalField(max_digits=10, decimal_places=2)
    teslimat_ucreti = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    toplam_tutar = models.DecimalField(max_digits=10, decimal_places=2)
    durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='ODEME_BEKLIYOR')
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)
    guncellenme_tarihi = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sipariş"
        verbose_name_plural = "Siparişler"
        ordering = ['-olusturulma_tarihi']

    def __str__(self):
        return f"#{self.pk} - {self.firma.isim if self.firma else 'Silinmiş Firma'}"


class SiparisKalemi(models.Model):
    siparis = models.ForeignKey(Siparis, on_delete=models.CASCADE, related_name='kalemler')
    paket = models.ForeignKey(Paket, on_delete=models.SET_NULL, null=True, blank=True)
    paket_adi = models.CharField(max_length=100)
    birim_fiyat = models.DecimalField(max_digits=10, decimal_places=2)
    adet = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Sipariş Kalemi"
        verbose_name_plural = "Sipariş Kalemleri"

    @property
    def satir_toplami(self):
        return self.birim_fiyat * self.adet


class TeslimatAdresi(models.Model):
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teslimat_adresleri')
    baslik = models.CharField(max_length=50, default='Ev')
    sehir = models.CharField(max_length=50)
    ilce = models.CharField(max_length=50)
    mahalle = models.CharField(max_length=100)
    acik_adres = models.TextField()
    teslimat_notu = models.CharField(max_length=255, blank=True)
    varsayilan_mi = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Teslimat Adresi"
        verbose_name_plural = "Teslimat Adresleri"

    def __str__(self):
        return f"{self.baslik} - {self.sehir}/{self.ilce}"

    @property
    def tam_adres(self):
        return f"{self.mahalle}, {self.acik_adres}, {self.ilce}/{self.sehir}"


class CateringTeklifi(models.Model):
    DURUM_SECENEKLERI = (
        ('BEKLIYOR', 'Müşteri onayı bekleniyor'),
        ('KABUL', 'Kabul edildi'),
        ('RED', 'Reddedildi'),
        ('SURESI_DOLDU', 'Süresi doldu'),
    )
    talep = models.ForeignKey(PaketTalebi, on_delete=models.CASCADE, related_name='teklifler')
    firma = models.ForeignKey(Firma, on_delete=models.SET_NULL, null=True, blank=True, related_name='catering_teklifleri')
    toplam_tutar = models.DecimalField(max_digits=10, decimal_places=2)
    menu_detayi = models.TextField()
    gecerlilik_tarihi = models.DateField()
    durum = models.CharField(max_length=15, choices=DURUM_SECENEKLERI, default='BEKLIYOR')
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Catering Teklifi"
        verbose_name_plural = "Catering Teklifleri"


class CateringRezervasyonu(models.Model):
    teklif = models.OneToOneField(CateringTeklifi, on_delete=models.SET_NULL, null=True, blank=True, related_name='rezervasyon')
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)
    notlar = models.TextField(blank=True)

    class Meta:
        verbose_name = "Catering Rezervasyonu"
        verbose_name_plural = "Catering Rezervasyonları"


# 9. Karşılaştırma Modeli
class Karsilastirma(models.Model):
    kullanici = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Kullanıcı")
    paketler = models.ManyToManyField(Paket, verbose_name="Paketler")

    class Meta:
        verbose_name = "Karşılaştırma"
        verbose_name_plural = "Karşılaştırmalar"

    def __str__(self):
        return f"{self.kullanici.username if self.kullanici else 'Misafir'} Karşılaştırma Listesi"


# 10. Esnaf Başvuru Modeli
class EsnafBasvurusu(models.Model):
    DURUM_SECENEKLERI = (
        ('Bekliyor', 'Bekliyor'),
        ('Onaylandı', 'Onaylandı'),
        ('Reddedildi', 'Reddedildi'),
    )

    ad_soyad = models.CharField(max_length=100, verbose_name="Yetkili Adı Soyadı")
    firma_adi = models.CharField(max_length=150, verbose_name="Firma / Restoran Adı")
    telefon = models.CharField(max_length=15, verbose_name="Telefon Numarası")
    email = models.EmailField(verbose_name="E-posta Adresi")
    mesaj = models.TextField(blank=True, null=True, verbose_name="Eklemek İstedikleriniz")
    durum = models.CharField(max_length=15, choices=DURUM_SECENEKLERI, default='Bekliyor', verbose_name="Durum")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Başvuru Tarihi")

    class Meta:
        verbose_name = "Esnaf Başvurusu"
        verbose_name_plural = "Esnaf Başvuruları"

    def __str__(self):
        return f"{self.firma_adi} - {self.ad_soyad}"


class SistemLog(models.Model):
    kullanici = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İşlemi Yapan")
    islem_detayi = models.CharField(max_length=255, verbose_name="İşlem Detayı")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Sistem Log Kaydı"
        verbose_name_plural = "Sistem Logları"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.kullanici} - {self.islem_detayi}"
    
# 11. Admin Finans Paneli (Proxy Model)
class FinansRaporu(PaketTalebi):
    class Meta:
        proxy = True
        verbose_name = "Finans ve Performans Paneli"
        verbose_name_plural = "Finans ve Performans Paneli"

# --- OTOMATİK GÖRSEL SIKIŞTIRMA VE WEBP DÖNÜŞÜM SİNYALLERİ ---
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.files.base import ContentFile
from io import BytesIO
from PIL import Image
import os

def compress_to_webp(image_field):
    """Görseli sıkıştırıp WebP formatına çeviren ana fonksiyon"""
    # Görsel yoksa veya zaten webp ise işlem yapma
    if not image_field or image_field.name.lower().endswith('.webp'):
        return

    try:
        img = Image.open(image_field)
        
        # PNG gibi şeffaf (Alpha) kanallı resimleri RGB'ye çevir ki arka plan siyah olmasın
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Çok büyük resimleri sınırla (Maksimum 1200x1200 piksel)
        img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
        
        # Sıkıştırılmış veriyi bellekte (RAM) tut
        output = BytesIO()
        img.save(output, format='WEBP', quality=75, optimize=True)
        output.seek(0)
        
        # Dosya uzantısını değiştir (.webp yap)
        yeni_isim = os.path.splitext(os.path.basename(image_field.name))[0] + '.webp'
        
        # İşlenmiş resmi kaydet (save=False döngüyü engeller)
        image_field.save(yeni_isim, ContentFile(output.read()), save=False)
        
    except Exception as e:
        print(f"Görsel sıkıştırma hatası: {e}")

# Hizmet Görsellerini Dinle
@receiver(pre_save, sender=Hizmet)
def hizmet_resim_optimize(sender, instance, **kwargs):
    compress_to_webp(instance.resim)


# Firma Logolarını Dinle
@receiver(pre_save, sender=Firma)
def firma_logo_optimize(sender, instance, **kwargs):
    compress_to_webp(instance.logo)

# Paket Görsellerini Dinle
@receiver(pre_save, sender=Paket)
def paket_resim_optimize(sender, instance, **kwargs):
    compress_to_webp(instance.resim)

class GenelTeklifTalebi(models.Model):
    etkinlik_turu = models.CharField(max_length=100, verbose_name="Etkinlik Türü")
    sehir = models.CharField(max_length=50, verbose_name="Şehir")
    kisi_sayisi = models.IntegerField(verbose_name="Kişi Sayısı")
    tarih = models.DateField(verbose_name="Etkinlik Tarihi")
    ogun = models.CharField(max_length=50, verbose_name="Öğün Tercihi")
    isim = models.CharField(max_length=100, verbose_name="Ad Soyad")
    telefon = models.CharField(max_length=15, verbose_name="Telefon")
    notlar = models.TextField(blank=True, null=True, verbose_name="Ekstra Talepler")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Talep Tarihi")

    class Meta:
        verbose_name = "Hızlı Teklif Talebi"
        verbose_name_plural = "Hızlı Teklif Talepleri"
        ordering = ['-olusturulma_tarihi']

    def __str__(self):
        return f"{self.isim} - {self.sehir} ({self.etkinlik_turu})"

# Tadım Randevusu Modeli
class TadimRandevusu(models.Model):
    DURUM_SECENEKLERI = (
        ('Bekliyor', 'Onay Bekliyor'),
        ('Onaylandı', 'Randevu Onaylandı'),
        ('İptal', 'İptal Edildi'),
    )
    paket = models.ForeignKey(Paket, on_delete=models.CASCADE, related_name='tadim_randevulari', verbose_name="İncelenen Paket")
    isim = models.CharField(max_length=100, verbose_name="Yetkili Adı Soyadı")
    telefon = models.CharField(max_length=15, verbose_name="Telefon Numarası")
    sirket = models.CharField(max_length=150, blank=True, null=True, verbose_name="Kurum / Şirket Adı")
    tarih = models.DateField(verbose_name="İstenen Tadım Tarihi")
    durum = models.CharField(max_length=20, choices=DURUM_SECENEKLERI, default='Bekliyor', verbose_name="Durum")
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tadım Randevusu"
        verbose_name_plural = "Tadım Randevuları"
        ordering = ['-olusturulma_tarihi']

    def __str__(self):
        return f"{self.sirket or self.isim} - {self.tarih} Tadım Talebi"

class Bildirim(models.Model):
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bildirimler', verbose_name="Kullanıcı")
    baslik = models.CharField(max_length=100, verbose_name="Başlık")
    mesaj = models.TextField(verbose_name="Mesaj")
    okundu_mu = models.BooleanField(default=False, verbose_name="Okundu mu?")
    link = models.CharField(max_length=255, blank=True, null=True, verbose_name="Yönlendirme Linki")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")

    class Meta:
        verbose_name = "Bildirim"
        verbose_name_plural = "Bildirimler"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.kullanici.username} - {self.baslik}"


from django.db import models
from django.contrib.auth.models import User

# (Mevcut Paket vb. modellerin burada duruyor...)

class Favori(models.Model):
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorileri')
    paket = models.ForeignKey('Paket', on_delete=models.CASCADE)
    klasor_adi = models.CharField(max_length=100, default='Tüm Favoriler') # İleride klasörleme için
    eklenme_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('kullanici', 'paket') # Bir paket sadece bir kez favorilenebilir

    def __str__(self):
        return f"{self.kullanici.username} - {self.paket.isim}"

class Bildirim(models.Model):
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bildirimleri')
    baslik = models.CharField(max_length=255)
    mesaj = models.TextField()
    okundu_mu = models.BooleanField(default=False)
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True) # Tıklayınca gideceği sayfa

    def __str__(self):
        return f"{self.kullanici.username} - {self.baslik}"