(function() {

    fullctl.graphs = {}

    /**
     * Format the y-axis values using pretty_speed formatter
     * @param {number} value - The value to be formatted
     * @return {string} - The formatted value
     */
    function format_y_axis(value) {
        return fullctl.formatters.pretty_speed_bits(value);
    }

    /**
     * Calculate bps_in_peak and bps_out_peak from the data
     * @param {Array} data - The data array containing bps_in and bps_out values
     * @return {Object} - An object containing bps_in_peak and bps_out_peak values
     */
    function calculate_peak(data) {
        let bps_in_peak = 0;
        let bps_out_peak = 0;

        data.forEach(function(d) {
            bps_in_peak = Math.max(bps_in_peak, d.bps_in_max);
            bps_out_peak = Math.max(bps_out_peak, d.bps_out_max);
        });

        return {bps_in_peak, bps_out_peak};
    }

    fullctl.graphs.render_graph = function(data, titleLabel = "") {
        // Set up dimensions and margins for the graph
        const margin = {top: 20, right: 20, bottom: 50, left: 80}; // Increase left margin for traffic numbers and bottom margin for legend
        const width = 768 - margin.left - margin.right;
        const height = 256 - margin.top - margin.bottom;

        // Set up x and y scales
        const x = d3.scaleTime().range([0, width]);
        const y = d3.scaleLinear().range([height, 0]);

        // Set up line generators for bps_in and bps_out
        const line_in = d3.line()
            .x(function(d) { return x(d.timestamp * 1000); }) // Multiply by 1000 to convert unix timestamp to JavaScript timestamp
            .y(function(d) { return y(d.bps_in); });

        const line_out = d3.line()
            .x(function(d) { return x(d.timestamp * 1000); }) // Multiply by 1000 to convert unix timestamp to JavaScript timestamp
            .y(function(d) { return y(d.bps_out); });

        // Calculate bps_in_peak and bps_out_low
        const {bps_in_peak, bps_out_peak} = calculate_peak(data);

        // Set up SVG container for the graph
        const svg = d3.select("#graph").append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        // Set up domains for x and y scales
        x.domain(d3.extent(data, function(d) { return d.timestamp * 1000; })); // Multiply by 1000 to convert unix timestamp to JavaScript timestamp
        y.domain([0, d3.max(data, function(d) { return Math.max(d.bps_in, d.bps_out); }) * 1.1]); // Add 10% padding to the maximum value

        // Add x-axis to the graph
        svg.append("g")
            .attr("transform", "translate(0," + height + ")")
            .call(d3.axisBottom(x));

        // Add y-axis to the graph
        svg.append("g")
            .call(d3.axisLeft(y).tickFormat(format_y_axis)); // Format y-axis using pretty_speed formatter

        // Add area for bps_in
        const area_in = d3.area()
            .x(function(d) { return x(d.timestamp * 1000); }) // Multiply by 1000 to convert unix timestamp to JavaScript timestamp
            .y0(height)
            .y1(function(d) { return y(d.bps_in); });

        // Update the area_in definition to fill all the way to the bottom of the graph
        const area_in_updated = d3.area()
            .x(function(d) { return x(d.timestamp * 1000); }) // Multiply by 1000 to convert unix timestamp to JavaScript timestamp
            .y0(height)
            .y1(function(d) { return y(Math.max(d.bps_in, 0)); });

        svg.append("path")
            .datum(data)
            .attr("fill", "#d1ff27")
            .attr("d", area_in_updated);

        // Add lines for bps_in and bps_out
        svg.append("path")
            .datum(data)
            .attr("fill", "none")
            .attr("stroke", "#d1ff27")
            .attr("stroke-width", 1.5)
            .attr("d", line_in);

        svg.append("path")
            .datum(data)
            .attr("fill", "none")
            .attr("stroke", "#0d6efd")
            .attr("stroke-width", 1.5)
            .attr("d", line_out);

        // Add horizontal lines for bps_in_peak and bps_out_peak
        svg.append("line")
            .attr("x1", 0)
            .attr("x2", width)
            .attr("y1", y(bps_in_peak))
            .attr("y2", y(bps_in_peak))
            .attr("stroke", "#20c997")
            .attr("stroke-width", 1);

        svg.append("line")
            .attr("x1", 0)
            .attr("x2", width)
            .attr("y1", y(bps_out_peak))
            .attr("y2", y(bps_out_peak))
            .attr("stroke", "#6f42c1")
            .attr("stroke-width", 1);


        // Add legend
        const legend = svg.append("g")
            .attr("font-family", "sans-serif")
            .attr("font-size", 10)
            .attr("text-anchor", "start") // Change text-anchor to "start" for left alignment
            .attr("transform", "translate(0," + (height + margin.bottom - 20) + ")") // Move legend to the bottom
            .selectAll("g")
            .data([
                {key: "bps_in", label: "Bps IN"},
                {key: "bps_out", label: "Bps OUT"},
                {key: "bps_in_peak", label: "IN Peak"},
                {key: "bps_out_peak", label: "OUT Peak"}
            ])
            .enter().append("g")
            .attr("transform", function(d, i) { return "translate(" + (i * 100) + ",0)"; }); // Make legend horizontal

        legend.append("rect")
            .attr("x", 0) // Change x position to 0 for left alignment
            .attr("width", 19)
            .attr("height", 19)
            .attr("fill", function(d) {
                switch (d.key) {
                    case "bps_in":
                        return "#d1ff27";
                    case "bps_out":
                        return "#0d6efd";
                    case "bps_in_peak":
                        return "#20c997";
                    case "bps_out_peak":
                        return "#6f42c1";
                }
            });

        legend.append("text")
            .attr("x", 24) // Change x position to 24 for left alignment
            .attr("y", 9.5)
            .attr("dy", "0.32em")
            .attr("fill", "#fff") // Set legend font color to #fff
            .text(function(d) { return d.label; });;

        // Add logo
        const logoPath = document.querySelector("img.app-logo").getAttribute("src");
        svg.append("image")
            .attr("xlink:href", logoPath)
            .attr("x", width - 100) // Adjust x position to place the logo in the upper right corner
            .attr("y", -25)
            .attr("width", 100) // Adjust width of the logo
            .attr("height", 50); // Adjust height of the logo

        // Add title label
        if (titleLabel) {
            svg.append("text")
                .attr("x", width / 2) // Center the label
                .attr("y", 0) // Move the label down to avoid being cut off
                .attr("text-anchor", "middle") // Center the text
                .attr("font-family", "sans-serif")
                .attr("font-size", 16)
                .attr("fill", "#fff") // Set the font color to white
                .text(titleLabel);
        }

    },

    fullctl.graphs.render_graph_from_file = function(path, titleLabel = "") {
        d3.json(path).then(function(data) {
            fullctl.graphs.render_graph(data.data[0].traffic, titleLabel);
        });
    }
})();