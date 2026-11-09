import faulthandler
faulthandler.dump_traceback_later(60, repeat=True)
"""Load/download local models using synthetic input, and report no personal data."""
from PIL import Image, ImageDraw, ImageFont
from paddle_engine import recognize_image
image = Image.new('RGB', (1200, 400), 'white')
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 40)
draw.text((40, 40), 'Aarav Example\nDOB: 19/08/2002\nXXXX XXXX 1234', fill='black', font=font, spacing=25)
result = recognize_image(image)
assert result['engine'] == 'paddleocr'
assert 'Aarav Example' in result['text'], 'Synthetic name recognition failed'
assert '19/08/2002' in result['text'], 'Synthetic date recognition failed'
faulthandler.cancel_dump_traceback_later()
print({'engine': result['engine'], 'synthetic_name': True, 'synthetic_date': True, 'lines': len(result['lines'])})
