# -*- coding: utf-8 -*-

import json

from bes.lims import logger
from bes.lims.reflex import ReflexTestingBaseAdapter
from bes.lims.reflex import utils
from bika.lims.utils.analysis import create_analysis
from senaite.ast.config import IDENTIFICATION_KEY


class CultureInterpretationSubmitAdapter(ReflexTestingBaseAdapter):
    """Adapter in charge of adding the Organisms analysis if the result
    of the culture interpretation is positive
    """

    def __call__(self):
        if not self.is_positive():
            # No growth/Negative, do nothing
            return

        sibling = self.get_siblings(IDENTIFICATION_KEY)
        if sibling:
            # The sample current analysis belongs to already has an Organism
            # Identification analysis set
            return

        # Create a new Organism test
        self.create_organism_identification()

    def get_siblings(self, keyword):
        """Returns the analysis siblings for the given keyword, that belong to
        the same sample as the current analysis
        """
        sample = self.analysis.getRequest()
        analyses = sample.getAnalyses(full_objects=True)
        return filter(lambda an: an.getKeyword() == keyword, analyses)

    def is_positive(self):
        """Returns whether there is culture growth based on the result of the
        Culture Interpretation test
        """
        options = self.analysis.getResultOptions()
        if not options:
            return False

        values = map(lambda opt: str(opt.get("ResultValue", "")), options)
        texts = map(lambda opt: opt.get("ResultText", ""), options)
        flags = map(lambda opt: opt.get("Flag", ""), options)
        values_texts = dict(zip(values, texts))
        values_flags = dict(zip(values, flags))

        # Result might contain a single result option
        result = self.analysis.getResult()
        text_value = values_texts.get(str(result))
        if text_value:
            return values_flags.get(str(result)) == "positive"

        # Result might be a string with multiple options e.g. "['2', '1']"
        try:
            raw_result = json.loads(result)
            for result in raw_result:
                text_value = values_texts.get(str(result))
                if text_value:
                    flag = values_flags.get(str(result))
                    if flag == "positive":
                        return True
        except (ValueError, TypeError):
            pass

        return False

    def create_organism_identification(self):
        """Creates a new Microorganism identification test (senaite.ast) in the
        same samples as the current analysis. The result options of the new
        test are populated with the list (names) of the organisms that are
        available in the system and the control input is set to "multiselect".
        """
        keyword = IDENTIFICATION_KEY
        service = utils.get_service(keyword)
        if not service:
            logger.error("Service '{}' is missing".format(keyword))

        # Make some room for the new identifier
        sample = self.analysis.getRequest()
        new_id = utils.new_analysis_id(sample, keyword)

        # Create the analysis
        new_test = create_analysis(sample, service, id=new_id)
        new_test.setResult("")
        new_test.setResultCaptureDate(None)

        # On occasions the gram stain may be positive (eg Gram negative rods)
        # but nothing will grow. Accommodate "No culture growth obtained"
        no_growth = "No culture growth obtained"

        # Get the organisms vocabulary
        organisms = utils.get_organisms_vocabulary(empty=no_growth)

        # Create and assign the result options
        values_organisms = zip(range(len(organisms)), organisms)
        options = map(self.to_result_option, values_organisms)
        new_test.setResultOptions(options)
        new_test.setResultOptionsType("multiselect")
        new_test.reindexObject()
        return new_test

    def to_result_option(self, value_organism):
        """Converts a tuple of (index, organism_name) to a ResultOption entry
        suitable for Analysis, in which the first element of the tuple is the
        ResultValue and the second is the text to be displayed in widgets
        :param value_organism: tuple of (result value, result text)
        :return: dict {"ResultValue": <value>, "ResultText": <text>}
        """
        return {
            "ResultValue": value_organism[0],
            "ResultText": value_organism[1]
        }
