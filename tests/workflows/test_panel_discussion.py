#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import pytest
from unittest.mock import Mock, patch
from pytest import mark

from backend.workflows.panel_discussion import PanelDiscussionWorkflow, PanelState


@mark.workflow
@mark.panel_discussion
class TestWorkflow:
    def test_workflow_behaviours(self):
        inquiry = "How should we improve our company's market position?"
        workflow_instance = PanelDiscussionWorkflow()
        result = workflow_instance.run(inquiry)
        print(result)
        assert result is not None