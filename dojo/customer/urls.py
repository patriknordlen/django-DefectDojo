from django.conf.urls import url

from dojo.customer import views

urlpatterns = [
    #  customer
    url(r'^product/type$', views.customer, name='customer'),
    url(r'^product/type/(?P<ptid>\d+)/edit$',
        views.edit_customer, name='edit_customer'),
    url(r'^product/type/add$', views.add_customer,
        name='add_customer'),
    url(r'^product/type/(?P<ptid>\d+)/add_product',
        views.add_product_to_customer,
        name='add_product_to_customer'),
]