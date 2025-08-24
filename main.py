from utils.manager import *
from utils.models import *

def main():
    print("=== Testes do sistema ===")

    ### TESTE AGENCIAS
    print("\n--- TESTE AGENCIAS ---")
    agencias = listar_registros(Agencia)
    print("Agencias:", agencias[:3])
    input("Digite algo para continuar...")

    # 2. Adicionar registro
    nova_agencia = Agencia(id_agencia="0999", nome_agencia="Agência Teste", local_envio="Rua X")
    adicionar_registro(nova_agencia, Agencia)
    print("Agência adicionada!")
    input("Digite algo para continuar...")

    # 3. Atualizar registro
    atualizar_registro("id_agencia", "0999", {"nome_agencia": "Agência Atualizada"}, Agencia)
    print("Agência atualizada!")
    input("Digite algo para continuar...")

    # 4. Buscar registro
    agencia = buscar_registro("id_agencia", "0999", Agencia)
    print("Busca:", agencia)
    input("Digite algo para continuar...")

    # 5. Filtrar registros
    agencias_filtradas = filtrar_registros(Agencia, nome_agencia="Agência Atualizada")
    print("Filtradas:", agencias_filtradas)
    input("Digite algo para continuar...")

    # 6. Ordenar registros
    agencias_ordenadas = ordenar_registros(Agencia, "nome_agencia")
    print("Ordenadas:", [a.nome_agencia for a in agencias_ordenadas[:5]])
    input("Digite algo para continuar...")

    # 7. Paginar registros
    pagina1 = paginar_registros(agencias_ordenadas, pagina=1, tamanho_pagina=3)
    print("Página 1:", pagina1)
    input("Digite algo para continuar...")

    # 8. Remover registro
    remover_registro("id_agencia", "0999", Agencia)
    print("Agência removida!")
    input("Digite algo para continuar...")

    ### TESTE COLABORADORES
    print("\n--- TESTE COLABORADORES ---")
    colaboradores = listar_registros(Colaborador)
    print("Colaboradores:", colaboradores[:3])
    input("Continuar...")

    novo_colab = Colaborador(id_colaborador="C001", nome_colaborador="Maria Teste",
                             email_colaborador="maria@teste.com", id_gestor="G001",
                             id_kit="K001", data_admissao="2024-01-01",
                             tamanho_camisa="M", id_agencia="A001", situacao="Ativo")
    adicionar_registro(novo_colab, Colaborador)
    print("Colaborador adicionado!")
    input("Continuar...")

    atualizar_registro("id_colaborador", "C001", {"situacao": "Inativo"}, Colaborador)
    print("Colaborador atualizado!")
    input("Continuar...")

    colab = buscar_registro("id_colaborador", "C001", Colaborador)
    print("Busca:", colab)
    input("Continuar...")

    remover_registro("id_colaborador", "C001", Colaborador)
    print("Colaborador removido!")
    input("Continuar...")

    ### TESTE ESTOQUE
    print("\n--- TESTE ESTOQUE ---")
    estoque = listar_registros(EstoqueItem)
    print("Estoque:", estoque[:3])
    input("Continuar...")

    novo_item = EstoqueItem(id_item="I001", item="Camisa Azul", tamanho_camisa="G",
                            id_kit=1, qntd=50)
    adicionar_registro(novo_item, EstoqueItem)
    print("Item adicionado!")
    input("Continuar...")

    atualizar_registro("id_item", "I001", {"qntd": 45}, EstoqueItem)
    print("Item atualizado!")
    input("Continuar...")

    item = buscar_registro("id_item", "I001", EstoqueItem)
    print("Busca:", item)
    input("Continuar...")

    remover_registro("id_item", "I001", EstoqueItem)
    print("Item removido!")
    input("Continuar...")

    ### TESTE KITS_CADASTRADOS
    print("\n--- TESTE KITS ---")
    kits = listar_registros(Kit)
    print("Kits:", kits[:3])
    input("Continuar...")

    novo_kit = Kit(id_kit="K999", nome_kit="Kit Teste")
    adicionar_registro(novo_kit, Kit)
    print("Kit adicionado!")
    input("Continuar...")

    atualizar_registro("id_kit", "K999", {"nome_kit": "Kit Atualizado"}, Kit)
    print("Kit atualizado!")
    input("Continuar...")

    kit = buscar_registro("id_kit", "K999", Kit)
    print("Busca:", kit)
    input("Continuar...")

    remover_registro("id_kit", "K999", Kit)
    print("Kit removido!")
    input("Continuar...")

    ### TESTE USUARIOS
    print("\n--- TESTE USUARIOS ---")
    usuarios = listar_registros(Usuario)
    print("Usuários:", usuarios[:3])
    input("Continuar...")

    novo_user = Usuario(id_usuario="U001", usuario="teste", senha="1234",
                        nome="Usuário Teste", email="teste@teste.com",
                        id_classe="1", nome_classe="Administrador")
    adicionar_registro(novo_user, Usuario)
    print("Usuário adicionado!")
    input("Continuar...")

    atualizar_registro("id_usuario", "U001", {"email": "novo@teste.com"}, Usuario)
    print("Usuário atualizado!")
    input("Continuar...")

    user = buscar_registro("id_usuario", "U001", Usuario)
    print("Busca:", user)
    input("Continuar...")

    remover_registro("id_usuario", "U001", Usuario)
    print("Usuário removido!")
    input("Continuar...")

if __name__ == "__main__":
    main()
