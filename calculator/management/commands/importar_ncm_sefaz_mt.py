import requests
from bs4 import BeautifulSoup
from decimal import Decimal
from datetime import date
from django.core.management.base import BaseCommand
from calculator.models import NcmMva


URL_PORTARIA = (
    "https://app1.sefaz.mt.gov.br/sistema/legislacao/"
    "legislacaotribut.nsf/07fa81bed2760c6b84256710004d3940/"
    "4c7283a0b4318486042584c4004436c1?OpenDocument"
)

PORTARIA_NUMERO = "PORTARIA SEFAZ-MT (vigente)"
DATA_VIGENCIA = date(2024, 1, 1)


class Command(BaseCommand):
    help = "Importa NCM e MVA da Portaria da SEFAZ-MT"

    def handle(self, *args, **kwargs):
        self.stdout.write("🔄 Iniciando importação da SEFAZ-MT...")

        response = requests.get(URL_PORTARIA, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 🔒 Desativa todos antes de importar novamente
        NcmMva.objects.update(ativo=False)

        total_importados = 0
        headers = []
        tabela_encontrada = False

        for linha in soup.find_all("tr"):
            colunas = linha.find_all(["th", "td"])

            # 🔹 Identifica o cabeçalho correto
            if not tabela_encontrada:
                headers = [c.get_text(strip=True).lower() for c in colunas]

                if "ncm/sh" in headers and "mva" in headers:
                    tabela_encontrada = True
                continue

            if not tabela_encontrada or len(colunas) != len(headers):
                continue

            try:
                dados = dict(zip(headers, colunas))

                # 🔹 NCM
                ncm_raw = dados.get("ncm/sh", "").get_text(strip=True)
                ncm = "".join(filter(str.isdigit, ncm_raw))

                if len(ncm) < 4:
                    continue

                # 🔹 Descrição (trata variações de acento)
                descricao_col = (
                    dados.get("descrição")
                    or dados.get("descricao")
                    or ""
                )
                descricao = descricao_col.get_text(strip=True) if descricao_col else ""

                # 🔹 MVA
                mva_raw = dados.get("mva", "").get_text(strip=True)
                mva_raw = mva_raw.replace("%", "").replace(",", ".")

                mva = Decimal(mva_raw)

                # 🔹 Salva no banco
                NcmMva.objects.update_or_create(
                    ncm=ncm,
                    portaria=PORTARIA_NUMERO,
                    defaults={
                        "descricao": descricao,
                        "mva": mva,
                        "inicio_vigencia": DATA_VIGENCIA,
                        "ativo": True,
                    },
                )

                total_importados += 1

            except Exception as e:
                self.stderr.write(f"⚠️ Linha ignorada: {e}")
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Importação concluída com sucesso ({total_importados} NCMs)"
            )
        )
