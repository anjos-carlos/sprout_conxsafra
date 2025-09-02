import os, csv
from utils import manager, models

usuario_teste = "script_teste"

def imprimir_log_formatado():
    from utils.manager import DATA_DIR
    manager.restore_data()    
    log_file = os.path.join(DATA_DIR, "logs.csv")
    if not os.path.exists(log_file):
        print("\n[LOG] Nenhum log encontrado.")
        return

    print("\n===== LOG DE AÇÕES =====")
    with open(log_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            print(f"\n#{i} [{row['data']} {row['hora']}] usuário={row['usuario']} ação={row['acao']}")
            print("  - Antes :", row["linha_antes"])
            print("  - Depois:", row["linha_depois"])
    print("========================\n")
    manager.backup_data()

def teste_crud(entidade, chave, dados_iniciais, dados_atualizados):
    print(f"\n# --- TESTE {entidade.__name__.upper()} --- #")

    registros = manager.listar_registros(entidade)
    print("Registros iniciais:", registros[:3])
    input("Continuar...")

    # 1. Criar
    novo = entidade(**dados_iniciais)
    resultado = manager.adicionar_registro(novo, entidade)
    manager.log_action(usuario_teste, resultado)
    print("Adicionado!")
    input("Continuar...")
    

    # 2. Atualizar
    valor_chave = resultado["linha_depois"][chave]
    resultado = manager.atualizar_registro(chave, valor_chave, dados_atualizados, entidade)
    manager.log_action(usuario_teste, resultado)
    print("Atualizado!")
    input("Continuar...")

    # 3. Buscar
    encontrado = next((r for r in manager.listar_registros(entidade) if getattr(r, chave) == valor_chave), None)
    print("Busca:", encontrado)
    input("Continuar...")

    # 4. Remover
    resultado = manager.remover_registro(chave, valor_chave, entidade)
    manager.log_action(usuario_teste, resultado)
    print("Removido!")
    input("Continuar...")


# --- Funções de teste específicas --- #

def teste_agencias():
    teste_crud(
        models.Agencia,
        "id_agencia",
        {"cidade_envio": "Agência Teste", "uf_envio": "Rua X", "prazo_dias": "999"},
        {"cidade_envio": "Agência Atualizada"}
    )


def teste_colaboradores():
    teste_crud(
        models.Colaborador,
        "id_colaborador",
        {"nome_colaborador": "Maria Teste",
         "email_colaborador": "maria@teste.com",
         "id_gestor": "U001",
         "id_kit": "K001",
         "data_admissao": "2024-01-01",
         "tamanho_camisa": "G",
         "id_agencia": "A001",
         "situacao": "Ativo"},
        {"situacao": "Inativo"}
    )


def teste_estoque():
    teste_crud(
        models.EstoqueItem,
        "id_item",
        {"item": "Camisa Azul", "tamanho_camisa": "G",
         "id_kit": "K001", "qntd": 50},
        {"qntd": 45}
    )

def teste_kits():
    teste_crud(
        models.Kit,
        "id_kit",
        {"nome_kit": "Kit Teste"},
        {"nome_kit": "Kit Atualizado"}
    )

def teste_usuarios():
    teste_crud(
        models.Usuario,
        "id_usuario",
        {"usuario": "teste", "senha": "1234",
         "nome": "Usuário Teste", "email": "teste@teste.com",
         "id_classe": "1", "nome_classe": "Administrador"},
        {"email": "novo@teste.com"}
    )

def main():
    print("=== Testes do sistema ===")
    teste_agencias()
    teste_colaboradores()
    teste_estoque()
    teste_kits()
    teste_usuarios()
    imprimir_log_formatado()
    manager.debug_dados(mostrar_tudo=False, limite=3)
    print("=== Testes finalisados ===")

if __name__ == "__main__":
    main()
