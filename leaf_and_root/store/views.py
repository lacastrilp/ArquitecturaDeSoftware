from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView, DetailView, ListView, FormView
from django.contrib.auth.views import LoginView as AuthLoginView, LogoutView as AuthLogoutView
from django.contrib.auth import login
from django.http import HttpResponse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import Product, Review, Order, Customer  # 👈 agrega Customer
from .forms import RegisterForm, ReviewForm, ProductForm



# ---------- Solo admins ----------
def is_admin(user):
    return user.is_authenticated and user.is_staff
def is_admin(user):
    return user.is_staff  # o user.is_superuser


@user_passes_test(is_admin)
def admin_dashboard(request):
    products = Product.objects.all()
    return render(request, "admin/dashboard.html", {"products": products})

# --- Agregar producto ---
@login_required
@user_passes_test(is_admin)
def add_product(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("product_list")  # redirige a la lista de productos
    else:
        form = ProductForm()
    return render(request, "add_product.html", {"form": form})

# --- Editar producto ---
@login_required
@user_passes_test(is_admin)
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm(instance=product)
    return render(request, "edit_product.html", {"form": form, "product": product})

# --- Eliminar producto ---
@login_required
@user_passes_test(is_admin)
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        product.delete()
        return redirect("product_list")
    return render(request, "delete_product.html", {"product": product})
# ---------- Home ----------
class HomeView(TemplateView):
    template_name = "home.html"


# ---------- Productos ----------
class ProductDetailView(DetailView):
    model = Product
    template_name = "product_detail.html"
    context_object_name = "product"
    pk_url_kwarg = "product_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reviews"] = Review.objects.filter(product=self.object, approved=True)
        context["review_form"] = ReviewForm()  # 👈 form para el POST
        return context


class ProductSearchView(ListView):
    model = Product
    template_name = "product_search.html"
    context_object_name = "products"

    def get_queryset(self):
        query = self.request.GET.get("q", "")
        return Product.objects.filter(name__icontains=query)


# ---------- Autenticación ----------
class LoginView(AuthLoginView):
    template_name = "auth/login.html"


class LogoutView(AuthLogoutView):
    next_page = "/"


class RegisterView(FormView):
    template_name = "auth/register.html"
    form_class = RegisterForm

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return redirect("home")


# ---------- Carrito (simple) ----------
class AddToCartView(LoginRequiredMixin, View):
    def get(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        return HttpResponse(f"{product.name} agregado al carrito")


class RemoveFromCartView(LoginRequiredMixin, View):
    def get(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        return HttpResponse(f"{product.name} eliminado del carrito")


# ---------- Reseñas ----------
class SubmitReviewView(LoginRequiredMixin, View):
    def post(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        form = ReviewForm(request.POST)
        if form.is_valid():
            # asegurar Customer asociado al user
            customer = Customer.objects.filter(user=request.user).first()
            if not customer:
                # crea un Customer mínimo para poder guardar la reseña
                customer, _ = Customer.objects.get_or_create(
                    user=request.user,
                    defaults={
                        "name": request.user.get_full_name() or request.user.username,
                        "email": request.user.email or f"{request.user.username}@local.local",
                        "address": "",
                        "phone": "",
                    },
                )
            review = form.save(commit=False)
            review.product = product
            review.customer = customer   # 👈 usa customer, no user
            review.approved = True       # o déjalo False si quieres moderación
            review.save()
        return redirect("product_detail", product_id=product.pk)


class ModerateReviewView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff

    def get(self, request, review_id):
        review = get_object_or_404(Review, pk=review_id)
        review.approved = True
        review.save()
        return HttpResponse("Reseña moderada")


# ---------- Administración ----------
class AdminDashboardView(UserPassesTestMixin, TemplateView):
    template_name = "admin/dashboard.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = Product.objects.all()
        context["orders"] = Order.objects.all()
        context["reviews"] = Review.objects.filter(approved=False)
        return context


# ---------- Facturación ----------
class GenerateInvoicePDF(LoginRequiredMixin, View):
    def get(self, request, order_id):
        order = get_object_or_404(Order, pk=order_id)
        return HttpResponse(f"Factura PDF generada para la orden {order.pk}")


class ProductListView(ListView):
    model = Product
    template_name = "product_list.html"
    context_object_name = "products"
    
def product_list(request):
    products = Product.objects.all()
    return render(request, "product_list.html", {"products": products})
