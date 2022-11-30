from django.db import models
from datetime import datetime, timedelta,date
from phonenumber_field.modelfields import PhoneNumberField
from django.contrib import admin
from django.contrib.auth.models import AbstractUser
from django.template.defaultfilters import truncatechars
from django.contrib.contenttypes.fields import  GenericRelation

class Publisher(models.Model):
    publisher = models.CharField(max_length=30, null=False, unique=True)

    def __str__(self):
        return self.publisher

class Author(models.Model):
    name = models.CharField(max_length=50, unique=True, default="ANONYMOUS")
    
    def __str__(self):
        return self.name
    
class Book(models.Model):
    isbn10 = models.CharField(max_length=10, unique=True, null=False)
    isbn13 = models.CharField(max_length=13, unique=True, null=False)
    title = models.CharField(max_length=50, null=False)
    pages = models.IntegerField(null=False, default=0)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    # book_authors = models.ManyToManyRel('self', 'BookAuthor')

    def __str__(self):
        return self.title

    class Meta:
        unique_together = ('isbn10', 'isbn13', 'title', 'publisher')
    
    @property
    def short_publisher(self):
        return truncatechars(str(self.publisher), 15)

    @property
    def book_authors(self):
        info = BookAuthor.objects.filter(book=self)
        return ', '.join([str(i) for i in info])

class BookAuthor(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.author)

    class Meta:
        unique_together = ('author', 'book',)

class Borrower(AbstractUser):
    REQUIRED_FIELDS = ['card_num', 'ssn', 'phone']
    card_num = models.IntegerField(unique=True, null=False)
    ssn = models.CharField(max_length=9, null=False)
    address = models.TextField()
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=2)
    phone = PhoneNumberField(unique=True, null=False)

    class Meta:
        unique_together = ('ssn','phone')

    @admin.display(description='Library ID')
    def card_num_display(self):
        return 'ID'+ '0' * (6 - len(str(self.card_num))) + str(self.card_num)

    def __str__(self):
        return self.last_name + ', ' + self.first_name

def generate_unique():
    import uuid
    return uuid.uuid4().hex[:7]

def get_date_14_days():
    return datetime.now() + timedelta(14)

class Loan(models.Model):
    loan_num = models.CharField(max_length=7, unique=True, null=False, default=generate_unique)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    borrower = models.ForeignKey(Borrower, on_delete=models.CASCADE)
    date_out = models.DateField(auto_now_add=False, null=False,default=datetime.now)
    date_due = models.DateField(default=get_date_14_days, auto_now=False, auto_now_add=False, null=False)
    date_in = models.DateField(auto_now=False, auto_now_add=False, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    @admin.display(description='Library ID')
    def calc_fine(self):
        if (date.today() - self.date_due).days < 0:
            return str(0)
        return str('$' + str(0.25 * (date.today() - self.date_due).days))

    class Meta:
        unique_together = ('loan_num','book_id', 'borrower_id')

    def __str__(self):
        return str(self.borrower) + ' → ' + str(self.book)

class Fine(models.Model):
    loan =  models.ForeignKey(Loan, on_delete=models.CASCADE)
    fine_amt = models.DecimalField(decimal_places=2, max_digits=8,null=False)
    paid = models.BooleanField(default=False)

    @admin.display(description='Library ID')
    def fine_amt_disp(self):
        return '$ ' + str(self.fine_amt)
    def __str__(self):
        return str(self.loan)
