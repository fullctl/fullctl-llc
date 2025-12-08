(function ($) {
    $.fn.show_bgp_stat = function (bgp_stat, row) {
        const bgp_stats_v4 = row.find('[data-element="bgp_stat_v4"]');
        const bgp_stats_v6 = row.find('[data-element="bgp_stat_v6"]');
        Object.keys(bgp_stat).forEach((routeserver, routeserver_index) => {
            bgp_stat[routeserver].forEach((stat, _) => {
                const {
                    up = false,
                    last_change = "",
                    state = "",
                    routes_imported = 0,
                    routes_exported = 0,
                    address = "",
                    routeserver_hostname = "",
                    routeserver_name = "",
                    routeserver_router_id = ""
                } = stat;

                // Tooltip
                let tooltip_data = `${routeserver_hostname}<br>`;
                tooltip_data = `${tooltip_data}Session: ${state}<br>`;
                tooltip_data = `${tooltip_data}Routes Received: ${routes_imported}<br>`;
                tooltip_data = `${tooltip_data}Routes Advertised: ${routes_exported}<br>`;
                tooltip_data = `${tooltip_data}${up ? "Up" : "Down"} Since: ${last_change}<br>`;
                const bgp_stat = $('<div>');
                bgp_stat.attr("data-bs-toggle", "tooltip")
                    .attr("data-bs-placement", "top")
                    .attr("data-bs-html", true)
                    .attr("title", tooltip_data);

                // Tooltip Container
                const outer = $('<div>');
                outer.append($('<span class="small-header decent">').text(routeserver_name || routeserver_hostname || routeserver_router_id));
                const node = $('<div class="d-flex align-items-center">');
                if (up) {
                    node.append($('<span class="icon icon-triangle-fill-up">'));
                    node.addClass("up");
                } else {
                    node.append($('<span class="icon icon-triangle-fill-down">'));
                    node.addClass("down");
                }
                node.append(
                    $('<span class="dotted-underline">').text(
                        `${routes_imported} / ${routes_exported}`
                    )
                );
                bgp_stat.append(outer);
                bgp_stat.append(node);
                new bootstrap.Tooltip(bgp_stat);
                if (address.includes(":")) {
                    bgp_stats_v6.append(bgp_stat)
                } else {
                    bgp_stats_v4.append(bgp_stat)
                }
            });
        });
    };

})(jQuery);
