import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages

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

@login_required
def dashboard_view(request):
    """Exibe o painel principal com dados resumidos."""
    total_produtos = Produto.objects.filter(proprietario=request.user).count()
    context = {
        'total_produtos': total_produtos
    }
    return render(request, 'calculator/dashboard.html', context)


@login_required
def calculator_view(request):
    """Exibe a calculadora de preços."""
    produtos_do_usuario = Produto.objects.filter(proprietario=request.user)
    
    context = {
        'origem_states': ORIGEM_STATES,
        'destino_states': DESTINO_STATES,
        'produtos': produtos_do_usuario,
    }
    return render(request, 'calculator/calculator.html', context)


@login_required
@require_POST
def calculate_api_view(request):
    """API interna para realizar o cálculo de preços."""
    try:
        data = json.loads(request.body)

        def get_float(key):
            return float(data.get(key) or 0)

        def get_bool(key):
            return bool(data.get(key))

        # Cálculos (lógica existente mantida)
        custo_mp = get_float('custo_mp')
        ipi_percentual = get_float('ipi') / 100
        frete_custo = get_float('frete_custo')
        custo_total_produto = (custo_mp + frete_custo) * (1 + ipi_percentual)
        markup_percentual = get_float('margem_bruta') / 100
        lucro_bruto_valor = custo_total_produto * markup_percentual
        frete_venda_valor = get_float('frete_venda')
        preco_venda_final = custo_total_produto + lucro_bruto_valor + frete_venda_valor
        
        # ... (resto da lógica de cálculo detalhada) ...
        custo_operacional_pct = get_float('custo_operacional') / 100
        tx_adm_pct = get_float('tx_adm') / 100
        irpj_csll_pct = get_float('irpj_csll') / 100
        comissao_pct = get_float('comissao') / 100
        frete_leve_pct = 0.05 if get_bool('frete_leve') else 0
        frete_pesado_pct = 0.10 if get_bool('frete_pesado') else 0
        pis_venda = 0.0065
        cofins_venda = 0.03
        estado_origem = data.get('estado_origem')
        estado_destino = data.get('estado_destino')
        icms_percentual = 0
        if get_bool('icms_saida_checkbox') and estado_origem == estado_destino and estado_origem != 'NENHUM':
            icms_percentual = 0.12
        elif estado_destino in ALIQUOTAS_ICMS:
            icms_percentual = ALIQUOTAS_ICMS[estado_destino]
        difal_percentual = 0
        if get_bool('calc_difal') and estado_origem != estado_destino and estado_destino != 'NENHUM':
            difal_map = {'RO': 0.075, 'MS': 0.075, 'RS': 0.05, 'MG': 0.06}
            difal_percentual = difal_map.get(estado_destino, 0)
        abrange_volus_pct = 0.10 if get_bool('abrange_volus') else 0
        troca_pct = 0.10 if get_bool('troca') else 0
        helio_pct = 0.02 if get_bool('helio') else 0
        valor_outros_custos = preco_venda_final * (custo_operacional_pct + tx_adm_pct + irpj_csll_pct + comissao_pct + frete_leve_pct + frete_pesado_pct + pis_venda + cofins_venda)
        valor_icms = preco_venda_final * icms_percentual
        valor_difal = preco_venda_final * difal_percentual
        valor_abrange = preco_venda_final * abrange_volus_pct
        valor_troca = preco_venda_final * troca_pct
        valor_helio = preco_venda_final * helio_pct
        valor_total_custos_analise = valor_outros_custos + valor_icms + valor_difal + valor_abrange + valor_troca + valor_helio
        lucro_liquido_estimado = lucro_bruto_valor - valor_total_custos_analise
        
        response_data = {
            'custo_total_produto': custo_total_produto,
            'preco_venda_final': preco_venda_final,
            'detalhes': {
                'Custo do Produto': custo_total_produto,
                'Lucro Bruto (Markup)': lucro_bruto_valor,
                'Outros Custos Operacionais': valor_outros_custos,
                'ICMS Saída': valor_icms,
                'DIFAL': valor_difal,
                'Abrange/Volus': valor_abrange,
                'Troca': valor_troca,
                'Hélio': valor_helio,
                'Lucro Líquido (Estimado)': lucro_liquido_estimado,
                'Frete de Venda': frete_venda_valor,
            }
        }
        
        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# --- VIEWS PARA GESTÃO DE PRODUTOS (CRUD) ---

@login_required
def produto_list_view(request):
    """Lista todos os produtos do usuário logado."""
    produtos = Produto.objects.filter(proprietario=request.user)
    return render(request, 'calculator/produto_list.html', {'produtos': produtos})


@login_required
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


@login_required
def produto_update_view(request, pk):
    """Edita um produto existente."""
    produto = get_object_or_404(Produto, pk=pk, proprietario=request.user)
    
    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso!')
            return redirect('produto_list')
    else:
        form = ProdutoForm(instance=produto)
        
    return render(request, 'calculator/produto_form.html', {'form': form})


@login_required
def produto_delete_view(request, pk):
    """Deleta um produto."""
    produto = get_object_or_404(Produto, pk=pk, proprietario=request.user)
    
    if request.method == 'POST':
        produto.delete()
        messages.success(request, 'Produto excluído com sucesso!')
        return redirect('produto_list')
        
    return render(request, 'calculator/produto_confirm_delete.html', {'produto': produto})