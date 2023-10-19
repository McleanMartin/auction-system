from typing import Optional
from django.contrib import admin
from django.http.request import HttpRequest
from .models import Auction,AuctionBid,Product,Category,Pre_Bidder,Delivery_Price

class AuctionItemInline(admin.TabularInline):
    model = AuctionBid
    raw_id_fields = ['product']
    ordering = ['bid_price']


    # def has_change_permission(self, request, obj):
    #     return False
    
    def has_delete_permission(self, request, obj):
        return False
    
    def has_add_permission(self, request,obj):
        return False
    
@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name','start_date','end_date','expired']
    list_filter = ['expired', 'created']
    list_display_links = ['name']
    search_fields = ['name']
    inlines = [AuctionItemInline]

@admin.register(Pre_Bidder)
class Pre_BidderAdmin(admin.ModelAdmin):
    list_display = ['bidder','product','bid_price','expired']
    search_fields = ['bidder','product']
    

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['name','price']
    list_display = ['name','category','price','slot','sold']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ['name']

@admin.register(Delivery_Price)
class Delivery_PriceAdmin(admin.ModelAdmin):
    pass


admin.site.site_header = 'Croco Motors'
    
