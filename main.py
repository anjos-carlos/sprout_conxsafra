from utils.manager import *
from utils.models import *

nova_agencia = Agencia(id_agencia=10, nome_agencia="Nova", local_envio="SP")
# lista = listar_registros("agencias.csv", Agencia)
# for l in lista:
#     print(l)
adicionar_registro("agencias.csv", nova_agencia)