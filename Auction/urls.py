
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from core import views as v

urlpatterns = [
    path('jet/', include('jet.urls', 'jet')),
    path('admin/', admin.site.urls),
    path('',v.index,name='index'),
    path('auction/<int:pk>/',v.auction,name='auction'),
    path('bid/<int:pk>/',v.bidder,name='bid'),
    path('prebid/<int:pk>/',v.set_bid,name='prebid'),
    path('live-bids/',v.live_bids,name='live-bids'),
    path('bids/',v.my_bids,name='bids'),
    path('paynow',v.payment_process,name='paynow'),
    path('checkout/<int:pk>/',v.checkout,name='checkout'),

    path('accounts/',include('accounts.urls')),
]+ static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
