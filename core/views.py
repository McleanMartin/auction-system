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
from decimal import Decimal
from .report import generate_invoice_pdf

# Paynow configuration
paynow = Paynow(
    '14813', 
    '3e688baf-5630-4145-a99c-d5deb32e5b2e',
    'http://google.com', 
    'http://127.0.0.1:8000'
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
    all_bids = AuctionBid.objects.all().order_by('-created')[:6]
    return render(request, 'partials/livebids.html', {'all_bids': all_bids})

@login_required
def my_bids(request):
    """
    Display the winning bids for the logged-in user.
    """
    bids = AuctionBid.objects.filter(bidder=request.user)
    return render(request, 'partials/mybids.html', {'bids': bids,})

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
        'end_date': timezone.localtime(auction.end_date), 
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
        
        return redirect('auction', pk=product.auction.pk)

    messages.error(request, 'Invalid request method.')
    return redirect('index')

@login_required
def payment_process(request, pk):
    """Handle payment processing via Paynow."""
    try:
        obj = AuctionBid.objects.get(pk=pk)
    except AuctionBid.DoesNotExist:
        messages.error(request, 'Bid not found.')
        return redirect('bids')

    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('bids')

    phone_number = request.POST.get('phonenumber')
    if not phone_number:
        messages.error(request, 'Phone number is required.')
        return redirect('bids')

    try:
        # Calculate platform fee and tax fee
        platform_fee = Decimal('5.00')
        tax_fee = obj.product.price * Decimal('0.15')

        # Create payment record
        payment = Payment.objects.create(
            auction=obj.auction.name,
            phonenumber=phone_number,
            item=obj.product.name,
            amount=obj.product.price + tax_fee + platform_fee,
            payment_method='ecocash',
            status='pending',
        )

        payment.save()

        # Initiate Paynow payment
        paynow_payment = paynow.create_payment('Order', 'test@example.com')
        paynow_payment.add('Payment', float(payment.amount)) 
        response = paynow.send_mobile(paynow_payment, phone_number, 'ecocash')

        if (response.success):
            payment.status = 'completed'
            payment.save()

            obj.product.sold = True
            obj.product.save()

            # Generate invoice PDF
            generate_invoice_pdf(payment)

            messages.success(request, 'Payment initiated successfully.')
        else:
            messages.error(request, 'Payment initiation failed. Please try again.')
    except Exception as e:
        # Log the error for debugging
        print(f"Payment error: {str(e)}")
        messages.error(request, f'Payment error: {str(e)}')

    return redirect('bids')
@login_required
def checkout(request, pk):
    """
    Display the checkout page for a winning bid.
    """
    auction = get_object_or_404(AuctionBid, pk=pk)

    # Calculate fees
    platform_fee = Decimal('5.00')  
    tax_fee = auction.product.price * Decimal('0.15')  
    delivery_fee = Decimal('10.00') 

    # Calculate total amount
    total_amount = auction.product.price + platform_fee + tax_fee + delivery_fee

    context = {
        'product': auction.product,
        'platform_fee': platform_fee,
        'tax_fee': tax_fee,
        'delivery_fee': delivery_fee,
        'total_amount': total_amount,
        'auction':auction.pk
    }

    return render(request, 'partials/payment.html', context)

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