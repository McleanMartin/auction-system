from django.db import models
from django.urls import reverse
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, RegexValidator
from django.utils.text import slugify
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone


class CustomUser(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    """
    has_proxy = models.BooleanField(default=False, null=True, blank=True)
    is_seller = models.BooleanField(default=False, null=True, blank=True)
    phonenumber = models.CharField(
        max_length=50,
        validators=[
            RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
            )
        ]
    )
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class Category(models.Model):
    """
    Model representing product categories.
    """
    name = models.CharField(max_length=200, db_index=True, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('core:items_list_by_category', args=[self.slug])


class Auction(models.Model):
    """
    Model representing auction events.
    """
    STATUS_CHOICES = (
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
    )

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    start_date = models.DateTimeField(auto_now=False)
    end_date = models.DateTimeField(auto_now=False)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='upcoming')
    minimum_bid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    expired = models.BooleanField(default=False)

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        return f'{self.name} Auction'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


@receiver(pre_save, sender=Auction)
def update_auction_status(sender, instance, **kwargs):
    """
    Signal to update auction status based on start and end dates.
    """
    now = timezone.now()
    if instance.start_date > now:
        instance.status = 'upcoming'
    elif instance.start_date <= now <= instance.end_date:
        instance.status = 'ongoing'
    else:
        instance.status = 'completed'
        instance.expired = True


class Product(models.Model):
    """
    Model representing products in an auction.
    """
    CONDITION_CHOICES = (
        ('new', 'New'),
        ('used', 'Used'),
        ('refurbished', 'Refurbished'),
    )

    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE, related_name='products')
    image = models.ImageField(upload_to='auction/%Y/%m/%d', blank=True)
    description = models.TextField(blank=True)
    condition = models.CharField(choices=CONDITION_CHOICES, default="new", max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    quantity = models.PositiveIntegerField(default=1)
    sold = models.BooleanField(default=False)
    seller = models.ForeignKey(CustomUser, verbose_name="seller_user", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ('name',)
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('core:product_detail', args=[self.slug])


class AuctionBid(models.Model):
    """
    Model representing bids placed on products in an auction.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('outbid', 'Outbid'),
        ('won', 'Won'),
    )

    bidder = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    bid_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    winner = models.BooleanField(default=False)
    payment_status = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.bidder.username} - {self.bid_price}"

    class Meta:
        ordering = ('-created',)


class StorageBill(models.Model):
    """
    Model representing storage bills for auctions.
    """
    auction = models.ForeignKey(Auction, on_delete=models.CASCADE)
    charge = models.PositiveIntegerField(default=0)
    days = models.PositiveIntegerField(default=0)
    paid = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"Storage Bill for {self.auction.name}"


class Delivery_Price(models.Model):
    """
    Model representing delivery prices between locations.
    """
    frm = models.CharField(max_length=50)
    to = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.CharField(max_length=50, blank=True, help_text="Estimated delivery duration")

    class Meta:
        verbose_name = "Delivery Price"
        verbose_name_plural = "Delivery Prices"

    def __str__(self):
        return f"{self.frm} - {self.to} Delivery price: {self.price}"

    def get_absolute_url(self):
        return reverse("Delivery_Price_detail", kwargs={"pk": self.pk})


class Payment(models.Model):
    """
    Model representing payment transactions.
    """
    PAYMENT_METHOD_CHOICES = (
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    transcation_id = models.AutoField(primary_key=True)
    auction = models.CharField(max_length=50)
    phonenumber = models.CharField(max_length=50)
    item = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total amount for the product")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='credit_card')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment {self.transcation_id} - {self.amount}"