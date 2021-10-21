(function($, $tc) {


window.fullctl = {
  urlparam : new URLSearchParams(window.location.search)
}
var fullctl = window.fullctl;

fullctl.template = function(name) {
  return $('[data-template="'+name+'"]').clone().attr("data-template",null);
}

fullctl.application = {}
fullctl.widget = {}
fullctl.formatters = {}

fullctl.formatters.pretty_speed = (value) => {
  if(value >= 1000000)
    value = (value / 1000000).toFixed(2)+"T";
  else if(value >= 1000)
    value = (value / 1000).toFixed(2)+"G";
  else
    value = value+"M";
  return value
}

fullctl.formatters.monitor_status = (value) => {
  if(value == "ok") {
     return $('<span>').addClass('active').text('Active');
  } else if(value == "deactivated") {
     return $('<span>').addClass('inactive').text('Stopped');
  }
  return value
}


fullctl.widget.StatusBadge = $tc.extend(
  "StatusBadge",
  {

    StatusBadge : function(base_url, jq, refresh_values) {
      this.row_id = jq.data("row-id")
      this.field_name = jq.data("name")
      this.refresh_time = parseInt(jq.data("refresh") || 1000);
      this.loading_shim_disabled = true;
      this.refresh_timer = new twentyc.util.SmartTimeout(()=>{},1000);
      this.refresh_values = refresh_values;
      this.Widget(base_url, jq);
    },


    spinner : function() {
			return $('<div class="spinner loadingio-spinner-bars-k879i8bcs9"><div class="ldio-a9ruqenne8l"><div></div><div></div><div></div><div></div></div></div>');
    },

    load : function() {
      return this.get().then((response) => {
        response.rows((row) => {
          if(row.id == this.row_id) {
            var value = row[this.field_name];
            this.render(value, row);
          }
        })
      });
    },

    refresh : function() {
      this.refresh_timer.set(
        ()=>{this.load()},
        this.refresh_time
      );
    },

    render : function(value, row) {
      this.element.removeClass().addClass("status-badge "+value)
      this.element.empty().append($('<span>').text(value));
      if(this.refresh_values && $.inArray(value, this.refresh_values) == -1) {
          this.element.append(this.spinner());
          this.refresh();
      }

    }
  },
  twentyc.rest.Widget
);


fullctl.widget.OrganizationSelect = $tc.extend(
  "OrganizationSelect",
  {
    OrganizationSelect : function(jq) {
      this.Select(jq);
    }
  },
  twentyc.rest.Select
);

fullctl.application.Component = $tc.define(
  "Component",
  {
    Component : function(name) {
      this.name = name;
      this.jquery = $('[data-component="'+name+'"]')
      var elements = this.elements = this.$e = {}
      var templates = this.templates = this.$t = {}

      this.widgets = this.$w = {};

      this.jquery.find('[data-element]').each(function(idx) {
        elements[$(this).data("element")] = $(this);
      });

      this.jquery.find('[data-template]').each(function(idx) {
        templates[$(this).data("template")] = $(this);
      });

      this.wire_elements();
    },

    template : function(name, appendTo) {
      var element = this.$t[name].clone().attr('data-template',null);
      if(appendTo)
        element.appendTo(appendTo)
      return element;
    },

    widget : function(name, fn) {
      fn = fn.bind(this);
      var widget = this.$w[name] = fn(this.$e, this.$t);
      return widget;
    },

    wire_elements : function() {
    }
  }
);

fullctl.application.Modal = $tc.extend(
  "Modal",
  {
    Modal : function(type, title, content) {
      this.Component("modal_"+type)
      this.set_title(title);
      this.set_content(content);

      var modal = this;

      content.find('.modal-action-note-text').each(function() {
        $(this).appendTo(modal.jquery.find('.modal-action-note'))
      });

      this.show();
    },
    show : function() {
      this.jquery.modal('show');
    },
    hide : function() {
      this.jquery.modal('hide');
    },
    set_title : function(title) {
      this.jquery.find('.modal-title').text(title);
    },
    set_content : function(content) {
      this.jquery.find('.modal-body').empty().append(content);
    }
  },
  fullctl.application.Component
);

fullctl.application.Tool = $tc.extend(
  "Tool",
  {
    Tool : function(name) {
      this.Component(name);
      this.init();
      this.menu();
      this.active = false;
    },

    init : function() {
    },

    sync : function() {

    },

    hide : function() {
      this.$e.body.parents(".tool").hide();
    },

    show : function() {
      this.$e.body.parents(".tool").show();
    },

    menu : function() {
      var menu = this.template("menu")
      console.log(this);
      this.$e.menu.append(menu);
      return menu
    },

    activate : function() {
      this.active = true
    },

    deactivate : function() {
      this.active = false
    },

    initialize_sortable_headers: function() {
      const list = this.$w.list

      // Add click function to headings to sort
      const table = list.element[0];
      this.tableHeadings = $(table).first().find("th[data-sort-target]");
      this.tableHeadings.click( function(event) {
        let button = event.currentTarget;
        this.handle_click( $(button) );
      }.bind(this))

      let sortButton = this.tableHeadings.filter("[data-sort-initial]");
      this.sortHeading = sortButton.data("sort-target");
      this.sortSecondary = sortButton.data("sort-secondary");

      this.sortAsc = true;
      this.ordering = "";

      /*
      Specific to django-rest-framework: we add "ordering" as a query
      parameter to the API calls
      */
      list.payload = function(){return {ordering: this.ordering}}
    },

    handle_click: function(button) {
        let sortTarget = button.data("sort-target");

        this.sortSecondary = button.data("sort-secondary")

        if ( sortTarget == this.sortHeading ){
          this.sortAsc = !this.sortAsc;
        } else {
          this.sortHeading = sortTarget;
          this.sortAsc = true;
        };
        this.sync();
    },

    apply_ordering : function() {
        this.$w.list.ordering = this.return_ordering();
        this.format_headings();
    },

    return_ordering: function() {

      let secondary = (this.sortSecondary ? ","+this.sortSecondary : "")

      if ( this.sortAsc ){
        return this.sortHeading + secondary;
      }
      return "-" + this.sortHeading + secondary;
    },


    format_headings : function() {
      let heading = this.sortHeading;
      let asc = this.sortAsc;

      $(this.tableHeadings).each( function() {
        $(this).find("span").remove();
        if ( $(this).data("sort-target") == heading ){
          if ( asc ){
            $(this).removeClass("selected-order-header-desc")
            $(this).addClass("selected-order-header-asc");
          } else {
            $(this).removeClass("selected-order-header-asc")
            $(this).addClass("selected-order-header-desc");
          }
        } else {
            $(this).removeClass("selected-order-header-asc");
            $(this).removeClass("selected-order-header-desc");
        }
      })
    },
  },
  fullctl.application.Component
);

fullctl.application.TabbedTool = $tc.extend(
  "TabbedTool",
  {
    "TabbedTool" : function(name) {
      this.Tool(name)
    },

    menu : function() {
      var menu = this.Tool_menu()

      var tool = this;
      var urlparam = this.urlparam

      if(urlparam) {
        var preselect = fullctl.urlparam.get(urlparam)
      } else {
        var preselect = false;
      }

      this.widget('tabs_fetcher', ($e) => {
        var w = new twentyc.rest.List(menu)

        w.formatters.row = (row, data) => {
          if(!w.element.find(".active").length) {
            if(!preselect || preselect == ""+data[urlparam])
              tool.tab(row, data);
          }

          row.click(function() {
            tool.tab(row, data);
            if(urlparam)
              window.history.replaceState({}, document.title, "?"+urlparam+"="+data[urlparam])
          });
        }

        $(w).on("api-read:success", (event, endpoint, payload, response) => {
          if(!response.content.data.length) {
            this.hide();
          } else {
            this.show();
          }
        });
        $(w).on("api-read:error", ()=> {
          this.hide();
        })

        w.load()
        return w;
      })

      return menu
    },

    tab : function(tab, data) {
      tab.siblings().removeClass("active")
      tab.addClass("active")
    }


  },
  fullctl.application.Tool
);

fullctl.application.Header = $tc.extend(
  "Header",
  {
    Header : function() {
      this.Component("header");

    },

    wire_elements : function() {

      this.widget('select_org', ($e) => {
        var w = new twentyc.rest.List($e.select_org);
        var org = $e.select_org.data('org')
        $(w).on("insert:after", (e, row, data) => {
          if(org == data.slug) {
            row.addClass('selected')
            row.find('.manage').click(() => {
              new fullctl.application.Orgctl.PermissionsModal();
            });
          } else {
            row.find('.manage').hide();
            row.click(() => {
              window.location.href = "/"+data.slug+"/";
            })
          }
        });
        w.load()

        this.wire_app_switcher();

        return w;
      });
    },

    wire_app_switcher : function() {
      this.widget("app_switcher", ($e) => {
        var others = $e.app_switcher.find('.others')
        var selected = $e.app_switcher.find('.selected')
        selected.click(() => {
          others.show();
          selected.addClass('app_bg muted');
        });
        $(document.body).click(function(e) {
          if( !$(e.target).parent().hasClass('selected') ) {
            others.hide();
            selected.removeClass('app_bg muted');
          }
        });
        return {};
      });
    }
  },
  fullctl.application.Component
);


fullctl.application.Toolbar = $tc.extend(
  "Toolbar",
  {
    Toolbar : function() {
      this.Component("toolbar");
    }
  },
  fullctl.application.Component
);


fullctl.application.Application = $tc.define(
  "Application",
  {
    Application : function(id) {
      this.id = id;
      this.components = this.$c = {
        header : new fullctl.application.Header(),
        toolbar : new fullctl.application.Toolbar(),
        main : new fullctl.application.Component("main")
      }
      this.tools = this.$t = {}
      $(fullctl.application).trigger("initialized", [this, id]);
    },

    tool : function(name, fn) {
      fn = fn.bind(this);
      var tool = this.$t[name] = fn()
      return tool;
    },

    sync : function() {
      var i, app = this;
      for(i in this.$t) {
        if(this.$t[i].active) {
          this.$t[i].sync(app);
        }
      }
    }
  }
);


fullctl.application.Orgctl = $tc.extend(
  "Orgctl",
  {

  },
  fullctl.application.Tool
)

fullctl.application.Orgctl.Users = $tc.extend(

  "Users",
  {
    Users : function() {
      this.Component("user_listing");
    },

    wire_elements : function() {
      this.rest_api_list = new twentyc.rest.List(this.jquery);

      this.rest_api_list.formatters.name = function(value, data) {
        return $('<span>').append(
          $('<span>').text(value),
          $('<strong>').text(data.you?" (You)":"")
        );
      }

      this.rest_api_list.formatters.permissions = function(value, data) {
        if(!data.manageable.match(/ud/))
          return;
        var component, editor, widget, container = $('<div>');
        for(component in value) {
          editor = this.template("permissions")
          editor.find('[data-field="component"]').text(component);
          widget = new twentyc.rest.PermissionsForm(editor);
          widget.fill(data);
          widget.fill({component:component});
          widget.set_flag_values(value[component]);
          container.append(editor)
        }
        return container;
      }.bind(this.rest_api_list)


      this.rest_api_list.formatters.row = function(row,data) {
        var manage_container = row.filter('.manage')
        if(data.you)
          row.find('.btn-permissions').attr('disabled', true);
        else if(!data.manageable.match(/[ud]/))
          row.find('.btn-permissions').hide();
        else {
          row.find('.btn-permissions').click(function() {
            if(manage_container.is(':visible'))
              manage_container.hide();
            else
              manage_container.show();
          });
        }
        manage_container.hide();
      }

      this.rest_api_list.load();
    }
  },
  fullctl.application.Component
);

fullctl.application.Orgctl.PermissionsModal = $tc.extend(
  "PermissionsModal",
  {
    PermissionsModal : function() {
      var user_listing = new fullctl.application.Orgctl.Users();
      this.Modal("manage", fullctl.org.name+" User Permissions", user_listing.jquery);
    }
  },
  fullctl.application.Modal
);

$.fn.grainy_toggle = function(namespace, level) {
  if(grainy.check(namespace, level)) {
    this.show();
  } else {
    this.hide();
  }
};

})(jQuery, twentyc.cls);
