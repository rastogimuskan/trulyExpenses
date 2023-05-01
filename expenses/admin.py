from django.contrib import admin
from .models import Expenses, Category
# Register your models here.


class ExpensesAdmin(admin.ModelAdmin):
    list_display = ('amount', 'description', 'owner', 'category', 'date')
    # search_fields = ('description', 'owner', 'category', 'date',)
    list_per_page = 5


admin.site.register(Expenses, ExpensesAdmin)
admin.site.register(Category)
