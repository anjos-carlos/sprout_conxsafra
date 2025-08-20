import csv

class usuarioGestao:
    def __init__(self, user: str, pwd: str):
        self.user = user
        self.pwd = pwd
    
    def visualiza_base(self, arquivo: str, max_linhas=5):
        """
        Visualiza tabelas específicas (carrega um CSV).
        Mostra apenas algumas linhas.
        """
        try:
            with open(arquivo, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                linhas = [linha for _, linha in zip(range(max_linhas), reader)]
            return linhas
        except FileNotFoundError:
            return f"Arquivo {arquivo} não encontrado."


class usuarioRH(usuarioGestao):
    """
    Usuário do RH: funções de cadastro, exclusão e validação de usuários.
    """
    def valida_usuario(self, arquivo_usuarios="usuarios.csv"):
        """
        Verifica se o usuário está na base de usuários.
        """
        with open(arquivo_usuarios, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["usuario"] == self.user and row["senha"] == self.pwd:
                    return True
        return False

    def cadastra_usuario(self, novo_user: str, novo_pwd: str, arquivo_usuarios="usuarios.csv"):
        """
        Cadastra um novo usuário no CSV.
        """
        usuarios = []
        with open(arquivo_usuarios, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            usuarios = list(reader)
            campos = reader.fieldnames

        for row in usuarios:
            if row["usuario"] == novo_user:
                return "Usuário já cadastrado."

        usuarios.append({"usuario": novo_user, "senha": novo_pwd})

        with open(arquivo_usuarios, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(usuarios)

        return f"Usuário {novo_user} cadastrado com sucesso."

    def exclusao_usuario(self, usuario_excluir: str, arquivo_usuarios="usuarios.csv"):
        """
        Exclui usuário do cadastro.
        """
        usuarios = []
        removido = False
        with open(arquivo_usuarios, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            campos = reader.fieldnames
            for row in reader:
                if row["usuario"] != usuario_excluir:
                    usuarios.append(row)
                else:
                    removido = True

        if not removido:
            return "Usuário não encontrado."

        with open(arquivo_usuarios, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(usuarios)

        return f"Usuário {usuario_excluir} excluído com sucesso."


class usuarioAL(usuarioGestao):
    """
    Permite edição na tabela de estoque.
    """
    def altera_estoque(self, id_item: str, coluna: str, novo_valor, arquivo="estoque.csv"):
        """
        Altera uma informação do estoque (quantidade, preço, etc.).
        id_item: valor da chave primária do item (string ou número convertido para str).
        """
        estoque = []
        alterado = False
        with open(arquivo, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            campos = reader.fieldnames
            for row in reader:
                if row["id"] == str(id_item):
                    if coluna in row:
                        row[coluna] = str(novo_valor)
                        alterado = True
                estoque.append(row)

        if not alterado:
            return f"Item {id_item} não encontrado ou coluna {coluna} inválida."

        with open(arquivo, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(estoque)

        return f"Estoque atualizado: item {id_item}, {coluna} = {novo_valor}"


class usuarioGA(usuarioGestao):
    """
    Permite alteração de linhas específicas da tabela empregados.
    """
    def altera_empregado(self, id_empregado: str, coluna: str, novo_valor, arquivo="empregados.csv"):
        empregados = []
        alterado = False
        with open(arquivo, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            campos = reader.fieldnames
            for row in reader:
                if row["id"] == str(id_empregado):
                    if coluna in row:
                        row[coluna] = str(novo_valor)
                        alterado = True
                empregados.append(row)

        if not alterado:
            return f"Empregado {id_empregado} não encontrado ou coluna {coluna} inválida."

        with open(arquivo, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            writer.writerows(empregados)

        return f"Empregado {id_empregado} atualizado: {coluna} = {novo_valor}"
