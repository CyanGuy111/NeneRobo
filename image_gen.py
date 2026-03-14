from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

def generate_b30_image(ranking_score, top_30_songs, type = None, output_filename="my_b30.png"):
    WIDTH = 1000
    HEIGHT = 1500
    HEADER_HEIGHT = 32
    GUTTER_WIDTH = 30
    GUTTER_HEIGHT = 35
    
    CARD_WIDTH = int((WIDTH - (GUTTER_WIDTH * 4)) / 3)
    CARD_HEIGHT = int((HEIGHT - HEADER_HEIGHT - (GUTTER_HEIGHT * 11)) / 10)
    JACKET_PADDING = 15
    JACKET_SIZE = CARD_HEIGHT - (JACKET_PADDING * 2)

    try:
        image = Image.open("assets/background/kitty.png").convert("RGBA")
        image = image.resize((WIDTH, HEIGHT))
    except FileNotFoundError:
        image = Image.new("RGBA", (WIDTH, HEIGHT), (20, 25, 40, 255))
    draw = ImageDraw.Draw(image)

    draw.rectangle([0, 0, WIDTH, HEADER_HEIGHT], fill=(180, 204, 250, 255))
    
    try:
        font_title = ImageFont.truetype("assets/fonts/itim.ttf", 24)
        font_song = ImageFont.truetype("assets/fonts/itim.ttf", 16)
        font_badge = ImageFont.truetype("assets/fonts/itim.ttf", 14)
        font_diamond = ImageFont.truetype("assets/fonts/itim.ttf", 12)
    except IOError:
        font_title = ImageFont.load_default()
        font_song = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_diamond = ImageFont.load_default()

    if type == 'AP':
        draw.text((10, 4), "Your best 30 APs", fill="black", font=font_title)
    else:
        draw.text((10, 4), "Your best 30 charts", fill="black", font=font_title)
    
    ranking_text = f"Ranking: {ranking_score:.2f}"
    
    text_bbox = draw.textbbox((0, 0), ranking_text, font=font_title)
    text_width = text_bbox[2] - text_bbox[0]
    draw.text((WIDTH - text_width - 10, 4), ranking_text, fill="black", font=font_title)

    for idx, song in enumerate(top_30_songs):
        if idx >= 30:
            break
            
        grid_x = idx % 3
        grid_y = idx // 3
        
        x_pos = grid_x * CARD_WIDTH + (GUTTER_WIDTH * (grid_x + 1))
        y_pos = HEADER_HEIGHT + (grid_y * CARD_HEIGHT) + (GUTTER_HEIGHT * (grid_y + 1))

        is_ap = song.get('clear_type', 'FC').upper() == 'AP'
        border_color = (0, 227, 199, 255) if is_ap else (254, 131, 254, 255)
        border_width = 4 if is_ap else 2

        draw.rounded_rectangle(
            [x_pos, y_pos, x_pos + CARD_WIDTH, y_pos + CARD_HEIGHT],
            radius=4,
            fill="white",
            outline=border_color,
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
            
        draw.text((text_x, text_y), wrapped_name, fill="black", font=font_song)

        difficulty = song.get('difficulty', 'Master')
        if difficulty == 'Expert':
            badge_color = (255, 69, 122, 255)
        elif difficulty == 'Append':
            badge_color = (120, 87, 255, 255)
        else:
            badge_color = (120, 28, 148, 255)

        badge_width = 40
        badge_height = 22
        badge_x = x_pos - (badge_width // 2)
        badge_y = y_pos - (badge_height // 2)

        draw.rounded_rectangle(
            [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
            radius=10,
            fill=badge_color
        )

        constant_val = f"{song.get('constant', 0.0):.1f}"
        b_bbox = draw.textbbox((0, 0), constant_val, font=font_badge)
        b_w = b_bbox[2] - b_bbox[0]
        b_h = b_bbox[3] - b_bbox[1]
        draw.text(
            (badge_x + (badge_width - b_w) / 2, badge_y + (badge_height - b_h) / 2 - 2), 
            constant_val, 
            fill="white", 
            font=font_badge
        )
        
        # The Diamond Indicator
        d_width = 36
        d_height = 36
        
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

        draw.polygon(diamond_points, fill=border_color, outline="black", width=2)

        clear_text = "AP" if is_ap else "FC"
        d_bbox = draw.textbbox((0, 0), clear_text, font=font_diamond)
        d_w = d_bbox[2] - d_bbox[0]
        d_h = d_bbox[3] - d_bbox[1]
        
        draw.text(
            (d_x + (d_width - d_w) / 2, d_y + (d_height - d_h) / 2 - 2),
            clear_text,
            fill="white",
            font=font_diamond
        )

    image.save(output_filename)
    print(f"Successfully generated {output_filename}!")