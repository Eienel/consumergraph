from __future__ import annotations

import pytest

from scripts.verify_live_datahub import contains_entity, tool_payload, verify_document_readback


URN = "urn:li:document:changesafe-decision"


class ReadbackClient:
    def __init__(self, payloads):
        self.payloads = iter(payloads)
        self.calls = 0

    def call_tool(self, name, arguments):
        self.calls += 1
        assert name == "get_entities"
        assert arguments == {"urns": [URN]}
        return next(self.payloads)


def test_tool_payload_and_entity_detection_support_official_mcp_wrapper():
    result = {"structuredContent": {"entities": [{"urn": URN, "type": "DOCUMENT"}]}}
    payload = tool_payload(result)
    assert contains_entity(payload, URN)


def test_entity_detection_supports_datahub_oss_result_wrapper():
    payload = {"result": [{"urn": URN}]}
    assert contains_entity(payload, URN)


def test_tool_payload_falls_back_to_text_content():
    result = {"content": [{"type": "text", "text": f'[{chr(123)}"urn": "{URN}"{chr(125)}]'}]}
    assert contains_entity(tool_payload(result), URN)


def test_readback_retries_without_sleeping_in_test():
    client = ReadbackClient(
        [
            {"structuredContent": {"entities": []}},
            {"structuredContent": {"entities": [{"urn": URN}]}},
        ]
    )
    proof = verify_document_readback(client, URN, attempts=2, delay_seconds=0)
    assert proof == {"success": True, "urn": URN, "attempts": 2}
    assert client.calls == 2


def test_readback_failure_is_not_a_false_green():
    client = ReadbackClient([{"structuredContent": {"entities": []}}])
    with pytest.raises(RuntimeError, match="could not be read back"):
        verify_document_readback(client, URN, attempts=1, delay_seconds=0)
