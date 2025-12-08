(function ($) {
    $.fn.show_traffic_alert = function (data, element) {
        // Displays an emoji on the speed to indicate that the device has reached a traffic threshold
        // Displays a red flame or a caution sign depending on the threshold
        const {
            traffic_level,
            capacity_alert,
            traffic_poll_time,
            at_capacity,
            time_period,
        } = data.traffic_alert_data;
        const counter_threshold = time_period / Math.round(traffic_poll_time / 60);
        const DAYS_SPAN = 30;

        const date_last_at_capacity = new Date(at_capacity);
        const current_date = new Date();
        // Add {SPAN_DAYS} days to the date it was last at capacity
        date_last_at_capacity.setDate(date_last_at_capacity.getDate() + DAYS_SPAN)

        // Check alert is triggered in the past {DAYS_SPAN} days
        if (capacity_alert > 0 && (!at_capacity || current_date < date_last_at_capacity)) {
            const downtime = Math.round(traffic_poll_time / 60) * capacity_alert;
            let tooltip_data = `Port over ${traffic_level}% utilization for ${downtime} minutes in the past ${DAYS_SPAN} days`;
            const port_is_hot_tooltip = $('<div>');
            port_is_hot_tooltip.attr("data-bs-toggle", "tooltip")
                .attr("data-bs-placement", "top")
                .attr("data-bs-html", true)
                .attr("title", tooltip_data);

            let node = null;
            if (capacity_alert >= counter_threshold) {
                // Flame emoji unicode &#x1F525;
                node = $("<div>&#x1F525;</div>");
            } else {
                // Caution emoji unicode &#x26A0;
                node = $('<div style="color: yellow; font-size: 24px;">&#x26A0;</div>');
            }
            port_is_hot_tooltip.html(node);
            new bootstrap.Tooltip(port_is_hot_tooltip);
            element.append(port_is_hot_tooltip);
        }
    };

})(jQuery);
