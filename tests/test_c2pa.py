import struct

from metascrub.c2pa import parse_c2pa, identify_tool_from_c2pa, format_c2pa_summary


def make_cabx_box(data: bytes) -> bytes:
    box_size = struct.pack(">I", 8 + len(data))
    return box_size + b"caBX" + data


class TestParseC2pa:
    def test_empty_input(self):
        result = parse_c2pa(b"")
        assert result == {}

    def test_too_small_input(self):
        result = parse_c2pa(b"\x00" * 5)
        assert result == {}

    def test_empty_cabx(self):
        result = parse_c2pa(make_cabx_box(b""))
        assert isinstance(result, dict)


class TestIdentifyToolFromC2pa:
    def test_chatgpt(self):
        data = {"actions": [{"softwareAgent": "gpt-image"}]}
        result = identify_tool_from_c2pa(data)
        assert result == "ChatGPT (OpenAI)"

    def test_dalle(self):
        data = {"actions": [{"softwareAgent": "dall-e-3"}]}
        result = identify_tool_from_c2pa(data)
        assert result == "DALL-E (OpenAI)"

    def test_midjourney(self):
        data = {"actions": [{"softwareAgent": "Midjourney v6"}]}
        result = identify_tool_from_c2pa(data)
        assert result == "Midjourney"

    def test_adobe_firefly(self):
        result = identify_tool_from_c2pa({"claim_generator": "Adobe Firefly"})
        assert result == "Adobe Firefly"

    def test_unknown_tool(self):
        data = {"actions": [{"softwareAgent": "UnknownTool v1"}]}
        result = identify_tool_from_c2pa(data)
        assert result == "UnknownTool v1"

    def test_no_agent(self):
        result = identify_tool_from_c2pa({})
        assert result is None

    def test_from_actions_list(self):
        data = {"actions": [{"softwareAgent": "gpt-image"}]}
        result = identify_tool_from_c2pa(data)
        assert result == "ChatGPT (OpenAI)"

    def test_from_claim_generator_info(self):
        data = {"claim_generator_info": {"name": "dall-e-3"}}
        result = identify_tool_from_c2pa(data)
        assert result == "DALL-E (OpenAI)"  # dall-e maps to "DALL-E (OpenAI)"


class TestFormatC2paSummary:
    def test_with_known_tool(self):
        data = {"actions": [{"softwareAgent": "gpt-image"}]}
        summary = format_c2pa_summary(data)
        assert "Tool: ChatGPT" in summary

    def test_with_generator(self):
        data = {"claim_generator": "Adobe Firefly"}
        summary = format_c2pa_summary(data)
        assert "Generator: Adobe Firefly" in summary

    def test_with_actions(self):
        data = {"actions": [{"action": "created"}, {"action": "converted"}]}
        summary = format_c2pa_summary(data)
        assert "Actions: created, converted" in summary

    def test_empty(self):
        summary = format_c2pa_summary({})
        assert summary == "C2PA manifest present"
