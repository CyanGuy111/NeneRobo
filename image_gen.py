from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

def gradient(width, height, color1, color2, direction='horizontal'):
    base = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(base)

    r1, g1, b1, a1 = color1
    r2, g2, b2, a2, = color2

    if direction == 'horizontal':
        for x in range(width):
            ratio = x / max(width - 1, 1)
            
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            a = int(a1 + (a2 - a1) * ratio)
            
            draw.line([(x, 0), (x, height)], fill=(r, g, b, a))

    if direction == 'vertical':
        for y in range(height):
            ratio = y / max(height - 1, 1)

            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            a = int(a1 + (a2 - a1) * ratio)
            
            draw.line([(0, y), (width, y)], fill=(r, g, b, a))

    return base

def draw_text_with_special_symbols(draw, x, y, text, main_font, secondary_font, fill = "black", scale = 1):
    cur_y = y
    line_spacing = main_font.size + (4 * scale)

    for line in text.split('\n'):
        cur_x = x
        for char in line:
            font = secondary_font if ord(char) > 0x024F else main_font

            draw.text((cur_x, cur_y), char, font=font, fill=fill)
            cur_x += font.getlength(char)
        cur_y += line_spacing

def generate_b30_image(ranking_score, top_30_songs, type = None, output_filename="my_b30.png"):
    SCALE = 2

    WIDTH = 1000 * SCALE
    HEIGHT = 1500 * SCALE
    HEADER_HEIGHT = 32 * SCALE
    GUTTER_WIDTH = 30 * SCALE
    GUTTER_HEIGHT = 35 * SCALE
    
    CARD_WIDTH = int((WIDTH - (GUTTER_WIDTH * 4)) / 3)
    CARD_HEIGHT = int((HEIGHT - HEADER_HEIGHT - (GUTTER_HEIGHT * 11)) / 10)
    JACKET_PADDING = 15 * SCALE
    JACKET_SIZE = CARD_HEIGHT - (JACKET_PADDING * 2)

    COLOR_AP_START = (255, 142, 255, 255)
    COLOR_AP_END = (0, 227, 199, 255)

    try:
        image = Image.open("assets/background/kitty.png").convert("RGBA")
        image = image.resize((WIDTH, HEIGHT))
    except FileNotFoundError:
        image = Image.new("RGBA", (WIDTH, HEIGHT), (20, 25, 40, 255))
    draw = ImageDraw.Draw(image)

    draw.rectangle([0, 0, WIDTH, HEADER_HEIGHT], fill=(180, 204, 250, 255))
    
    try:
        font_title = ImageFont.truetype("assets/fonts/itim.ttf", 24 * SCALE)
        font_song = ImageFont.truetype("assets/fonts/itim.ttf", 16 * SCALE)
        font_song_fallback = ImageFont.truetype("assets/fonts/NotoSansJP-Bold.ttf", 16 * SCALE)
        font_badge = ImageFont.truetype("assets/fonts/itim.ttf", 14 * SCALE)
        font_diamond = ImageFont.truetype("assets/fonts/itim.ttf", 12 * SCALE)
    except IOError:
        font_title = ImageFont.load_default()
        font_song = ImageFont.load_default()
        font_song_fallback = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_diamond = ImageFont.load_default()

    if type == 'AP':
        draw.text((10 * SCALE, 4 * SCALE), "Your best 30 APs", fill="black", font=font_title)
    else:
        draw.text((10 * SCALE, 4 * SCALE), "Your best 30 charts", fill="black", font=font_title)
    
    ranking_text = f"Ranking: {ranking_score:.2f}"
    
    text_bbox = draw.textbbox((0, 0), ranking_text, font=font_title)
    text_width = text_bbox[2] - text_bbox[0]
    draw.text((WIDTH - text_width - (10 * SCALE), 4 * SCALE), ranking_text, fill="black", font=font_title)

    for idx, song in enumerate(top_30_songs):
        if idx >= 30:
            break
            
        grid_x = idx % 3
        grid_y = idx // 3
        
        x_pos = grid_x * CARD_WIDTH + (GUTTER_WIDTH * (grid_x + 1))
        y_pos = HEADER_HEIGHT + (grid_y * CARD_HEIGHT) + (GUTTER_HEIGHT * (grid_y + 1))

        is_ap = song.get('clear_type', 'FC').upper() == 'AP'
        border_width = 4 * SCALE

        draw.rounded_rectangle(
            [x_pos, y_pos, x_pos + CARD_WIDTH - 1, y_pos + CARD_HEIGHT - 1],
            radius=4 * SCALE,
            fill="white"
        )
        
        if is_ap:
            card_gradient = gradient(CARD_WIDTH, CARD_HEIGHT, COLOR_AP_START, COLOR_AP_END, 'vertical')

            border_mask = Image.new('L', (CARD_WIDTH, CARD_HEIGHT), 0)
            mask_draw = ImageDraw.Draw(border_mask)
            mask_draw.rounded_rectangle(
                [0, 0, CARD_WIDTH - 1, CARD_HEIGHT - 1], 
                radius=4 * SCALE,
                outline=255,
                width=border_width
            )
            
            image.paste(card_gradient, (x_pos, y_pos), border_mask)

        else:
            draw.rounded_rectangle(
                [x_pos, y_pos, x_pos + CARD_WIDTH - 1, y_pos + CARD_HEIGHT - 1],
                radius=4 * SCALE,
                outline=(254, 131, 254, 255),
                width=border_width
            )

        song_id = song.get('id', 0)
        jacket_path = f"assets/jackets/jacket_s_{int(song_id):03}.webp"
        
        if os.path.exists(jacket_path):
            try:
                jacket = Image.open(jacket_path).convert("RGBA")
                jacket = jacket.resize((JACKET_SIZE, JACKET_SIZE))
                image.paste(jacket, (x_pos + JACKET_PADDING, y_pos + JACKET_PADDING), jacket)
            except Exception as e:
                print(f"Could not load jacket for ID {song_id}: {e}")
        else:
            draw.rectangle(
                [x_pos + JACKET_PADDING, y_pos + JACKET_PADDING, 
                 x_pos + JACKET_PADDING + JACKET_SIZE, y_pos + JACKET_PADDING + JACKET_SIZE],
                fill="gray"
            )

        text_x = x_pos + (2 * JACKET_PADDING) + JACKET_SIZE
        text_y = y_pos + JACKET_PADDING
        song_name = song.get('name')
        
        wrapped_name = "\n".join(textwrap.wrap(song_name, width=18))
        
        draw_text_with_special_symbols(draw, text_x, text_y, wrapped_name, font_song, font_song_fallback, scale=SCALE)

        difficulty = song.get('difficulty', 'Master')
        if difficulty == 'Expert':
            badge_color = (255, 69, 122, 255)
        elif difficulty == 'Master':
            badge_color = (120, 28, 148, 255)
        else:
            badge_color = None

        badge_width = 40 * SCALE
        badge_height = 22 * SCALE
        badge_x = x_pos - (badge_width // 2)
        badge_y = y_pos - (badge_height // 2)

        if badge_color is not None:
            draw.rounded_rectangle(
                [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
                radius=10 * SCALE,
                fill=badge_color
            )
        else:
            #Append gradient
            badge_gradient = gradient(badge_width, badge_height, (120, 87, 255, 255), (252, 172, 247, 255))
            
            badge_mask = Image.new("L", (badge_width, badge_height), 0)
            ImageDraw.Draw(badge_mask).rounded_rectangle(
                [0, 0, badge_width - 1, badge_height - 1],
                radius=10 * SCALE,
                fill=255
            )
            
            image.paste(badge_gradient, (int(badge_x), int(badge_y)), badge_mask)
            
            draw.rounded_rectangle(
                [badge_x, badge_y, badge_x + badge_width - 1, badge_y + badge_height - 1],
                radius=10 * SCALE,
                outline="white",
                width=2 * SCALE
            )

        constant_val = f"{song.get('constant', 0.0):.1f}"
        b_bbox = draw.textbbox((0, 0), constant_val, font=font_badge)
        b_w = b_bbox[2] - b_bbox[0]
        b_h = b_bbox[3] - b_bbox[1]
        draw.text(
            (badge_x + (badge_width - b_w) / 2, badge_y + (badge_height - b_h) / 2 - (3 * SCALE)), 
            constant_val, 
            fill="white", 
            font=font_badge
        )
        
        # The Diamond Indicator
        d_width = 36 * SCALE
        d_height = 36 * SCALE
        
        d_x = x_pos + CARD_WIDTH - (d_width // 2)
        d_y = y_pos + CARD_HEIGHT - (d_height // 2)

        if difficulty == 'Append':
            diamond_points = [
                (d_x, d_y),
                (d_x + d_width // 2, d_y + d_height // 7),
                (d_x + d_width, d_y),
                (d_x + d_width - d_width // 7, d_y + d_height // 2),
                (d_x + d_width, d_y + d_height),
                (d_x + d_width // 2, d_y + d_height - d_height // 7),
                (d_x, d_y + d_height),
                (d_x + d_width // 7, d_y + d_height // 2)
            ]
        else:
            diamond_points = [
                (d_x + d_width // 2, d_y),
                (d_x + d_width, d_y + d_height // 2),
                (d_x + d_width // 2, d_y + d_height),
                (d_x, d_y + d_height // 2)
            ]
        if is_ap:
            diamond_gradient = gradient(d_width, d_height, COLOR_AP_START, COLOR_AP_END, 'vertical')
            
            diamond_mask = Image.new("L", (d_width, d_height), 0)
            mask_draw = ImageDraw.Draw(diamond_mask)
            
            rel_points = [(p[0] - d_x, p[1] - d_y) for p in diamond_points]
            mask_draw.polygon(rel_points, fill=255)
            
            image.paste(diamond_gradient, (d_x, d_y), diamond_mask)
            
            draw.polygon(diamond_points, outline="black", width=2 * SCALE)
            
        else:
            draw.polygon(diamond_points, fill=(254, 131, 254, 255), outline="black", width=2 * SCALE)

        clear_text = "AP" if is_ap else "FC"
        d_bbox = draw.textbbox((0, 0), clear_text, font=font_diamond)
        d_w = d_bbox[2] - d_bbox[0]
        d_h = d_bbox[3] - d_bbox[1]
        
        draw.text(
            (d_x + (d_width - d_w) / 2, d_y + (d_height - d_h) / 2 - (3 * SCALE)),
            clear_text,
            fill="white",
            font=font_diamond
        )

    final_image = image.resize((1000, 1500), Image.Resampling.LANCZOS)
    final_image.save(output_filename)
    print(f"Successfully generated {output_filename}!")