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
fullctl.modals = {}
fullctl.util = {}

fullctl.util.slugify = (txt) => {
  return txt.toLowerCase().replace(/\s/g, "-").replace(/_/g, "-").replace(/[^a-zA-Z0-9-]/g,"").replace(/-+/g, '-');
};

fullctl.formatters.pretty_speed = (value) => {
  if(value >= 1000000)
    value = parseInt(value / 1000000)+"T";
  else if(value >= 1000)
    value = parseInt(value / 1000)+"G";
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

fullctl.formatters.meta_data = (value) => {
  if(!value)
    return;

  var k, node = $('<div>');
  for(k in value) {
    node.append($('<div>').addClass("badge").text(k+": "+value[k]));
  }
  return node;
}


fullctl.loading_animation = () => {
  var anim = $('<div class="spinner loadingio-spinner-bars-k879i8bcs9"><div class="ldio-a9ruqenne8l"><div></div><div></div><div></div><div></div></div></div>');
  return $('<div>').addClass("loading-anim").append(anim);
}

fullctl.widget.Wizard = $tc.define(
  "Wizard",
  {
    Wizard : function(jq) {
      this.element = jq;
      this.step = 1;
      this.element.addClass("wiz-step wiz-step-1");

      var wizard = this;

      this.element.find('button[data-wizard-step]').click(function() {
        wizard.set_step($(this).data("wizard-step"));
      });
    },

    set_step : function(n) {
      this.element.removeClass("wiz-step-"+this.step);
      this.element.addClass("wiz-step-"+n);
      this.step = n;
    }
  }

);

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
      this.$e.menu.append(menu);
      return menu
    },

    activate : function() {
      this.active = true
    },

    deactivate : function() {
      this.active = false
    },

    apply_ordering: function() {
      //deprecated
      return;
    },

    initialize_sortable_headers: function() {
      //deprecated
      return;
    },

    custom_dialog : function(title) {
      this.$e.body.empty();
      var custom_dialog = $('<div>').addClass("tool-custom")
      custom_dialog.append($('<h4>').addClass("tool-title").text(title));
      this.$e.body.append(custom_dialog);
      return custom_dialog;
    }

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

fullctl.application.Pages = $tc.extend(
  "Pages",
  {
    Pages : function() {
      this.Component("pages");
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
      $('[data-grainy-remove]').each(function() {
        $(this).grainy_toggle($(this).data("grainy-remove"), "r");
      });


      $('[data-bs-toggle="tab"]').on('show.bs.tab', function() {
        window.history.replaceState({}, document.title, $(this).attr("href"));
      });

      fullctl[id] = this;


    },

    autoload_page : function() {
      var hash = window.location.hash;
      if(hash) {
        hash = hash.substr(1);

        parts = hash.split(";");
        hash = parts[0];

        this.autoload_args = parts;

        if(this.get_page(hash)) {
          this.page(hash);
        }

      }
    },

    autoload_arg : function(idx) {
      if(this.autoload_args) {
        var value = this.autoload_args[idx];
        if(value) {
          this.autoload_args[idx] = null;
        }
        return value;
      }
      return null;
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

    },

    /**
     * Gets the element representing the page in the pages menu.
     *
     * @method get_page
     * @param {String} page Value set for aria-controls
     */
    get_page : function(page) {
      return $('[data-component="pages"]').find('[aria-controls="'+page+'"]');
    },

    page : function(page) {
      this.get_page(page).tab('show');
    },

    /**
     * Makes visible the page in the pages menu so you can navigate to the tab
     *
     * @method show_page
     * @param {String} page Value set for aria-controls
     */
    show_page : function(page) {
      this.get_page(page).show();
    },

    /**
     * Hides the page in the pages menu so you can't navigate to the tab
     *
     * @method hide_page
     * @param {String} page Value set for aria-controls
     */
    hide_page : function(page) {
      this.get_page(page).hide();
    }
  }
);

fullctl.application.ContainerApplication = $tc.extend(
	"ContainerApplication",
	{
    init_container : function(ref_tag, ref_tag_p) {

      this[ref_tag_p] = this.containers = {}
      this[ref_tag+"_slugs"] = this.container_slugs = {}

      var selector_name = "select_"+ref_tag;

      this.selector_name = selector_name;
      this.title_base = window.document.title;

      this.$c.toolbar.widget(selector_name, ($e) => {
        var e = $e[selector_name];
        var w = new twentyc.rest.Select(e);
        $(w).on("load:after", (event, element, data) => {
          var i;
          for(i = 0; i < data.length; i++) {
            this.containers[data[i].id] = data[i];
            this.container_slugs[data[i].id] = data[i].slug;
          }

          if(data.length == 0) {
            e.attr('disabled', true);
            $(this).trigger("no-containers", []);
            this.permission_ui();
          } else {
            e.attr('disabled', false)
            this.permission_ui();
          }
        });
        return w

      });

      $(this.$c.toolbar.$w[selector_name]).one("load:after", () => {

        if(this["preselect_"+ref_tag]) {
          this[selector_name](this["preselect_"+ref_tag])
        } else {
          this.sync();
          this.sync_url(this.$c.toolbar.$e[selector_name].val());
          this.sync_title(this.$c.toolbar.$e[selector_name].val());
        }
      });

      $(this.$c.toolbar.$e[selector_name]).on("change", () => {
        this.sync();
        this.sync_url(this.$c.toolbar.$e[selector_name].val())
        if(this.$t.settings) { this.$t.settings.sync(); }
      });

      this[ref_tag] = function() { return this.container(); }.bind(this);
      this[ref_tag+"_slug"] = function() { return this.container_slug(); }.bind(this);
      this[ref_tag+"_object"] = function() { return this.container_object(); }.bind(this);
      this["unload_"+ref_tag] = function() { return this.unload_container(); }.bind(this);
      this["select_"+ref_tag] = function(id){ return this.select_container(id); }.bind(this);
      this["refresh_select_"+ref_tag] = function() { return this.refresh_select_container(); }.bind(this);

    },

    permission_ui : function () { return; },

    container : function() {
      return this.$c.toolbar.$w[this.selector_name].element.val();
    },

    container_slug : function() {
      return this.container_slugs[this.container()];
    },

    container_object: function() {
      return this.containers[this.container()]
    },

    unload_container : function(id) {
      delete this.containers[id];
      delete this.container_slugs[id];
    },

    select_container : function(id) {
      if(id)
        this.$c.toolbar.$e[this.selector_name].val(id);
      else {
        id = this.$c.toolbar.$e[this.selector_name].find('option').val();
        this.$c.toolbar.$e[this.selector_name].val(id);
      }

      this.sync();
      this.sync_url(id);
      this.sync_title(id);
    },

    sync_title : function(id) {
      var container = this.containers[id];
      if(container)
        window.document.title = this.title_base + " / " + container.slug;
      else
        window.document.title = this.title_base;
    },

    sync_url: function(id) {
      var container = this.containers[id];
      var url = new URL(window.location)
      if(!container) {
        $('#no-container-notify').show();
        url.pathname = `/${fullctl.org.slug}/`
      } else {
        url.pathname = `/${fullctl.org.slug}/${container.slug}/`
        $('#no-container-notify').hide();
      }
      window.history.pushState({}, '', url);
    },

    refresh : function() {
      return this.refresh_select_container();
    },

    refresh_select_container : function() {
      return this.$c.toolbar.$w[this.selector_name].refresh();
    }




	},
	fullctl.application.Application
)


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

fullctl.TemplateSelect = $tc.extend(
  "TemplateSelect",
  {
    load_params : function() {
      //to override
    }
  },
  twentyc.rest.Select
)

fullctl.TemplatePreview = $tc.extend(
  "TemplatePreview",
  {
    TemplatePreview: function(jq, select_widget, type) {
      this.Form(jq);
      this.select = new select_widget(this.element.find('select'));
      this.editor = this.element.find('textarea');
      this.type = type;

      if(type) {
        this.select.filter = (tmpl) => {
          return tmpl.type == type;
        };
      }

      $(this.select).on("load:after", ()=>{ this.preview();});
      $(this.select.element).on("change", ()=>{ this.preview();});
      $(this).on("api-write:success", (ev,ep,data,response) => {
          this.editor.val(response.first().body);
      });

      this.select.load();
    },

    payload : function() {
      return { type: this.type }
    },

    preview : function() {
      var tmpl_id = parseInt(this.select.element.val())
      if(tmpl_id)
        var url = this.editor.data("api-preview").replace("tmpl_id", tmpl_id);
      else
        var url = this.editor.data("api-preview-default").replace("type", this.type);

      this.base_url = url;

      this.submit();
    }
  },
  twentyc.rest.Form
);

$.fn.grainy_toggle = function(namespace, level) {
  if(grainy.check(namespace, level)) {
    this.show();
  } else {
    this.hide();
  }
};

})(jQuery, twentyc.cls);
