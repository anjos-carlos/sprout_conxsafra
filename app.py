# app.py
import threading
import webbrowser
import sys
import logging
import os
import csv

from flask import Flask, render_template, request, redirect, url_for, session, flash
from utils.manager import *   # read_csv, write_csv, listar_registros, adicionar_registro, atualizar_registro, remover_registro, validar_estoque_para_kit, ajustar_estoque_para_kit
from utils.models import *    # Agencia, Colaborador, EstoqueItem, Kit, Usuario
from datetime import datetime

# $ alterar para puxar o utils
# from utils import manager
# from utils import models  

# $ nas funções de adicionar, remover e alterar tem que chamar o log

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
os.environ['FLASK_ENV'] = 'production'

app = Flask(__name__)
app.secret_key = "chave_secreta_supersegura"

# ---------------- HELPERS ROBUSTOS ----------------
def normalize(value):
    """Converte qualquer valor para string segura (sem quebrar tipos)."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool, list, tuple, set, dict)):
        return str(value).strip()
    return str(value).strip()

def get_field(rec, *names, default=""):
    """Lê rec.nome OU rec['nome'], tentando aliases. Retorna sem normalizar."""
    for name in names:
        if hasattr(rec, name):
            val = getattr(rec, name)
            return default if val is None else val
        if isinstance(rec, dict) and name in rec:
            val = rec.get(name)
            return default if val is None else val
    return default

def flatten_record(u):
    """
    Converte formatos estranhos em dict plano.
    Suporta: dict(s) e dataclass/objeto (usa vars()).
    """
    # dict
    if isinstance(u, dict):
        # se já parece o formato final, devolve como está
        if any(k in u for k in ("usuario", "login", "username", "nome_usuario")) or \
           any(k in u for k in ("id_usuario", "email", "nome_classe", "senha", "password", "hash_senha")):
            return u
        if len(u) == 1:
            inner = next(iter(u.values()))
            if isinstance(inner, dict):
                return inner
        for v in u.values():
            if isinstance(v, dict):
                return v
        return u

    # objeto / dataclass
    if hasattr(u, "__dict__"):
        d = {k: v for k, v in vars(u).items() if not k.startswith("_")}
        if len(d) == 1:
            inner = next(iter(d.values()))
            if isinstance(inner, dict):
                return inner
        for v in d.values():
            if isinstance(v, dict):
                return v
        return d

    return {"raw": u}

def build_class_map(usuarios_flat):
    """Aprende mapa nome_classe -> id_classe a partir dos usuários existentes."""
    m = {}
    for u in usuarios_flat or []:
        nome = (u.get("nome_classe") or "").strip()
        cid  = (u.get("id_classe") or "").strip()
        if nome and cid and nome not in m:
            m[nome] = cid
    if not m:
        m = {"Administrador": "0001", "Gestor": "0002", "Almoxarifado": "0003", "RH": "0004"}
    return m

def gerar_id_item():
    """Gera próximo id_item numérico com 4 dígitos baseado nos itens atuais do estoque (via storage seguro)."""
    try:
        lista = listar_registros(EstoqueItem) or []
    except Exception:
        lista = []

    max_n = 0
    for e in lista:
        rec = flatten_record(e)
        s = str(rec.get("id_item", "")).strip()
        if s.isdigit():
            max_n = max(max_n, int(s))
    proximo = max_n + 1 if max_n >= 0 else 1
    return str(proximo).zfill(4)

def senha_confere(senha_digitada: str, senha_armazenada: str) -> bool:
    """Suporta hash (Werkzeug) OU texto puro (CSV)."""
    try:
        from werkzeug.security import check_password_hash
    except Exception:
        check_password_hash = None
    sd = normalize(senha_digitada)
    sa = normalize(senha_armazenada)
    if not sa:
        return False
    if check_password_hash and (sa.startswith("pbkdf2:") or "$" in sa):
        try:
            return check_password_hash(sa, sd)
        except Exception:
            pass
    return sd == sa

# ---------- Catálogo de kits/itens/tamanhos usando storage seguro ----------
def _build_kit_catalog_from_rows(rows):
    """
    Constrói o catálogo a partir de linhas (dicts/objs) do modelo Kit,
    lidas via read_csv(Kit) ou listar_registros(Kit).
    """
    kit_catalog = {}
    size_order = ["PP", "P", "M", "G", "GG", "XG", "XXG", "XXL"]

    for row in rows or []:
        r = flatten_record(row)
        id_kit  = (r.get("id_kit") or "").strip()
        nome    = (r.get("nome_kit") or "").strip()
        item_nm = (r.get("item") or "").strip()
        size    = (r.get("tamanho_camisa") or "").strip()

        if not nome:
            continue
        if nome not in kit_catalog:
            kit_catalog[nome] = {"id_kit": id_kit, "items": {}}
        else:
            if not kit_catalog[nome].get("id_kit") and id_kit:
                kit_catalog[nome]["id_kit"] = id_kit

        if item_nm:
            kit_catalog[nome]["items"].setdefault(item_nm, [])
            if size and size not in kit_catalog[nome]["items"][item_nm]:
                kit_catalog[nome]["items"][item_nm].append(size)

    # ordenar tamanhos
    for _, data in kit_catalog.items():
        for it, sizes in list(data["items"].items()):
            uniq = list(dict.fromkeys(sizes))
            uniq.sort(key=lambda s: (size_order.index(s) if s in size_order else 999, s))
            data["items"][it] = uniq

    nomes_kits_ordenados = sorted(kit_catalog.keys(), key=lambda s: s.lower())
    return kit_catalog, nomes_kits_ordenados

def load_kit_catalog_csv():
    """Nome legado mantido: agora lê via read_csv(Kit) (seguro)."""
    try:
        rows = read_csv(Kit)  # usa restore/backup por dentro
    except Exception:
        rows = []
    return _build_kit_catalog_from_rows(rows)

def carregar_kits_catalogo_csv():
    """Compat: delega para load_kit_catalog_csv()."""
    return load_kit_catalog_csv()

def carregar_usuarios_unificado():
    """
    1) Tenta via listar_registros(Usuario) (objetos).
    2) Fallback: read_csv(Usuario) (dicts).
    Retorna lista de dicts padronizados.
    """
    usuarios_norm = []

    # 1) via manager (objetos)
    try:
        lista = listar_registros(Usuario) or []
    except Exception:
        lista = []
    for u in lista:
        rec = flatten_record(u)
        usuarios_norm.append({
            "id_usuario":  normalize(rec.get("id_usuario") or rec.get("id") or rec.get("user_id")),
            "usuario":     normalize(rec.get("usuario") or rec.get("login") or rec.get("username") or rec.get("nome_usuario")),
            "senha":       rec.get("senha") or rec.get("password") or rec.get("hash_senha"),
            "nome":        normalize(rec.get("nome") or rec.get("nome_completo") or rec.get("name")),
            "email":       normalize(rec.get("email")),
            "id_classe":   normalize(rec.get("id_classe") or rec.get("classe_id")),
            "nome_classe": normalize(rec.get("nome_classe") or rec.get("perfil") or rec.get("role")),
        })
    if usuarios_norm:
        return usuarios_norm

    # 2) fallback seguro: read_csv(Usuario)
    try:
        rows = read_csv(Usuario) or []
        for r0 in rows:
            r = flatten_record(r0)
            usuarios_norm.append({
                "id_usuario":  normalize(r.get("id_usuario")),
                "usuario":     normalize(r.get("usuario")),
                "senha":       r.get("senha", ""),
                "nome":        normalize(r.get("nome")),
                "email":       normalize(r.get("email")),
                "id_classe":   normalize(r.get("id_classe")),
                "nome_classe": normalize(r.get("nome_classe")),
            })
    except Exception as e:
        print("[LOGIN DEBUG] Fallback seguro falhou:", e)

    return usuarios_norm

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario_input = normalize(request.form.get("usuario"))
        senha_input   = normalize(request.form.get("senha"))

        usuarios = carregar_usuarios_unificado()

        # DEBUG opcional
        print("\n[LOGIN DEBUG] total usuarios:", len(usuarios))
        for i, u in enumerate(usuarios[:5]):
            u_copy = dict(u)
            if "senha" in u_copy:
                u_copy["senha"] = "(oculta)"
            print(f"[LOGIN DEBUG] user[{i}]:", u_copy)

        # procura usuário (case-insensitive)
        candidato = next(
            (u for u in usuarios if u.get("usuario", "").lower() == usuario_input.lower()),
            None
        )

        if not candidato:
            flash("Usuário ou senha inválidos!", "danger")
            print(f"[LOGIN DEBUG] Usuário '{usuario_input}' não encontrado.")
            return render_template("login.html")

        if not senha_confere(senha_input, candidato.get("senha", "")):
            flash("Usuário ou senha inválidos!", "danger")
            print("[LOGIN DEBUG] Senha não confere para:", candidato.get("usuario"))
            return render_template("login.html")

        # guarda na sessão apenas dados essenciais
        session["usuario"] = {
            "id_usuario":  candidato.get("id_usuario"),
            "usuario":     candidato.get("usuario"),
            "nome":        candidato.get("nome"),
            "email":       candidato.get("email"),
            "id_classe":   candidato.get("id_classe"),
            "nome_classe": candidato.get("nome_classe"),
        }
        print("[LOGIN DEBUG] Login OK:", session["usuario"])
        return redirect(url_for("home"))

    return render_template("login.html")

# $ retornar o nome do usuario para ser usado na função log

# ---------------- HOME ----------------
@app.route("/home")
def home():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("home.html", usuario=session["usuario"])

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- CONTROLE DE ACESSO ----------------
def acesso_permitido(perfis):
    return session.get("usuario", {}).get("nome_classe") in perfis or session.get("usuario", {}).get("nome_classe") == "Administrador"

# ---------------- ALMOXARIFADO ----------------
@app.route("/almoxarifado", methods=["GET", "POST"])
def almoxarifado():
    if not acesso_permitido(["Almoxarifado"]):
        flash("Acesso negado!", "danger")
        return redirect(url_for("home"))

    try:
        kits_raw           = listar_registros(Kit)          or []
        estoque_raw        = listar_registros(EstoqueItem)  or []
        colaboradores_raw  = listar_registros(Colaborador)  or []
    except Exception:
        kits_raw, estoque_raw, colaboradores_raw = [], [], []

    kits          = [flatten_record(k) for k in kits_raw]
    estoque       = [flatten_record(e) for e in estoque_raw]
    colaboradores = [flatten_record(c) for c in colaboradores_raw]

    # Catálogo de kits (via read_csv(Kit) -> seguro)
    kit_catalog, nomes_kits_ordenados = load_kit_catalog_csv()

    # Mapa auxiliar nome_kit -> id_kit
    kits_map = {}
    for e in estoque:
        nomek = (e.get("nome_kit") or "").strip()
        idk   = (e.get("id_kit") or "").strip()
        if nomek and idk and nomek not in kits_map:
            kits_map[nomek] = idk

    if request.method == "POST":

        # ADICIONAR item de estoque
        if "adicionar_estoque" in request.form:
            novo_item = EstoqueItem(
                id_item=gerar_id_item(),  # gera automaticamente
                item=request.form["item"],
                tamanho_camisa=request.form.get("tamanho_camisa", ""),
                id_kit=request.form.get("id_kit", ""),
                nome_kit=request.form.get("nome_kit", ""),
                qntd=int(request.form["qntd"]),
            )
            adicionar_registro(novo_item, EstoqueItem)
            flash("Item adicionado com sucesso!", "success")

        # EDITAR ITEM (quantidade/tamanho)
        if "alterar_estoque" in request.form or "editar_estoque" in request.form:
            id_item = request.form["id_item"]
            novos = {}
            if request.form.get("qntd"):
                novos["qntd"] = int(request.form["qntd"])
            if request.form.get("tamanho_camisa"):
                novos["tamanho_camisa"] = request.form["tamanho_camisa"]
            atualizar_registro("id_item", id_item, novos, EstoqueItem)
            flash("Estoque atualizado com sucesso!", "success")

        # ALTERAR SITUAÇÃO COLABORADOR
        if "alterar_situacao" in request.form:
            id_colab = request.form["id_colaborador"]
            nova_situacao = request.form["situacao"]
            atualizar_registro("id_colaborador", id_colab, {"situacao": nova_situacao}, Colaborador)
            flash("Situação alterada com sucesso!", "success")

        return redirect(url_for("almoxarifado"))

    return render_template(
        "almoxarifado.html",
        kits=kits,
        estoque=estoque,
        colaboradores=colaboradores,
        kits_map=kits_map,
        kit_catalog=kit_catalog,
        nomes_kits_ordenados=nomes_kits_ordenados
    )

# ---------------- REMOVER USUÁRIO (via RH) ----------------
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

# ---------------- GESTOR ----------------
@app.route("/gestor", methods=["GET", "POST"])
def gestor():
    if not acesso_permitido(["Gestor"]):
        flash("Acesso negado!", "danger")
        return redirect(url_for("home"))
    try:
        colaboradores_raw = listar_registros(Colaborador) or []
    except Exception:
        colaboradores_raw = []

    colaboradores = [flatten_record(c) for c in colaboradores_raw]

    u = session.get("usuario", {})
    perfil    = (u.get("nome_classe") or "").strip()
    my_id     = normalize(u.get("id_usuario"))
    my_nome   = normalize(u.get("nome")).lower()
    my_email  = normalize(u.get("email")).lower()
    my_login  = normalize(u.get("usuario")).lower()

    def is_my_collab(rec: dict) -> bool:
        idg    = normalize(rec.get("id_gestor"))
        nomeg  = normalize(rec.get("nome_gestor")).lower()
        emailg = normalize(rec.get("email_gestor")).lower()
        return (
            (my_id    and idg    and idg    == my_id)    or
            (my_email and emailg and emailg == my_email) or
            (my_nome  and nomeg  and nomeg  == my_nome)  or
            (my_login and nomeg  and nomeg  == my_login)
        )

    if perfil == "Gestor":
        colaboradores = [c for c in colaboradores if is_my_collab(c)]

    if request.method == "POST":
        if "nova_situacao" in request.form:
            id_colab = request.form["id_colaborador"]
            nova_situacao = request.form["nova_situacao"]

            if perfil == "Gestor":
                all_cols = [flatten_record(x) for x in (listar_registros(Colaborador) or [])]
                alvo = next((r for r in all_cols if normalize(r.get("id_colaborador")) == normalize(id_colab)), None)
                if not alvo or not is_my_collab(alvo):
                    flash("Você não pode alterar colaboradores de outro gestor.", "danger")
                    return redirect(url_for("gestor"))

            atualizar_registro("id_colaborador", id_colab, {"situacao": nova_situacao}, Colaborador)
            flash("Situação atualizada!", "success")
            return redirect(url_for("gestor"))

        if "excluir_colaborador" in request.form:
            id_colab = request.form["id_colaborador"]

            if perfil == "Gestor":
                all_cols = [flatten_record(x) for x in (listar_registros(Colaborador) or [])]
                alvo = next((r for r in all_cols if normalize(r.get("id_colaborador")) == normalize(id_colab)), None)
                if not alvo or not is_my_collab(alvo):
                    flash("Você não pode remover colaboradores de outro gestor.", "danger")
                    return redirect(url_for("gestor"))

            remover_registro("id_colaborador", id_colab, Colaborador)
            flash("Colaborador removido!", "success")
            return redirect(url_for("gestor"))

    return render_template("gestor.html", colaboradores=colaboradores)

# ---------------- RH ----------------
@app.route("/rh", methods=["GET", "POST"])
def rh():
    if not acesso_permitido(["RH"]):
        flash("Acesso negado!", "danger")
        return redirect(url_for("home"))

    try:
        usuarios_raw       = listar_registros(Usuario)      or []
        colaboradores_raw  = listar_registros(Colaborador)  or []
        kits_raw           = listar_registros(Kit)          or []
        estoque_raw        = listar_registros(EstoqueItem)  or []
        agencias_raw       = listar_registros(Agencia)      or []
    except Exception:
        usuarios_raw, colaboradores_raw, kits_raw, estoque_raw, agencias_raw = [], [], [], [], []

    usuarios      = [flatten_record(u) for u in usuarios_raw]
    colaboradores = [flatten_record(c) for c in colaboradores_raw]
    kits          = [flatten_record(k) for k in kits_raw]
    estoque       = [flatten_record(e) for e in estoque_raw]
    agencias      = [flatten_record(a) for a in agencias_raw]

    class_map = build_class_map(usuarios)

    if request.method == "POST":
        # ---- Usuários ----
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
            flash("Usuário adicionado!", "success")

        if "editar_usuario" in request.form:
            id_usuario = request.form["id_usuario"]
            novos_dados = {
                "usuario": request.form.get("usuario", ""),
                "senha": request.form.get("senha", ""),
                "nome": request.form.get("nome", ""),
                "email": request.form.get("email", ""),
                "id_classe": request.form.get("id_classe", ""),
                "nome_classe": request.form.get("nome_classe", "")
            }
            novos_dados = {k: v for k, v in novos_dados.items() if v not in (None, "")}
            atualizar_registro("id_usuario", id_usuario, novos_dados, Usuario)
            flash("Usuário atualizado!", "success")

        if "remover_usuario" in request.form:
            id_usuario = request.form["id_usuario"]
            remover_registro("id_usuario", id_usuario, Usuario)
            flash("Usuário removido!", "success")

        # ---- Colaboradores ----
        if "adicionar_colaborador" in request.form:
            novo = Colaborador(
                id_colaborador=request.form["id_colaborador"],
                nome_colaborador=request.form["nome_colaborador"],
                email_colaborador=request.form["email_colaborador"],
                id_gestor=request.form["id_gestor"],
                nome_gestor=request.form["nome_gestor"],
                email_gestor=request.form["email_gestor"],
                id_kit=request.form["id_kit"],
                nome_kit=request.form.get("nome_kit", ""),
                data_admissao=request.form["data_admissao"],
                tamanho_camisa=request.form["tamanho_camisa"],
                id_agencia=request.form.get("id_agencia", ""),
                nome_agencia=request.form.get("nome_agencia", ""),
                local_envio=request.form.get("local_envio", ""),
                situacao=request.form.get("situacao", "Ativo")
            )
            adicionar_registro(novo, Colaborador)
            flash("Colaborador adicionado!", "success")

        if "editar_colaborador" in request.form:
            id_colab = request.form["id_colaborador"]
            novos = {
                "nome_colaborador": request.form.get("nome_colaborador", ""),
                "email_colaborador": request.form.get("email_colaborador", ""),
                "id_gestor": request.form.get("id_gestor", ""),
                "nome_gestor": request.form.get("nome_gestor", ""),
                "email_gestor": request.form.get("email_gestor", ""),
                "id_kit": request.form.get("id_kit", ""),
                "nome_kit": request.form.get("nome_kit", ""),
                "tamanho_camisa": request.form.get("tamanho_camisa", ""),
                "id_agencia": request.form.get("id_agencia", ""),
                "nome_agencia": request.form.get("nome_agencia", ""),
                "local_envio": request.form.get("local_envio", ""),
                "data_admissao": request.form.get("data_admissao", ""),
                "situacao": request.form.get("situacao", "")
            }
            novos = {k: v for k, v in novos.items() if v not in (None, "")}
            atualizar_registro("id_colaborador", id_colab, novos, Colaborador)
            flash("Colaborador atualizado!", "success")

        if "remover_colaborador" in request.form:
            id_colab = request.form["id_colaborador"]
            remover_registro("id_colaborador", id_colab, Colaborador)
            flash("Colaborador removido!", "success")

        # ---- Estoque ----
        if "adicionar_estoque" in request.form:
            novo_item = EstoqueItem(
                id_item=request.form["id_item"],  # mantém a lógica atual do form do RH
                item=request.form["item"],
                tamanho_camisa=request.form.get("tamanho_camisa", ""),
                id_kit=request.form["id_kit"],
                nome_kit=request.form.get("nome_kit", ""),
                qntd=int(request.form["qntd"]),
            )
            adicionar_registro(novo_item, EstoqueItem)
            flash("Item de estoque adicionado!", "success")

        if "editar_estoque" in request.form:
            id_item = request.form["id_item"]
            novos = {
                "tamanho_camisa": request.form.get("tamanho_camisa", ""),
                "qntd": int(request.form["qntd"]) if request.form.get("qntd") else None
            }
            novos = {k: v for k, v in novos.items() if v not in (None, "")}
            atualizar_registro("id_item", id_item, novos, EstoqueItem)
            flash("Estoque atualizado!", "success")

        if "remover_estoque" in request.form:
            id_item = request.form["id_item"]
            remover_registro("id_item", id_item, EstoqueItem)
            flash("Item de estoque removido!", "success")

        # ---- Kits ----
        if "adicionar_kit" in request.form:
            novo = Kit(
                id_kit=request.form["id_kit"],
                nome_kit=request.form["nome_kit"],
                id_item=request.form.get("id_item", ""),
                item=request.form.get("item", ""),
                tamanho_camisa=request.form.get("tamanho_camisa", "")
            )
            adicionar_registro(novo, Kit)
            flash("Kit adicionado!", "success")

        if "editar_kit" in request.form:
            id_original = request.form["id_kit"]
            novos = {
                "id_kit": request.form.get("id_kit_edit", id_original),
                "nome_kit": request.form.get("nome_kit", ""),
                "id_item": request.form.get("id_item", ""),
                "item": request.form.get("item", ""),
                "tamanho_camisa": request.form.get("tamanho_camisa", "")
            }
            novos = {k: v for k, v in novos.items() if v not in (None, "")}
            atualizar_registro("id_kit", id_original, novos, Kit)
            flash("Kit atualizado!", "success")

        if "remover_kit" in request.form:
            id_kit = request.form["id_kit"]
            remover_registro("id_kit", id_kit, Kit)
            flash("Kit removido!", "success")

        return redirect(url_for("rh"))

    return render_template(
        "rh.html",
        usuarios=usuarios,
        colaboradores=colaboradores,
        kits=kits,
        estoque=estoque,
        agencias=agencias,
        class_map=class_map,
    )

def run_app():
    app.run(debug=False, use_reloader=False, port = 5000)

# ---------------- RODA APLICATIVO ----------------
if __name__ == "__main__":
    url = "http://127.0.0.1:5000/"
    server_thread = threading.Thread(target=run_app)
    server_thread.daemon = True
    server_thread.start()
    import time
    time.sleep(1.5)
    try:
        webbrowser.open_new(url)
    except Exception as e:
        print("Não foi possível abrir o navegador automaticamente:", e)
    print("\nAplicação iniciada em:", url)
    print("Pressione 'q' e ENTER para encerrar.\n")
    while True:
        command = input()
        if command.strip().lower() == "q":
            print("Encerrando aplicação...")
            sys.exit(0)
