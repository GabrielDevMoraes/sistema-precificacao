
from django.db import models
from django.conf import settings # Para relacionar com o User

class Produto(models.Model):
    # Relaciona cada produto a um usuário. Se o usuário for deletado, seus produtos também serão.
    proprietario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    nome = models.CharField(max_length=200, help_text="Nome ou descrição do produto")
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="Código de Referência (SKU)")
    custo_producao = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        help_text="Custo de Material + Produção do produto"
    )
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ['nome']