from django.db import models
from django.urls import reverse
from accounts.models import User


class Category(models.Model):
    name = models.CharField(max_length=200, db_index=True, unique=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('core:items_list_by_category', args=[self.name])


class Auction(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    start_date = models.DateTimeField(auto_now=False)
    end_date = models.DateTimeField(auto_now=False)
    description = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    expired = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'{self.name} Auction'

class Product(models.Model):
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('used', 'Used'),
        ('refurbished', 'Refurbished'),
    )

    name = models.CharField(max_length=200, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='auction/%Y/%m/%d', blank=True)
    description = models.TextField(blank=True)
    condition = models.CharField(choices=CONDITION_CHOICES, default="new", max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    sold = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('name',)
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('core:product_detail', args=[self.id])



class AuctionBid(models.Model):
    bidder = models.ForeignKey(User, on_delete=models.CASCADE)
    auction = models.ForeignKey(Auction,on_delete=models.CASCADE)
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    bid_price = models.DecimalField(max_digits=10, decimal_places=2)
    winner = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.bidder.username)

class StorageBill(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)
    charge = models.PositiveIntegerField(default=0)
    days = models.PositiveIntegerField(default=0)


class Delivery_Price(models.Model):
    frm = models.CharField(max_length=50)
    to = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = ("Delivery Price")
        verbose_name_plural = ("Delivery Prices")

    def __str__(self):
        return self.frm +" - "+ self.to + " Delivery price: "+ str(self.price)

    def get_absolute_url(self):
        return reverse("Delivery_Price_detail", kwargs={"pk": self.pk})


class Payment(models.Model):
    transcation_id = models.AutoField(primary_key=True)
    acution = models.CharField(max_length=50)
    phonenumber = models.CharField(max_length=50)
    item = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2,help_text="total amount for the product")
    created = models.DateTimeField(auto_now=True)


