from django.shortcuts import render,get_object_or_404,HttpResponseRedirect,redirect
from django.utils import timezone
from core.models import *
import paynow
import time
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseRedirect,HttpResponse
from django.contrib.auth.views import LogoutView ,LoginView


from django.conf import settings
from django.core.mail import send_mail




def close():
    auctions = Auction.objects.all()
    for auction in auctions:
        if timezone.now() > auction.end_date:
            if auction.expired != True:
                auction.expired = True #close auction
                auction.save()
                
                slot = Pre_Bidder.objects.filter(auction=auction.pk)
                bidder = slot.last()
                bidder.winner = True
                bidder.save()

                #send email to winner
                subject = 'Winner'
                message = f'Hi {bidder.bidder.username}, congratulation you won ,  {bidder.product.name}'
                email_from = settings.EMAIL_HOST_USER
                recipient_list = [bidder.user.email, ]
                send_mail( subject, message, email_from, recipient_list )


def pre_bidder():
    prebids =  Pre_Bidder.objects.all()
    for bid in prebids:
        product_id = bid.product.pk
        product = Product.objects.get(pk=product_id)
        slot = product.slot # auction slot 
        if timezone.now() > slot.end_date:
            if slot.expired == False:
                slot.expired = True #close auction
                slot.save()


        elif bid.expired == False and slot.expired == False:
            try:
                if slot.start_date < timezone.now():
                    if slot.end_date > timezone.now():
                        if bid.bid_price > product.price:
                            product.price = bid.bid_price
                            product.save() # placing a bid
                        else:
                            bid.expired = True
                        bid.expired = True
                        bid.save() # deactivate pre bid
                        auction_id = Auction.objects.get(pk=slot.pk)
                        bid_log = AuctionBid.objects.create(
                            bidder=bid.bidder,
                            auction=auction_id,
                            bid_price = product.price,
                            product = product,)
                        bid_log.save()
                        print('bid successful') 
            except:
                print('bidding failed')

@login_required(login_url='/accounts/login/')
def index(request):
    auction_list = Auction.objects.filter(expired=False)
    return render(request,'index.html',{'auction_list':auction_list})

@login_required(login_url='/accounts/login/')
def auction(request,pk):
    try:
        auction = Auction.objects.get(pk=pk)
        items = Product.objects.filter(slot=auction)
        related = Product.objects.filter(slot=auction)[:4]

        if timezone.now() < auction.start_date :
            status = False
        else:
            status = True
        
                
    finally:
        pass
    return render(request,'auction.html',
                        {'items':items,
                        'auction':auction,
                        'related':related,
                        'status':status})

@login_required(login_url='/accounts/login/')
def bidder(request,pk):
    if request.method == 'POST':
        bid = request.POST.get('amount')
        product = Product.objects.get(pk=pk)
        id = product.slot.pk
        if int(bid) > product.price:
            product.price = bid #placing a bid
            product.save()
            bid_log = AuctionBid.objects.create(
                    bidder=request.user,
                    auction=product.slot,
                    bid_price = bid,
                    product = product,)
            bid_log.save()

            #alert here
            msg = messages.success(request,'You placed  $'+ bid +'  bid for '+ product.name)
            return HttpResponseRedirect('/auction/'+str(id),{'msg':msg})
        else:
            #alert here
            msg = messages.warning(request,'Your bid for '+ product.name +' is less than the current price' )
            return HttpResponseRedirect('/auction/'+str(id))
    else:
        msg = messages.error(request,'invalid method used')
        return HttpResponseRedirect('/auction/'+str(id))


@login_required(login_url='/accounts/login/')
def set_bid(request,pk):
    if request.method == 'POST':
        user = request.user
        set_amount = request.POST.get('amount')
        item = Product.objects.get(pk=pk)
        pre_bid = Pre_Bidder.objects.create(
            bidder=user,
            product=item,
            bid_price=set_amount)
        pre_bid.save()
        proxy_status  = item_status.objects.create(
            user = user,
            auction = item.slot.pk,
            item = item.pk,
            status = True 
        ) 
        proxy_status.save()
        id = item.slot.pk
        msg = messages.success(request,'Your Pre bid for '+ item.name + ' was successful')
        return HttpResponseRedirect('/auction/'+ str(id),{'msg':msg})


def live_bids(request):
    all_bids = AuctionBid.objects.all().order_by('-created')[:6]
    return render(request,'partials/livebids.html',{'all_bids':all_bids})


def my_bids(request):
    bids= AuctionBid.objects.filter(bidder=request.user,winner=True)
    pre_bids = Pre_Bidder.objects.filter(bidder=request.user)
    delivery = Delivery_Price.objects.all()
    return render(request,'partials/mybids.html',{'bids':bids,'pre_bids':pre_bids,'delivery':delivery,})


def checkout(request,pk):
    product = Product.objects.get(pk=pk)
    routes = Delivery_Price.objects.all()
    price = product.price
    if request.method == 'GET':
        d_price = request.GET.get('d_price')
        if d_price == "": 
            price = float(product.price) + float(d_price) 
    else:
        pass  
    return render(request,'partials/payment.html',{'product':product,'routes':routes,'price':price})

def payment_process(request,pk):
    bid = AuctionBid.objects.get(pk=pk)
    product = Product.objects.get(pk=bid.product.pk)
    if request.method == 'POST':
        number = request.POST.get('number')
        try:
            payment = paynow.create_payment('ecocash','smasonfukuzeya123@gmail.com')
            payment.add('ecocash',bid.product.price)
            response = paynow.send_mobile(payment,str(number),'ecocash')
            if response.success:
                poll_url = response.poll_url
                print(poll_url)
                status  = paynow.check_transaction_status(poll_url)
                time.sleep(15)
                if status.paid:
                    Payment.objects.create(auction=bid.product.slot.name,
                                           phonenumber=number,
                                           item = bid.product.name,
                                           amount = bid.product.price,
                                        )
                    product.sold = True
                    product.save()
                    msg = messages.success(request,f'Transaction {status.status}.')
                    return HttpResponseRedirect('/bids/',{'msg':msg})

                else:
                    Payment.objects.create(auction=bid.product.slot.name,
                                           phonenumber=number,
                                           item = bid.product.name,
                                           amount = bid.product.price,
                                        )
                    product.sold = True
                    product.save()
                    msg = messages.success(request,f'Transaction {status.status}.')
                    return HttpResponseRedirect('/bids/',{'msg':msg})
            else:
                msg = messages.error(request,f'something  went wrong with paynow server, check your transaction number.')
                return HttpResponseRedirect('/bids/',{'msg':msg})

        except:
            msg = messages.error(request,"something  went wrong with paynow server, check your transaction number.")
            return HttpResponseRedirect('/bids/',{'msg':msg})



def hide(request):
    proxy = item_status.objects.filter(user=request.user,pk=item.pk)
    return proxy









