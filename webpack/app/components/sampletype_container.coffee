### Please use this command to compile this file into the proper folder:
coffee --no-header -w -o ../ -c sampletype_container.coffee
###

###
This controller is in charge of displaying the suitable widget/control for
container selection depending on the selected sample type.
Sample Type content type has the field "ContainerWidget" that allows the user to
define the control to display in Add sample form or sample view depending on the
sample type selected.
If the selected Sample Type has the widget "bottles" selected, the system hides
the "Container" field from the form and displays "Bottles" field instead.
https://github.com/beyondessential/pnghealth.lims/issues/28
###
class SampleTypeContainerController

  constructor: ->
    # Do not load this controller unless required
    return unless @is_required()

    @debug "load"

    @sample_type_selector = "div.uidreferencefield textarea[name^='SampleType']"
    @template_selector = "div.uidreferencefield textarea[name^='Template']"
    @bottle_weights_selector = "input[id^='Bottles-'][id*='-Weight-']"
    @bottle_containers_selector = "input[id^='Bottles-'][id*='-Container-']"

    # Bind the event handler to the elements
    @bind_event_handler()

    # Trigger the "select" event for SampleType to show/Hide Container/Bottles
    if "template-ar_add" in document.body.classList
      for el in document.querySelectorAll @sample_type_selector
        uid = $("##{ el.id }").attr "uid"
        @trigger_event el, "select",
          uids: [uid]
    else
      bottles = document.querySelector("div[data-fieldname='Bottles']")
      if bottles
        el = document.querySelector "input[id='Volume']"
        el.setAttribute("readonly", "readonly")

    return @

  ###
  Returns whether this controller needs to be loaded or not
  ###
  is_required: =>
     targets = ["template-ar_add", "portaltype-analysisrequest"]
     for clazz, i in document.body.classList
       if targets.includes clazz
         return true
     return false

  ###
  Binds callbacks on elements
  Attaches all the events to the body and refine the selector to delegate the
  event: https://learn.jquery.com/events/event-delegation/
  ###
  bind_event_handler: =>
    @debug "bind_event_handler"
    $("body").on "select", @sample_type_selector, @on_sample_type_selected
    $("body").on "select", @template_selector, @on_template_selected
    $("body").on "blur", @bottle_containers_selector, @on_bottle_container_blur
    $("body").on "change", @bottle_weights_selector, @on_bottle_weight_change

  ###
  Trigger a named event
  ###
  trigger_event: (el, event_name, event_data) ->
    # Trigger a custom event
    event = new CustomEvent event_name,
      detail: event_data
      bubbles: yes
    el.dispatchEvent event

  ###
  Event triggered when the value for Sample Template field changes
  Checks for the selection control widget assigned to the Sample Type the
  selected Template is assigned to and hides/display other fields (Bottles,
  Container) accordingly.
  ###
  on_template_selected: (event) =>
    @debug "on_template_selected"
    el = event.currentTarget

    # Get the index of the column (each column represents a Sample)
    idx = @get_sample_index el

    # UID of the Sample Template selected
    uid = el.value
    if not uid
      # Do nothing. Rely on sample type value instead
      return

    # Find-out the sample type assigned to this template
    @fetch uid, []
    .done (data) ->
      if data
        # manually assign the sample type uid to SampleType field
        field_id = "SampleType-#{ idx }"
        sample_type_uid = data["sampletype_uid"]
        window.senaite.core.widgets[field_id].set_values([sample_type_uid])
        # Update the sample container
        @update_container idx, sample_type_uid

  ###
  Event triggered when the weight value of a record from inside the Bottles
  widget is changed. Calculates the sample volume of each bottle as the
  difference between the weight set and the bottle's dry weight
  ###
  on_bottle_weight_change: (event) =>
    @debug "on_bottle_weight_change"
    el = event.currentTarget

    # Get the index of the column (each column represents a Sample)
    sample_idx = @get_sample_index el

    # Recalculate the volume of the bottles and sample
    @calculate_volume sample_idx

  ###
  Event triggered when the container value of a record from inside the Bottles
  widget changes. Calculates the sample volume of each bottle as the difference
  between the weight set and the bottle's dry weight
  ###
  on_bottle_container_blur: (event) =>
    @debug "on_bottle_container_blur"
    el = event.currentTarget

    # Get the index of the column (each column represents a Sample)
    sample_idx = @get_sample_index el

    # Recalculate the volume of the bottles and sample
    @calculate_volume sample_idx

  ###
  Event triggered when the value for Sample Type field changes.
  Checks for the selection control widget assigned to the Sample Type and
  hides/display other fields (Bottles, Container) in accordance
  ###
  on_sample_type_selected: (event) =>
    @debug "on_sample_type_selected"
    el = event.currentTarget

    # Get the index of the column (each column represents a Sample)
    idx = @get_sample_index el

    # Update the container with the selected UID
    @update_container idx, el.value


  ###
  Returns the column/sample index of the Add form for the element passed in
  ###
  get_sample_index: (element) =>
    @debug "get_sample_index:element=#{ element.id }"
    parent = element.closest "td[arnum]"
    if not parent
      return null
    return $(parent).attr "arnum"


  ###
  Updates the type of widget to display as container (traditional Container or
  Bottles) depending on the values set for Sample Type and/or Sample Template
  ###
  update_container: (sample_index, sample_type_uid) =>
    @debug "update_container:sample_index=#{ sample_index },sample_type_uid=#{ sample_type_uid }"

    if not sample_type_uid
      # By default, show Container and hide Bottles
      @toggle_container_visibility sample_index, true
      # Volume field is editable
      @set_volume_readonly sample_index, false

    else
      # Find-out the control to use for this sample type
      field_name = "container_widget"
      @fetch sample_type_uid, field_name
      .done (data) ->
        show_container = false
        if data
          show_container = data[field_name] == "container"

        # Toggle the visibility of Container field vs Bottles field
        @toggle_container_visibility sample_index, show_container

        # Enable/Disable Volume depending on the visibility of Container
        @set_volume_readonly sample_index, not show_container

        if not show_container
          # Volume field is calculated automatically
          @calculate_volume sample_index


  ###
  Sets the visibility of both the "Container" field and the "Bottles" field
  Displays the "Container" and hides the "Bottles" if true
  ###
  toggle_container_visibility: (sample_index, show_container) =>
    @debug "toggle_container_visibility:sample_index=#{ sample_index },show_container=#{ show_container }"
    @set_visible "Container", sample_index, show_container
    @set_visible "Bottles", sample_index, not show_container


  ###
  Sets the readonly mode of the Volume field
  ###
  set_volume_readonly: (sample_index, readonly) =>
    @debug "set_volume_readonly:sample_index=#{ sample_index },readonly=#{ readonly }"
    selector = "#Volume"
    if sample_index
      selector = "#Volume-#{ sample_index }"
    el = document.querySelector selector
    return unless el
    if readonly
      el.setAttribute "readonly", "readonly"
    else
      el.removeAttribute "readonly"

  ###
  Calculates the volumes of each bottle and the total volume of the sample
  ###
  calculate_volume: (sample_index) =>
    @debug "calculate_volume:sample_index=#{ sample_index }"
    total_volume = 0

    # Walk-through all record rows from Bottles Widget
    selector = "tr.records_row_Bottles"
    if sample_index
      selector = "tr.records_row_Bottles-#{ sample_index }"

    elements = document.querySelectorAll selector
    that = @
    $.each elements, (index, el) ->
      # Calculate the weight and dry weight of the bottle
      weight_selector = "#Bottles-Weight-#{ index }"
      if sample_index
        weight_selector = "#Bottles-#{ sample_index }-Weight-#{ index }"

      weight = el.querySelector weight_selector
      weight = that.get_float_value weight
      that.debug "Not a valid volume: #{ weight }"

      dry_weight_selector = "#Bottles-DryWeight-#{ index }"
      if sample_index
        dry_weight_selector = "#Bottles-#{ sample_index }-DryWeight-#{ index }"

      dry_weight = el.querySelector dry_weight_selector
      dry_weight = that.get_float_value dry_weight
      that.debug "Not a valid volume: #{ dry_weight }"

      # Calculate the weight difference
      vol = weight - dry_weight

      # XXX What to do if volume <= 0 ?
      if vol <= 0
        that.debug "Not a valid bottle volume: #{ vol }"
        vol = ""
      else
        # Multiply the difference of weights by 1.05 to get the mL
        vol = that.round vol * 1.05, 3
        total_volume = total_volume + vol

      volume_selector = "#Bottles-Volume-#{ index }"
      if sample_index
        volume_selector = "#Bottles-#{ sample_index }-Volume-#{ index }"

      volume = el.querySelector volume_selector
      volume.value = vol

    total_volume = parseFloat total_volume
    total_volume = @round total_volume, 4
    if total_volume <= 0
      @debug "Not a valid volume: #{ total_volume }"
      total_volume = ""
    else
      total_volume += " ml"

    # Update the total volume
    volume_selector = "#Volume"
    if sample_index
      volume_selector = "#Volume-#{ sample_index }"
    volume = document.querySelector volume_selector
    return unless volume
    volume.value = total_volume


  ###
  Returns the value of the element passed-in as a float number
  ###
  get_float_value: (el, default_value=0) =>
    val = parseFloat el.value
    if isNaN val
      val = parseFloat default_value
    return val

  ###
  Rounds a number to the given decimals number
  ###
  round: (value, decimals=2) =>
    return Number(Math.round(value+'e'+decimals)+'e-'+decimals)


  ###
  Sets the visibility of the field with the given name
  ###
  set_visible: (field_name, sample_index, visible) =>
    @debug "set_visible:field_name=#{ field_name },sample_index=#{ sample_index },visible=#{ visible }"

    # Default field selector
    selector = "div[data-fieldname='#{ field_name }']"
    if sample_index
      selector = "div[data-fieldname='#{ field_name }-#{ sample_index }']"

    # If there is only one sample (column), just hide/show the whole row
    if sample_index == "0"
      cols_num = document.querySelector "#ar_count"
      if cols_num.value == "1"
        selector = "tr[fieldname=#{ field_name }]"

    el = document.querySelector selector
    if visible
      $(el).show()
    else
      $(el).hide()


  ###
  Fetches the object with the UID passed-in
  ###
  fetch: (uid, field_names) =>
    @debug "fetch:uid=#{ uid },field_names=#{ field_names }"
    deferred = $.Deferred()
    options =
      url: @get_portal_url() + "/@@API/read"
      data:
        catalog_name: "senaite_catalog_setup"
        UID: uid
        include_fields: field_names
        page_size: 1

    @ajax_submit options
    .done (data) ->
      object = {}
      if data.objects
        # resolve with the first item of the list
        object = data.objects[0]
      return deferred.resolveWith this, [object]

    deferred.promise()


  ###
  Ajax Submit with automatic event triggering and some sane defaults
  ###
  ajax_submit: (options={}) =>
    @debug "ajax_submit"

    # some sane option defaults
    options.type ?= "POST"
    options.url ?= @get_portal_url()
    options.context ?= this
    options.dataType ?= "json"
    options.data ?= {}
    options._authenticator ?= $("input[name='_authenticator']").val()

    @debug ">>> ajax_submit::options=", options

    $(this).trigger "ajax:submit:start"
    done = ->
      $(this).trigger "ajax:submit:end"
    return $.ajax(options).done done

  ###
  Returns the portal url (calculated in code)
  ###
  get_portal_url: =>
    url = $("input[name=portal_url]").val()
    return url or window.portal_url

  ###
  Prints a debug message in console with this component name prefixed
  ###
  debug: (message) =>
    console.debug "[bes.lims]", "SampleTypeController::"+message

  ###
  Returns the AnalysisRequestAdd controller
  ###
  get_add_controller: =>
    return window.bika.lims.AnalysisRequestAdd

export default SampleTypeContainerController
