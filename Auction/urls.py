from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from core import views as v

urlpatterns = [
    path('seller/dashboard/', v.SellerDashboardView.as_view(), name='seller_dashboard'),
    path('seller/add-product/', v.AddProductView.as_view(), name='add_product'),
    path('seller/update-product/<int:pk>/', v.UpdateProductView.as_view(), name='update_product'),
    path('seller/delete-product/<int:pk>/', v.DeleteProductView.as_view(), name='delete_product'),
    path('seller/view-bids/', v.ViewBidsView.as_view(), name='view_bids'),

    path('',v.index,name='index'),
    path('admin/', admin.site.urls),
    path('auction/<int:pk>/',v.auction_detail,name='auction'),
    path('bid/<int:pk>/',v.place_bid,name='bid'),
    path('live-bids/', v.live_bids, name='live-bids'),
    path('bids/', v.my_bids, name='bids'),
    path('paynow/<int:pk>/',v.payment_process,name='paynow'),
    path('checkout/<int:pk>/',v.checkout,name='checkout'),

    path('register/', v.user_register, name='user_register'),
    path('accounts/login/', v.user_login, name='user_login'),
    path('accounts/logout/', v.user_logout, name='user_logout'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='password_reset.html',
            success_url=reverse_lazy('password_reset_done'),
            email_template_name='email_template.html'
        ),
        name='password_reset'
    ),
    path(
        'password-reset/done',
        auth_views.PasswordResetDoneView.as_view(
            template_name='password_reset_done.html',
        ),
        name='password_reset_done'
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm'
    ),
    path(
        'password-reset-complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='password_reset_complete.html',
        ),
        name='password_reset_complete'
    ),
]+ static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
