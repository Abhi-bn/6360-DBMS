from django.contrib import admin
import Library.models as mod
from django.contrib.auth.models import User, Group, UserManager
from django.contrib.auth.admin import UserAdmin
from django.template.response import TemplateResponse
from django.urls import path
from django.db import transaction
import pandas as pd
from django.utils.text import capfirst
from django.core.exceptions import ValidationError
from copy import deepcopy
from django.forms import ModelForm
from datetime import  date

class MyModelAdmin(admin.AdminSite):
    site_url = None
    site_title = "Library"
    site_header ="Library Management System"
    # login_form = AuthenticationForm
    index_title = "Library Management System"
    index_template = 'admin/library_index.html'
    
    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        if request.user.is_anonymous:
            return app_list
        
        loans = mod.Loan.objects.filter(borrower=request.user, is_active=True)
        if len(loans) == 0:
            return app_list
        books = {
            'name': 'Rented Books',
            'app_label': "Library",
            'app_url':'/Library/loan/',
            'has_module_perms':True,
            'models':[]
            }
        models = {
                    "model": mod.Loan,
                    "object_name": 'Loans',
                    "perms": {'add': False, 'change': False, 'delete': False, 'view': True},
                    "admin_url": books['app_url'],
                    "add_url": None,
                }
        for loan in loans:
            md = deepcopy(models)
            md['name'] = capfirst(str(loan.book.isbn10) +" : " + str(loan.book))
            md['admin_url'] += str(loan.id)
            books['models'].append(md)
        app_list.insert(0, books)
        return app_list

    def get_urls(self):
        urls = super().get_urls()
        
        my_urls = [
            path('upload_data/', self.upload_data, name='upload_data'),
        ]
        
        return my_urls + urls

    @transaction.atomic
    def upload_data(self, request):
        context = {
            **self.each_context(request),
            "title": 'Upload Data',
            'options': ['', 'Borrower', 'Book'],
            **({})
        }
        if request.method == 'GET':
            return TemplateResponse(request, 'admin/upload_terms.html', context)

        if 'myfile' not in request.FILES:
            context['is_successful'] = False
            context['error'] = 'Please attach File'
        else:
            if request.POST['option_id'] == 'Borrower':
                dtype = {
                    'ID0000id': 'str',
                    'ssn': 'int32',
                    'first_name': 'str',
                    'last_name': 'str',
                    'email': 'str',
                    'address': 'str',
                    'city': 'str',
                    'state': 'str',
                    'phone': 'str',
                }
                try:
                    data = pd.read_csv(request.FILES['myfile'], dtype=dtype)
                    for row in data.itertuples():
                        b = mod.Borrower()
                        b.card_num = int(row[1].lstrip('ID')) + 1
                        b.ssn = str(row[2])
                        b.first_name = row[3]
                        b.last_name = row[4]
                        b.email = row[5]
                        b.address = row[6]
                        b.city = row[7]
                        b.state = row[8]
                        b.phone = row[9]
                        b.username = row[5]
                        b.set_password(row[3] + '@123!')
                       
                        b.is_staff = True
                        b.save()
                        my_group = Group.objects.get(name='Students') 
                        my_group.user_set.add(b)
                        print(row[0], row[3])
                    context['is_successful'] = True
                except Exception as e:
                    print(e)
                    context['is_successful'] = False
                    context['error'] = e.args.__str__()
            elif request.POST['option_id'] == 'Book':
                dtype = {
                    "ISBN10" : 'str',
                    "ISBN13": 'str',
                    "Title": 'str',
                    "Authro": 'str',
                    "Publisher": 'str',
                    "Pages": 'int',
                }
                try:
                    data = [str(line.decode('utf-8','ignore')).split('\t') for line in request.FILES['myfile']]

                    for i, row in enumerate(data):
                        if i == 0: 
                            continue
                        row[3] = row[3] if len(row[3]) > 0 else 'ANONYMOUS'
                        row[4] = row[4] if len(row[4]) > 0 else 'ANONYMOUS'

                        pub, _ = mod.Publisher.objects.get_or_create(publisher=row[4])
                        bk = mod.Book()
                        bk.isbn10 = row[0]
                        bk.isbn13 = row[1]
                        bk.title = row[2]
                        bk.pages = row[5]
                        bk.publisher = pub
                        bk.save()
                        for auth in row[3].split(','):
                            auth, _ = mod.Author.objects.get_or_create(name=auth)
                            book_auth, _ = mod.BookAuthor.objects.get_or_create(author=auth, book=bk)

                    context['is_successful'] = True
                except Exception as e:
                    print(e)
                    context['is_successful'] = False
                    context['error'] = e.args.__str__()
        return TemplateResponse(request, 'admin/upload_terms.html', context)
       

site = MyModelAdmin(name="Library")

admin.site = site

class MyUserAdmin(UserAdmin):
    model = User

admin.site.register(User, MyUserAdmin)

@admin.register(Group, site=site)
class Groups(admin.ModelAdmin):
    pass

@admin.register(mod.Author, site=site)
class Author(admin.ModelAdmin):
    search_fields = ['name']
    search_help_text = "Search by Author Name"
    list_display = ('id', 'name',)
    list_display_links = ['name']

class BookAuthorInline(admin.TabularInline):
    model = mod.BookAuthor
    raw_id_fields = ('author', 'book')
    extra = 0

# @admin.register(mod.BookAuthor, site=site)
# class BookAuthor(admin.ModelAdmin):
#     raw_id_fields = ('book','author')
@admin.register(mod.Book, site=site)
class Book(admin.ModelAdmin):
    actions = None
    inlines = [BookAuthorInline]
    list_display = ['isbn13', 'title', 'book_authors', 'publisher']
    list_display_links = ['title']
    search_fields = ['=isbn10', '=isbn13', 'title', 'publisher__publisher','bookauthor__author__name']
    search_help_text = "Search by isbn10, isbn13, title, author name or even from publisher name"
    raw_id_fields = ('publisher',)
    change_form_template = "admin/change_book_form.html"
    fieldsets = [
        ["Meta Info", {'fields': ('isbn13', 'isbn10')}, ],
        ['Book info', {'fields': ('title','book_authors','publisher','pages')},]
        ]

@admin.register(mod.Borrower, site=site)
class Borrower(UserAdmin):
    model = mod.Borrower
    list_display_links = ['first_name']
    readonly_fields = ['card_num_display']
    list_display = ( "first_name", "last_name","email")
    search_fields = ['first_name', 'last_name', 'email']
    search_help_text = "Search by first_name, last_name or from email"
    def __init__(self, model, admin_site) -> None:
        super().__init__(model, admin_site)
        self.fieldsets = list(self.fieldsets) + [
        ["Standard Info", {'fields': ('card_num_display', 'ssn')}, ],
        ['Address info', {'fields': ('address','city','state','phone',)}]
    ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(id=request.user.id)

class MyModelAdminForm(ModelForm):
    class Meta:
        model = mod.Loan
        fields = '__all__'



    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('book') is None:
            return cleaned_data
        obj = mod.Loan.objects.filter(book=cleaned_data['book'], is_active=True)
        if len(obj) !=0:
            raise ValidationError({
                'book': ValidationError('The Book is Currently not available'),
            })
        books = mod.Loan.objects.filter(borrower=cleaned_data['borrower'], is_active=True)
        if len(books) > 2:
            raise ValidationError({
                'borrower': ValidationError('You have Reached Maximum Borrowing Limit'),
            })
        return cleaned_data

@admin.register(mod.Loan, site=site)
class Loan(admin.ModelAdmin):
    form = MyModelAdminForm
    raw_id_fields = ('book','borrower')
    list_display_links = ['book']
    readonly_fields = ('loan_num', 'date_out', 'date_in', 'is_active')
    fields = ('loan_num', 'book', "borrower", 'date_due', 'date_out', 'date_in', 'is_active')
    list_display = ['loan_num', 'book', 'borrower', 'date_due', 'is_active']
    search_fields = ['=loan_num', 'book__title', 'borrower__first_name']
    change_form_template = 'admin/custom_loan_change_form.html'
    search_help_text = "Search by Loan Num, book title or borrower first Name"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(borrower=request.user)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj = None):
        if obj != None:
            fields = ['loan_num', 'date_out', 'date_in', 'book', 'borrower', 'is_active']
            if not obj.is_active:
                fields += ['date_due', 'book', 'borrower']
            if not request.user.is_superuser:
                fields += ['date_due']
            return fields
        else:
            fields = ['loan_num', 'date_out', 'date_in', 'is_active']
            if not request.user.is_superuser:
                fields += ['date_due']
            return fields

        return super().get_readonly_fields(request, obj)

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        if not change:
            fine = mod.Fine()
            fine.loan = obj
            fine.fine_amt = 0.0
            fine.save()
       

    def change_view(self, request, object_id: str, form_url: str = "", extra_context = None):
        extra_context = {
            'fine': mod.Fine.objects.get(loan_id=object_id)
        }
        return super().change_view(request, object_id, form_url, extra_context)

@admin.register(mod.Fine, site=site)
class Fine(admin.ModelAdmin):
    readonly_fields = ('loan','paid', 'fine_amt_disp')
    fields = ('loan', 'fine_amt_disp', "paid",)
    list_display_links = ['loan']
    list_display = ('id', 'loan', 'fine_amt_disp', "paid",)
    search_fields = ["=id", '=loan__loan_num', 'loan__book__title', 'loan__borrower__first_name']
    change_form_template = 'admin/custom_fine_change_form.html'
    search_help_text = "Search by Fine ID, Loan Number, book title or borrower first Name"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(loan__borrower=request.user)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_object(self, request, object_id: str, from_field= None):
        obj = super().get_object(request, object_id, from_field)
        obj.fine_amt = 0.25 * max(0, (date.today() - obj.loan.date_due).days)
        if request.POST.get('paid') and request.POST.get('paid') == 'true':
            obj.paid = True
            obj.loan.is_active = False
            obj.loan.date_in = date.today()
            obj.loan.save()
        obj.save()
        return obj

@admin.register(mod.Publisher, site=site)
class Publisher(admin.ModelAdmin):
    search_fields = ['publisher']
    list_display = ('id', 'publisher',)
    search_help_text = "Search by Publisher title"
    list_display_links = ['publisher']
