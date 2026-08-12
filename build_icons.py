"""
Gera os ícones PWA (icon-192.png, icon-512.png) a partir de formas simples
desenhadas com Pillow — logo abstrato de "rede neural" sobre fundo roxo,
seguindo a identidade visual da Segunda Mente (--accent: #6c5ce7).

Uso: python3 build_icons.py
"""
from PIL import Image, ImageDraw

BG = (108, 92, 231, 255)       # --accent
BG_DARK = (10, 10, 15, 255)    # --bg-primary
NODE = (255, 255, 255, 255)
LINE = (232, 232, 240, 200)    # --text-primary translúcido


def rounded_square(size: int, radius_ratio: float = 0.22) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    radius = int(size * radius_ratio)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BG)
    return img, draw


def draw_brain_nodes(draw: ImageDraw.ImageDraw, size: int) -> None:
    """Desenha um pequeno grafo de nós conectados (representando 'rede neural')."""
    c = size / 2
    r_big = size * 0.09
    r_small = size * 0.055

    # Posições relativas ao centro, formando um padrão tipo "cérebro/rede"
    points = [
        (c, c - size * 0.22, r_big),          # topo
        (c - size * 0.20, c - size * 0.02, r_small),
        (c + size * 0.20, c - size * 0.02, r_small),
        (c - size * 0.13, c + size * 0.20, r_small),
        (c + size * 0.13, c + size * 0.20, r_small),
        (c, c + size * 0.02, r_big),           # centro
    ]

    edges = [(0, 1), (0, 2), (1, 5), (2, 5), (5, 3), (5, 4), (1, 3), (2, 4)]

    line_width = max(2, int(size * 0.012))
    for a, b in edges:
        ax, ay, _ = points[a]
        bx, by, _ = points[b]
        draw.line([ax, ay, bx, by], fill=LINE, width=line_width)

    for x, y, r in points:
        draw.ellipse([x - r, y - r, x + r, y + r], fill=NODE)


def build_icon(size: int, path: str) -> None:
    img, draw = rounded_square(size)
    draw_brain_nodes(draw, size)
    img.save(path, "PNG")
    print(f"Gerado {path} ({size}x{size})")


if __name__ == "__main__":
    build_icon(192, "public/icons/icon-192.png")
    build_icon(512, "public/icons/icon-512.png")
