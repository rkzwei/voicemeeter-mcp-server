"""Create a 400x400 PNG logo for the Voicemeeter MCP Server."""

from PIL import Image, ImageDraw, ImageFont
import os

def create_logo():
    """Create a professional logo for the Voicemeeter MCP Server."""
    
    # Create a 400x400 image with a gradient background
    size = 400
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    
    # Create a gradient background (dark blue to light blue)
    for y in range(size):
        # Calculate color based on position
        ratio = y / size
        r = int(20 + (60 - 20) * ratio)    # Dark blue to lighter blue
        g = int(30 + (120 - 30) * ratio)
        b = int(80 + (200 - 80) * ratio)
        
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    
    # Add a circular background for the main content
    circle_center = (size // 2, size // 2)
    circle_radius = 160
    
    # Draw outer circle (white with slight transparency effect)
    draw.ellipse([
        circle_center[0] - circle_radius,
        circle_center[1] - circle_radius,
        circle_center[0] + circle_radius,
        circle_center[1] + circle_radius
    ], fill=(255, 255, 255), outline=(200, 200, 200), width=3)
    
    # Draw inner circle for contrast
    inner_radius = 140
    draw.ellipse([
        circle_center[0] - inner_radius,
        circle_center[1] - inner_radius,
        circle_center[0] + inner_radius,
        circle_center[1] + inner_radius
    ], fill=(240, 245, 255), outline=(180, 180, 180), width=2)
    
    # Draw audio waveform-like elements
    wave_colors = [(50, 150, 255), (100, 200, 255), (150, 220, 255)]
    
    # Draw multiple audio bars to represent mixing
    bar_width = 8
    bar_spacing = 12
    num_bars = 8
    start_x = circle_center[0] - (num_bars * bar_spacing) // 2
    
    for i in range(num_bars):
        x = start_x + i * bar_spacing
        # Vary bar heights to look like audio levels
        heights = [60, 80, 45, 90, 70, 55, 85, 40]
        bar_height = heights[i]
        
        y_top = circle_center[1] - bar_height // 2
        y_bottom = circle_center[1] + bar_height // 2
        
        color = wave_colors[i % len(wave_colors)]
        
        # Draw the bar with rounded edges effect
        draw.rectangle([x, y_top, x + bar_width, y_bottom], fill=color)
        
        # Add highlight on top
        draw.rectangle([x, y_top, x + bar_width, y_top + 3], fill=(255, 255, 255, 100))
    
    # Add "VM" text (Voicemeeter abbreviation)
    try:
        # Try to use a system font
        font_size = 48
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("calibri.ttf", font_size)
            except:
                font = ImageFont.load_default()
        
        text = "VM"
        
        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # Position text at bottom of circle
        text_x = circle_center[0] - text_width // 2
        text_y = circle_center[1] + 60
        
        # Draw text shadow
        draw.text((text_x + 2, text_y + 2), text, fill=(100, 100, 100), font=font)
        # Draw main text
        draw.text((text_x, text_y), text, fill=(30, 60, 120), font=font)
        
    except Exception as e:
        print(f"Font loading failed: {e}")
        # Fallback: draw simple text
        draw.text((circle_center[0] - 20, circle_center[1] + 60), "VM", fill=(30, 60, 120))
    
    # Add "MCP" text smaller
    try:
        font_small = ImageFont.truetype("arial.ttf", 24) if 'arial.ttf' else ImageFont.load_default()
        mcp_text = "MCP"
        
        bbox = draw.textbbox((0, 0), mcp_text, font=font_small)
        mcp_width = bbox[2] - bbox[0]
        
        mcp_x = circle_center[0] - mcp_width // 2
        mcp_y = circle_center[1] + 100
        
        # Draw MCP text
        draw.text((mcp_x + 1, mcp_y + 1), mcp_text, fill=(150, 150, 150), font=font_small)
        draw.text((mcp_x, mcp_y), mcp_text, fill=(80, 120, 180), font=font_small)
        
    except:
        draw.text((circle_center[0] - 15, circle_center[1] + 100), "MCP", fill=(80, 120, 180))
    
    # Add small connection dots to represent MCP protocol
    dot_radius = 4
    dot_positions = [
        (circle_center[0] - 50, circle_center[1] - 80),
        (circle_center[0], circle_center[1] - 90),
        (circle_center[0] + 50, circle_center[1] - 80)
    ]
    
    for pos in dot_positions:
        draw.ellipse([
            pos[0] - dot_radius, pos[1] - dot_radius,
            pos[0] + dot_radius, pos[1] + dot_radius
        ], fill=(100, 200, 100))
    
    # Draw connecting lines between dots
    draw.line([dot_positions[0], dot_positions[1]], fill=(100, 200, 100), width=2)
    draw.line([dot_positions[1], dot_positions[2]], fill=(100, 200, 100), width=2)
    
    # Save the logo
    logo_path = "logo.png"
    img.save(logo_path, "PNG")
    print(f"✅ Logo created: {logo_path}")
    print(f"   Size: 400x400 pixels")
    print(f"   Format: PNG")
    print(f"   File size: {os.path.getsize(logo_path):,} bytes")
    
    return logo_path

if __name__ == "__main__":
    print("Creating Voicemeeter MCP Server Logo...")
    create_logo()
    print("Logo creation complete!")
