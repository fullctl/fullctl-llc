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
    if y >= 1e13:
        return f"{int(y * 1e-12)}T"
    elif y >= 1e10:
        return f"{int(y * 1e-9)}G"
    elif y >= 1e7:
        return f"{int(y * 1e-6)}M"
    elif y >= 1e4:
        return f"{int(y * 1e-3)}K"
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

    # Apply a rolling window to smooth the data
    # if data duration is greater than a week
    if (df["timestamp"].max() - df["timestamp"].min()).days > 7:
        window_size = 4
    else:
        window_size = 1
    df["bps_in_smooth"] = df["bps_in"].rolling(window_size, min_periods=1).mean()
    df["bps_out_smooth"] = df["bps_out"].rolling(window_size, min_periods=1).mean()

    # Calculate the duration in days
    duration = (df["timestamp"].max() - df["timestamp"].min()).days

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
    
    # Get current (most recent) bps_in and bps_out values
    bps_in_current = df["bps_in"].iloc[-1]
    bps_out_current = df["bps_out"].iloc[-1]

    # Plot bps_in and bps_out
    ax.plot(df["timestamp"], df["bps_in_smooth"], color="#d1ff27", linewidth=1.5)
    ax.plot(df["timestamp"], df["bps_out_smooth"], color="#0d6efd", linewidth=1.5)

    # Set the x and y limits to make the plot sit snug against the left and bottom axis
    ax.set_xlim(left=df["timestamp"].min(), right=df["timestamp"].max())
    ax.set_ylim(
        bottom=df[["bps_in", "bps_out"]].min().min(),
        top=max(bps_in_peak, bps_out_peak) * 1.1,
    )

    # Fill area under bps_in line
    ax.fill_between(df["timestamp"], df["bps_in_smooth"], color="#d1ff27", alpha=1)

    # Add horizontal lines for bps_in_peak and bps_out_peak
    ax.axhline(y=bps_in_peak, color="#6f42c1", linewidth=1)
    ax.axhline(y=bps_out_peak, color="#20c997", linewidth=1)

    # Format y-axis
    ax.yaxis.set_major_formatter(FuncFormatter(format_y_axis))

    # Format x-axis
    if duration <= 2:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    elif duration <= 7:  # for 7 days, use day ticks
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%a"))
    elif duration <= 30:  # for 30 days, use week ticks
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("Week %W"))
    elif duration <= 365:  # for 365 days, use month ticks
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    # Add legend
    legend_elements = [
        Line2D([0], [0], color="#d1ff27", lw=2, label=f"bps IN: {format_y_axis(bps_in_current)}"),
        Line2D([0], [0], color="#0d6efd", lw=2, label=f"bps OUT: {format_y_axis(bps_out_current)}"),
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
    # close figure to prevent memory leak
    plt.close(fig)
    buf_resized.seek(0)

    return buf_resized.getvalue()
