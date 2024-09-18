import SampleTypeContainerController from "./components/sampletype_container.coffee"
import SampleViewLayoutController from "./components/sampleview_layout.coffee"


###* DOCUMENT READY ENTRY POINT ###
document.addEventListener "DOMContentLoaded", ->
  console.debug "*** BES LIMS JS LOADED ***"

  # Initialize controllers
  window.sampletype_container = new SampleTypeContainerController
  window.sampleview_layout = new SampleViewLayoutController
