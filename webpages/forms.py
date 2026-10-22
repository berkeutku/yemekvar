from django import forms
from .models import Paket, IletisimMesaji, PaketTalebi, TeslimatAdresi, CateringTeklifi, EkHizmet


# Paket ekleme formu (Bootstrap 5 sınıflarıyla optimize edildi)
class PaketEkleForm(forms.ModelForm):
    class Meta:
        model = Paket 
        # 'abonelik_uygun_mu' eklendi
        fields = ['hizmet', 'isim', 'aciklama', 'fiyat', 'resim', 'min_kisi_sayisi', 'siparis_turu', 'abonelik_uygun_mu']
        widgets = {
            'hizmet': forms.Select(attrs={'class': 'form-select bg-light border-0 py-2 rounded-pill'}),
            'isim': forms.TextInput(attrs={'class': 'form-control bg-light border-0 py-2 px-3 rounded-pill', 'placeholder': 'Örn: 50 Kişilik Lüks Kokteyl'}),
            'aciklama': forms.Textarea(attrs={'class': 'form-control bg-light border-0 p-3 rounded-4', 'rows': 3, 'placeholder': 'Paket içeriği hakkında detaylar...'}),
            'fiyat': forms.NumberInput(attrs={'class': 'form-control bg-light border-0 py-2 px-3 rounded-pill'}),
            'resim': forms.FileInput(attrs={'class': 'form-control bg-light border-0 py-2 px-3 rounded-pill'}),
            'min_kisi_sayisi': forms.NumberInput(attrs={'class': 'form-control bg-light border-0 py-2 px-3 rounded-pill', 'min': 1}),
            'siparis_turu': forms.Select(attrs={'class': 'form-select bg-light border-0 py-2 rounded-pill'}),
            'abonelik_uygun_mu': forms.CheckboxInput(attrs={'class': 'form-check-input fs-5'}),
        }


class IletisimForm(forms.ModelForm):
    class Meta:
        model = IletisimMesaji
        fields = ['isim', 'email', 'konu', 'mesaj']
        widgets = {
            'isim': forms.TextInput(attrs={'class': 'form-control bg-light border-0 py-2 px-3 rounded-pill', 'placeholder': 'Adınız Soyadınız'}),
            'email': forms.EmailInput(attrs={'class': 'form-control bg-light border-0 py-2 px-3 rounded-pill', 'placeholder': 'ornek@email.com'}),
            'konu': forms.TextInput(attrs={'class': 'form-control bg-light border-0 py-2 px-3 rounded-pill', 'placeholder': 'Konu'}),
            'mesaj': forms.Textarea(attrs={'class': 'form-control bg-light border-0 py-3 px-3 rounded-4', 'rows': 5, 'placeholder': 'Mesajınızı buraya yazın...'}),
        }


class PaketTalebiForm(forms.ModelForm):
    class Meta:
        model = PaketTalebi
        # YENİ EKLENEN: 'secilen_ek_hizmetler' ve 'abonelik_suresi' eklendi
        fields = ['isim', 'telefon', 'kisi_sayisi', 'etkinlik_tarihi', 'mesaj', 'secilen_ek_hizmetler', 'abonelik_suresi']
        widgets = {
            'etkinlik_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-control rounded-pill'}),
            'secilen_ek_hizmetler': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}), # Checkbox yapısı
            'abonelik_suresi': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Örn: 20 (Sadece abonelik paketleri için)'}),
        }

    def clean_kisi_sayisi(self):
        kisi_sayisi = self.cleaned_data['kisi_sayisi']
        if kisi_sayisi < 1:
            raise forms.ValidationError('Kişi sayısı en az 1 olmalıdır.')
        return kisi_sayisi

    def clean_etkinlik_tarihi(self):
        etkinlik_tarihi = self.cleaned_data['etkinlik_tarihi']
        # Abonelik siparişlerinde tarih opsiyonel olabilir veya ileri bir tarih girilebilir, ama standart kontrolü koruyoruz:
        if etkinlik_tarihi:
            from datetime import date
            if etkinlik_tarihi < date.today():
                raise forms.ValidationError('Etkinlik tarihi geçmiş olamaz.')
        return etkinlik_tarihi


class TeslimatAdresiForm(forms.ModelForm):
    class Meta:
        model = TeslimatAdresi
        fields = ['baslik', 'sehir', 'ilce', 'mahalle', 'acik_adres', 'teslimat_notu', 'varsayilan_mi']


class CateringTeklifiForm(forms.ModelForm):
    class Meta:
        model = CateringTeklifi
        fields = ['toplam_tutar', 'menu_detayi', 'gecerlilik_tarihi']
        widgets = {
            'gecerlilik_tarihi': forms.DateInput(attrs={'type': 'date'}),
        }

class BireyselAbonelikForm(forms.ModelForm):
    class Meta:
        model = PaketTalebi
        fields = ['isim', 'telefon', 'etkinlik_tarihi', 'abonelik_suresi', 'teslimat_sekli', 'mesaj']
        widgets = {
            'isim': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': 'Adınız Soyadınız'}),
            'telefon': forms.TextInput(attrs={'class': 'form-control rounded-pill', 'placeholder': '05XX XXX XX XX'}),
            'etkinlik_tarihi': forms.DateInput(attrs={'type': 'date', 'class': 'form-control rounded-pill'}),
            'abonelik_suresi': forms.NumberInput(attrs={'class': 'form-control rounded-pill', 'min': 20, 'value': 20}),
            'teslimat_sekli': forms.Select(attrs={'class': 'form-select rounded-pill'}),
            'mesaj': forms.Textarea(attrs={'class': 'form-control rounded-4', 'rows': 3, 'placeholder': 'Açık adresiniz ve varsa alerji/notlarınız...'}),
        }
        labels = {
            'etkinlik_tarihi': 'Abonelik Başlangıç Tarihi',
            'abonelik_suresi': 'Kaç Günlük Abonelik? (Min. 20)',
            'mesaj': 'Teslimat Adresi ve Ek Notlar'
        }

    def clean_abonelik_suresi(self):
        sure = self.cleaned_data.get('abonelik_suresi')
        if sure and sure < 20:
            raise forms.ValidationError("Ekonomik fiyatlandırma için abonelik minimum 20 günlük olmalıdır.")
        return sure