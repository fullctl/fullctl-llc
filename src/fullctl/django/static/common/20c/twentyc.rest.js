(function(twentyc, $) {

/**
 * jquery function for closest descendant
 * credit: https://stackoverflow.com/a/8962023
 */

(function($) {
    $.fn.closest_descendant = function(filter) {
        var $found = $(),
            $currentSet = this.children(); // Current place
        while ($currentSet.length) {
            $found = $currentSet.filter(filter);
            if ($found.length) break;  // At least one match: break loop
            // Get all children of the current set
            $currentSet = $currentSet.children();
        }
        return $found.first(); // Return first match of the collection
    }
})(jQuery);

/**
 * takes a jquery result and replaces all plain text occurences
 * of email addresses and urls with links
 *
 * @method replace_urls_with_links
 */

function replace_urls_with_links(jQueryResult) {
  jQueryResult.contents().filter(function() {
    return this.nodeName != "A";
  }).each(function() {
    const text = $(this).text();
    const urlRegex = /((https?:\/\/[^\s]+)|(\S+@\S+))/g;
    const html = text.replace(urlRegex, (match) => {
      const emailRegex = /\S+@\S+/;
      if (emailRegex.test(match)) {
        return `<a href="mailto:${match}">${match}</a>`;
      }
      return `<a href="${match}">${match}</a>`;
    });
    $(this).replaceWith(html);
  });
}

/**
 * namespace for twentyc.rest
 */

twentyc.rest = {

  /**
   * object holding global config
   * @property config
   * @type Object
   * @namespace twentyc.rest
   */

  config : {

    /**
     * set this to the CSRF token that should
     * be sent with write requests to the API
     * if any
     *
     * @property csrf
     * @type String
     * @namespace twentyc.rest.config
     */

    csrf : ""
  },

  /**
   * object holding URL utility functions
   * @property url
   * @type Object
   * @namespace twentyc.rest
   */

  url: {
    /**
     * Trims leading and trailing slashes from the given endpoint.
     *
     * @method trim_endpoint
     * @param {String} endpoint - The endpoint string to trim.
     * @return {String} The trimmed endpoint string.
     */
    trim_endpoint: function (endpoint) {
      // urljoin is not guaranteed to strip trailing double slashes on
      // either side of the endpoint, so we do it manually
      return endpoint.replace(/^\/+|\/+$/g, "");
    },

    /**
     * Joins URL parts, removing extra slashes at the edges of the parts.
     *
     * @method url_join
     * @param {String} left - The leftmost URL part.
     * @param {...String} args - The remaining URL parts.
     * @return {String} The joined URL string with removed extra slashes.
     */
    url_join: function (left, ...args) {
      // Simplified urljoin that gets rid of extra / at the edges
      // of parts

      let right = [];
      let trailing_slash = !twentyc.rest.no_end_slash;

      // trim left

      left = left.replace(/\/+$/g, "");

      for (const parts of args) {
        right = right.concat(
          parts
            .split("/")
            .filter((part) => part)
            .map((part) => this.trim_endpoint(part))
        );
      }

      if(!right.length)
        return trailing_slash ? `${left}/` : left;

      right = right.join("/");

      if (!left) {
        return trailing_slash ? `/${right}/` : `/${right}`;
      }

      const joinedUrl = `${left.replace(/\/$/, "")}/${right}`;

      return trailing_slash ? `${joinedUrl}/` : joinedUrl;
    }

  }

};



/**
 * Wrapper for API responses
 * @class Response
 * @constructor
 * @namespace twentyc.rest
 * @param {XHR Response} response
 * @param {Number} status
 */

twentyc.rest.Response = twentyc.cls.define(
  "Response",
  {

    Response : function(response, status) {

      if(!response || (!response.data && !response.errors) ) {
        this.status = status;
        return;
      }
      this.status = status;
      this.content = response;
    },

    /**
     * invokes a callback on each row in the api response
     * data resultset
     *
     * callback will be passed the data row as well as the index
     * of the row entry
     *
     * @method rows
     * @param {Function} callback
     */

    rows : function(callback) {
      var i;
      for(i = 0; i < this.content.data.length; i++) {
        callback(this.content.data[i], i)
      }
    },

    /**
     * returns the first row in the api response
     * data resultset
     *
     * @method first
     * @returns {Object}
     */

    first : function() {
      if(this.content && this.content.data) {
        return this.content.data[0];
      }
      return null;
    },

    /**
     * process field errors returned by the api
     * in a callback
     *
     * callback wil be invoked once for each field and
     * be passed an array of strings
     *
     * @method field_errors
     * @param {Function} callback
     */

    field_errors : function(callback) {
      if(!this.has_errors())
        return

      var key;

      if(this.content.errors.field_errors) {

        // format one, field errors are returned
        // as an array of object literals that
        // have errors and name fields

        $.each(this.content.errors.field_errors, (idx, err) => {
          callback(err.name, err.errors);
        });

      } else {

        // format two, field errors are returned
        // keyed to their field name in an object literal
        //
        // django-rest-framework format

        for(key in this.content.errors) {
          if(key == "non_field_errors")
            continue;

         callback(key, this.content.errors[key])
        }
      }
    },

    /**
     * process non-field errors returned by the api
     * in a callback
     *
     * @method non_field_errors
     * @param {Function} callback
     */

    non_field_errors : function(callback) {
      if(!this.has_errors())
        return

      var nfe = this.content.errors.non_field_errors;

      if(typeof nfe == "string")
        nfe = [nfe];

      if(nfe) {
        callback(nfe)
      }

    },

    /**
     * returns a user friendly error message for the
     * http status of the response
     *
     * @method http_status_text
     * @returns {String}
     */

    http_status_text : function() {
      if(this.status == 401) return "Unauthorized Access";
      if(this.status == 403) return "Permission Denied";
      if(this.status == 404) return "Resource not found";
      if(this.status == 405) return "Method not allowed";
      if(this.status == 429){
        if (this.content.errors.detail) return this.content.errors.detail;
        return "Request is rate limited";
      }
      if(this.status == 500) return "Internal Error";
      return "Http Error "+this.status;
    },

    /**
     * returns whether the response has error information
     * or not
     *
     * @method has_errors
     * @returns {Boolean}
     */

    has_errors : function() {
      if(this.status > 400) {
        if(!this.content)
          this.content = {}
        if(!this.content.errors)
          this.content.errors = {}

        this.content.errors.non_field_errors =  [this.http_status_text()]
      }
      return ($.isEmptyObject(this.content.errors) == false);
    }
  }
);

/**
 * Base API functionality / connection handler
 *
 * @class Client
 * @constructor
 * @namespace twentyc.rest
 * @param {String} base_url path to the api root
 */

twentyc.rest.Client = twentyc.cls.define(
  "Client",
  {
    Client : function(base_url) {
      this.base_url = base_url.replace(/\/$/g,'');

      /**
       * triggered before the request is dispatched and allows
       * for modification of the url parameters / request payload through `data`
       *
       * @event api-request:before
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {String} method request method
       */

      /**
       * triggered before the GET or OPTIONS request is dispatched and allows
       * for modification of the url parameters through `data`
       *
       * @event api-read:before
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {String} method request method
       */

      /**
       * triggered before the POST, PUT or DELETE request is dispatched and allows
       * for modification of the request payload
       *
       * @event api-write:before
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {String} method request method
       */

      /**
       * triggered before the request of the specified method is dispatched and allows
       * for modification of the url parameters
       *
       * @event api-[get|post|put|delete|options]:before
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       */

      /**
       * triggered after the request has returned
       *
       * @event api-request:after
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {String} method request method
       */

      /**
       * triggered after the GET or OPTIONS request has returned
       *
       * @event api-read:after
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {String} method request method
       */

      /**
       * triggered after the POST, PUT or DELETE request has returned
       *
       * @event api-write:after
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {String} method request method
       */


      /**
       * triggered after the request of the specified method has returned
       *
       * @event api-[get|post|put|delete|options]:after
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       */

      /**
       * triggered if the request returned with a succesful http status
       *
       * @event api-request:success
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {twentyc.rest.Response} response
       * @param {String} method request method
       */

      /**
       * triggered if the GET or OPTIONS request returned with a succesful http status
       *
       * @event api-read:success
       * @param {string} endpoint the api endpoint to be requested
       * @param {object} data request payload
       * @param {twentyc.rest.response} response
       * @param {string} method request method
       */

      /**
       * triggered if the POST, PUT or DELETE  request returned with a succesful http status
       *
       * @event api-write:success
       * @param {string} endpoint the api endpoint to be requested
       * @param {object} data request payload
       * @param {twentyc.rest.response} response
       * @param {string} method request method
       */

      /**
       * triggered if the request of the specified method returned with a succesful http status
       *
       * @event api-[get|post|put|delete|options]:success
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {twentyc.rest.Response} response
       */

      /**
       * triggered if the request returned with an error http status
       *
       * @event api-request:error
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {twentyc.rest.Response} response
       * @param {String} method request method
       */

      /**
       * triggered if the GET or OPTIONS request returned with an error http status
       *
       * @event api-read:error
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {twentyc.rest.Response} response
       * @param {String} method request method
       */

      /**
       * triggered if the POST, PUT or DELETE request returned with an error http status
       *
       * @event api-write:error
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {twentyc.rest.Response} response
       * @param {String} method request method
       */

      /**
       * triggered if the request of the specified method returned with an error http status
       *
       * @event api-[get|post|put|delete|options]:error
       * @param {String} endpoint the api endpoint to be requested
       * @param {Object} data request payload
       * @param {twentyc.rest.Response} response
       */

    },

    /**
     * returns path to endpoint by appending
     * provided value to the api root base url
     * @method endpoint_url
     * @param {String} endpoint
     */

    endpoint_url : function(endpoint) {
      if(!endpoint)
        return twentyc.rest.url.url_join(this.base_url);

      return twentyc.rest.url.url_join(this.base_url, endpoint);
    },

    /**
     * Encodes and object literal to json
     * @method encode
     * @param {Object} data
     * @returns {String}
     */

    encode : function(data) {
      return JSON.stringify(data);
    },

    format_request_url : function(url, method) {
      return url;
    },

    /**
     * Perform a read request (GET, HEAD, OPTIONS) on the api
     *
     * @method read
     * @param {String} endpoint api endpoint
     * @param {Object} data url parameters to pass
     * @param {String} method http request method (GET, HEAD or OPTIONS)
     * @returns {Promise}
     */

    read : function(endpoint, data, method) {
      method = method.toLowerCase()

      $(this).trigger("api-request:before", [endpoint,data,method])
      $(this).trigger("api-read:before", [endpoint,data,method])
      $(this).trigger("api-"+method+":before", [endpoint,data])
      var request = new Promise(function(resolve, reject) {
        $.ajax({
          method : method.toUpperCase(),
          data : data,
          url : this.format_request_url(this.endpoint_url(endpoint), method),
        }).done(function(result) {
          var response = new twentyc.rest.Response(result);
          $(this).trigger("api-request:success", [endpoint, data, response, method]);
          $(this).trigger("api-read:success", [endpoint, data, response, method]);
          $(this).trigger("api-"+method+":success", [endpoint, data, response]);
          resolve(response);
        }.bind(this)).fail(function(e) {
          var response = new twentyc.rest.Response(e.responseJSON);
          $(this).trigger("api-request:error", [endpoint, data, response, method]);
          $(this).trigger("api-read:error", [endpoint, data, response, method]);
          $(this).trigger("api-"+method+":error", [endpoint, data, response]);
          reject(response);
        }.bind(this)).always(function(e) {
          $(this).trigger("api-request:after", [endpoint, data, method]);
          $(this).trigger("api-read:after", [endpoint, data, method]);
          $(this).trigger("api-"+method+":after", [endpoint, data]);
        }.bind(this));
      }.bind(this));

      return request;
    },

    /**
     * Perform a write request (POST, PUT, PATCH, DELETE) on the api
     *
     * @method write
     * @param {String} endpoint api endpoint
     * @param {Object} data payload
     * @param {String} method http request method
     * @returns {Promise}
     */

    write : function(endpoint, data, method, url = null) {
      url = url || this.endpoint_url(endpoint);
      method = method.toLowerCase();

      $(this).trigger("api-request:before", [endpoint,data,method])
      $(this).trigger("api-write:before", [endpoint,data,method])
      $(this).trigger("api-"+method+":before", [endpoint,data])
      var request = new Promise(function(resolve, reject) {
        $.ajax({
          dataType : "json",
          method : method.toUpperCase(),
          url : this.format_request_url(url, method),
          data : this.encode(data),
          headers : {
            "Content-Type" : "application/json",
            "X-CSRFToken" : twentyc.rest.config.csrf
          },
        }).done(function(result) {
          var response = new twentyc.rest.Response(result);
          $(this).trigger("api-request:success", [endpoint, data, response, method]);
          $(this).trigger("api-write:success", [endpoint, data, response, method]);
          $(this).trigger("api-"+method+":success", [endpoint, data, response]);
          resolve(response);
        }.bind(this)).fail(function(e) {
          var response = new twentyc.rest.Response(e.responseJSON, e.status);
          $(this).trigger("api-request:error", [endpoint, data, response, method]);
          $(this).trigger("api-write:error", [endpoint, data, response, method]);
          $(this).trigger("api-"+method+":error", [endpoint, data, response]);
          reject(response);
        }.bind(this)).always(function(e) {
          $(this).trigger("api-request:after", [endpoint, data, method]);
          $(this).trigger("api-write:after", [endpoint, data, method]);
          $(this).trigger("api-"+method+":after", [endpoint, data]);
        }.bind(this));
      }.bind(this));

      return request;
    },

    /**
     * Wrapper to perform a `GET` request on the api
     *
     * @method get
     * @param {String} endpoint
     * @param {Object} params url parameters
     * @returns {Promise}
     */

    get : function(endpoint, params) {
      return this.read(endpoint, params, "get");
    },

    /**
     * Wrapper to perform a `OPTIONS` request on the api
     *
     * @method options
     * @param {String} endpoint
     * @param {Object} params url parameters
     * @returns {Promise}
     */

    options : function(endpoint, params) {
      return this.read(endpoint, params, "options");
    },

    /**
     * Wrapper to perform a `POST` request on the api
     *
     * @method post
     * @param {String} endpoint
     * @param {object} data payload
     * @returns {Promise}
     */

    post : function(endpoint, data) {
      return this.write(endpoint, data, "post");
    },

    /**
     * Wrapper to perform a `PUT` request on the api
     *
     * @method post
     * @param {String} endpoint
     * @param {object} data payload
     * @returns {Promise}
     */

    put : function(endpoint, data) {
      return this.write(endpoint, data, "put");
    },

    /**
     * Wrapper to perform a `DELETE` request on the api
     *
     * @method post
     * @param {String} endpoint
     * @param {object} data payload
     * @returns {Promise}
     */


    delete : function(endpoint, data) {
      return this.write(endpoint, data, "delete");
    }
  }
);

/**
 * Base class for API widgets
 *
 * @class Widget
 * @extends twentyc.rest.Client
 * @namespace twentyc.rest
 * @constructor
 * @param {String} base_url api root
 * @param {jQuery result} jq jquery result holding the main element of the widget
 */

twentyc.rest.Widget = twentyc.cls.extend(
  "Widget",
  {
    Widget : function(base_url, jq) {
     this.action = jq.data("api-action")

     /**
      * allows you to define local actions (experimental)
      * @property {Object} local_actions
      */
     this.local_actions = {};
     this.formatters = {};
     this.Client(base_url);
     this.bind(jq);
    },

    /**
     * Sets the widget state to processing
     *
     * This will trigger the `processing` event
     *
     * @method start_processing
     */

    start_processing : function() {
      this.busy = true
      if(!this.loading_shim) {
        this.loading_shim = $('<div>').addClass("loading-shim")
        this.element.append(this.loading_shim);
      }
      if(!this.loading_shim_disabled)
        this.loading_shim.show();

      $(this).trigger("processing");
    },


    /**
     * Sets the widget state to ready or done with processing
     *
     * This will trigger the `ready` event
     *
     * @method done_processing
     */

    done_processing : function() {
      this.busy = false
      if(this.loading_shim && !window.debug_loading_shim)
        this.loading_shim.hide();
      $(this).trigger("ready");
    },

    /**
     * Clones a template element by name and returns it
     *
     * Templates for a widget should be stored within an element inside
     * the widget that has it's `.templates` css class set
     *
     * A template is designated a template if it has the
     * `data-template` attribute set to hold the template name
     *
     * ```html
     * <div class="widget">
     *  <div class="templates">
     *    <div data-template="my_template"></div>
     *  </div>
     * </div>
     * ```
     *
     * ```javascript
     * var tmpl = widget.template('my_template')
     * ```
     *
     * @method template
     * @param {String} name template name (as specified in data-template)
     * @returns {jQuery result} jquery result holding the cloned template node
     */

    template : function(name) {
      var tmpl = this.element.closest_descendant('.templates').find('[data-template="'+name+'"]')
      var clone = tmpl.clone().attr('data-template', null);
      return clone;
    },

    /**
     * Binds the widget to a html element
     *
     * @method bind
     * @param {jQuery result} jq jquery result holding the html element
     */

    bind : function(jq) {
      jq.data("rest_widget", this);
      this.element = jq;

      this.redirect = this.element.data("api-redirect")

      $(this).on("api-write:before", function() {
        this.clear_errors();
        this.start_processing();
      }.bind(this));

      $(this).on("api-write:after", function() {
        this.done_processing();
      }.bind(this));

      $(this).on("api-read:before", function() {
        this.start_processing();
      }.bind(this));

      $(this).on("api-read:after", function() {
        this.done_processing();
      }.bind(this));
    },

    /**
     * Defines a local action that some widget's
     * may invoke
     *
     * Local actions can be set on the widget element or sub elements
     * via the `data-action` attribute
     *
     * @method local_action
     * @param {String} name action name
     * @param {Function} fn
     */

    local_action : function(name, fn) {
      this.local_actions[name] = fn;
    },

    /**
     * Clears all validation / input errors for the widget
     *
     * @method clear_errors
     */

    clear_errors : function() {
      this.element.find('.validation-error').detach();
      this.element.find('.validation-error-indicator').removeClass("validation-error-indicator");
    },

    /**
     * Renders field errors (think input vaidation errors)
     *
     * @method render_error
     * @param {String} key field name
     * @param {Array} errors list of error strings
     */

    render_error : function(key, errors) {
      if(!errors)
        return;
      var i;
      var error_node = $('<div>').addClass("validation-error");
      var input = this.element.find('[name="'+key+'"]');
      input.addClass("validation-error-indicator")
      for(i = 0; i < errors.length; i++) {
        error_node.append($('<p>').text(errors[i]))
      }
      if(input.attr("type") != "checkbox")
        error_node.insertAfter(input);
    },

    /**
     * Renders non field errors (think server errors, generic errors)
     *
     * @method render_non_field_errors
     * @param {Array} errors list of error strings
     */

    render_non_field_errors : function(errors) {
      var error_node = $('<div>').addClass("alert alert-danger validation-error non-field-errors");
      let i;
      for(i = 0; i < errors.length; i++) {
        $(twentyc.rest).trigger("non-field-error", [errors[i], errors, i, error_node, this]);
        if(errors[i])
          error_node.append($('<div>').addClass("non-field-error").text(errors[i]));
      }

      replace_urls_with_links(error_node);

      this.element.prepend(error_node);
    },

    /**
     * Prepares the payload for the widget's write request
     * by checking for form elements and converting their values
     * to an object literal compatible to be sent as a payload
     *
     * @method payload
     * @returns {Object}
     */

    payload : function() {
      var data = {};
      this.element.find('[data-api-submit="yes"]').each(function() {
        $(this).find("input,select,textarea").each(function() {
          var input = $(this)
          if(input.attr("type") == "checkbox") {
            if(input.prop("checked"))
              data[input.attr("name")] = true;
            else
              data[input.attr("name")] = false;
          } else {
            if (input.data("type") == "int") {
              data[input.attr("name")] = parseInt(input.val());
            } else if(input.data("type") == "bool") {
              data[input.attr("name")] = (input.val().toLowerCase() == "true" ?  true : false);
            } else {
              data[input.attr("name")] = input.val();
            }
          }

          // treat blank values as null where necessary

          if(input.data("blank-as-null") == "yes" && input.val() == "") {
            data[input.attr("name")] = null;
          }
        });
      });

      $(this).trigger("payload:after", [data]);

      return data;

    },

    /**
     * Applies data to the element of the widget assiging it
     * to elements that have data-field attributes
     * set
     *
     * Fires the `apply_data:before` event
     *
     * @method apply_data
     * @param k
     * @param data
     */

    apply_data : function(data, element) {

      $(this).trigger("apply_data:before", [data]);

      if(!element)
        element = this.element;

      var k, tag, val, formatter;
      for(k in data) {
        var formatter = this.formatters[k];
        var col_element = element.find('[data-field="'+k+'"]');

        if(col_element.length)
          tag = col_element.get(0).tagName.toLowerCase();

        var toggle = col_element.data("toggle");

        if(toggle) {
          if(data[k]) {
            col_element.addClass(toggle);
          } else {
            col_element.removeClass(toggle);
          }
        } else if(!formatter) {
          if(tag == "select" || tag == "input" || tag == "textarea") {
            if(col_element.attr("type") == "checkbox") {
              col_element.prop("checked", data[k]);
            } else {
              col_element.val(data[k]);
            }
          } else {
            col_element.text(data[k]).val(data[k])
          }
        } else {
          val = formatter(data[k], data, col_element)
          col_element.empty().append(val)
        }
      }
    }

  },
  twentyc.rest.Client
);

/**
 * Form widget that binds a HTML form to the REST api
 *
 * The form element should have the following attributes set
 *
 * # required
 *
 * - data-api-base: api root or full path to endpoint
 *
 * # optional
 *
 * - data-api-action: if specified will be appended as endpoint to data-api-base
 * - data-api-method: request method for writes, defaults to POST
 * - data-submit-inline: if "yes" input elements will be wired to submit form data
 *   when they detect change
 *
 * If the form element contains a button element with the
 * `submit` css class set it will be wired to submit the form
 * on click
 *
 * Input type elements (`<input>`, `<textarea>`, etc.,) will be collected into
 * the payload as long as they are nested inside a parent element that has
 * the `data-api-submit="yes"` attribute set.
 *
 * # example
 *
 * ```html
 * <form data-api-base="/api/add-object">
 *   <div data-api-submit="yes">
 *     <input type="text" name="name">
 *   </div>
 *   <div>
 *     <button class="submit">Add object</button>
 *   </div>
 * </form>
 * ```
 *
 * @class Form
 * @extends twentyc.rest.Widget
 * @namespace twentyc.rest
 * @constructor
 * @param {jQuery result} jq jquery result holding the form element
 */

twentyc.rest.Form = twentyc.cls.extend(
  "Form",
  {
    Form : function(jq) {
      var base_url = jq.data("api-base");
      this.form_action = jq.data("api-action");
      this.submit_inline = jq.data("submit-inline") == "yes";
      this.Widget(base_url, jq);
    },

    /**
     * Fill the form fields from values provided in
     * an object literal thats keyed by field name
     *
     * Names in `data` will be matched against the `name` attribute
     * of the form inputs
     *
     * For elements that you want to skip you can set the `data-constant="yes"`
     * attribute.
     *
     * @method fill
     * @param {Object} data
     */

    fill : function(data) {
      var key, value;
      this.clear_errors();
      for(key in data) {
        value = data[key];
        this.element.find('[name="'+key+'"]').each(function() {

          if($(this).data("constant") == "yes") {
            return;
          }

          if($(this).attr("type") == "checkbox") {
            $(this).prop("checked", value);
          } else {
            $(this).val(value);
          }
        });

        this.element.find('[data-field="'+key+'"]').each(function() {
          $(this).text(value);
        });
      }
    },


    reset : function() {
      var k ,empty = {};
      for(k in this.payload()) {
        empty[k] = ""
      }
      this.fill(empty);
    },

    post_success : function(result) {

    },

    post_failure : function(response) {
      response.field_errors(this.render_error.bind(this));
      response.non_field_errors(this.render_non_field_errors.bind(this))
    },

    /**
     * Submit the form using the specified method
     *
     * @method submit
     * @param {String} method http request method
     */

    submit : function(method) {
      this.clear_errors();

      if(!method)
        method = this.method

      var fn = this[method.toLowerCase()].bind(this);
      fn(this.form_action, this.payload()).then(
        this.post_success.bind(this),
        this.post_failure.bind(this)
      );
    },

    /**
     * Binds the form widget to a html element
     *
     * This is called automatically in the constructor
     *
     * @method bind
     * @param {jQuery result} jq
     */

    bind : function(jq) {
      this.Widget_bind(jq);
      this.method = jq.data("api-method") || "POST";

      this.element.find('input').keydown(function(event){
        if(event.keyCode == 13) {
          event.preventDefault();
          this.submit();
          return false;
        }
      }.bind(this));

      var widget = this;


      this.element.find('button').click(function(event) {
        event.preventDefault();
        return false;
      });

      this.element.find('button.submit,button[data-element="submit"]').click(function(event) {
        event.preventDefault();
        widget.submit(
          $(this).data("api-method")
        );
        return false;
      });

      if(this.submit_inline) {
        this.wire_inline_submit();
      }
    },

    /**
     * Wires the form for inline submitting where
     * Input elements will submit the form after they detect changes
     *
     * This is called automatically if the form element has the `data-submit-inline="yes"`
     * attribute.
     *
     * @method wire_inline_submit
     */

    wire_inline_submit : function() {
      var widget = this;
      var timer = new twentyc.util.SmartTimeout(()=>{},100);
      var submit_handler = function(ev) {
        console.log(ev);
        $(widget).one("api-write:success", () => {
          $(this).removeClass("saving").addClass("saved");
        });
        timer.set(() => {
          $(this).addClass("saving").removeClass("saved");
          widget.submit(this.method);
        }, ev.type == "keyup" ? 500 : 100);
      };

      this.element.find('input,textarea,select').each(function() {
        var input = $(this);
        var tag = this.tagName.toLowerCase();
        if(tag == "select" || input.attr("type") == "checkbox") {
          input.on("change", submit_handler);
        } else {
          input.on("keyup", submit_handler);
        }
      });

    },

    /**
     * Wires a button to submit the form
     *
     * @method wire_submit
     * @param {jQuery result} jq_button jquery result holding button element
     */

    wire_submit : function(jq_button) {
      var widget = this;
      jq_button.off("click").click(function() {
        widget.submit(this.method)
      });
    }
  },
  twentyc.rest.Widget
);

/**
 * Base input widget class
 *
 * # required
 *
 * - data-api-base: api root or full path to endpoint
 *
 * @class Button
 * @extends twentyc.rest.Widget
 * @namespace twentyc.rest
 * @param {jQuery result} jq jquery result holding the target element
 */



twentyc.rest.Input = twentyc.cls.extend(
  "Input",
  {
    Input : function(jq) {
      var base_url = jq.data("api-base");
      this.Widget(base_url, jq);
    },

    /**
     * Sets the widget state to processing
     *
     * This will trigger the `processing` event
     *
     * @method start_processing
     */

    start_processing : function() {
      this.busy = true
      this.element.prop("disabled", true);
      $(this).trigger("processing");
    },


    /**
     * Sets the widget state to ready or done with processing
     *
     * This will trigger the `ready` event
     *
     * @method done_processing
     */

    done_processing : function() {
      this.busy = false
      this.element.prop("disabled", false);
      $(this).trigger("ready");
    },


    post_success : function(result) {

    },

    post_failure : function(response) {
      console.error(response);
      response.field_errors(this.render_error.bind(this));
      response.non_field_errors(this.render_non_field_errors.bind(this))
    },


    bind : function(jq) {
      this.Widget_bind(jq);
      this.method = jq.data("api-method") || "POST";

      this.element.on("keyup", function(ev) {
        this.clear_errors();

        if(ev.which != 13)
          return;

        var action = this.action;
        var fn = this[this.method.toLowerCase()].bind(this);

        fn(action, this.payload()).then(
          this.post_success.bind(this),
          this.post_failure.bind(this)
        );
      }.bind(this));
    },

    val : function(v) {
      return this.element.val(v);
    }

  },
  twentyc.rest.Widget
);

/**
 * Checkbox widget
 *
 * Wires a html element (input type="checkbox") to the API
 *
 * The select element should have the following attributes set
 *
 * # required
 *
 * - data-api-base: api root or full path to endpoint
 *
 * @class Button
 * @extends twentyc.rest.Input
 * @namespace twentyc.rest
 * @param {jQuery result} jq jquery result holding the button element
 */


twentyc.rest.Checkbox = twentyc.cls.extend(
  "Checkbox",
  {
    payload : function() {
      var pl = {};
      pl[this.element.attr('name')] = (this.element.prop("checked") ? true : false);
      return pl;
    },
    bind : function(jq) {
      this.Widget_bind(jq);
      this.method = jq.data("api-method") || "POST";

      this.element.on("change", function(ev) {

        var confirm_required = this.element.data("confirm");
        if(confirm_required && !confirm(confirm_required))
          return;

        this.clear_errors();

        var action = this.action;
        var fn = this[this.method.toLowerCase()].bind(this);

        fn(action, this.payload()).then(
          this.post_success.bind(this),
          this.post_failure.bind(this)
        );
      }.bind(this));

    }
  },
  twentyc.rest.Input
);


/**
 * Button widget
 *
 * Wires a html element (typically `<a>` or `<button>` to the API
 *
 * The select element should have the following attributes set
 *
 * # required
 *
 * - data-api-base: api root or full path to endpoint
 *
 * @class Button
 * @extends twentyc.rest.Input
 * @namespace twentyc.rest
 * @param {jQuery result} jq jquery result holding the button element
 */


twentyc.rest.Button = twentyc.cls.extend(
  "Button",
  {
    bind : function(jq) {
      this.Widget_bind(jq);
      this.method = jq.data("api-method") || "POST";

      /**
       * which input event to bind to, defaults to 'mouseup'
       * @property bind_to_event
       * @type String
       */

      var bind_to_event = (this.bind_to_event || "mouseup")

      this.element.on( bind_to_event , function(ev) {

        var confirm_required = this.element.data("confirm");
        if(confirm_required && !confirm(confirm_required))
          return;

        this.clear_errors();

        var action = this.action;
        var fn = this[this.method.toLowerCase()].bind(this);

        fn(action, this.payload()).then(
          this.post_success.bind(this),
          this.post_failure.bind(this)
        );
      }.bind(this));

    }
  },
  twentyc.rest.Input
);

/**
 * Wires a `select` element to the API
 *
 * The select element should have the following attributes set
 *
 * # required
 *
 * - data-api-base: api root or full path to endpoint
 *
 * # optional
 *
 * - data-api-load: set to "yes" to load data
 * - data-name-field: which data resultset field to use for option text,
 *   defaults to "name"
 * - data-id-field: which data resultset field to use for option value,
 *   defaultd to "id"
 * - data-selected-field: which data resultset field to check whether and option
 *   should be auto-selected, defaults to "selected"
 * - data-load-type: what load method to use, can be "get" or "drf-choices",
 *   with the latter being a way to load in django-rest-framework field values
 *   choices. Defaults to "get"
 * - data-drf-name: relevant if load type is "drf-choices". Specifies the
 *   serializer field name, will default to "name" attribute if not specified.
 * - data-null-option: specify to add a "empty" value option with a label
 *
 * @class Select
 * @extends twentyc.rest.Input
 * @namespace twentyc.rest
 * @constructor
 * @param {jQuery result} jq jquery result holding the select element
 */

twentyc.rest.Select = twentyc.cls.extend(
  "Select",
  {
    Select : function(jq) {
      this.load_action = jq.data("api-load")
      this.name_field = jq.data("name-field") || "name"
      this.id_field = jq.data("id-field") || "id"
      this.selected_field = jq.data("selected-field") || "selected"
      this.load_type = jq.data("load-type") || "get"
      this.drf_name = jq.data("drf-name") || jq.attr("name");
      this.null_option = jq.data("null-option")
      this.proxy_data = jq.data("proxy-data")
      this.Input(jq);
    },

    payload: function() {
      return { "id": this.element.val() }
    },

    load_params : function() {
      return null;
    },

    filter : function(item) {
      return true;
    },


    /**
     * loads options from the api
     *
     * this will call _load_get or _load_drf_choices depending
     * on which load-type is specified (see data-load-type attribute)
     *
     * triggers load:after event
     *
     * @method load
     * @param {Mixed} select_this if specified will select this value after
     *   load
     */

    load : function(select_this) {

      if(this.proxy_data) {
        var select = this.element;
        select.empty();

        if(this.null_option) {
          let null_parts = this.null_option.split(";");
          select.append($('<option>').val(null_parts[0]).text(null_parts[1]));
        }

        $(this.proxy_data).find('option').each(function() {
          select.append($(this).clone());
        });
        $(this).trigger("load:after", [select, {}, this]);
        return new Promise((resolve, reject) => {
          resolve();
        });
      }

      if(this.load_type == "drf-choices")
        return this._load_drf_choices(select_this);

      return this._load_get(select_this);

    },

    /**
     * loads data in via a GET request
     *
     * expects data to come back as a list of object literals
     * containing keys for `this.name_field` and `this.id_field`
     *
     * this method is called automatically by `this.load` if the
     * the load-type of the select widget is set to "get"
     *
     * Example assuming this.name_field == 'name' and this.id_field = 'id'
     *
     * {
     *   "data": [
     *     { "name": "Choice 1", "id": 1 },
     *     { "name": "Choice 2", "id": 2 }
     *   ]
     * }
     *
     * @method _load_get
     * @private
     * @param {Mixed} select_this if specified will select this value after
     *   load
     */

    _load_get : function(select_this) {


      return this.get(null, this.load_params()).then(function(response) {
        var select = this.element;
        var name_field = this.name_field
        var id_field = this.id_field
        var selected_field = this.selected_field
        var widget = this;

        var old_val = select.val();

        select.empty();

        if(this.null_option) {
          let null_parts = this.null_option.split(";");
          select.append($('<option>').val(null_parts[0]).text(null_parts[1]));
        }


        $(response.content.data).each(function() {
          if(!widget.filter(this))
            return;
          var selected = this[selected_field] || false;
          var opt = $('<option>').val(this[id_field]).text(this[name_field])
          if(selected)
            opt.attr("selected", true);
          select.append(opt);
        });

        if(select_this) {
          select.val(select_this);
          if(select_this != old_val)
            select.trigger("change", []);
        }

        $(this).trigger("load:after", [select, response.content.data, this]);
      }.bind(this));
    },

    /**
     * loads data in via a OPTIONS request to a django-rest-framework
     * api endpoint
     *
     * this method is called automatically by `this.load` if the
     * the load-type of the select widget is set to "drf_choices"
     *
     * @method _load_drf_choices
     * @private
     * @param {Mixed} select_this if specified will select this value after
     *   load
     */

    _load_drf_choices : function(select_this) {
      return this.options().then(function(response) {
        var select = this.element.empty();
        var options = response.content.data[0].actions.POST[this.drf_name].choices;

        if(this.null_option) {
          let null_parts = this.null_option.split(";");
          select.append($('<option>').val(null_parts[0]).text(null_parts[1]));
        }


        $(options).each(function() {
          select.append(
            $('<option>').val(this.value).text(this.display_name)
          )
        });

        if(select_this)
          select.val(select_this);

      }.bind(this));
    },

    /**
     * refreshes options from the api
     *
     * this is the same as load, but will maintain the current
     * selection choice as long as it still exists in the the
     * fresh dataset
     *
     * @method refresh
     */

    refresh : function() {
      var val = this.element.val()
      return this.load().then(
       () => { this.element.val(val); },
       () => {}
      );
    },

    prepare_write_url : function(url) {
      return url;
    },


    bind : function(jq) {
      this.Widget_bind(jq);
      this.method = jq.data("api-method") || "POST";

      if(this.load_action)
        this.load();

      this.element.on("change", function() {
        this.clear_errors();

        if(!this.action)
          return;

        var action = this.action;
        var fn = this[this.method.toLowerCase()].bind(this);

        fn(action, this.payload()).then(
          this.post_success.bind(this),
          this.post_failure.bind(this)
        );
      }.bind(this));
    }
  },
  twentyc.rest.Input
);

/**
 * Data listing widget
 *
 * A way to visualize an api data response in a table
 *
 * # element attributes
 *
 * This widget element should have these html attributes set
 *
 * ## required
 *
 * - data-api-base: api root or full path to endpoint
 *
 * ## optional
 *
 * - data-api-action: if specified will be appended as endpoint to data-api-base
 *
 * # DOM structure
 *
 * The widget element should contain the following child elements
 *
 * - element with `list-body` css class, which will serve as a
 *   container for rows, if your widget element is a table this
 *   would be a tbody element.
 * - element with data-template="row" attr set, which will be used
 *   to clone for individual rows
 *
 *   within the row element, child elements will be scanned for
 *   data-field attributes to match against the field names in the api
 *   result set.
 *
 * # Example
 *
 * ```json
 * {
 *   "data": [
 *      { "id": 1, "name": "first row" },
 *      {" id": 2, "name": "second row" }
 *   ]
 * }
 * ```
 *
 * ```html
 * <table data-api-base="/api/my_list" id="my_list">
 *  <tbody class="list-body"></tbody>
 *  <tbody class="templates">
 *    <tr data-template="row">
 *      <td data-field="id"></td>
 *      <td data-field="name"></td>
 *    </tr>
 *  </tbody>
 * </table>
 * ```
 *
 * ```javascript
 * var list = new twentyc.rest.List($('#my_list'))
 * list.load();
 * ```
 *
 * # Example: wiring a delete button
 *
 * One of the most common things to add to a list is a delete button
 * for each row.
 *
 * ```html
 * <td>
 *   <button data-api-action="{id}" data-api-callback="remove" data-api-method="DELETE"></button>
 * </td>
 * ```
 *
 * `{id}` will be replaced by the value of `object.id` where `object` is the object
 * represented by the row.
 *
 * the value of `data-api-action` on the row will be joined to the list's `data-api-base` value.
 *
 *
 * @class List
 * @extends twentyc.rest.Widget
 * @namespace twentyc.rest
 * @constructor
 * @param {jQuery result} jq jquery result holding widget element (table)
 */

twentyc.rest.List = twentyc.cls.extend(
  "List",
  {
    List : function(jq) {
      var base_url = jq.data("api-base")

      this.id_field = "id"
      this.formatters = {}

      this.Widget(base_url, jq);
      this.list_head = this.element.find('thead,.list-header').first();
      this.initialize_sorting();
    },

    /**
     * loads rows into the list
     *
     * this empties all current rows before it does so
     *
     * triggers load:after event
     *
     * @method load
     */

    load : function() {
      if(this.sortable)
        this.apply_ordering();

      return this.get(this.action, this.payload()).then(function(response) {
        this.list_body.empty()
        response.rows(function(row, idx) {
          this.insert(row);
        }.bind(this));
        $(this).trigger("load:after", [response]);
        return
      }.bind(this));
    },

    /**
     * calls load() until the list is no longer empty
     * will pause for the specified delay after a load attempt
     *
     * @method load
     * @param {Number} delay pause (ms)
     * @param {Function} condition - if specified will be called to
     *   determine if another aload attempt should be made. The function
     *   should return true for yes, and false for no
     */

    load_until_data : function(delay, condition) {
      this.load().then(() => {
        if(this.element.find('.list-body').is(':empty')) {

          if(condition && !condition())
            return

          setTimeout(() => {
            this.load_until_data(delay, condition);
          }, delay);
        }
      });
    },

    /**
     * reload single row
     *
     * @method reload_row
     * @param {Mixed} id
     */

    reload_row : function(id) {
      var row = this.find_row(id);
      if(row) {
        return this.get(id, this.payload()).then(function(response) {
          var new_row = this.insert(response.first())
          new_row.insertAfter(row);
          row.detach();
        }.bind(this));
      }
    },

    /**
     * Builds the html elements for a row in the list
     *
     * Note this does not fill in any data by itself and is called
     * automatically by the `insert` method.
     *
     * Override this if you need to dynamically control how
     * a the row elements are built, for example if you want to
     * do different rows for different object types
     *
     * @method build_row
     * @param {Object} data
     * @returns {jQuery} row element
     */

    build_row : function(data) {
      return this.template('row');
    },

    /**
     * insert a new row from object
     *
     * triggers insert:after event
     *
     * @method insert
     * @param {Object} data
     */

    insert : function(data) {
      var row_element;

      row_element = this.build_row(data);

      this.apply_data(data, row_element);

      if(this.formatters.row)
        this.formatters.row(row_element, data)

      row_element.data("apiobject", data);
      row_element.addClass("row-"+data[this.id_field])

      this.list_body.append(row_element)
      this.wire(row_element)

      $(this).trigger("insert:after", [row_element, data]);

      return row_element;
    },

    api_callback_remove : function(response) {
      response.rows(function(row) {
        this.remove(row)
      }.bind(this));
    },

    /**
     * Removes the row for the supplied api response row object
     *
     * @method remove
     * @param {Object} data
     */

    remove : function(data) {
      $(this).trigger("remove:before", [data]);
      this.list_body.find('.row-'+data[this.id_field]).detach();
    },

    /**
     * return row element for object id
     *
     * @method find_row
     * @param {String} id
     * @returns {jQuery result}
     */

    find_row : function(id) {
      return this.list_body.find('.row-'+(""+id).replace(':','\\:'));
    },

    action_failure : function(response) {
      response.field_errors(this.render_error.bind(this));
      response.non_field_errors(this.render_non_field_errors.bind(this))
    },

    wire : function(row) {
      var widget = this;

      row.find('a[data-action]').click(function() {
        var actionName = $(this).data("action")
        if(widget.local_actions[actionName]) {
          widget.local_actions[actionName](row.data("apiobject"), row);
        }
      });

      row.find('a[data-api-action], button[data-api-action]').each(function() {
        var method = ($(this).data("api-method") || "POST").toLowerCase();
        var action = $(this).data("api-action").toLowerCase();
        var callback = $(this).data("api-callback");
        var callback_name = $(this).data("api-callback");
        var confirm_set = $(this).data("confirm")

        if(callback)
          callback = widget["api_callback_"+callback].bind(widget)

        $(this).click(function() {
          if(confirm_set && !confirm(confirm_set))
            return;
          var apiobj = row.data("apiobject")
          var _action = action.replace(
            /\{([^\{\}]+)\}/,
            (match, p1, offset, string) => {
              return apiobj[p1];
            }
          )
          widget[method](_action, row.data("apiobject")).then(
            callback, widget.action_failure.bind(widget)
          ).then(
            $(widget).trigger("api_callback_"+callback_name+":after")
          );
        });
      });
    },

    bind : function(jq) {
      this.Widget_bind(jq);

      this.list_body = jq.find(".list-body")
    },

    payload : function() {
      if(this.ordering) {
        return { ordering: this.ordering };
      }
      return {};
    },

    /**
     * initializes list for sorting
     *
     * TODO: docs / example
     *
     * @method initliaze_sorting
     */

    initialize_sorting: function() {
      var widget = this;

      this.sort_headings = this.list_head.find('[data-sort-target]');
      this.sortable = (this.sort_headings.length > 0);

      if(!this.sortable)
        return;

      this.sort_headings.click(function (){
        var button = $(this)
        widget.sort(button.data("sort-target"), button.data("sort-secondary"));
      });

      let sort_button = this.sort_headings.filter("[data-sort-initial]");
      this.sort_target = sort_button.data("sort-target");
      this.sort_secondary = sort_button.data("sort-secondary");

      this.sort_asc = true;
      this.ordering = "";

      /*
      Specific to django-rest-framework: we add "ordering" as a query
      parameter to the API calls
      */
      this.payload = function(){return {ordering: this.ordering};};
    },

    sort: function(target, secondary) {
      this.sort_secondary = secondary;
      if ( target == this.sort_target ){
          this.sort_asc = !this.sort_asc;
      } else {
          this.sort_target = target;
          this.sort_asc = true;
      };
      this.load();
    },

    apply_ordering : function() {
      this.ordering = this.return_ordering();
      this.indicate_ordering();
    },

    return_ordering: function() {
      let secondary = (this.sort_secondary ? ","+this.sort_secondary : "")
      if ( this.sort_asc ){
        return this.sort_target + secondary;
      }
      return "-" + this.sort_target + secondary;
    },


    indicate_ordering : function() {
      let heading = this.sort_target;
      let asc = this.sort_asc;

      $(this.sort_headings).each( function() {
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
  twentyc.rest.Widget
);

/**
 * Special form widget for handling user permissions
 *
 * This expects an element that contains checkboxes for
 * permission flags
 *
 * Each checkbox element should have these attributes set
 *
 * - data-permission-flag unique flag name to describe the permssion level
 *
 * # Example
 *
 * ```html
 * <div data-api-base="/api/user-perms">
 *  <span><input data-permission-flag="c" type="checkbox"> create</span>
 *  <span><input data-permission-flag="r" type="checkbox"> read</span>
 *  <span><input data-permission-flag="u" type="checkbox"> update</span>
 *  <span><input data-permission-flag="d" type="checkbox"> delete</span>
 * </div>
 * ```
 * @class PermissionsForm
 * @extends twentyc.rest.Form
 * @namespace twentyc.rest
 * @constructor
 * @param {jQuery result} jq jquery result holding the element.
 */

twentyc.rest.PermissionsForm = twentyc.cls.extend(
  "PermissionsForm",
  {

    /**
     * Updates the checkboxes states according to the flags
     * provided
     *
     * For example passing `crud` would check all checkboxes
     * while passing `r` would only check the checkbox for read access
     *
     * @method set_flag_values
     * @param {String} flags
     */

    set_flag_values : function(flags) {
      this.element.find('input[data-permission-flag]').each(function() {
        var flag_name = $(this).data("permission-flag")
        if(flag_name.length == 1) {
          var value = (flags.perms.indexOf(flag_name) > -1)
        } else {
          var i, value = true;
          for(i = 0; i < flag_name.length; i++) {
            if(flags.perms.indexOf(flag_name.charAt(i)) == -1)
              value = false;
          }
        }
        $(this).prop("checked", value)
      });
    },

    payload : function() {
      var payload = this.Form_payload();
      payload.permissions = ""
      this.element.find('input[data-permission-flag]').each(function() {
        if($(this).prop("checked"))
          payload.permissions += $(this).data("permission-flag")
      });

      return payload;
    },

    bind : function(jq) {
      this.Widget_bind(jq);
      this.method = jq.data("api-method") || "POST";
      this.element.find('input[data-permission-flag]').on("change", function() {
        this.clear_errors();
        var fn = this[this.method.toLowerCase()].bind(this);
        fn(this.action, this.payload()).then(
          this.post_success.bind(this),
          this.post_failure.bind(this)
        );
      }.bind(this));

    }
  },
  twentyc.rest.Form
);





})(twentyc, jQuery);
