from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.shortcuts import render
from django.views.generic import DetailView, View, ListView
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login

from .models import  Product, Customer, Cart, CartProduct, Category
from .mixins import CartMixin
from .forms import OrderForm, LoginForm
from .utils import recal_cart


# Create your views here.


class BaseView(CartMixin, View):

    models = ["notebook", "smartphone"]

    def get(self, request, *args, **kwargs):
        products = Product.objects.all()
        categories = Category.objects.all()
        context = {
            "products": products,
            "cart": self.cart,
            "categories": categories
        }
        return render(request, "item.html", context)


def test_view(request):
    return render(request, "base.html", {})


class ProductDetailView(CartMixin, DetailView):

    # model = Model
    # queryset = Model.objects.all()
    context_object_name = "product"
    template_name = "product_detail.html"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return  context


class CategoryDetailView(CartMixin, DetailView):

    model = Category
    queryset = Category.objects.all()
    context_object_name = 'category'
    template_name = 'category_detail.html'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = self.cart
        return context



class AddToCartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get("slug")
        product = Product.objects.get(slug=product_slug)
        cart_product, created = CartProduct.objects.get_or_create(
            user=self.cart.owner, cart=self.cart, product=product
        )
        if created:
            self.cart.products.add(cart_product)
        recal_cart(self.cart)
        messages.add_message(request, messages.INFO, "Item successfully added")
        return HttpResponseRedirect("/cart/")


class DeleteFromCartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get("slug")
        product = Product.objects.get(slug=product_slug)
        cart_product = CartProduct.objects.get(
            user=self.cart.owner, cart=self.cart, product=product
        )
        self.cart.products.remove(cart_product)
        cart_product.delete()
        recal_cart(self.cart)
        messages.add_message(request, messages.INFO, "Item successfully deleted")
        return HttpResponseRedirect("/cart/")


class ChangeQTYView(CartMixin, View):

    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get("slug")
        product = Product.objects.get(slug=product_slug)
        cart_product = CartProduct.objects.get(
            user=self.cart.owner, cart=self.cart, product=product
        )
        qty = int(request.POST.get('qty'))
        cart_product.qty = qty
        cart_product.save()
        recal_cart(self.cart)
        messages.add_message(request, messages.INFO, "Amount successfully changed")
        return HttpResponseRedirect('/cart/')


class CartView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        context = {
            "cart": self.cart,
            "categories": categories
        }
        return render(request, "cart.html", context)


class CheckoutView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        form = OrderForm(request.POST or None)
        context = {
            "cart": self.cart,
            "form": form,
            "categories": categories
        }
        return render(request, "checkout.html", context)

class MakeOrderView(CartMixin, View):

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = OrderForm(request.POST or None)
        customer = Customer.objects.get(user=request.user)
        if form.is_valid():
            new_order = form.save(commit=False)
            new_order.customer = customer
            new_order.first_name = form.cleaned_data['first_name']
            new_order.last_name = form.cleaned_data['last_name']
            new_order.phone = form.cleaned_data['phone']
            new_order.address = form.cleaned_data['address']
            new_order.buying_type = form.cleaned_data['baying_type']
            new_order.order_date = form.cleaned_data['order_date']
            new_order.comment = form.cleaned_data['comment']
            new_order.save()
            self.cart.in_order = True
            self.cart.save()
            new_order.cart = self.cart
            new_order.save()
            customer.orders.add(new_order)
            messages.add_message(request, messages.INFO, "Thanks for order! Our manager will phone you")
            return HttpResponseRedirect("/")
        return HttpResponseRedirect("/checkout/")


class LoginView(CartMixin, View):

    def get(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        categories = Category.objects.all()
        context = {'form': form, 'categories': categories, 'cart': self.cart}
        return render(request, 'login.html', context)

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return HttpResponseRedirect('/')
        return render(request, 'login.html', {'form': form, 'cart': self.cart})