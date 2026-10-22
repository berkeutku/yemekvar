from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseRedirect, HttpResponse
from django.middleware.csrf import get_token
from django_otp import match_token
from django_otp import login as otp_login
from django_otp.plugins.otp_totp.models import TOTPDevice

admin.site.site_header = "YemekVar Yönetim Paneli"
admin.site.site_title = "YemekVar Yönetim"
admin.site.index_title = "YemekVar Sistemine Hoş Geldiniz"

# --- UNFOLD İLE ÇAKIŞMAYAN KUSURSUZ 2FA SİSTEMİ ---
def yemekvar_2fa_view(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect('/admin/login/')
    if request.user.is_verified():
        return HttpResponseRedirect('/admin/')
        
    hata = ""
    if request.method == 'POST':
        token = request.POST.get('token')
        device = match_token(request.user, token)
        if device:
            otp_login(request, device)
            return HttpResponseRedirect('/admin/')
        else:
            hata = "Hatalı kod, lütfen tekrar deneyin."
            
    html = f"""
    <html>
    <body style="background-color: #111827; display: flex; justify-content: center; align-items: center; height: 100vh; font-family: sans-serif; color: white; margin: 0;">
        <div style="background-color: #1f2937; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); text-align: center; width: 350px;">
            <h2 style="margin-bottom: 20px; font-size: 24px;">Güvenlik Doğrulaması</h2>
            <p style="color: #ef4444; font-size: 14px; margin-bottom: 15px; font-weight: bold;">{hata}</p>
            <form method="POST" style="margin: 0;">
                <input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">
                <input type="text" name="token" placeholder="6 Haneli Kodu Girin" required autocomplete="off" autofocus
                       style="width: 100%; padding: 12px; border-radius: 6px; border: 1px solid #374151; background: #374151; color: white; margin-bottom: 20px; font-size: 18px; text-align: center; box-sizing: border-box; outline: none;">
                <button type="submit" style="width: 100%; background-color: #3b82f6; color: white; padding: 12px; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; font-weight: bold; transition: 0.2s;">Doğrula ve Gir</button>
            </form>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html)

class YemekVar2FAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        if request.path.startswith('/admin/') and request.user.is_authenticated:
            if request.path in ['/admin/2fa/', '/admin/logout/']:
                return self.get_response(request)
                
            has_device = TOTPDevice.objects.filter(user=request.user).exists()
            # Cihazı varsa ve doğrulamadan geçmediyse 2FA ekranına at
            if has_device and not request.user.is_verified():
                return HttpResponseRedirect('/admin/2fa/')
        return self.get_response(request)
# --------------------------------------------------

urlpatterns = [
    path('admin/2fa/', yemekvar_2fa_view, name='2fa_ekrani'),
    path('admin/', admin.site.urls),
    path('', include('webpages.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)