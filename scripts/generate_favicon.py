#!/usr/bin/env python3
"""
Generador de Favicon para Agrotech Digital
==========================================

Este script crea favicons básicos usando PIL/Pillow.
Para producción, se recomienda usar herramientas profesionales como:
- https://realfavicongenerator.net/
- https://favicon.io/

Uso:
    python generate_favicon.py

Requisitos:
    pip install Pillow
"""

import os
from PIL import Image, ImageDraw, ImageFont

# Configuración
OUTPUT_DIR = "metrica/static/images"
SIZES = {
    'favicon.ico': 32,
    'apple-touch-icon.png': 180,
    'android-chrome-192x192.png': 192,
    'android-chrome-512x512.png': 512,
}

# Colores de marca Agrotech
BRAND_GREEN = (76, 175, 80)  # #4CAF50
BRAND_ORANGE = (255, 111, 0)  # #FF6F00
DARK_BG = (26, 26, 26)  # #1a1a1a


def create_simple_favicon(size, output_path):
    """
    Crea un favicon simple con las iniciales 'AT'
    """
    # Crear imagen con fondo oscuro
    img = Image.new('RGB', (size, size), DARK_BG)
    draw = ImageDraw.Draw(img)
    
    # Dibujar círculo de fondo verde
    margin = size // 8
    circle_bbox = [margin, margin, size - margin, size - margin]
    draw.ellipse(circle_bbox, fill=BRAND_GREEN)
    
    # Intentar cargar fuente
    try:
        # Fuentes comunes en diferentes sistemas
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',  # macOS
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
            'C:\\Windows\\Fonts\\Arial.ttf',  # Windows
        ]
        
        font = None
        for path in font_paths:
            if os.path.exists(path):
                font_size = size // 2
                font = ImageFont.truetype(path, font_size)
                break
        
        if font is None:
            # Usar fuente por defecto si no se encuentra ninguna
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()
    
    # Dibujar texto "AT"
    text = "AT"
    
    # Calcular posición del texto (centrado)
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except AttributeError:
        # Fallback para versiones antiguas de Pillow
        text_width, text_height = draw.textsize(text, font=font)
    
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2 - size // 20  # Ajuste visual
    
    # Dibujar texto en blanco
    draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
    
    # Guardar
    if output_path.endswith('.ico'):
        img.save(output_path, format='ICO', sizes=[(32, 32)])
    else:
        img.save(output_path, format='PNG', optimize=True)
    
    print(f"✅ Creado: {output_path} ({size}x{size})")


def create_og_image():
    """
    Crea imagen para Open Graph (redes sociales)
    Tamaño: 1200x630px
    """
    width, height = 1200, 630
    img = Image.new('RGB', (width, height), DARK_BG)
    draw = ImageDraw.Draw(img)
    
    # Dibujar gradiente simple (dos rectángulos superpuestos)
    # Parte superior con verde
    draw.rectangle([0, 0, width, height // 2], fill=BRAND_GREEN)
    
    # Parte inferior con transición
    for y in range(height // 2, height):
        alpha = (y - height // 2) / (height // 2)
        color = tuple(int(BRAND_GREEN[i] * (1 - alpha) + DARK_BG[i] * alpha) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color)
    
    # Intentar cargar fuente grande
    try:
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
            'C:\\Windows\\Fonts\\Arial.ttf',
        ]
        
        title_font = None
        subtitle_font = None
        
        for path in font_paths:
            if os.path.exists(path):
                title_font = ImageFont.truetype(path, 120)
                subtitle_font = ImageFont.truetype(path, 48)
                break
        
        if title_font is None:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
    except Exception:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
    
    # Texto principal
    title = "AGROTECH DIGITAL"
    subtitle = "Agricultura de Precisión con Tecnología Satelital"
    
    # Calcular posiciones (centrado vertical)
    try:
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        subtitle_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        title_width = title_bbox[2] - title_bbox[0]
        subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
    except AttributeError:
        title_width, _ = draw.textsize(title, font=title_font)
        subtitle_width, _ = draw.textsize(subtitle, font=subtitle_font)
    
    title_x = (width - title_width) // 2
    title_y = height // 3
    subtitle_x = (width - subtitle_width) // 2
    subtitle_y = title_y + 150
    
    # Dibujar textos
    draw.text((title_x, title_y), title, fill=(255, 255, 255), font=title_font)
    draw.text((subtitle_x, subtitle_y), subtitle, fill=BRAND_ORANGE, font=subtitle_font)
    
    # Guardar
    output_path = os.path.join(OUTPUT_DIR, 'og-image.jpg')
    img.save(output_path, format='JPEG', quality=90, optimize=True)
    print(f"✅ Creado: {output_path} (1200x630)")


def main():
    """
    Función principal
    """
    print("🌱 Generador de Favicons - Agrotech Digital\n")
    
    # Crear directorio si no existe
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"📁 Directorio de salida: {OUTPUT_DIR}\n")
    
    # Generar favicons
    print("Generando favicons...")
    for filename, size in SIZES.items():
        output_path = os.path.join(OUTPUT_DIR, filename)
        create_simple_favicon(size, output_path)
    
    # Generar imagen Open Graph
    print("\nGenerando imagen Open Graph...")
    create_og_image()
    
    print("\n✨ ¡Proceso completado!")
    print("\n📝 Siguiente paso:")
    print("   1. Revisa las imágenes generadas en:", OUTPUT_DIR)
    print("   2. Para mejor calidad, usa https://realfavicongenerator.net/")
    print("   3. Actualiza las referencias en index.html")
    print("\n🎨 Personalización:")
    print("   - Edita los colores BRAND_GREEN, BRAND_ORANGE en este script")
    print("   - Cambia el texto 'AT' por tu logo/iniciales")
    print("   - Ajusta los tamaños en SIZES dictionary")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Asegúrate de tener Pillow instalado:")
        print("   pip install Pillow")
