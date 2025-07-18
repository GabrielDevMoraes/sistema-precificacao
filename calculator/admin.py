# calculator/admin.py

from django.contrib import admin
from .models import Produto

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'sku', 'custo_producao', 'proprietario')
    search_fields = ('nome', 'sku')
    list_filter = ('proprietario',)