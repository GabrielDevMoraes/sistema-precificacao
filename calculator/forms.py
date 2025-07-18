# calculator/forms.py
from django import forms
from .models import Produto

class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        # Campos que aparecerão no formulário para o usuário
        fields = ['nome', 'sku', 'custo_producao']
        # O campo 'proprietario' será preenchido automaticamente na view
        
        # Opcional: Adicionar classes do TailwindCSS e outros atributos
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'mt-1 block w-full p-2 rounded-md border-slate-300 shadow-sm'}),
            'sku': forms.TextInput(attrs={'class': 'mt-1 block w-full p-2 rounded-md border-slate-300 shadow-sm'}),
            'custo_producao': forms.NumberInput(attrs={'class': 'mt-1 block w-full p-2 rounded-md border-slate-300 shadow-sm'}),
        }