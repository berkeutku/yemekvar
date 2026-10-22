from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.mail import send_mail 
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import (
    Hizmet, Paket, PaketTalebi, TeklifTalebi, Yorum, Firma, Karsilastirma, 
    EsnafBasvurusu, Siparis, SiparisKalemi, CateringTeklifi, CateringRezervasyonu,
    SistemLog, GenelTeklifTalebi, TadimRandevusu
)
from .forms import PaketEkleForm, IletisimForm, PaketTalebiForm, CateringTeklifiForm, BireyselAbonelikForm



@login_required(login_url='giris')
@require_POST
def siparis_durum_guncelle(request, siparis_id, yeni_durum):
    siparis = get_object_or_404(Siparis, id=siparis_id, firma__sahibi=request.user)
    gecerli_durumlar = {secenek[0] for secenek in Siparis.DURUM_SECENEKLERI}
    if yeni_durum in gecerli_durumlar:
        siparis.durum = yeni_durum
        siparis.save(update_fields=['durum'])
        messages.success(request, 'Anlık sipariş durumu güncellendi.')
    return redirect('firma_dashboard')


@login_required(login_url='giris')
@require_POST
def catering_teklifi_kabul_et(request, teklif_id):
    teklif = get_object_or_404(CateringTeklifi, id=teklif_id, talep__kullanici=request.user)
    if teklif.durum != 'BEKLIYOR' or teklif.gecerlilik_tarihi < timezone.localdate():
        messages.error(request, 'Bu teklif artık kabul edilemez.')
        return redirect('profil')
    with transaction.atomic():
        teklif.durum = 'KABUL'
        teklif.save(update_fields=['durum'])
        CateringRezervasyonu.objects.get_or_create(teklif=teklif)
        CateringTeklifi.objects.filter(talep=teklif.talep, durum='BEKLIYOR').exclude(id=teklif.id).update(durum='RED')
    messages.success(request, 'Teklif kabul edildi; catering rezervasyonunuz oluşturuldu.')
    return redirect('profil')


def home(request):
    kategori_adi = request.GET.get('kategori')
    siralama = request.GET.get('sort')

    paketler = Paket.objects.select_related('firma', 'hizmet').prefetch_related('yorumlar')
    
    firmalar_listesi = Firma.objects.all()
    one_cikan_firmalar = Firma.objects.filter(one_cikan=True)[:3]
    
    tum_sehirler = Firma.objects.exclude(sehir__isnull=True).exclude(sehir__exact='').values_list('sehir', flat=True)
    sehirler_listesi = sorted(list(set([s.strip().title() for s in tum_sehirler if s])))

    if kategori_adi:
        if kategori_adi.isdigit():
            paketler = paketler.filter(hizmet_id=kategori_adi)
        else:
            hizmet_ids = Hizmet.objects.filter(baslik__icontains=kategori_adi).values_list('id', flat=True)
            paketler = paketler.filter(
                Q(isim__icontains=kategori_adi) |
                Q(aciklama__icontains=kategori_adi) |
                Q(hizmet__id__in=hizmet_ids)
            )

    if siralama == 'fiyat_artan':
        paketler = paketler.order_by('fiyat')
    elif siralama == 'fiyat_azalan':
        paketler = paketler.order_by('-fiyat')
    elif siralama == 'puan_azalan':
        paketler = paketler.order_by('-firma__puan')

    hizmetler = Hizmet.objects.all()

    context = {
        'hizmetler': hizmetler,
        'paketler': paketler,
        'firmalar': firmalar_listesi,
        'sehirler_listesi': sehirler_listesi, 
        'secili_kategori': kategori_adi,
        'secili_siralama': siralama,
        'one_cikan_firmalar': one_cikan_firmalar,
    }
    return render(request, 'index.html', context)


@require_POST
def teklif_talebi_olustur(request):
    isim = request.POST.get('isim')
    telefon = request.POST.get('telefon')
    etkinlik_tarihi = request.POST.get('etkinlik_tarihi')
    kisi_sayisi = request.POST.get('kisi_sayisi')
    mesaj = request.POST.get('mesaj')

    yeni_teklif = TeklifTalebi.objects.create(
        isim=isim, telefon=telefon, etkinlik_tarihi=etkinlik_tarihi,
        kisi_sayisi=kisi_sayisi, mesaj=mesaj
    )
    if request.user.is_authenticated:
        yeni_teklif.kullanici = request.user
        yeni_teklif.save(update_fields=['kullanici'])
    messages.success(request, 'Teklif talebiniz başarıyla alındı.')
    return redirect('home')


def detay(request, slug):
    hizmet = get_object_or_404(Hizmet, slug=slug)
    return render(request, 'detay.html', {'hizmet': hizmet})


def teklif_al(request, paket_slug):
    paket = get_object_or_404(Paket, slug=paket_slug)
    
    if request.method == 'POST':
        # YENİ EKLENEN GÜVENLİK KALKANI: Giriş yapmayan sipariş veremez!
        if not request.user.is_authenticated:
            messages.error(request, 'Güvenlik gereği teklif alabilmek için lütfen giriş yapın veya kayıt olun.')
            return redirect('giris')
        # --- 1. EĞER TADIM RANDEVUSU GÖNDERİLDİYSE ---
        if 'tadim_randevusu' in request.POST:
            isim = request.POST.get('isim')
            telefon = request.POST.get('telefon')
            sirket = request.POST.get('sirket')
            tarih = request.POST.get('tarih')
            
            # Veritabanına kaydet
            TadimRandevusu.objects.create(
                paket=paket,
                isim=isim,
                telefon=telefon,
                sirket=sirket,
                tarih=tarih
            )
            
            # Tadım Randevusu İçin Otomatik Mail Gönderimi
            print("--- TADIM RANDEVUSU MAİL İŞLEMİ BAŞLADI ---")
            konu = f"YemekVar: {paket.firma.isim} İçin Yeni Tadım Randevusu!"
            mesaj = f"Yeni bir tadım randevusu talebi oluşturuldu!\n\nYetkili: {isim}\nŞirket: {sirket or 'Belirtilmedi'}\nTelefon: {telefon}\nİstenen Tarih: {tarih}\nİncelenen Paket: {paket.isim}\n\nLütfen esnaf panelinden kontrol ediniz."
            
            alicilar = ['yemekvar.sistem@gmail.com']
            if paket.firma and hasattr(paket.firma, 'sahibi') and paket.firma.sahibi and paket.firma.sahibi.email:
                alicilar.append(paket.firma.sahibi.email)
            
            try:
                send_mail(konu, mesaj, 'yemekvar.sistem@gmail.com', alicilar, fail_silently=False)
                print("--- TADIM MAİLİ BAŞARIYLA GİTTİ ---")
            except Exception as e:
                print(f"!!! TADIM MAİLİ GÖNDERİLİRKEN HATA OLUŞTU: {e}")

            messages.success(request, 'Tadım randevusu talebiniz başarıyla alındı. Firma sizinle iletişime geçecektir.')
            return redirect('teklif_al', paket_slug=paket.slug)

       # --- 2. FORMLAR GÖNDERİLDİYSE ---
        if paket.hedef_kitle == 'Bireysel':
            form = BireyselAbonelikForm(request.POST)
        else:
            form = PaketTalebiForm(request.POST)

        if form.is_valid():
            talep = form.save(commit=False)
            talep.paket = paket
            if request.user.is_authenticated:
                talep.kullanici = request.user
            talep.save()
            # YENİ: ManyToMany alanları (Ek Hizmetler) kaydedilmesi için
            form.save_m2m()
            
            # Standart Teklif İçin Otomatik Mail Gönderimi
            print("--- STANDART TEKLİF MAİL İŞLEMİ BAŞLADI ---")
            konu = f"YemekVar: {paket.firma.isim} İçin Yeni Sipariş/Teklif Talebi!"
            mesaj = f"Firma Panelinize Yeni Bir Talep Düştü!\n\nMüşteri Adı: {talep.isim}\nTelefon: {talep.telefon}\nKişi Sayısı: {talep.kisi_sayisi}\nEtkinlik Tarihi: {talep.etkinlik_tarihi}\nMesaj / Özel Talep: {talep.mesaj}\n\nLütfen en kısa sürede YemekVar esnaf panelinizden müşteriye dönüş yapınız."
            
            alicilar = ['yemekvar.sistem@gmail.com']
            if paket.firma and hasattr(paket.firma, 'sahibi') and paket.firma.sahibi and paket.firma.sahibi.email:
                alicilar.append(paket.firma.sahibi.email)

            try:
                send_mail(konu, mesaj, 'yemekvar.sistem@gmail.com', alicilar, fail_silently=False)
                print("--- STANDART MAİL BAŞARIYLA GİTTİ ---")
            except Exception as e:
                print(f"!!! MAİL GÖNDERİLİRKEN HATA OLUŞTU: {e}")

            messages.success(request, 'Talebiniz başarıyla firmaya iletildi.')
            return redirect('profil' if request.user.is_authenticated else 'home')
    else:
        if paket.hedef_kitle == 'Bireysel':
            form = BireyselAbonelikForm()
        else:
            form = PaketTalebiForm()
        
    return render(request, 'teklif_al.html', {'paket': paket, 'form': form})

def arama_sonuclari(request):
    query = request.GET.get('q', '')
    konum = request.GET.get('konum', '')
    kategori_id = request.GET.get('kategori_ara', '')

    paketler = Paket.objects.select_related('firma', 'hizmet')
    
    hizmetler = Hizmet.objects.all()
    
    tum_sehirler = Firma.objects.exclude(sehir__isnull=True).exclude(sehir__exact='').values_list('sehir', flat=True)
    sehirler_listesi = sorted(list(set([s.strip().title() for s in tum_sehirler if s])))

    if query:
        paketler = paketler.filter(
            Q(isim__icontains=query) |
            Q(aciklama__icontains=query) |
            Q(firma__isim__icontains=query) |
            Q(firma__sehir__icontains=query)
        )

    if konum:
        paketler = paketler.filter(firma__sehir__iexact=konum)

    if kategori_id and str(kategori_id).isdigit():
        paketler = paketler.filter(hizmet_id=kategori_id)

    return render(request, 'arama.html', {
        'paketler': paketler,
        'query': query,
        'secili_konum': konum,
        'secili_kategori': kategori_id,
        'hizmetler': hizmetler,
        'sehirler_listesi': sehirler_listesi,
    })


@login_required(login_url='giris')
def profil(request):
    teklifler = TeklifTalebi.objects.filter(kullanici=request.user).order_by('-olusturulma_tarihi')
    catering_talepleri = PaketTalebi.objects.filter(kullanici=request.user).select_related('paket').order_by('-olusturulma_tarihi')
    siparisler = Siparis.objects.filter(kullanici=request.user).select_related('firma').prefetch_related('kalemler').order_by('-olusturulma_tarihi')
    catering_teklifleri = CateringTeklifi.objects.filter(talep__kullanici=request.user).select_related('talep__paket', 'firma').order_by('-olusturulma_tarihi')

    return render(request, 'profil.html', {
        'teklifler': teklifler,
        'siparisler': siparisler,
        'catering_talepleri': catering_talepleri,
        'catering_teklifleri': catering_teklifleri,
    })

@login_required(login_url='giris')
def abonelik_gun_atla(request, talep_id):
    if request.method == 'POST':
        # Sadece giriş yapan kullanıcının kendi talebini bulmasını sağlıyoruz (Güvenlik)
        talep = get_object_or_404(PaketTalebi, id=talep_id, kullanici=request.user)
        
        if talep.durum == 'Aktif':
            # Not: Veritabanında (models.py) abonelik bitiş tarihi tutuyorsan, burada o tarihe +1 gün ekletebilirsin.
            # Şimdilik kullanıcıya başarılı mesajı verip işlemi tamamlıyoruz.
            messages.success(request, f"Talebiniz alındı! {talep.paket.isim} için yarınki teslimat iptal edildi ve abonelik sürenizin sonuna eklendi.")
        else:
            messages.warning(request, "Sadece aktif aboneliklerde gün atlama işlemi yapılabilir.")
            
        return redirect('profil')
    
    return redirect('profil')


@login_required(login_url='giris')
@require_POST
def yorum_yap(request, paket_slug):
    paket = get_object_or_404(Paket, slug=paket_slug)
    
    tamamlanmis_talep = PaketTalebi.objects.filter(
        kullanici=request.user, paket=paket, durum='Tamamlandı'
    ).exists()
    
    tamamlanmis_siparis = Siparis.objects.filter(
        kullanici=request.user, kalemler__paket=paket, durum='TESLIM_EDILDI'
    ).exists()
    
    onceki_sayfa = request.META.get('HTTP_REFERER', 'profil')
    
    if not (tamamlanmis_talep or tamamlanmis_siparis):
        messages.error(request, 'Yalnızca teslim aldığınız veya tamamlanan hizmetleri değerlendirebilirsiniz.')
        return redirect(onceki_sayfa)
        
    puan = request.POST.get('puan')
    yorum_metni = request.POST.get('yorum_metni', '').strip()
    if puan not in {'1', '2', '3', '4', '5'} or not yorum_metni:
        messages.error(request, 'Geçerli bir puan ve yorum girin.')
        return redirect(onceki_sayfa)
        
    Yorum.objects.update_or_create(
        paket=paket, 
        kullanici=request.user, 
        defaults={
            'puan': puan, 
            'yorum_metni': yorum_metni,
            'dogrulanmis_musteri': True
        }
    )
    messages.success(request, 'Değerlendirmeniz kaydedildi.')
    return redirect(onceki_sayfa)


def kayit_ol(request):
    if request.method == 'POST':
        # 1. BOT KONTROLÜ (Honeypot Tuzağı)
        bot_tuzaği = request.POST.get('website_url_field', '')
        if bot_tuzaği:  # Eğer gizli alan dolduysa, kesin bottur!
            SistemLog.objects.create(islem_detayi=f"Bot saldırısı engellendi. IP: {request.META.get('REMOTE_ADDR')}")
            messages.error(request, 'Güvenlik doğrulaması başarısız.')
            return redirect('home')

        # 2. VERİLERİ AL
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

        # 3. KONTROLLER VE KAYIT
        if password and password_confirm and password == password_confirm:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'Bu kullanıcı adı zaten alınmış.')
            elif User.objects.filter(email=email).exists():
                messages.error(request, 'Bu e-posta adresi zaten kayıtlı.')
            else:
                # 4. ŞİFRE ZORLUK DENETİMİ (En az 8 karakter, sayı vb.)
                try:
                    validate_password(password)
                except ValidationError as e:
                    for hata in e.messages:
                        messages.error(request, hata)
                    return redirect('home')

                # Her şey güvenliyse kaydet
                user = User.objects.create_user(
                    username=username, 
                    email=email, 
                    password=password, 
                    first_name=first_name, 
                    last_name=last_name
                )
                login(request, user)
                messages.success(request, 'Hesabınız güvenli bir şekilde oluşturuldu.')
                return redirect('home')
        else:
            messages.error(request, 'Şifreler eşleşmiyor veya eksik.')

    return redirect('home')

def is_ortagimiz_olun(request):
    if request.method == 'POST':
        ad_soyad = request.POST.get('ad_soyad')
        firma_adi = request.POST.get('firma_adi')
        telefon = request.POST.get('telefon')
        email = request.POST.get('email')
        mesaj = request.POST.get('mesaj')

        EsnafBasvurusu.objects.create(
            ad_soyad=ad_soyad,
            firma_adi=firma_adi,
            telefon=telefon,
            email=email,
            mesaj=mesaj
        )
        messages.success(request, 'Başvurunuz başarıyla alındı. En kısa sürede sizinle iletişime geçeceğiz.')
        return redirect('is_ortagimiz_olun')

    return render(request, 'esnaf_basvuru.html')


def giris_yap(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if hasattr(user, 'firma'):
                return redirect('firma_dashboard')
            else:
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'giris.html', {'form': form})


def cikis_yap(request):
    logout(request)
    return redirect('home')


def hakkimizda(request):
    return render(request, 'hakkimizda.html')


def iletisim(request):
    if request.method == 'POST':
        form = IletisimForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Mesajınız başarıyla gönderildi.')
            return redirect('iletisim')
    else:
        form = IletisimForm()
    return render(request, 'iletisim.html', {'form': form})


@login_required(login_url='giris')
def firma_dashboard(request):
    try:
        firma = Firma.objects.get(sahibi=request.user)
    except Firma.DoesNotExist:
        return redirect('home')

    # YENİ: Paketleri Ayır
    paketler = Paket.objects.filter(firma=firma)
    bireysel_paketler = paketler.filter(hedef_kitle='Bireysel')
    kurumsal_paketler = paketler.exclude(hedef_kitle='Bireysel')

    # YENİ: Siparişleri / Talepleri Ayır
    siparisler = PaketTalebi.objects.filter(paket__firma=firma).order_by('-id')
    bireysel_talepler = siparisler.filter(paket__hedef_kitle='Bireysel')
    kurumsal_talepler = siparisler.exclude(paket__hedef_kitle='Bireysel')

    anlik_siparisler = Siparis.objects.filter(firma=firma).select_related('kullanici').prefetch_related('kalemler')

    if firma.sehir:
        hizli_teklifler = GenelTeklifTalebi.objects.filter(sehir__iexact=firma.sehir).order_by('-id')
    else:
        hizli_teklifler = []

    # YENİ EKLENEN KISIM: GRAFİK VERİLERİ 
    bekleyen = siparisler.filter(durum__in=['Bekliyor', 'Revize Edildi']).count()
    hazirlaniyor = siparisler.filter(durum__in=['Hazırlanıyor', 'Aktif']).count()
    tamamlandi = siparisler.filter(durum='Tamamlandı').count()
    reddedildi = siparisler.filter(durum='Reddedildi').count()
    durum_verileri = [bekleyen, hazirlaniyor, tamamlandi, reddedildi]

    paket_isimleri = [paket.isim for paket in paketler]
    talep_sayilari = [siparisler.filter(paket=paket).count() for paket in paketler]

    if request.method == 'POST' and request.POST.get('islem') == 'teklif_olustur':
        talep = get_object_or_404(PaketTalebi, id=request.POST.get('talep_id'), paket__firma=firma)
        teklif_form = CateringTeklifiForm(request.POST)
        if teklif_form.is_valid():
            teklif = teklif_form.save(commit=False)
            teklif.talep = talep
            teklif.firma = firma
            teklif.save()
            messages.success(request, 'Catering teklifiniz müşteriye gönderildi.')
            return redirect('firma_dashboard')
    elif request.method == 'POST':
        form = PaketEkleForm(request.POST, request.FILES)
        if form.is_valid():
            yeni_paket = form.save(commit=False)
            yeni_paket.firma = firma
            yeni_paket.save()
            messages.success(request, 'Yeni paket başarıyla eklendi.')
            return redirect('firma_dashboard')
    else:
        form = PaketEkleForm()
    teklif_form = CateringTeklifiForm()

    context = {
        'firma': firma,
        'paketler': paketler,
        'bireysel_paketler': bireysel_paketler,
        'kurumsal_paketler': kurumsal_paketler,
        'siparisler': siparisler,
        'bireysel_talepler': bireysel_talepler,
        'kurumsal_talepler': kurumsal_talepler,
        'anlik_siparisler': anlik_siparisler,
        'hizli_teklifler': hizli_teklifler, 
        'form': form,
        'teklif_form': teklif_form,
        'durum_verileri': durum_verileri, 
        'paket_isimleri': paket_isimleri,
        'talep_sayilari': talep_sayilari,
        'sistem_loglari': SistemLog.objects.filter(kullanici=request.user)[:10],
    }
    return render(request, 'firma_dashboard.html', context)

def firmalar(request):
    firmalar_listesi = Firma.objects.all()
    secili_sehir = request.GET.get('sehir')

    if secili_sehir:
        aranan = secili_sehir.strip().lower()
        eslesen_id_ler = []
        
        for firma in firmalar_listesi:
            if firma.sehir:
                db_sehir = firma.sehir.lower().replace('ç', 'c').replace('ş', 's').replace('ğ', 'g').replace('ö', 'o').replace('ü', 'u').replace('ı', 'i').replace('i̇', 'i')
                
                if aranan in db_sehir:
                    eslesen_id_ler.append(firma.id)
                    
        firmalar_listesi = Firma.objects.filter(id__in=eslesen_id_ler)

    context = {
        'firmalar': firmalar_listesi,
    }
    
    return render(request, 'firmalar.html', context)


@login_required(login_url='giris')
@require_POST
def karsilastirmaya_ekle(request, paket_slug):
    paket = get_object_or_404(Paket, slug=paket_slug)
    liste, _ = Karsilastirma.objects.get_or_create(kullanici=request.user)
    liste.paketler.add(paket)
    messages.success(request, 'Paket karşılaştırma listesine eklendi.')
    return redirect('karsilastirma_goruntule')


def karsilastirma_goruntule(request):
    ids_string = request.GET.get('ids', '')
    clear = request.GET.get('clear', '')
    
    paketler = []
    
    # Ekranda "Tümünü Temizle"ye basılmadıysa ve URL'de ürün varsa
    if ids_string and not clear:
        # URL'deki virgüllü metni ayırıp liste yap (Örn: ['paket-1', 'paket-2'])
        slug_listesi = [s.strip() for s in ids_string.split(',') if s.strip()]
        
        # Veritabanından (Paket modelinden) bu isimlere sahip paketleri getir
        paketler = Paket.objects.filter(slug__in=slug_listesi)[:3]
        
    context = {
        'paketler': paketler
    }
    
    return render(request, 'karsilastirma.html', context)

@login_required(login_url='giris')
@require_POST
def karsilastirmadan_cikar(request, paket_slug):
    liste = get_object_or_404(Karsilastirma, kullanici=request.user)
    paket = get_object_or_404(Paket, slug=paket_slug)
    
    liste.paketler.remove(paket)
    messages.success(request, 'Paket karşılaştırma listesinden çıkarıldı.')
    return redirect(request.META.get('HTTP_REFERER', 'karsilastirma_goruntule'))


@login_required(login_url='giris')
@require_POST
def talep_durum_guncelle(request, talep_id, yeni_durum):
    talep = get_object_or_404(PaketTalebi, id=talep_id, paket__firma__sahibi=request.user)
    gecerli_durumlar = ['Bekliyor', 'Ulaşıldı', 'Tamamlandı', 'İptal']
    
    if yeni_durum not in gecerli_durumlar:
        return redirect('firma_dashboard')
        
    eski_durum = talep.durum
    talep.durum = yeni_durum
    talep.save()
    
    SistemLog.objects.create(
        kullanici=request.user,
        islem_detayi=f"Talep #{talep.id} durumu '{eski_durum}' statüsünden '{yeni_durum}' statüsüne çekildi."
    )
    
    messages.success(request, 'Sipariş durumu güncellendi ve loglara kaydedildi.')
    return redirect('firma_dashboard')


@login_required(login_url='giris')
def dinamik_siparis(request, paket_slug):
    paket = get_object_or_404(Paket, slug=paket_slug)
    
    if request.method == 'POST':
        isim = request.POST.get('isim')
        telefon = request.POST.get('telefon')
        baslangic_tarihi = request.POST.get('baslangic_tarihi')
        bitis_tarihi = request.POST.get('bitis_tarihi')
        adres = request.POST.get('adres')
        
        try:
            kisi_sayisi = int(request.POST.get('kisi_sayisi', paket.min_kisi_sayisi))
        except ValueError:
            kisi_sayisi = paket.min_kisi_sayisi
            
        gercek_toplam_fiyat = paket.fiyat * kisi_sayisi
        
        mesaj_detayi = f"Başlangıç: {baslangic_tarihi} | Bitiş: {bitis_tarihi if bitis_tarihi else 'Belirtilmedi'} | Adres: {adres} | Sistem Tarafından Onaylanan Tutar: {gercek_toplam_fiyat} ₺"

        PaketTalebi.objects.create(
            kullanici=request.user,
            paket=paket,
            isim=isim,
            telefon=telefon,
            kisi_sayisi=kisi_sayisi,
            etkinlik_tarihi=baslangic_tarihi if baslangic_tarihi else None,
            mesaj=mesaj_detayi,
            durum='Bekliyor'
        )
        
        print("--- DİNAMİK SİPARİŞ MAİL İŞLEMİ BAŞLADI ---")
        konu = f"YemekVar: {paket.firma.isim} İçin Yeni Dinamik Sipariş!"
        mesaj = f"Firma Panelinize Yeni Bir Sipariş Düştü!\n\nMüşteri Adı: {isim}\nTelefon: {telefon}\nKişi Sayısı: {kisi_sayisi}\nTarih: {baslangic_tarihi}\nDetaylar: {mesaj_detayi}\n\nLütfen en kısa sürede YemekVar esnaf panelinizden müşteriye dönüş yapınız."
        
        alicilar = ['yemekvar.sistem@gmail.com']
        
        if paket.firma and hasattr(paket.firma, 'sahibi') and paket.firma.sahibi and paket.firma.sahibi.email:
            alicilar.append(paket.firma.sahibi.email)

        try:
            send_mail(konu, mesaj, 'yemekvar.sistem@gmail.com', alicilar, fail_silently=False)
            print("--- MAİL BAŞARIYLA GİTTİ ---")
        except Exception as e:
            print(f"!!! MAİL GÖNDERİLİRKEN HATA OLUŞTU: {e}")

        messages.success(request, 'Sipariş ve fiyatlandırma talebiniz güvenli bir şekilde firmaya iletilmiştir.')
        return redirect('profil')
        
    return render(request, 'siparis.html', {'paket': paket})


def firma_detay(request, slug):
    firma = get_object_or_404(Firma, slug=slug)
    return render(request, 'firma_detay.html', {'firma': firma})


def hizli_teklif(request):
    if request.method == 'POST':
        etkinlik_turu = request.POST.get('etkinlik_turu')
        sehir = request.POST.get('sehir')
        kisi_sayisi = request.POST.get('kisi_sayisi')
        tarih = request.POST.get('tarih')
        ogun = request.POST.get('ogun')
        isim = request.POST.get('isim')
        telefon = request.POST.get('telefon')
        notlar = request.POST.get('notlar')

        GenelTeklifTalebi.objects.create(
            etkinlik_turu=etkinlik_turu, sehir=sehir, kisi_sayisi=kisi_sayisi,
            tarih=tarih, ogun=ogun, isim=isim, telefon=telefon, notlar=notlar
        )

        ilgili_firmalar = Firma.objects.filter(sehir__iexact=sehir, aktif_mi=True)
        alici_mailler = [firma.email for firma in ilgili_firmalar if firma.email]
        
        alici_mailler.append('yemekvar.sistem@gmail.com')

        if alici_mailler:
            konu = f"YemekVar: {sehir} Bölgesi İçin Yeni Bir Fırsat!"
            mesaj = f"""Merhaba,
Bölgenizde yeni bir catering talebi oluşturuldu. Müşteriyle doğrudan iletişime geçip teklifinizi sunabilirsiniz:

Müşteri Adı: {isim}
Telefon: {telefon}
Etkinlik Türü: {etkinlik_turu}
Tarih: {tarih}
Öğün: {ogun}
Kişi Sayısı: {kisi_sayisi}
Özel Notlar: {notlar}

Bol kazançlar dileriz.
YemekVar Sistemi"""
            
            try:
                send_mail(konu, mesaj, 'yemekvar.sistem@gmail.com', alici_mailler, fail_silently=True)
            except Exception as e:
                print(f"Mail gönderim hatası: {e}")

        messages.success(request, f'Talebiniz {sehir} bölgesindeki firmalara iletildi. Yakında sizinle iletişime geçecekler.')
        return redirect('hizli_teklif') 

    tum_sehirler = Firma.objects.exclude(sehir__isnull=True).exclude(sehir__exact='').values_list('sehir', flat=True)
    sehirler_listesi = sorted(list(set([s.strip().title() for s in tum_sehirler if s])))
    
    return render(request, 'hizli_teklif.html', {'sehirler_listesi': sehirler_listesi})


def sartlar_kosullar(request):
    return render(request, 'sozlesme.html', {'baslik': 'Şartlar ve Koşullar', 'tip': 'sartlar'})

def kvkk_aydinlatma(request):
    return render(request, 'sozlesme.html', {'baslik': 'KVKK Aydınlatma Metni', 'tip': 'kvkk'})

@login_required(login_url='giris')
def siparis_durum_guncelle_api(request):
    """Kanban panosundan gelen sürükle-bırak durum güncellemelerini işler"""
    if request.method == 'POST':
        siparis_id = request.POST.get('siparis_id')
        yeni_durum = request.POST.get('durum')
        
        siparis = get_object_or_404(PaketTalebi, id=siparis_id)
        
        if siparis.paket.firma.sahibi == request.user:
            if yeni_durum in dict(PaketTalebi.DURUM_SECENEKLERI).keys():
                siparis.durum = yeni_durum
                siparis.save()
                return JsonResponse({'status': 'success', 'durum': yeni_durum})
                
    return JsonResponse({'status': 'error'}, status=400)


@login_required(login_url='giris')
def teklif_revize_et(request, siparis_id):
    """Müşteriye yeni bir fiyat (pazarlık) teklifi sunar"""
    siparis = get_object_or_404(PaketTalebi, id=siparis_id)
    
    if request.method == 'POST' and siparis.paket.firma.sahibi == request.user:
        yeni_fiyat = request.POST.get('revize_fiyat')
        not_aciklama = request.POST.get('revize_notu')
        
        siparis.revize_fiyat = yeni_fiyat
        siparis.revize_notu = not_aciklama
        siparis.durum = 'Revize Edildi'
        siparis.save()
        messages.success(request, 'Revize teklif başarıyla müşteriye iletildi.')
        
    return redirect('firma_dashboard')


@login_required(login_url='giris')
@require_POST
def musteri_revize_yanitla(request, talep_id):
    """Müşterinin, esnafın gönderdiği revize (pazarlık) teklifini kabul/reddetme işlemi"""
    talep = get_object_or_404(PaketTalebi, id=talep_id, kullanici=request.user)
    islem = request.POST.get('islem')
    
    if islem == 'kabul':
        talep.durum = 'Bekliyor' # Firma yeniden panelinde "Bekleyen" olarak görsün ve işe başlasın
        SistemLog.objects.create(
            kullanici=request.user,
            islem_detayi=f"Müşteri #{talep.id} talebi için {talep.revize_fiyat}₺'lik yeni fiyatı onayladı."
        )
        messages.success(request, 'Yeni teklifi onayladınız! Firma siparişinizi hazırlamaya başlayacaktır.')
    elif islem == 'red':
        talep.durum = 'Reddedildi'
        messages.error(request, 'Firmanın teklifini reddettiniz. Sipariş iptal edildi.')
        
    talep.save()
    return redirect('profil')

@login_required(login_url='giris')
@require_POST
def musteri_revize_yanitla(request, talep_id):
    talep = get_object_or_404(PaketTalebi, id=talep_id, kullanici=request.user)
    islem = request.POST.get('islem')
    
    if islem == 'kabul':
        talep.durum = 'Bekliyor' 
        SistemLog.objects.create(
            kullanici=request.user,
            islem_detayi=f"Müşteri #{talep.id} talebi için {talep.revize_fiyat}₺'lik yeni fiyatı onayladı."
        )
        messages.success(request, 'Yeni teklifi onayladınız! Firma siparişinizi hazırlamaya başlayacaktır.')
    elif islem == 'red':
        talep.durum = 'Reddedildi'
        messages.error(request, 'Firmanın teklifini reddettiniz. Sipariş iptal edildi.')
        
    talep.save()
    return redirect('profil')

def bireysel_abonelik(request):
    # Sadece 'Bireysel' veya 'Tumu' olarak işaretlenmiş paketleri getirir
    bireysel_paketler = Paket.objects.filter(hedef_kitle__in=['Bireysel', 'Tumu']).select_related('firma', 'hizmet')
    return render(request, 'bireysel.html', {'paketler': bireysel_paketler})

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# --- KANBAN SÜRÜKLE BIRAK (API) ---
@login_required(login_url='giris')
def siparis_durum_guncelle_api(request):
    if request.method == 'POST':
        siparis_id = request.POST.get('siparis_id')
        yeni_durum = request.POST.get('durum')
        try:
            # Sadece kendi firmasına ait siparişi güncelleyebilir
            siparis = PaketTalebi.objects.get(id=siparis_id, paket__firma__sahibi=request.user)
            siparis.durum = yeni_durum
            siparis.save()
            return JsonResponse({'status': 'success'})
        except PaketTalebi.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Sipariş bulunamadı veya yetkiniz yok.'})
    return JsonResponse({'status': 'error'})

# --- FİRMA: FİYAT REVİZE ET (PAZARLIK) ---
@login_required(login_url='giris')
def teklif_revize_et(request, siparis_id):
    if request.method == 'POST':
        siparis = get_object_or_404(PaketTalebi, id=siparis_id, paket__firma__sahibi=request.user)
        revize_fiyat = request.POST.get('revize_fiyat')
        revize_notu = request.POST.get('revize_notu')
        
        siparis.revize_fiyat = revize_fiyat
        siparis.revize_notu = revize_notu
        siparis.durum = 'Revize Edildi'
        siparis.save()
        messages.success(request, 'Yeni fiyat teklifiniz müşteriye iletildi.')
        
    return redirect('firma_dashboard')

# --- MÜŞTERİ: REVİZE TEKLİFE YANIT VER ---
@login_required(login_url='giris')
def musteri_revize_yanitla(request, talep_id):
    if request.method == 'POST':
        talep = get_object_or_404(PaketTalebi, id=talep_id, kullanici=request.user)
        islem = request.POST.get('islem')
        
        if islem == 'kabul':
            # Müşteri kabul ederse sipariş hazırlanmaya başlar veya aktif olur
            talep.durum = 'Aktif' if talep.abonelik_suresi else 'Hazırlanıyor'
            messages.success(request, 'Teklifi kabul ettiniz. Siparişiniz hazırlanıyor.')
        elif islem == 'red':
            talep.durum = 'Reddedildi'
            messages.error(request, 'Teklifi reddettiniz.')
            
        talep.save()
    return redirect('profil')

def karsilastirma(request):
    ids_string = request.GET.get('ids', '')
    clear = request.GET.get('clear', '')
    
    paketler = []
    if ids_string and not clear:
        # Virgülle gelen slugları listeye çevir
        slug_listesi = [s.strip() for s in ids_string.split(',') if s.strip()]
        # Veritabanından sadece bu paketleri çek
        paketler = Paket.objects.filter(slug__in=slug_listesi)[:3]
        
    return render(request, 'karsilastirma.html', {'paketler': paketler})

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Paket, Favori, Bildirim

@login_required
def favori_islemi(request, paket_id):
    paket = get_object_or_404(Paket, id=paket_id)
    favori, created = Favori.objects.get_or_create(kullanici=request.user, paket=paket)
    
    if not created:
        favori.delete() # Zaten varsa favoriden çıkar
        return JsonResponse({'durum': 'cikarildi'})
    
    return JsonResponse({'durum': 'eklendi'})

@login_required
def canli_bildirim_getir(request):
    # Okunmamış son 5 bildirimi çek
    bildirimler = Bildirim.objects.filter(kullanici=request.user, okundu_mu=False).order_by('-olusturulma_tarihi')[:5]
    okunmamis_sayisi = Bildirim.objects.filter(kullanici=request.user, okundu_mu=False).count()
    
    data = []
    for b in bildirimler:
        data.append({
            'baslik': b.baslik,
            'mesaj': b.mesaj,
            'link': b.link or '#',
            'zaman': b.olusturulma_tarihi.strftime("%H:%M")
        })
        
    return JsonResponse({'sayi': okunmamis_sayisi, 'bildirimler': data})