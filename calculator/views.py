# gabrieldevmoraes/sistema-precificacao/sistema-precificacao-4897d9676849616ba71945fe56a5b8efafbd22fa/calculator/views.py

import json
import requests
from bs4 import BeautifulSoup
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from decimal import Decimal, InvalidOperation
# Importa os modelos e formulários
from .models import Produto
from .forms import ProdutoForm

# Constantes e dados
ALIQUOTAS_ICMS = {
    'MT': 0.17, 'RO': 0.175, 'MS': 0.17, 'RS': 0.17, 'MG': 0.18
}
ORIGEM_STATES = ['NENHUM', 'MT']
DESTINO_STATES = ['NENHUM', 'MT', 'RO', 'MS', 'RS', 'MG']


# --- VIEWS PRINCIPAIS ---

def dashboard_view(request):
    """Exibe o painel principal com dados resumidos."""
    total_produtos = Produto.objects.count()
    context = {
        'total_produtos': total_produtos
    }
    return render(request, 'calculator/dashboard.html', context)



def calculator_view(request):
    """Exibe a calculadora de preços."""
    produtos_do_usuario = Produto.objects.all()
    
    context = {
        'origem_states': ORIGEM_STATES,
        'destino_states': DESTINO_STATES,
        'produtos': produtos_do_usuario,
    }
    return render(request, 'calculator/calculator.html', context)


# --- API DE BUSCA DE NCM ---
from .models import NcmMva

@require_GET
def search_ncm_api_view(request):
    ncm_query = request.GET.get("ncm", "").replace(".", "").strip()

    if not ncm_query:
        return JsonResponse({"error": "NCM não informado"}, status=400)

    registros = NcmMva.objects.filter(
        ncm__icontains=ncm_query,
        ativo=True
    )[:50]

    return JsonResponse([
        {
            "ncm_sh": r.ncm,
            "descricao": r.descricao,
            "mva": float(r.mva),
        }
        for r in registros
    ], safe=False)

# --- API DE CÁLCULO DE PREÇO ---

@require_POST
def calculate_api_view(request):
    try:
        data = json.loads(request.body)

        # ===============================
        # HELPERS
        # ===============================
        def get_decimal(key, default=0):
            try:
                value = data.get(key, default)
                if value in ("", None):
                    return Decimal(default)
                return Decimal(str(value))
            except (InvalidOperation, TypeError):
                return Decimal(default)

        def get_bool(key):
            return bool(data.get(key))

        # ===============================
        # DADOS BASE
        # ===============================
        custo_mp = get_decimal('custo_mp')
        frete_custo = get_decimal('frete_custo')
        ipi_pct = get_decimal('ipi') / 100

        # Mercadoria + IPI
        base_sem_mva = custo_mp + frete_custo
        valor_ipi = base_sem_mva * ipi_pct
        mercadoria_com_ipi = base_sem_mva + valor_ipi

        # ===============================
        # ICMS PRÓPRIO
        # ===============================
        icms_proprio_pct = get_decimal('icms_proprio') / 100
        valor_icms_proprio = custo_mp * icms_proprio_pct

        # ===============================
        # MVA / ICMS-ST
        # ===============================
        mva_pct = get_decimal('mva') / 100
        icms_st_pct = get_decimal('icms_st_aliquota') / 100

        base_st = Decimal('0')
        valor_icms_st = Decimal('0')

        if mva_pct > 0 and icms_st_pct > 0:
            base_st = mercadoria_com_ipi * (1 + mva_pct)
            icms_presumido = base_st * icms_st_pct
            valor_icms_st = icms_presumido - valor_icms_proprio
            if valor_icms_st < 0:
                valor_icms_st = Decimal('0')

        # ===============================
        # CUSTO TOTAL (produto)
        # ===============================
        custo_total_produto = mercadoria_com_ipi + valor_icms_st

        # ===============================
        # MARGEM LÍQUIDA (OBJETIVO)
        # ===============================
        margem_liquida_pct = get_decimal('margem_liquida') / 100
        if margem_liquida_pct >= 1:
            return JsonResponse({'error': 'Margem líquida inválida'}, status=400)

        preco_base_venda = custo_total_produto / (1 - margem_liquida_pct)
        lucro_liquido_base = preco_base_venda - custo_total_produto

        # ===============================
        # SALVAR / ATUALIZAR PRODUTO
        # ===============================
        produto_id = data.get('produto_id')
        produto_nome_manual = data.get('produto_nome_manual')
        salvar_produto = data.get('salvar_produto', False)
        ncm_selecionado = data.get('ncm')
        if salvar_produto:
            # Produto selecionado (já existe)
            if produto_id:
                try:
                    produto = Produto.objects.get(
                        id=produto_id,
                        proprietario=request.user
                    )
                    produto.custo_producao = custo_mp
                    produto.ncm = ncm_selecionado
                    produto.save(update_fields=['custo_producao', 'ncm'])
                except Produto.DoesNotExist:
                    pass

            # Produto digitado manualmente
            elif produto_nome_manual:
                nome_limpo = produto_nome_manual.strip()

                if nome_limpo:
                    produto, created = Produto.objects.get_or_create(
                        proprietario=request.user,
                        nome__iexact=nome_limpo,
                        defaults={
                            'nome': nome_limpo,
                            'custo_producao': custo_mp,
                            'ncm':ncm_selecionado
                        }
                    )

                    if not created:
                        produto.custo_producao = custo_mp
                        produto.ncm = ncm_selecionado
                        produto.save(update_fields=['custo_producao', 'ncm'])


        # ===============================
        # OUTROS CUSTOS SOBRE VENDA
        # ===============================
        preco = preco_base_venda

        custos_pct = (
            get_decimal('tx_adm') / 100 +
            get_decimal('irpj_csll') / 100 +
            get_decimal('comissao') / 100 +
            (Decimal('0.05') if get_bool('frete_leve') else Decimal('0')) +
            (Decimal('0.10') if get_bool('frete_pesado') else Decimal('0')) +
            Decimal('0.0065') +  # PIS
            Decimal('0.03')      # COFINS
        )

        estado_origem = data.get('estado_origem')
        estado_destino = data.get('estado_destino')

        icms_saida_pct = Decimal('0')
        if get_bool('icms_saida_checkbox') and estado_origem == estado_destino and estado_origem != 'NENHUM':
            icms_saida_pct = Decimal('0.12')

        difal_pct = Decimal('0')
        if get_bool('calc_difal') and estado_origem != estado_destino and estado_destino != 'NENHUM':
            difal_pct = Decimal('0.075')

        extras_pct = (
            icms_saida_pct +
            difal_pct +
            (Decimal('0.10') if get_bool('abrange_volus') else Decimal('0')) +
            (Decimal('0.10') if get_bool('troca') else Decimal('0')) +
            (Decimal('0.02') if get_bool('helio') else Decimal('0'))
        )

        valor_outros_custos = preco * (custos_pct + extras_pct)

        # ===============================
        # PREÇO FINAL
        # ===============================
        frete_venda = get_decimal('frete_venda')
        preco_venda_final = preco + frete_venda

        lucro_liquido_final = lucro_liquido_base - valor_outros_custos

        # ===============================
        # RESPOSTA
        # ===============================
        return JsonResponse({
            'custo_total_produto': round(custo_total_produto, 2),
            'preco_venda_final': round(preco_venda_final, 2),
            'produto_salvo': salvar_produto,


            'st_detalhado': {
                'mercadoria': round(custo_mp, 2),
                'ipi_valor': round(valor_ipi, 2),
                'ipi_percentual': round(ipi_pct * 100, 2),
                'mercadoria_com_ipi': round(mercadoria_com_ipi, 2),

                'icms_proprio_valor': round(valor_icms_proprio, 2),
                'icms_proprio_percentual': round(icms_proprio_pct * 100, 2),

                'mva_percentual': round(mva_pct * 100, 2),
                'base_st': round(base_st, 2),
                'icms_st_valor': round(valor_icms_st, 2),

                'impacto_st_percentual': round(
                    (valor_icms_st / custo_mp * 100) if custo_mp > 0 else 0,
                    2
                )
            },

            'detalhes': {
                'Custo do Produto': round(custo_total_produto, 2),
                'ICMS Próprio': round(valor_icms_proprio, 2),
                'ICMS-ST': round(valor_icms_st, 2),
                'Outros Custos Operacionais': round(valor_outros_custos, 2),
                'Lucro Líquido Final': round(lucro_liquido_final, 2),
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    

# --- VIEWS PARA GESTÃO DE PRODUTOS (CRUD) ---

def produto_list_view(request):
    """Lista todos os produtos do usuário logado."""
    produtos = Produto.objects.all()
    return render(request, 'calculator/produto_list.html', {'produtos': produtos})


def produto_create_view(request):
    """Cria um novo produto."""
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.proprietario = request.user
            produto.save()
            messages.success(request, 'Produto cadastrado com sucesso!')
            return redirect('produto_list')
    else:
        form = ProdutoForm()
    
    return render(request, 'calculator/produto_form.html', {'form': form})


def produto_update_view(request, pk):
    """Edita um produto existente."""
    produto = get_object_or_404(Produto, pk=pk)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('produto_list')
    else:
        form = ProdutoForm(instance=produto)
        
    return render(request, 'calculator/produto_form.html', {'form': form})


def produto_delete_view(request, pk):
    """Deleta um produto."""
    produto = get_object_or_404(Produto, pk=pk)
    
    if request.method == 'POST':
        produto.delete()
        messages.success(request, 'Produto excluído com sucesso!')
        return redirect('produto_list')
        
    return render(request, 'calculator/produto_confirm_delete.html', {'produto': produto})