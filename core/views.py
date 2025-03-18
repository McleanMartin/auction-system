import time
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.mail import send_mail
from django.conf import settings
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from paynow import Paynow
from .models import *
from .forms import *
from .report import generate_invoice_pdf

# Paynow configuration
paynow = Paynow(
    settings.PAYNOW_ID,
    settings.PAYNOW_KEY,
    settings.PAYNOW_RETURN_URL,
    settings.PAYNOW_RESULT_URL
)

# Auth Views
def user_register(request):
    """Handle user registration."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('user_login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'register.html', {'title': 'Signup', 'form': form})

def user_login(request):
    """Handle user login."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user:
                login(request, user)
                return redirect('admin:index' if user.is_superuser else 'index')
        messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'title': 'Login', 'form': form})

@login_required
def user_logout(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('user_login')

# Auction Views
@login_required
def index(request):
    """Display active auctions."""
    auction_list = Auction.objects.filter(expired=False).order_by('end_date')
    paginator = Paginator(auction_list, 10)
    page = request.GET.get('page', 1)

    try:
        auctions = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        auctions = paginator.page(1)

    return render(request, 'index.html', {'auction_list': auctions})

@login_required
def live_bids(request):
    """
    Display the latest bids across all auctions.
    """
    # Fetch the latest 6 bids
    all_bids = AuctionBid.objects.all().order_by('-created')[:6]
    return render(request, 'partials/livebids.html', {'all_bids': all_bids})

@login_required
def my_bids(request):
    """
    Display the winning bids for the logged-in user.
    """
    try:
        # Fetch winning bids for the logged-in user
        
        winning_bids = get_object_or_404(AuctionBid,bidder=request.user)

        return render(request, 'partials/mybids.html', {
            'bids': bids,
        })

    except Exception as e:
        messages.error(request, "An error occurred while fetching your bids. Please try again later.")
        return render(request, 'partials/mybids.html', {
            'bids': []
        })

@login_required
def auction_detail(request, pk):
    """Display details of a specific auction."""
    auction = get_object_or_404(Auction, pk=pk)
    items = Product.objects.filter(auction=auction)
    related = Product.objects.filter(auction=auction).exclude(pk__in=items.values_list('pk', flat=True))[:4]
    status = timezone.now() >= auction.start_date

    return render(request, 'auction.html', {
        'items': items,
        'auction': auction,
        'related': related,
        'status': status,
    })

@login_required
def place_bid(request, pk):
    """Handle bid placement."""
    if request.method == 'POST':
        product = get_object_or_404(Product, pk=pk)
        bid_amount = request.POST.get('amount')

        try:
            bid_amount = float(bid_amount)
            if bid_amount <= product.price:
                messages.warning(request, f'Bid must be higher than the current price of ${product.price}.')
            else:
                product.price = bid_amount
                product.save()

                AuctionBid.objects.create(
                    bidder=request.user,
                    auction=product.auction,
                    bid_price=bid_amount,
                    product=product,
                )
                messages.success(request, f'Bid of ${bid_amount} placed successfully.')
        except ValueError:
            messages.error(request, 'Invalid bid amount.')
        
        return redirect('auction_detail', pk=product.auction.pk)

    messages.error(request, 'Invalid request method.')
    return redirect('index')

# Payment Views
@login_required
def payment_process(request, pk):
    """Handle payment processing via Paynow."""
    bid = get_object_or_404(AuctionBid, pk=pk)
    product = bid.product

    if request.method == 'POST':
        phone_number = request.POST.get('number')

        if not phone_number or not phone_number.isdigit():
            messages.error(request, 'Invalid phone number.')
            return redirect('my_bids')

        try:
            # Calculate platform fee and tax fee
            platform_fee = Decimal('5.00')
            tax_fee = product.price * Decimal('0.15')

            # Create payment
            payment = Payment.objects.create(
                auction=product.auction.name,
                phonenumber=phone_number,
                item=product.name,
                amount=product.price,
                platform_fee=platform_fee,
                tax_fee=tax_fee,
                payment_method='ecocash',
                status='pending',
            )

            # Initiate Paynow payment
            paynow_payment = paynow.create_payment('ecocash', request.user.email)
            paynow_payment.add('ecocash', payment.total_amount)
            response = paynow.send_mobile(paynow_payment, phone_number, 'ecocash')

            if response.success:
                payment.status = 'completed'
                payment.save()
                product.sold = True
                product.save()
                generate_invoice_pdf(payment)
                
                messages.success(request, 'Payment initiated successfully.')
                return redirect('my_bids')
            else:
                messages.error(request, 'Payment initiation failed.')
        except Exception as e:
            messages.error(request, f'Payment error: {str(e)}')

        return redirect('my_bids')

    messages.error(request, 'Invalid request method.')
    return redirect('my_bids')

@login_required
def checkout(request, pk):
    """
    Display the checkout page for a winning bid.
    """
    winning_bid = get_object_or_404(AuctionBid, pk=pk, bidder=request.user, winner=True)
    product = winning_bid.product

    # Calculate fees
    platform_fee = Decimal('5.00')  # Example: $5 platform fee
    tax_fee = winning_bid.bid_price * Decimal('0.15')  # Example: 15% tax
    delivery_fee = Decimal('10.00')  # Example: $10 delivery fee

    # Calculate total amount
    total_amount = winning_bid.bid_price + platform_fee + tax_fee + delivery_fee

    context = {
        'product': product,
        'platform_fee': platform_fee,
        'tax_fee': tax_fee,
        'delivery_fee': delivery_fee,
        'total_amount': total_amount,
    }

    return render(request, 'checkout.html', context)

# Seller Views
class SellerDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Seller dashboard to view listed products."""
    model = Product
    template_name = 'seller/dashboard.html'
    context_object_name = 'products'

    def test_func(self):
        return self.request.user.is_seller

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)

class AddProductView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """View to add a new product."""
    model = Product
    template_name = 'seller/add_product.html'
    fields = ['name', 'category', 'auction', 'image', 'description', 'condition', 'price', 'quantity']
    success_url = reverse_lazy('seller_dashboard')

    def test_func(self):
        return self.request.user.is_seller

    def form_valid(self, form):
        form.instance.seller = self.request.user
        return super().form_valid(form)

class UpdateProductView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View to update an existing product."""
    model = Product
    template_name = 'seller/update_product.html'
    fields = ['name', 'category', 'auction', 'image', 'description', 'condition', 'price', 'quantity']
    success_url = reverse_lazy('seller_dashboard')

    def test_func(self):
        product = self.get_object()
        return self.request.user.is_seller and product.seller == self.request.user

class DeleteProductView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """View to delete a product."""
    model = Product
    template_name = 'seller/delete_product.html'
    success_url = reverse_lazy('seller_dashboard')

    def test_func(self):
        product = self.get_object()
        return self.request.user.is_seller and product.seller == self.request.user

class ViewBidsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View bids on products listed by the seller."""
    model = AuctionBid
    template_name = 'seller/view_bids.html'
    context_object_name = 'bids'

    def test_func(self):
        return self.request.user.is_seller

    def get_queryset(self):
        return AuctionBid.objects.filter(product__seller=self.request.user)