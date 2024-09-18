### Please use this command to compile this file into the proper folder:
coffee --no-header -w -o ../ -c sampleview_layout.coffee
###

###
This controller makes possible to collapse and expand sections from sample view
and keep the configuration stored in a cookie. This prevents the user to have to
constantly scroll as they enter and verify results.
https://github.com/beyondessential/pnghealth.lims/issues/163
###
class SampleViewLayoutController

  constructor: ->
    # Do not load this controller unless required
    return unless @is_required()

    @debug "load"

    # List of [anchor_selector, section_selector, section_id]
    sections = [

      ["#content h1",
       "#senaite-sampleheader",
       "palau-lims-sample-header"],

      ["#content h1",
       "div[id=ar-attachments]",
       "palau-lims-sample-header"],

      ["div.remarks-widget h3",
       "div.remarks-widget div",
       "palau-lims-sample-remarks-section"],

      ["div.analysis-listing-table h3",
       "div.analysis-listing-table form",
       "palau-lims-sample-analyses-section"],

      ["div[id=results-interpretation] h3",
       "div[id=results-interpretation] form",
       "palau-lims-sample-results-interpretation-section"],
    ]

    # Initializes toggle sections
    for section in sections
      @init_toggle section[0], section[1], section[2]

    # Bind the event handler to the elements
    $("body").on "click", ".toggle_selector", @on_toggle_selector_clicked

    # Show/Hide sections depending on the cookie value(s)
    @init_sections_visibility()

    return @

  ###
  Returns whether this controller needs to be loaded or not
  ###
  is_required: =>
     targets = ["portaltype-analysisrequest"]
     for clazz, i in document.body.classList
       if targets.includes clazz
         return true
     return false

  ###
  Event triggered when a toggle selector is clicked. Toggles the visibility of
  the section associated to the toggle selector and stores the visibility into
  a cookie
  ###
  on_toggle_selector_clicked: (event) =>
    @debug "on_toggle_selector_clicked"
    el = event.currentTarget

    section_id = el.getAttribute "target-section"
    sections = document.querySelectorAll "[section=#{ section_id }]"
    for section in sections
      if not section
        continue
      visible = @is_visible(section)
      if visible
        $(section).hide()
      else
        $(section).show()

    site.set_cookie section_id, not visible

  ###
  Initializes a toggle selector
  ###
  init_toggle: (anchor_selector, section_selector, section_id) =>
    @debug "init_toggle:anchor_selector='#{ anchor_selector }',section_selector='#{ section_selector }',section_id='#{ section_id }'"
    anchor = document.querySelector anchor_selector
    return unless anchor
    anchor.classList.add "toggle_selector"
    anchor.setAttribute "target-section", section_id
    section = document.querySelector section_selector
    return unless section
    section.setAttribute "section", section_id

  ###
  Returns whether the element is visible or not
  ###
  is_visible: (element) ->
    if $(element).css("display") is "none"
      return no
    return yes

  ###
  Sets the visibility of sample sections based on the configuration stored in
  cookies
  ###
  init_sections_visibility: =>
    @debug "set_visibility"
    selector = ".toggle_selector"

    anchors = document.querySelectorAll ".toggle_selector"
    for anchor in anchors
      section_id = anchor.getAttribute "target-section"
      visible = site.read_cookie(section_id) or "true"
      @debug "section_id=#{ section_id }, visible=#{ visible }"
      visible = visible == "true"
      sections = document.querySelectorAll "[section=#{ section_id }]"
      for section in sections
        if visible
          $(section).show()
        else
          $(section).hide()

  ###
  Prints a debug message in console with this component name prefixed
  ###
  debug: (message) =>
    console.debug "[palau.lims]", "SampleViewLayoutController::"+message

export default SampleViewLayoutController
