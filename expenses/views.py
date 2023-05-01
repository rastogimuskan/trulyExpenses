from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Category, Expenses
from django.contrib import messages
from django.core.paginator import Paginator
import json
from django.http import JsonResponse, HttpResponse
from userpreferences.models import Userpreference
import datetime
import csv
import xlwt
from django.template.loader import render_to_string
from weasyprint import HTML
import tempfile
from django.db.models import Sum


def search_expenses(request):
    if request.method == 'POST':
        search_str = json.loads(request.body).get('searchText', '')
        expenses = Expenses.objects.filter(
            amount__istartswith=search_str, owner=request.user) | Expenses.objects.filter(
            date__istartswith=search_str, owner=request.user) | Expenses.objects.filter(
            description__icontains=search_str, owner=request.user) | Expenses.objects.filter(
            category__icontains=search_str, owner=request.user)
        data = expenses.values()
        return JsonResponse(list(data), safe=False)


@login_required(login_url='/authentication/login')
def index(request):
    categories = Category.objects.all()
    expenses = Expenses.objects.filter(owner=request.user)
    paginator = Paginator(expenses, 2)
    page_number = request.GET.get('page')
    page_obj = Paginator.get_page(paginator, page_number)
    # import pdb
    # pdb.set_trace()
    currency = Userpreference.objects.get(user=request.user).currency
    context = {
        'expenses': expenses,
        'page_obj': page_obj,
        'currency': currency,
    }
    return render(request, 'expenses/index.html', context)


def add_expenses(request):
    categories = Category.objects.all()
    context = {
        "categories": categories,
        "values": request.POST
    }

    if request.method == 'GET':

        return render(request, 'expenses/add_expenses.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']
        description = request.POST['description']
        date = request.POST['expenses_date']
        category = request.POST['category']
        owner = request.user
        if not amount:
            messages.error(request, "Amount is required")
            return render(request, 'expenses/add_expenses.html', context)

        if not description:
            messages.error(request, "description is required")
            return render(request, 'expenses/add_expenses.html', context)

    Expenses.objects.create(owner=owner, amount=amount, date=date,
                            category=category, description=description)
    messages.success(request, "Expense added successfully")
    return redirect('expenses')


def expense_edit(request, id):
    categories = Category.objects.all()
    expenses = Expenses.objects.get(pk=id)

    context = {
        'expense': expenses,
        'values': expenses,
        'categories': categories
    }
    # import pdb
    # pdb.set_trace()
    if request.method == 'GET':
        return render(request, 'expenses/expense-edit.html', context)
    if request.method == 'POST':
        amount = request.POST['amount']
        description = request.POST['description']
        date = request.POST['expenses_date']
        category = request.POST['category']
        owner = request.user
        if not amount:
            messages.error(request, "Amount is required")
            return render(request, 'expenses/expense-edit.html', context)

        if not description:
            messages.error(request, "description is required")
            return render(request, 'expenses/expense-edit.html', context)

    Expenses.objects.create(owner=owner, amount=amount, date=date,
                            category=category, description=description)

    expenses.owner = request.user
    expenses.amount = amount
    expenses.date = date
    expenses.description = description
    expenses.category = category

    expenses.save()

    messages.success(request, "Expense updated successfully")
    return redirect('expenses')


def delete_expense(request, id):
    expense = Expenses.objects.get(pk=id)
    expense.delete()
    messages.success(request, "Expense removed")
    return redirect('expenses')


def expense_category_summary(request):
    today_date = datetime.date.today()
    six_months_ago = today_date - datetime.timedelta(days=30*6)
    print(six_months_ago)
    expenses = Expenses.objects.filter(owner=request.user,
                                       date__gte=six_months_ago, date__lte=today_date)
    finalrep = {}

    def get_category(expense):
        return expense.category

    def get_expense_category_amount(category):
        amount = 0
        filter_by_category = expenses.filter(category=category)
        for item in filter_by_category:
            amount = amount + item.amount

        return amount

    category_list = list(set(map(get_category, expenses)))
    for x in expenses:
        for y in category_list:
            finalrep[y] = get_expense_category_amount(y)
    return JsonResponse({'expense_category_data': finalrep}, safe=False)


def stats_view(request):
    return render(request, 'expenses/stats.html')


def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=Expenses' + \
        str(datetime.datetime.now())+'.csv'
    writer = csv.writer(response)
    writer.writerow(['Amount', 'Description', 'category', 'Date'])
    expenses = Expenses.objects.filter(owner=request.user)
    for expense in expenses:
        writer.writerow([expense.amount, expense.description,
                        expense.category, expense.date])
    return response


def export_excel(request):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=Expenses' + \
        str(datetime.datetime.now())+'.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Expenses')
    row_num = 0
    font_style = xlwt.XFStyle()
    font_style.font.bold = True
    columns = ['Amount', 'Description', 'category', 'Date']
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], font_style)

    font_style = xlwt.XFStyle()
    rows = Expenses.objects.filter(owner=request.user).values_list(
        'amount', 'description', 'category', 'date')
    for row in rows:
        row_num += 1
        for col_num in range(len(row)):
            ws.write(row_num, col_num, str(row[col_num]), font_style)
    wb.save(response)
    return response


def export_pdf(request):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; attachment; filename=Expenses' + \
        str(datetime.datetime.now())+'.pdf'
    response['Content-Transfer-Encoding'] = 'binary'
    expenses = Expenses.objects.filter(owner=request.user)
    sum = expenses.aggregate(Sum('amount'))
    html_string = render_to_string(
        'expenses/pdf-output.html', {'expenses': expenses, 'total': sum['amount__sum']})
    html = HTML(string=html_string)
    result = html.write_pdf()
    with tempfile.NamedTemporaryFile(delete=True) as output:
        output.write(result)
        output.flush()

        output = open(output.name, 'rb')
        response.write(output.read())

    return response
