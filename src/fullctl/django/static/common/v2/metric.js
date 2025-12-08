(function($) {
  $.fn.show_metric_list = function(row, metrics_data) {
    const light_level_stat = row.find('[data-element="light_level_stat"]');
    const {status, device_name, metric = {}} = metrics_data;
    const result = {};
    $.each(metric, (metric_index, value) => {
      if (metric_index.includes('optics')) {
        const segments = metric_index.split('.');
        const opticsIndex = segments.indexOf('optics');
        let port = null;

        // The index is added to the metrics if there are more than 1 metrics data
        // If not it is not added
        // e.g. ceos00.optics.0.Ethernet1.physical_channels.channel.0.index being index 0
        // ceos00.optics.1.Ethernet1.physical_channels.channel.1.index being index 1
        if (isNaN(parseInt(segments[opticsIndex + 1]))) {
          port = segments[opticsIndex + 1];
        } else {
          port = segments[opticsIndex + 2];
        }
        const metric_data = segments.slice(-2).join(".");
        if (!result[port]) {
          result[port] = {};
        }
        result[port][metric_data] = value;
      }
    });

    $.each(result, (port, metric) => {
      // Tooltip
      const tootlip_div = $('<div>')
      .attr("data-bs-toggle", "tooltip")
      .attr("data-bs-placement", "top")
      .attr("data-bs-html", true);

      let tooltip_data = `${device_name} ${port}<br>`;
      const allowed_metrics = {
        "input_power.instant": "TX Power",
        "output_power.instant": "RX Power",
        "laser_bias_current.instant": "Bias Current",
      };
      const allowed_metrics_keys = Object.keys(allowed_metrics);
      $.each(metric, (key, data) => {
        if (allowed_metrics_keys.indexOf(key) !== -1) {
          tooltip_data = `${tooltip_data}${allowed_metrics[key]}: ${data}<br>`;
        }
      });
      tootlip_div.attr("title", tooltip_data);

      // Tooltip Container
      const node = $('<div class="d-flex align-items-center">');
      node.append($('<span class="dotted-underline">').text(`${device_name} ${port}`));
      if (status == "ok") {
        node.append($('<span class="icon icon-triangle-fill-up">'));
        node.addClass("up");
      } else {
        node.append($('<span class="icon icon-triangle-fill-down">'));
        node.addClass("down");
      }
      tootlip_div.html(node);
      new bootstrap.Tooltip(tootlip_div);
      light_level_stat.append(tootlip_div);
    });
  };

  $.fn.show_metric_table = function(url, port_reference) {
    if ((port_reference.port == null || port_reference.port.virtual_port == null) && !port_reference.port_id) return;
    
    // Extract metric data from member object
    let metricsData = [];
    
    // Helper function to process metric entries
    const processMetrics = (deviceName, interfaceName, metrics) => {
      if (!metrics) return;
      
      Object.entries(metrics).forEach(([key, value]) => {
        // Parse the metric key to extract the subject
        const parts = key.split('.');
        // Get only the last 2 parts of the metric key
        let subjectParts = parts.slice(-2);
        
        // If the first part is the interface name or a digit, drop it
        if (subjectParts.length === 2 && 
            (subjectParts[0] === interfaceName || /^\d+$/.test(subjectParts[0]))) {
          subjectParts = subjectParts.slice(1);
        }
        
        let subject = subjectParts.join('.');
        
        metricsData.push({
          device: deviceName,
          interface: interfaceName,
          subject: subject,
          value: value
        });
      });
    };
    
    // Check if port_reference has metric array (first format)
    if (port_reference.metric && Array.isArray(port_reference.metric)) {
      port_reference.metric.forEach(metricItem => {
        processMetrics(metricItem.device_name, metricItem.name, metricItem.metric);
      });
    }
    // Check if port_reference has port.physical_ports (second format)
    else if (port_reference.port && port_reference.port.physical_ports && Array.isArray(port_reference.port.physical_ports)) {
      port_reference.port.physical_ports.forEach(physicalPort => {
        const deviceName = physicalPort.device_name || port_reference.device_name || port_reference.port.device_name;
        processMetrics(deviceName, physicalPort.name, physicalPort.metric);
      });
    }

    $('#metric_table').DataTable({
      // https://datatables.net/manual/options
      destroy: true,
      paging: false,
      searching: false,
      info: false,
      autoWidth: true,
      // No need for processing indicator since data is local
      processing: false, 
      responsive: true,
      language: {"emptyTable": "No metrics available"},
      scrollCollapse: true,
      scrollY: '200px',

      // Use data option instead of ajax
      data: metricsData,

      columns: [
        { data: "device" },
        { data: "interface" },
        { data: "subject" },
        { data: "value" }
      ],
      
      // Add initComplete callback
      initComplete: function() {
        // Force a redraw after initialization
        this.api().columns.adjust().draw();
      }
    });
    
    // Also try with a small delay in case the container is still rendering
    setTimeout(function() {
      $('#metric_table').DataTable().columns.adjust().draw();
    }, 100);
  };

  $.fn.reset_metric_table = function(url, member) {
    // Clean metric table.

    $('#metric_table').DataTable().clear();
    $('#metric_table').DataTable().destroy();
    $('#metric_table').DataTable({
      destroy: true,
      paging: false,
      searching: false,
      info: false,
      autoWidth:false,
      processing: true,
      responsive: true,
      language: {"emptyTable": "No port assigned"}
    });

    return true;
  };

})(jQuery);
