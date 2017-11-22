# #  customer
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse
from django.core import serializers
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from dojo.filters import ProductTypeFilter
from dojo.forms import CustomerForm, CustomerProductForm
from dojo.models import Customer, Product
from dojo.utils import get_page_items, add_breadcrumb, get_system_setting

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] %(message)s',
    datefmt='%d/%b/%Y %H:%M:%S',
    filename=settings.DOJO_ROOT + '/../django_app.log',
)
logger = logging.getLogger(__name__)

"""
Jay
Status: in prod
Customer views
"""


def customer(request):
    initial_queryset = Customer.objects.all().order_by('name')
    name_words = [product.name for product in
                  initial_queryset]

    cl = ProductTypeFilter(request.GET, queryset=initial_queryset)
    cs = get_page_items(request, cl.qs, 25)
    add_breadcrumb(title="Customer List", top_level=True, request=request)
    return render(request, 'dojo/customer.html', {
        'name': 'Customer List',
        'metric': False,
        'user': request.user,
        'cs': cs,
        'cl': cl,
        'name_words': name_words})


def customers_json(request):
    if request.user.is_superuser:
        customers = Customer.objects.all().order_by('name')
    else:
        customers = Customer.objects.filter(authorized_users__in=[request.user]).order_by('name')

    return HttpResponse(serializers.serialize('json', customers), content_type='application/json')


def customer_json(request, cid):
    if request.user.is_superuser:
        products = Product.objects.filter(customer__id=cid)
    else:
        products = Product.objects.filter(customer__id=cid,customer__authorized_users__in=[request.user])

    return HttpResponse(serializers.serialize('json', products), content_type='application/json')


@user_passes_test(lambda u: u.is_staff)
def add_customer(request):
    form = CustomerForm()
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'customer added successfully.',
                                 extra_tags='alert-success')
            return HttpResponseRedirect(reverse('customer'))
    add_breadcrumb(title="Add Customer", top_level=False, request=request)
    return render(request, 'dojo/new_customer.html', {
        'name': 'Add Customer',
        'metric': False,
        'user': request.user,
        'form': form,
    })


@user_passes_test(lambda u: u.is_staff)
def edit_customer(request, cid):
    customer = get_object_or_404(Customer, pk=cid)
    form = CustomerForm(instance=customer)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'customer updated successfully.',
                                 extra_tags='alert-success')
            return HttpResponseRedirect(reverse('customer'))
    add_breadcrumb(title="Edit Customer", top_level=False, request=request)
    return render(request, 'dojo/edit_customer.html', {
        'name': 'Edit Customer',
        'metric': False,
        'user': request.user,
        'form': form,
        'c': customer})


@user_passes_test(lambda u: u.is_staff)
def add_product_to_customer(request, cid):
    customer = get_object_or_404(Customer, pk=cid)
    form = CustomerProductForm(initial={'customer': customer.id})
    add_breadcrumb(title="New %s Product" % customer.name, top_level=False, request=request)
    return render(request, 'dojo/new_product.html',
                  {'form': form,
                   'customer': customer.name
                   })
