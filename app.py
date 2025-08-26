from flask import Flask, render_template, request, redirect, url_for, session, flash
from utils.manager import *
from utils.models import *
from datetime import datetime
import csv, os

app = Flask(__name__)
app.secret_key = "chave_secreta_supersegura"

# ---------------- FUNÇÃO PARA CARREGAR USUÁRIOS ----------------
def carregar_usuarios_csv():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(base_dir, "data", "usuarios.csv")
    usuarios = []
    with open(caminho, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            usuarios.append(row)
    return usuarios


# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario_input = request.form.get("usuario")
        senha_input = request.form.get("senha")
        usuarios = carregar_usuarios_csv()

        for u in usuarios:
            if u["usuario"] == usuario_input and u["senha"] == senha_input:
                session["usuario"] = u  # salva o usuário completo na sessão
                return redirect(url_for("home"))

        flash("Usuário ou senha inválidos!", "danger")
    return render_template("login.html")

# ---------------- HOME ----------------
@app.route("/home")
def home():
    if "usuario" not in session:
        return redirect(url_for("login"))

    usuario = session["usuario"]
    return render_template("home.html", usuario=usuario, year=datetime.now().year)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- FUNÇÃO DE CONTROLE DE ACESSO ----------------
def acesso_permitido(perfis):
    return session.get("usuario", {}).get("nome_classe") in perfis or session.get("usuario", {}).get("nome_classe") == "Administrador"

# ---------------- ROTAS ----------------

@app.route("/almoxarifado", methods=["GET", "POST"])
def almoxarifado():
    if not acesso_permitido(["Almoxarifado"]):
        flash("Acesso negado!", "danger")
        return redirect(url_for("home"))

    kits = listar_registros(Kit)
    estoque = listar_registros(EstoqueItem)
    colaboradores = listar_registros(Colaborador)

    if request.method == "POST":
        # ---------------- ADICIONAR ITEM ----------------
        if "adicionar_estoque" in request.form:
            novo_item = EstoqueItem(
                id_item=request.form["id_item"],
                item=request.form["item"],
                tamanho_camisa=request.form.get("tamanho_camisa", ""),
                id_kit=request.form["id_kit"],
                nome_kit=request.form["nome_kit"],
                qntd=int(request.form["qntd"]),
            )
            adicionar_registro(novo_item, EstoqueItem)
            flash("Item adicionado com sucesso!", "success")

        # ---------------- EDITAR ITEM ----------------
        if "alterar_estoque" in request.form:
            id_item = request.form["id_item"]
            nova_qntd = request.form.get("qntd")
            if nova_qntd is not None:
                atualizar_registro("id_item", id_item, {"qntd": int(nova_qntd)}, EstoqueItem)
                flash("Quantidade atualizada com sucesso!", "success")

        # ---------------- EXCLUIR ITEM ----------------
        if "remover_estoque" in request.form:
            id_item = request.form["id_item"]
            remover_registro("id_item", id_item, EstoqueItem)
            flash("Item removido com sucesso!", "success")

        # ---------------- ALTERAR SITUAÇÃO COLABORADOR ----------------
        if "alterar_situacao" in request.form:
            id_colab = request.form["id_colaborador"]
            nova_situacao = request.form["situacao"]
            atualizar_registro("id_colaborador", id_colab, {"situacao": nova_situacao}, Colaborador)
            flash("Situação alterada com sucesso!", "success")

        return redirect(url_for("almoxarifado"))

    return render_template("almoxarifado.html", kits=kits, estoque=estoque, colaboradores=colaboradores)


@app.route("/remover_usuario", methods=["POST"])
def remover_usuario():
    if not acesso_permitido(["RH", "Administrador"]):
        flash("Acesso negado!", "danger")
        return redirect(url_for("home"))

    id_usuario = request.form.get("id_usuario")
    if id_usuario:
        remover_registro("id_usuario", id_usuario, Usuario)
        flash("Usuário removido com sucesso!", "success")

    return redirect(url_for("rh"))

@app.route("/rh", methods=["GET", "POST"])
def rh():
    if not acesso_permitido(["RH"]):
        flash("Acesso negado!", "danger")
        return redirect(url_for("home"))

    usuarios = listar_registros(Usuario)
    colaboradores = listar_registros(Colaborador)
    kits = listar_registros(Kit)
    estoque = listar_registros(EstoqueItem)

    if request.method == "POST":
        if "adicionar_usuario" in request.form:
            novo = Usuario(
                id_usuario=request.form["id_usuario"],
                usuario=request.form["usuario"],
                senha=request.form["senha"],
                nome=request.form["nome"],
                email=request.form["email"],
                id_classe=request.form["id_classe"],
                nome_classe=request.form["nome_classe"],
            )
            adicionar_registro(novo, Usuario)

        if "remover_usuario" in request.form:
            id_usuario = request.form["id_usuario"]
            remover_registro("id_usuario", id_usuario, Usuario)

        if "editar_usuario" in request.form:
            id_usuario = request.form["id_usuario"]
            novos_dados = {
                "nome": request.form["nome"],
                "email": request.form["email"],
                "nome_classe": request.form["nome_classe"]
            }
            atualizar_registro("id_usuario", id_usuario, novos_dados, Usuario)

        return redirect(url_for("rh"))

    return render_template("rh.html", usuarios=usuarios, colaboradores=colaboradores, kits=kits, estoque=estoque)

@app.route("/gestor", methods=["GET", "POST"])
def gestor():
    if not acesso_permitido(["Gestor"]):
        flash("Acesso negado!", "danger")
        return redirect(url_for("home"))

    colaboradores = listar_registros(Colaborador)

    if request.method == "POST":
        if "nova_situacao" in request.form:
            id_colab = request.form["id_colaborador"]
            nova_situacao = request.form["nova_situacao"]
            atualizar_registro("id_colaborador", id_colab, {"situacao": nova_situacao}, Colaborador)

        if "excluir_colaborador" in request.form:
            id_colab = request.form["id_colaborador"]
            remover_registro("id_colaborador", id_colab, Colaborador)

        return redirect(url_for("gestor"))

    return render_template("gestor.html", colaboradores=colaboradores)

# ---------------- RODA APLICATIVO ----------------
if __name__ == "__main__":
    app.run(debug=True)
