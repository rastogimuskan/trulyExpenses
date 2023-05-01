from django.shortcuts import render, redirect
from .models import Source, UserIncome
from django.core.paginator import Paginator
from django.contrib import messages
from userpreferences.models import Userpreference
from django.contrib.auth.decorators import login_required
import json
from django.http import JsonResponse
# Create your views here.


@login_required(login_url='/authentication/login')
def index(request):
    categories = Source.objects.all()
    income = UserIncome.objects.filter(owner=request.user)
    paginator = Paginator(income, 2)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    # import pdb
    # pdb.set_trace()
    currency = Userpreference.objects.get(user=request.user).currency
    context = {
        'income': income,
        'page_obj': page_obj,
        'currency': currency,
    }
    return render(request, 'income/index.html', context)


@login_required(login_url='/authentication/login')
def add_income(request):
    sources = Source.objects.all()
    # import pdb
    # pdb.set_trace()
    context = {
        "sources": sources,
        "values": request.POST
    }

    if request.method == 'GET':

        return render(request, 'income/add_income.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']
        description = request.POST['description']
        date = request.POST['income_date']
        source = request.POST['source']
        owner = request.user
        if not amount:
            messages.error(request, "Amount is required")
            return render(request, 'income/add_income.html', context)

        if not description:
            messages.error(request, "description is required")
            return render(request, 'income/add_income.html', context)

    UserIncome.objects.create(owner=owner, amount=amount, date=date,
                              source=source, description=description)
    messages.success(request, "Income added successfully")
    return redirect('income')


def income_edit(request, id):
    sources = Source.objects.all()
    income = UserIncome.objects.get(pk=id)

    context = {
        'income': income,
        'values': income,
        'sources': sources
    }

    if request.method == 'GET':
        return render(request, 'income/edit_income.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']
        description = request.POST['description']
        date = request.POST['income_date']
        source = request.POST['source']
        owner = request.user
        if not amount:
            messages.error(request, "Amount is required")
            return render(request, 'income/edit_income.html', context)

        if not description:
            messages.error(request, "description is required")
            return render(request, 'income/edit_income.html', context)

    UserIncome.objects.create(owner=owner, amount=amount, date=date,
                              source=source, description=description)

    # Income.owner = request.user
    income.amount = amount
    income.date = date
    income.description = description
    income.source = source

    income.save()

    messages.success(request, "Income updated successfully")
    return redirect('income')


def delete_income(request, id):
    income = UserIncome.objects.get(pk=id)
    income.delete()
    messages.success(request, "Income removed")
    return redirect('income')


def search_income(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText', '')
        income = UserIncome.objects.filter(
            amount__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            date__istartswith=search_str, owner=request.user) | UserIncome.objects.filter(
            description__icontains=search_str, owner=request.user) | UserIncome.objects.filter(
            source__icontains=search_str, owner=request.user)
        data = income.values()
        return JsonResponse(list(data), safe=False)
