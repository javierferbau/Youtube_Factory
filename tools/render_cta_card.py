#!/usr/bin/env python3
import sys
import os
import argparse
import re
from PIL import Image, ImageDraw, ImageFont

def render_cta_card(text, out_path, font_size=110):
    emoji_pattern = re.compile(
        '('
        '[\U0001F1E0-\U0001F1FF]'  # flags
        '|[\U0001F300-\U0001F5FF]' # symbols & pictographs
        '|[\U0001F600-\U0001F64F]' # emoticons
        '|[\U0001F680-\U0001F6FF]' # transport & map
        '|[\U0001F700-\U0001F77F]' # alchemical symbols
        '|[\U0001F780-\U0001F7FF]' # Geometric Shapes Extended
        '|[\U0001F800-\U0001F8FF]' # Supplemental Arrows-C
        '|[\U0001F900-\U0001F9FF]' # Supplemental Symbols and Pictographs
        '|[\U0001FA00-\U0001FA6F]' # Chess Symbols
        '|[\U0001FA70-\U0001FAFF]' # Symbols and Pictographs Extended-A
        '|[\u2600-\u26FF]'          # misc symbols (heart, etc.)
        '|[\u2700-\u27BF]'          # dingbats
        ')+'
    )
    
    # Fonts
    font_text_path = '/usr/share/fonts/TTF/DejaVuSans-Bold.ttf'
    font_emoji_path = '/usr/share/fonts/noto/NotoColorEmoji.ttf'
    
    font_text = ImageFont.truetype(font_text_path, font_size)
    font_emoji = ImageFont.truetype(font_emoji_path, 109) # NotoColorEmoji works natively at 109
    
    match = emoji_pattern.search(text)
    if match:
        part1 = text[:match.start()].strip()
        emoji = match.group(0).strip()
        part2 = text[match.end():].strip()
    else:
        part1 = text
        emoji = ''
        part2 = ''
        
    dummy = Image.new('RGBA', (1, 1))
    draw_dummy = ImageDraw.Draw(dummy)
    
    b1 = draw_dummy.textbbox((0, 0), part1 + ' ', font=font_text) if part1 else (0, 0, 0, 0)
    w1 = b1[2] - b1[0] if part1 else 0
    
    w_emoji = 135 if emoji else 0
    
    b2 = draw_dummy.textbbox((0, 0), ' ' + part2, font=font_text) if part2 else (0, 0, 0, 0)
    w2 = b2[2] - b2[0] if part2 else 0
    
    total_w = w1 + w_emoji + w2
    card_w = max(total_w + 100, 800)
    card_h = 240
    
    img = Image.new('RGBA', (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    start_x = (card_w - total_w) // 2
    cur_x = start_x
    base_y = 50
    
    if part1:
        draw.text((cur_x, base_y), part1 + ' ', font=font_text, fill=(255, 255, 255, 255), stroke_width=8, stroke_fill=(0, 0, 0, 255))
        cur_x += w1
    if emoji:
        draw.text((cur_x, base_y - 15), emoji, font=font_emoji, embedded_color=True)
        cur_x += w_emoji
    if part2:
        draw.text((cur_x, base_y), ' ' + part2, font=font_text, fill=(255, 255, 255, 255), stroke_width=8, stroke_fill=(0, 0, 0, 255))
        
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    img.save(out_path)
    print(f"CTA card saved: {out_path} ({card_w}x{card_h})")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--text', required=True, help='CTA text e.g. "Comment 🧀 if you agree"')
    parser.add_argument('--out', required=True, help='Output PNG path')
    parser.add_argument('--fontsize', type=int, default=110, help='Font size')
    args = parser.parse_args()
    render_cta_card(args.text, args.out, args.fontsize)
