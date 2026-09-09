#!/usr/bin/env python3
"""
Gera o SVG do README de perfil do GitHub (dark_mode.svg e light_mode.svg)
no estilo "neofetch de terminal": foto convertida em ASCII art à esquerda,
specs coloridas e estatisticas reais do GitHub à direita.

Inspirado na abordagem de github.com/Andrew6rant/Andrew6rant (today.py):
um script gera um SVG estatico a partir de dados da API do GitHub e de
uma foto de perfil, e uma GitHub Action roda esse script periodicamente
e faz commit do resultado.

Uso:
    python generate_svg.py

Variaveis de ambiente opcionais:
    USER_NAME     -> usuario do GitHub (default: andreluizpedroso)
    ACCESS_TOKEN  -> token para autenticar na API do GitHub (maior rate limit).
                     Em GitHub Actions, o GITHUB_TOKEN padrao já serve.
"""
import io
import os
import sys

import requests
from PIL import Image, ImageOps, ImageFilter

# --------------------------------------------------------------------------
# Configuracao
# --------------------------------------------------------------------------

USER_NAME = os.environ.get("USER_NAME", "andreluizpedroso")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")

API_ROOT = "https://api.github.com"
HEADERS = {"Accept": "application/vnd.github+json"}
if ACCESS_TOKEN:
    HEADERS["Authorization"] = f"Bearer {ACCESS_TOKEN}"

ART_COLS = 44
ART_ASPECT_CORRECTION = 0.58  # compensa a proporcao ~2:1 (altura:largura) do caractere monoespacado
RAMP = " .:-=+*#%@"  # do mais claro/esparso ao mais escuro/denso

FONT_SIZE = 14
CHAR_W = 8.4          # largura aproximada de um caractere monoespacado a FONT_SIZE=14 (Consolas-like)
LINE_H = 15            # espacamento vertical entre linhas -> mantem a proporcao usada na ASCII art
ART_X = 15
GUTTER = 20
SPECS_X = ART_X + ART_COLS * CHAR_W + GUTTER
MARGIN_RIGHT = 20

# Paleta pedida: labels em amarelo/dourado, valores em azul claro, separadores em cinza
DARK = {
    "bg": "#0d1117",
    "text": "#c9d1d9",
    "key": "#e3b341",
    "value": "#79c0ff",
    "cc": "#6e7681",
    "border": "#30363d",
}
LIGHT = {
    "bg": "#ffffff",
    "text": "#24292f",
    "key": "#9a6700",
    "value": "#0969da",
    "cc": "#6e7681",
    "border": "#d0d7de",
}


# --------------------------------------------------------------------------
# Dados da API do GitHub
# --------------------------------------------------------------------------

def api_get(url, params=None):
    r = requests.get(url, headers=HEADERS, params=params, timeout=30)
    r.raise_for_status()
    return r


def get_user(username):
    return api_get(f"{API_ROOT}/users/{username}").json()


def get_all_repos(username):
    repos, page = [], 1
    while True:
        r = api_get(f"{API_ROOT}/users/{username}/repos", params={"per_page": 100, "page": page})
        chunk = r.json()
        if not chunk:
            break
        repos.extend(chunk)
        if len(chunk) < 100:
            break
        page += 1
    return repos


def get_commit_count(username, repo):
    """Numero de commits do usuario num repositorio, via truque do header Link (per_page=1)."""
    try:
        r = api_get(
            f"{API_ROOT}/repos/{username}/{repo}/commits",
            params={"author": username, "per_page": 1},
        )
    except requests.HTTPError:
        return 0
    link = r.headers.get("Link")
    if link:
        for part in link.split(","):
            if 'rel="last"' in part:
                try:
                    return int(part.split("page=")[-1].split(">")[0])
                except ValueError:
                    pass
    try:
        return len(r.json())
    except ValueError:
        return 0


def collect_github_stats(username):
    user = get_user(username)
    repos = get_all_repos(username)
    total_stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_forks = sum(r.get("forks_count", 0) for r in repos)
    total_commits = sum(get_commit_count(username, r["name"]) for r in repos if not r.get("fork"))
    return {
        "repos": user.get("public_repos", len(repos)),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "stars": total_stars,
        "forks": total_forks,
        "commits": total_commits,
        "avatar_url": user.get("avatar_url"),
    }


# --------------------------------------------------------------------------
# Foto -> ASCII art
# --------------------------------------------------------------------------

def fetch_avatar(username):
    r = requests.get(f"https://github.com/{username}.png", params={"size": 460}, timeout=30)
    r.raise_for_status()
    return Image.open(io.BytesIO(r.content)).convert("RGB")


def image_to_ascii(img, cols=ART_COLS, aspect=ART_ASPECT_CORRECTION):
    gray = img.convert("L")
    gray = gray.filter(ImageFilter.GaussianBlur(radius=max(1, img.width // 130)))
    gray = ImageOps.autocontrast(gray, cutoff=1)

    rows = round(gray.height / gray.width * cols * aspect)
    small = gray.resize((cols, rows), Image.LANCZOS)
    small = ImageOps.autocontrast(small, cutoff=0)
    pixels = small.load()

    n = len(RAMP)
    lines = []
    for y in range(rows):
        line = []
        for x in range(cols):
            lum = pixels[x, y]
            idx = n - 1 - min(n - 1, int(lum / 256 * n))
            line.append(RAMP[idx])
        lines.append("".join(line))
    return lines


# --------------------------------------------------------------------------
# Specs (conteudo estatico + campos dinamicos com id, no estilo do today.py)
# --------------------------------------------------------------------------

def build_specs(stats):
    sep = "-" * 40
    return [
        ("andreluizpedroso@github", None, None),
        (sep, None, None),
        ("OS", "Machine Learning Engineer / Senior Data Engineer", None),
        ("Host", "Consultoria Independente em Dados e IA (desde 2013)", None),
        ("Kernel", "Python 3.x | SQL | R", None),
        ("Uptime", "10+ anos de experiencia em dados", None),
        ("Shell", "FastAPI + Docker + Kubernetes", None),
        ("DE", "dbt | Airflow | Spark | Data Lakehouse", None),
        ("MLOps", "MLflow | CI/CD | Evidently AI | Feast", None),
        ("Cloud", "GCP (BigQuery, Vertex AI) | AWS (SageMaker) | Azure ML | Databricks", None),
        ("ML/DL", "Scikit-learn | TensorFlow | PyTorch | XGBoost | LightGBM", None),
        ("GenAI", "LLMs | Prompt Engineering | NLP | MCP (Model Context Protocol)", None),
        ("BI", "Power BI | Tableau | Looker Studio | Metabase", None),
        ("Languages", "Portugues (nativo) | Ingles (C2 Fluente)", None),
        ("Locale", "Barueri, SP, Brasil", None),
        (sep, None, None),
        ("Contact", None, None),
        ("Email", "andreluizp87@gmail.com", None),
        ("LinkedIn", "linkedin.com/in/andreluizpedroso", None),
        ("Portfolio", "portifolio-andre-pedroso.vercel.app", None),
        (sep, None, None),
        ("Formacao", "Pos-Tech Machine Learning Engineering - FIAP (2025)", None),
        (None, "Pos-Tech Data Analytics - FIAP (2024)", None),
        (None, "Bacharel em Sistemas de Informacao - UNINOVE (2022)", None),
        (sep, None, None),
        ("Experiencia", "NIO Tecnologia - Senior Data Analyst (jul/2025 - jan/2026)", None),
        (None, "Kumon Brasil - Senior Data Analyst (nov/2023 - abr/2025)", None),
        (None, "Consultoria Independente - Especialista em Dados e IA (desde 2013)", None),
        (sep, None, None),
        ("GitHub Stats", None, None),
        ("Repos", f"{stats['repos']}", "repo_data"),
        (None, f"Stars: {stats['stars']} | Forks: {stats['forks']}", "star_data"),
        ("Commits", f"{stats['commits']}", "commit_data"),
        (None, f"Followers: {stats['followers']} | Following: {stats['following']}", "follower_data"),
    ]


# --------------------------------------------------------------------------
# Montagem do SVG
# --------------------------------------------------------------------------

def esc(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _line_char_len(label, value):
    if value is None:
        return len(label or "")
    prefix = f"{label}: " if label else ""
    return len(prefix) + len(value)


def render_svg(art_lines, specs, palette):
    n_lines = max(len(art_lines), len(specs))
    max_chars = max(_line_char_len(label, value) for label, value, _ in specs)
    width = round(SPECS_X + max_chars * CHAR_W) + MARGIN_RIGHT
    # linha do cabecalho (usuario@github + separador) soma +1 acima do restante
    height = 30 + n_lines * LINE_H + 20

    art_tspans = []
    for i, line in enumerate(art_lines):
        y = 30 + i * LINE_H
        art_tspans.append(f'<tspan x="{ART_X}" y="{y}">{esc(line)}</tspan>')

    spec_tspans = []
    for i, (label, value, elem_id) in enumerate(specs):
        y = 30 + i * LINE_H
        if label is not None and label.startswith("-"):
            # linha separadora
            spec_tspans.append(
                f'<tspan x="{SPECS_X}" y="{y}" class="cc">{esc(label)}</tspan>'
            )
        elif value is None and label is not None:
            # cabecalho de secao (ex: "Contact", "GitHub Stats", "andreluizpedroso@github")
            spec_tspans.append(f'<tspan x="{SPECS_X}" y="{y}">{esc(label)}</tspan>')
        else:
            id_attr = f' id="{elem_id}"' if elem_id else ""
            if label is not None:
                spec_tspans.append(
                    f'<tspan x="{SPECS_X}" y="{y}" class="key">{esc(label)}</tspan>'
                    f'<tspan class="cc">: </tspan>'
                    f'<tspan class="value"{id_attr}>{esc(value)}</tspan>'
                )
            else:
                # continuacao (sem label), indentada
                spec_tspans.append(
                    f'<tspan x="{SPECS_X}" y="{y}" class="value"{id_attr}>{esc(value)}</tspan>'
                )

    svg = f'''<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns="http://www.w3.org/2000/svg" font-family="Consolas,'SFMono-Regular','Courier New',monospace" width="{width}px" height="{height}px" font-size="{FONT_SIZE}px">
<style>
.key {{fill: {palette["key"]};}}
.value {{fill: {palette["value"]};}}
.cc {{fill: {palette["cc"]};}}
text, tspan {{white-space: pre;}}
</style>
<rect width="{width}px" height="{height}px" fill="{palette["bg"]}" rx="12"/>
<text x="{ART_X}" y="30" fill="{palette["text"]}">
{chr(10).join(art_tspans)}
</text>
<text x="{SPECS_X}" y="30" fill="{palette["text"]}">
{chr(10).join(spec_tspans)}
</text>
</svg>
'''
    return svg


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    print(f"Gerando SVG de perfil para {USER_NAME}...")

    try:
        stats = collect_github_stats(USER_NAME)
        print("Estatisticas do GitHub obtidas:", stats)
    except Exception as exc:  # pragma: no cover - fallback defensivo
        print(f"Aviso: falha ao buscar estatisticas do GitHub ({exc}). Usando valores em cache.", file=sys.stderr)
        stats = {
            "repos": 18, "followers": 7, "following": 13,
            "stars": 0, "forks": 0, "commits": 232,
            "avatar_url": f"https://github.com/{USER_NAME}.png",
        }

    try:
        avatar = fetch_avatar(USER_NAME)
        art_lines = image_to_ascii(avatar)
    except Exception as exc:  # pragma: no cover - fallback defensivo
        print(f"Aviso: falha ao converter avatar em ASCII ({exc}). Mantendo arte em cache.", file=sys.stderr)
        with open("ascii_cache.txt") as f:
            art_lines = f.read().splitlines()
    else:
        with open("ascii_cache.txt", "w") as f:
            f.write("\n".join(art_lines))

    specs = build_specs(stats)

    dark_svg = render_svg(art_lines, specs, DARK)
    light_svg = render_svg(art_lines, specs, LIGHT)

    with open("dark_mode.svg", "w", encoding="utf-8") as f:
        f.write(dark_svg)
    with open("light_mode.svg", "w", encoding="utf-8") as f:
        f.write(light_svg)

    print("dark_mode.svg e light_mode.svg gerados com sucesso.")


if __name__ == "__main__":
    main()
