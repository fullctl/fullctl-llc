import io
import os

import cairosvg
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image


def render_service_logo(service, ax):
    image_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "django",
        "static",
        "common",
        "logos",
        f"{service}-dark.svg",
    )

    # Convert the SVG file to PNG data
    png_data = cairosvg.svg2png(url=image_path)

    # Load the PNG data into a PIL Image
    img = Image.open(io.BytesIO(png_data))

    img = img.convert("RGBA")
    bg = Image.new("RGBA", img.size, (25, 27, 34))
    img = Image.alpha_composite(bg, img)

    # Create an OffsetImage from the PIL image
    # Increase the zoom level to make the logo bigger
    imagebox = OffsetImage(img, zoom=0.075)

    # Create an AnnotationBbox from the OffsetImage
    # Change the position of the logo to the top right corner
    ab = AnnotationBbox(
        imagebox,
        (1, 1),
        box_alignment=(1, 0.5),
        xycoords="axes fraction",
        pad=0,
        frameon=False,
    )

    # Add the AnnotationBbox to the axes
    ax.add_artist(ab)


def resize_in_buffer(buf, width, height):
    # resize
    # Load the image data into a PIL Image
    img = Image.open(buf)

    # Resize the image
    img_resized = img.resize((width, height))

    # Save the resized image to a BytesIO object
    buf_resized = io.BytesIO()
    img_resized.save(buf_resized, format="png")
    buf_resized.seek(0)

    return buf_resized.getvalue()
