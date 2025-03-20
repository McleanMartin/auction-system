from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Category, Auction, Product, AuctionBid, Payment
)
from .models import CustomUser

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'start_date', 'end_date', 'expired']
    list_filter = ['expired', 'created']
    search_fields = ['name']
    date_hierarchy = 'start_date'
    readonly_fields = ['created', 'updated']
    actions = ['mark_as_expired']

    def mark_as_expired(self, request, queryset):
        queryset.update(expired=True)
    mark_as_expired.short_description = "Mark selected auctions as expired"


# @admin.register(Product)
# class ProductAdmin(admin.ModelAdmin):
#     list_display = ['name', 'category', 'auction', 'price', 'sold', 'condition']
#     list_filter = ['sold', 'condition', 'category', 'auction']
#     search_fields = ['name', 'description']
#     readonly_fields = ['created', 'updated']
#     raw_id_fields = ['category', 'auction']
#     actions = ['mark_as_sold']

#     def mark_as_sold(self, request, queryset):
#         queryset.update(sold=True)
#     mark_as_sold.short_description = "Mark selected products as sold"


@admin.register(AuctionBid)
class AuctionBidAdmin(admin.ModelAdmin):
    list_display = ['bidder', 'product', 'bid_price', 'winner', 'created']
    list_filter = ['winner', 'created']
    search_fields = ['bidder__username', 'product__name']
    raw_id_fields = ['bidder', 'product', 'auction']
    readonly_fields = ['created']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['transcation_id', 'phonenumber', 'item', 'amount', 'created']
    search_fields = ['item', 'phonenumber']
    list_filter = ['created']
    readonly_fields = ['created']

admin.site.site_header = 'Auction Admin'
admin.site.index_title = 'Auction Management'
admin.site.site_title = 'Auction Admin Panel'