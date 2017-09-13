from django.conf.urls import url

from dojo.customer import views

urlpatterns = [
    #  customer
    url(r'^customer$', views.customer, name='customer'),
    url(r'^customer/json$', views.customers_json, name='customers_json'),
    url(r'^customer/(?P<cid>\d+)/json$', views.customer_json, name='customer_json'),
    url(r'^customer/(?P<cid>\d+)$', views.edit_customer,
        name='view_customer'),
    url(r'^customer/(?P<cid>\d+)/edit$',
        views.edit_customer, name='edit_customer'),
    url(r'^customer/add$', views.add_customer,
        name='add_customer'),
    url(r'^customer/(?P<cid>\d+)/add_product',
        views.add_product_to_customer,
        name='add_product_to_customer'),
]