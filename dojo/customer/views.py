# #  customer
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse
from django.core import serializers
from django.shortcuts import render, get_object_or_404
from dojo.filters import ProductTypeFilter
from dojo.forms import CustomerForm, CustomerProductForm
from dojo.models import Customer
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

    ptl = ProductTypeFilter(request.GET, queryset=initial_queryset)
    pts = get_page_items(request, ptl.qs, 25)
    add_breadcrumb(title="Customer List", top_level=True, request=request)
    return render(request, 'dojo/customer.html', {
        'name': 'Customer List',
        'metric': False,
        'user': request.user,
        'pts': pts,
        'ptl': ptl,
        'name_words': name_words})


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
def edit_customer(request, ptid):
    pt = get_object_or_404(Customer, pk=ptid)
    form = CustomerForm(instance=pt)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=pt)
        if form.is_valid():
            pt = form.save()
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
        'pt': pt})


@user_passes_test(lambda u: u.is_staff)
def add_product_to_customer(request, ptid):
    pt = get_object_or_404(Customer, pk=ptid)
    form = CustomerProductForm(initial={'prod_type': pt})
    add_breadcrumb(title="New %s Product" % pt.name, top_level=False, request=request)
    return render(request, 'dojo/new_product.html',
                  {'form': form,
                   })
