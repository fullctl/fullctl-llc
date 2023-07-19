import io

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter
from PIL import Image

from .util import render_service_logo


def format_y_axis(y, pos=None):
    """
    This function is used to format the y-axis values.
    """
    # Format the y-axis values based on their magnitude
    if y >= 1e12:
        return f"{int(y*1e-12)}T"
    elif y >= 1e9:
        return f"{int(y*1e-9)}G"
    elif y >= 1e6:
        return f"{int(y*1e-6)}M"
    elif y >= 1e3:
        return f"{int(y*1e-3)}K"
    else:
        return str(int(y))


def calculate_peak(data):
    """
    This function is used to calculate the peak values.
    """
    # Calculate the peak values for bps_in and bps_out
    bps_in_peak = data["bps_in_max"].max()
    bps_out_peak = data["bps_out_max"].max()

    return bps_in_peak, bps_out_peak


def render_graph(data, selector="#graph", title_label="", service=None, save_path=None):
    """
    This function is used to render the graph.
    """
    # Check if data is empty
    if not data:
        return

    # Convert data to pandas DataFrame
    df = pd.DataFrame(data)

    # Convert timestamp to datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")

    # Set up dimensions and margins for the graph
    fig, ax = plt.subplots(figsize=(10, 4))

    plt.subplots_adjust(right=0.99, left=0.1)

    # Set the background color
    fig.patch.set_facecolor("#191b22")
    ax.set_facecolor("#191b22")

    # Set the font / border colors
    ax.spines["bottom"].set_color("#fff")
    ax.spines["top"].set_color("#fff")
    ax.spines["right"].set_color("#fff")
    ax.spines["left"].set_color("#fff")

    ax.spines["right"].set_visible(False)
    ax.spines["top"].set_visible(False)

    ax.xaxis.label.set_color("#fff")
    ax.yaxis.label.set_color("#fff")
    ax.tick_params(axis="x", colors="#fff")
    ax.tick_params(axis="y", colors="#fff")

    # Calculate bps_in_peak and bps_out_peak
    bps_in_peak, bps_out_peak = calculate_peak(df)

    # Plot bps_in and bps_out
    ax.plot(df["timestamp"], df["bps_in"], color="#d1ff27", linewidth=1.5)
    ax.plot(df["timestamp"], df["bps_out"], color="#0d6efd", linewidth=1.5)

    # Set the x and y limits to make the plot sit snug against the left and bottom axis
    ax.set_xlim(left=df["timestamp"].min(), right=df["timestamp"].max())
    ax.set_ylim(
        bottom=df[["bps_in", "bps_out"]].min().min(),
        top=max(bps_in_peak, bps_out_peak) * 1.1,
    )

    # Fill area under bps_in line
    ax.fill_between(df["timestamp"], df["bps_in"], color="#d1ff27", alpha=1)

    # Add horizontal lines for bps_in_peak and bps_out_peak
    ax.axhline(y=bps_in_peak, color="#6f42c1", linewidth=1)
    ax.axhline(y=bps_out_peak, color="#20c997", linewidth=1)

    # Format y-axis
    ax.yaxis.set_major_formatter(FuncFormatter(format_y_axis))

    # Format x-axis
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # Add legend
    legend_elements = [
        Line2D([0], [0], color="#d1ff27", lw=2, label="Bps IN"),
        Line2D([0], [0], color="#0d6efd", lw=2, label="Bps OUT"),
        Line2D(
            [0],
            [0],
            color="#6f42c1",
            lw=2,
            label="IN Peak: " + format_y_axis(bps_in_peak),
        ),
        Line2D(
            [0],
            [0],
            color="#20c997",
            lw=2,
            label="OUT Peak: " + format_y_axis(bps_out_peak),
        ),
    ]
    ax.legend(
        handles=legend_elements,
        facecolor="#191b22",
        edgecolor="none",
        labelcolor="#fff",
        loc="upper center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=4,
        frameon=False,
    )

    # Add title label
    if title_label:
        ax.set_title(title_label, color="#fff")

    if service:
        render_service_logo(service, ax)

    # Save the figure as a PNG file
    if save_path:
        return fig.savefig(
            save_path, facecolor=fig.get_facecolor(), dpi=300, edgecolor="none"
        )

    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", facecolor=fig.get_facecolor(), dpi=300, edgecolor="none"
    )
    buf.seek(0)

    # resize
    # Load the image data into a PIL Image
    img = Image.open(buf)

    # Resize the image
    img_resized = img.resize((1000, 400))

    # Save the resized image to a BytesIO object
    buf_resized = io.BytesIO()
    img_resized.save(buf_resized, format="png")
    buf_resized.seek(0)

    return buf_resized.getvalue()
