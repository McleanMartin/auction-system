import paynow
import time
from django.shortcuts import render, get_object_or_404, HttpResponseRedirect, redirect, reverse
from django.utils import timezone
from core.models import *
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LogoutView, LoginView
from django.core.paginator import Paginator
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser
from paynow import Paynow
from .forms import UserRegistrationForm, EditProfileForm
from django.views.generic import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

paynow = Paynow(
    '14813', 
    '3e688baf-5630-4145-a99c-d5deb32e5b2e',
    'http://google.com', 
    'http://127.0.0.1:8000'
    )

def user_register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            # messages.success(request, 'Your account has been created successfully! Please log in.')
            return redirect('user_login')
    else:
        form = UserRegistrationForm()
    
    context = {'title': 'Signup', 'form': form}
    return render(request, 'register.html', context)

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                if user.is_superuser:
                    return redirect('admin:index')
                else:
                    return redirect('index')
        else:
            return redirect('user_login')
    else:
        form = AuthenticationForm()
    
    context = {'title': 'Login', 'form': form}
    return render(request, 'login.html', context)

@login_required
def user_logout(request):
    logout(request)
    return redirect('user_login')


def dailySales(): 
    products = Product.objects.all()

def charge():
    clients = AuctionBid.objects.filter(winner=True)
    for client in clients:
        auction = client.auction
        product = client.product

        if product.sold:
            continue 

        bill, created = StorageBill.objects.get_or_create(
            auction=auction,
            defaults={'charge': 0, 'days': 0}
        )

        bill.charge += 2
        bill.days += 1
        bill.save()

        product.price += 2
        product.save()

        if bill.days > 5:
            AuctionBid.objects.filter(auction=auction, winner=True).delete()

            auction.expired = False
            auction.save()

            product.sold = False
            product.save()

            
def close():
    auctions = Auction.objects.filter(expired=False) 
    for auction in auctions:
        if timezone.now() > auction.end_date:
            auction.expired = True
            auction.save()

            last_bidder = AuctionBid.objects.filter(auction=auction).last()

            if last_bidder:
                last_bidder.winner = True
                last_bidder.save()

                subject = 'Congratulations! You Won the Auction'
                message = (
                    f'Hi {last_bidder.bidder.username},\n\n'
                    f'Congratulations! You have won the auction for "{last_bidder.product.name}".\n\n'
                    f'Thank you for participating in our auction.\n\n'
                    f'Best regards,\n'
                    f'The Auction Team'
                )
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [last_bidder.bidder.email] 

                try:
                    send_mail(subject, message, email_from, recipient_list)
                except Exception as e:
                    print(f"Failed to send email to {last_bidder.bidder.email}: {e}")


@login_required(login_url='/accounts/login/')
def index(request):
    auction_list = Auction.objects.filter(expired=False).order_by('end_date')

    page = request.GET.get('page', 1)
    paginator = Paginator(auction_list, 10)

    try:
        auctions = paginator.page(page)
    except PageNotAnInteger:
        auctions = paginator.page(1)
    except EmptyPage:
        auctions = paginator.page(paginator.num_pages)

    context = {
        'auction_list': auctions,
    }
    return render(request, 'index.html', context)


@login_required(login_url='/accounts/login/')
def auction(request, pk):
    try:
        auction = get_object_or_404(Auction, pk=pk)
        items = Product.objects.filter(auction=auction)
        related = Product.objects.filter(auction=auction).exclude(pk__in=[item.pk for item in items])[:4]
        status = timezone.now() >= auction.start_date

    except Exception as e:
        print(f"Error in auction view: {e}")
        raise

    context = {
        'items': items,
        'auction': auction,
        'related': related,
        'status': status,
    }
    return render(request, 'auction.html', context)


@login_required(login_url='/accounts/login/')
def bidder(request, pk):
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, pk=pk)
            auction_id = product.auction.pk

            bid = request.POST.get('amount')
            if not bid:
                messages.error(request, 'Bid amount is required.')
                return redirect('auction', pk=auction_id)

            bid = int(bid)

            if bid <= product.price:
                messages.warning(request, f'Your bid for {product.name} must be higher than the current price of ${product.price}.')
                return redirect('auction', pk=auction_id)

            product.price = bid
            product.save()

            AuctionBid.objects.create(
                bidder=request.user,
                auction=product.auction,
                bid_price=bid,
                product=product,
            )

            messages.success(request, f'You placed a bid of ${bid} for {product.name}.')
            return redirect('auction', pk=auction_id)

        except ValueError:
            messages.error(request, 'Invalid bid amount. Please enter a valid number.')
            return redirect('auction', pk=auction_id)

        except Exception as e:
            print(f"Error in bidder view: {e}")
            messages.error(request, 'An error occurred while processing your bid. Please try again.')
            return redirect('auction', pk=auction_id)

    else:
        messages.error(request, 'Invalid request method.')
        return redirect('index')


@login_required(login_url='/accounts/login/')
def set_bid(request, pk):
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to place a bid.")
        return redirect('login')

    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, pk=pk)
            set_amount = float(request.POST.get('amount', 0))

            if set_amount <= 0:
                raise ValidationError("Bid amount must be greater than 0.")

            existing_bid = Pre_Bidder.objects.filter(bidder=request.user, product=product).first()
            if existing_bid:
                messages.warning(request, f"You have already placed a bid for {product.name}.")
                return redirect('auction_detail', pk=product.auction.pk)

            highest_bid = Pre_Bidder.objects.filter(product=product).order_by('-bid_price').first()
            if highest_bid and set_amount <= highest_bid.bid_price:
                messages.error(request, f"Your bid must be higher than the current highest bid of {highest_bid.bid_price}.")
                return redirect('auction_detail', pk=product.auction.pk)

            pre_bid = Pre_Bidder.objects.create(
                bidder=request.user,
                product=product,
                bid_price=set_amount
            )
            pre_bid.save()
            messages.success(request, f"Your pre-bid for {product.name} was successful.")
            return redirect('auction_detail', pk=product.auction.pk)

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('auction_detail', pk=pk)
        except Exception as e:
            messages.error(request, "An error occurred while processing your bid.")
            return redirect('auction_detail', pk=pk)

    return redirect('auction_detail', pk=pk)

def live_bids(request):
    all_bids = AuctionBid.objects.all().order_by('-created')[:6]
    return render(request,'partials/livebids.html',{'all_bids':all_bids})


@login_required
def my_bids(request):
    try:
        winning_bids = AuctionBid.objects.filter(bidder=request.user, winner=True) \
                                        .select_related('auction', 'product')

        delivery_prices = Delivery_Price.objects.all()
        if not winning_bids.exists():
            messages.info(request, "You have no winning bids at the moment.")
            return render(request, 'partials/mybids.html', {'winning_bids': [], 'delivery_prices': delivery_prices})

       
        return render(request, 'partials/mybids.html', {
            'winning_bids': winning_bids,
            'delivery_prices': delivery_prices,
        })

    except Exception as e:
        messages.error(request, "An error occurred while fetching your bids. Please try again later.")
        return render(request, 'partials/mybids.html', {'winning_bids': [], 'delivery_prices': []})


def checkout(request, pk):
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to proceed to checkout.")
        return redirect('login')

    product = get_object_or_404(Product, pk=pk)
    routes = Delivery_Price.objects.all()
    total_price = float(product.price)

    if request.method == 'GET':
        delivery_price = request.GET.get('d_price')
        if delivery_price is not None and delivery_price != "":
            try:
                delivery_price = float(delivery_price)
                total_price += delivery_price
            except (ValueError, TypeError):
                messages.error(request, "Invalid delivery price provided.")

    return render(request, 'partials/payment.html', {
        'product': product,
        'routes': routes,
        'total_price': total_price,
    })

def payment_process(request, pk):
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to proceed with payment.")
        return redirect('login')

    bid = get_object_or_404(AuctionBid, pk=pk)
    product = get_object_or_404(Product, pk=bid.product.pk)

    if request.method == 'POST':
        number = request.POST.get('number')
        if not number or not number.isdigit():
            messages.error(request, "Invalid phone number provided.")
            return redirect('bids') 

        try:
            payment = paynow.create_payment('ecocash', 'smasonfukuzeya123@gmail.com')
            payment.add('ecocash', bid.product.price)
            response = paynow.send_mobile(payment, str(number), 'ecocash')

            if response.success:
                poll_url = response.poll_url
                print(poll_url)
                status = paynow.check_transaction_status(poll_url)
                time.sleep(15)

                Payment.objects.create(
                    auction=bid.product.auction.name,
                    phonenumber=number,
                    item=bid.product.name,
                    amount=bid.product.price,
                )
                product.sold = True
                product.save()

                messages.success(request, f'Transaction {status.status}.')
                return redirect('bids')

            else:
                messages.error(request, "Something went wrong with the Paynow server. Check your transaction number.")
                return redirect('bids')

        except Exception as e:
            print(f"Error during payment processing: {e}")
            messages.error(request, "Something went wrong with the Paynow server. Check your transaction number.")
            return redirect('bids')

    return redirect('bids')



class SellerDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Seller Dashboard: Displays products listed by the seller.
    """
    model = Product
    template_name = 'seller/dashboard.html'
    context_object_name = 'products'

    def test_func(self):
        """
        Ensure only sellers can access this view.
        """
        return self.request.user.is_seller

    def get_queryset(self):
        """
        Filter products to only those listed by the logged-in seller.
        """
        return Product.objects.filter(seller=self.request.user)


class AddProductView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    Add a new product to an auction.
    """
    model = Product
    template_name = 'seller/add_product.html'
    fields = ['name', 'category', 'auction', 'image', 'description', 'condition', 'price', 'quantity']
    success_url = reverse_lazy('seller_dashboard')

    def test_func(self):
        """
        Ensure only sellers can access this view.
        """
        return self.request.user.is_seller

    def form_valid(self, form):
        """
        Set the seller to the logged-in user before saving the product.
        """
        form.instance.seller = self.request.user
        return super().form_valid(form)


class UpdateProductView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Update an existing product.
    """
    model = Product
    template_name = 'seller/update_product.html'
    fields = ['name', 'category', 'auction', 'image', 'description', 'condition', 'price', 'quantity']
    success_url = reverse_lazy('seller_dashboard')

    def test_func(self):
        """
        Ensure only the seller who listed the product can update it.
        """
        product = self.get_object()
        return self.request.user.is_seller and product.seller == self.request.user


class DeleteProductView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    Delete a product.
    """
    model = Product
    template_name = 'seller/delete_product.html'
    success_url = reverse_lazy('seller_dashboard')

    def test_func(self):
        """
        Ensure only the seller who listed the product can delete it.
        """
        product = self.get_object()
        return self.request.user.is_seller and product.seller == self.request.user


class ViewBidsView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View bids on products listed by the seller.
    """
    model = AuctionBid
    template_name = 'seller/view_bids.html'
    context_object_name = 'bids'

    def test_func(self):
        """
        Ensure only sellers can access this view.
        """
        return self.request.user.is_seller

    def get_queryset(self):
        """
        Filter bids to only those on products listed by the logged-in seller.
        """
        return AuctionBid.objects.filter(product__seller=self.request.user)

