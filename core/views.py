from django.shortcuts import render, get_object_or_404, HttpResponseRedirect, redirect, reverse
from django.utils import timezone
from core.models import *
import paynow
import time
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LogoutView, LoginView
from django.conf import settings
from django.core.mail import send_mail


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
        items = Product.objects.filter(slot=auction)
        related = Product.objects.filter(slot=auction).exclude(pk__in=[item.pk for item in items])[:4]
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
            auction_id = product.slot.pk

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
                auction=product.slot,
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
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to place a bid.")
        return redirect('login')  # Redirect to the login page

    if request.method == 'POST':
        try:
            # Get the product and validate the bid amount
            product = get_object_or_404(Product, pk=pk)
            set_amount = float(request.POST.get('amount', 0))

            if set_amount <= 0:
                raise ValidationError("Bid amount must be greater than 0.")

            # Check if the user has already placed a bid for this product
            existing_bid = Pre_Bidder.objects.filter(bidder=request.user, product=product).first()
            if existing_bid:
                messages.warning(request, f"You have already placed a bid for {product.name}.")
                return redirect('auction_detail', pk=product.slot.pk)

            # Ensure the bid amount is higher than the current highest bid
            highest_bid = Pre_Bidder.objects.filter(product=product).order_by('-bid_price').first()
            if highest_bid and set_amount <= highest_bid.bid_price:
                messages.error(request, f"Your bid must be higher than the current highest bid of {highest_bid.bid_price}.")
                return redirect('auction_detail', pk=product.slot.pk)

            # Create and save the new bid
            pre_bid = Pre_Bidder.objects.create(
                bidder=request.user,
                product=product,
                bid_price=set_amount
            )
            pre_bid.save()

            # Success message and redirect
            messages.success(request, f"Your pre-bid for {product.name} was successful.")
            return redirect('auction_detail', pk=product.slot.pk)

        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('auction_detail', pk=pk)
        except Exception as e:
            messages.error(request, "An error occurred while processing your bid.")
            return redirect('auction_detail', pk=pk)

    # If not a POST request, redirect to the auction detail page
    return redirect('auction_detail', pk=pk)

def live_bids(request):
    all_bids = AuctionBid.objects.all().order_by('-created')[:6]
    return render(request,'partials/livebids.html',{'all_bids':all_bids})


@login_required
def my_bids(request):
    try:
        # Fetch the user's winning bids with related data to optimize queries
        winning_bids = AuctionBid.objects.filter(bidder=request.user, winner=True) \
                                        .select_related('auction', 'product')

        # Fetch all delivery prices (or filter if necessary)
        delivery_prices = Delivery_Price.objects.all()

        # Handle empty state
        if not winning_bids.exists():
            messages.info(request, "You have no winning bids at the moment.")
            return render(request, 'partials/mybids.html', {'winning_bids': [], 'delivery_prices': delivery_prices})

        # Render the template with context
        return render(request, 'partials/mybids.html', {
            'winning_bids': winning_bids,
            'delivery_prices': delivery_prices,
        })

    except Exception as e:
        # Log the error and return a user-friendly message
        messages.error(request, "An error occurred while fetching your bids. Please try again later.")
        return render(request, 'partials/mybids.html', {'winning_bids': [], 'delivery_prices': []})


def checkout(request, pk):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to proceed to checkout.")
        return redirect('login')  # Redirect to the login page

    # Get the product or return a 404 error if not found
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
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to proceed with payment.")
        return redirect('login')  # Redirect to the login page

    # Get the bid and product or return a 404 error if not found
    bid = get_object_or_404(AuctionBid, pk=pk)
    product = get_object_or_404(Product, pk=bid.product.pk)

    if request.method == 'POST':
        number = request.POST.get('number')
        if not number or not number.isdigit():
            messages.error(request, "Invalid phone number provided.")
            return redirect('bids')  # Redirect to the bids page

        try:
            # Create payment with Paynow
            payment = paynow.create_payment('ecocash', 'smasonfukuzeya123@gmail.com')
            payment.add('ecocash', bid.product.price)
            response = paynow.send_mobile(payment, str(number), 'ecocash')

            if response.success:
                poll_url = response.poll_url
                print(poll_url)
                status = paynow.check_transaction_status(poll_url)
                time.sleep(15)  # Simulate waiting for payment confirmation

                # Create payment record and mark product as sold
                Payment.objects.create(
                    auction=bid.product.slot.name,
                    phonenumber=number,
                    item=bid.product.name,
                    amount=bid.product.price,
                )
                product.sold = True
                product.save()

                # Notify user of payment status
                messages.success(request, f'Transaction {status.status}.')
                return redirect('bids')

            else:
                messages.error(request, "Something went wrong with the Paynow server. Check your transaction number.")
                return redirect('bids')

        except Exception as e:
            # Log the error and notify the user
            print(f"Error during payment processing: {e}")
            messages.error(request, "Something went wrong with the Paynow server. Check your transaction number.")
            return redirect('bids')

    # If not a POST request, redirect to the bids page
    return redirect('bids')

def remove_prebid(request, pk):
    # Ensure the user is authenticated
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to remove a pre-bid.")
        return redirect('login')  # Redirect to the login page

    # Get the pre-bid or return a 404 error if not found
    pre_bid = get_object_or_404(Pre_Bidder, pk=pk)

    # Ensure the user is the owner of the pre-bid
    if pre_bid.bidder != request.user:
        messages.error(request, "You do not have permission to remove this pre-bid.")
        return redirect('bids')

    try:
        # Delete the pre-bid
        pre_bid.delete()
        messages.success(request, "Your pre-bid has been successfully removed.")
    except Exception as e:
        # Log the error and notify the user
        print(f"Error removing pre-bid: {e}")
        messages.error(request, "An error occurred while removing your pre-bid. Please try again later.")

    # Redirect to the bids page
    return redirect('bids')








