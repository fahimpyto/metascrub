import struct
import json

try:
    import cbor2
    HAS_CBOR2 = True
except ImportError:
    HAS_CBOR2 = False


def parse_c2pa(data: bytes) -> dict:
    if len(data) < 12:
        return {}
    boxes = _parse_boxes(data, 0, len(data))
    result = {}
    _extract_c2pa_info(boxes, result)
    return result


def _parse_boxes(data: bytes, offset: int, end: int) -> list:
    boxes = []
    pos = offset
    while pos + 8 <= end:
        size = struct.unpack('>I', data[pos:pos+4])[0]
        box_type = data[pos+4:pos+8]
        if size == 0:
            box_end = end
        else:
            box_end = pos + size
        if box_end > end:
            box_end = end
        box = {
            'type': box_type.decode('latin-1', errors='replace').rstrip(),
            'size': box_end - pos,
        }
        content_start = pos + 8
        content_end = box_end
        content = data[content_start:content_end]
        if box_type == b'jumd' and len(content) >= 18:
            uuid = content[:16]
            p = 16
            if p < len(content):
                type_len = content[p]
                p += 1
                type_str = content[p:p+type_len].decode('utf-8', errors='replace') if type_len > 0 else ''
                p += type_len
                if p < len(content):
                    label_len = content[p]
                    p += 1
                    label = content[p:p+label_len].decode('utf-8', errors='replace') if label_len > 0 else ''
                    p += label_len
            else:
                uuid, type_str, label = b'', '', ''
            box['uuid'] = uuid.hex() if len(uuid) == 16 else uuid.hex()
            box['type_str'] = type_str
            box['label'] = label
            box['content'] = content[p:]
        else:
            box['uuid'] = None
            box['type_str'] = None
            box['label'] = None
            box['content'] = content
        if box_type in (b'jumb ', b'jumb', b'jumb'):
            box['boxes'] = _parse_boxes(content, 0, len(content))
        else:
            box['boxes'] = []
        boxes.append(box)
        pos = box_end
    return boxes


def _extract_c2pa_info(boxes: list, result: dict):
    objects = _collect_data_boxes(boxes)
    for obj in objects:
        if isinstance(obj, dict):
            _merge_c2pa_data(obj, result)


def _collect_data_boxes(boxes: list) -> list:
    found = []
    for box in boxes:
        if box['boxes']:
            found.extend(_collect_data_boxes(box['boxes']))
        content = box['content']
        if not content:
            continue
        # CBOR content (C2PA uses CBOR heavily)
        if HAS_CBOR2 and box['type'] in ('cbor', 'json'):
            try:
                obj = cbor2.loads(content)
                found.append(obj)
            except Exception:
                pass
        # JSON content
        if box['type'] == 'json' and isinstance(content, bytes):
            try:
                obj = json.loads(content.decode('utf-8', errors='replace'))
                found.append(obj)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        # Try raw content as JSON
        if isinstance(content, bytes):
            try:
                decoded = content.decode('utf-8', errors='replace').strip()
                if decoded.startswith('{') and decoded.endswith('}'):
                    obj = json.loads(decoded)
                    found.append(obj)
            except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                pass
    return found


C2PA_TOOL_MAP = {
    'gpt-image': 'ChatGPT (OpenAI)',
    'openai media service': 'ChatGPT / DALL-E (OpenAI)',
    'openai': 'OpenAI',
    'dall-e': 'DALL-E (OpenAI)',
    'dall-e-3': 'DALL-E 3 (OpenAI)',
    'firefly': 'Adobe Firefly',
    'midjourney': 'Midjourney',
    'stable diffusion': 'Stable Diffusion',
    'comfyui': 'ComfyUI',
    'automatic1111': 'Stable Diffusion (A1111)',
}


def _get_agent_name(action: dict) -> str | None:
    agent = action.get('softwareAgent') or action.get('software_agent') or action.get('software_agent_name')
    if isinstance(agent, dict):
        name = agent.get('name') or str(agent)
        if name:
            return str(name)
    if isinstance(agent, str):
        return agent
    return None


def identify_agent_name(c2pa_data: dict) -> str | None:
    actions = c2pa_data.get('actions', [])
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, dict):
                agent = _get_agent_name(action)
                if agent:
                    return agent
    elif isinstance(actions, dict):
        agent = _get_agent_name(actions)
        if agent:
            return agent
    gi = c2pa_data.get('claim_generator_info', {})
    if isinstance(gi, dict):
        name = gi.get('name')
        if name:
            return str(name)
    generator = c2pa_data.get('claim_generator')
    if generator:
        return str(generator)
    return None


def identify_tool_from_c2pa(c2pa_data: dict) -> str | None:
    agent = identify_agent_name(c2pa_data)
    if agent:
        agent_lower = agent.lower()
        for key, label in C2PA_TOOL_MAP.items():
            if key in agent_lower:
                return label
        return agent
    gi = c2pa_data.get('claim_generator_info', {})
    if isinstance(gi, dict):
        gen_name = gi.get('name')
        if gen_name:
            gen_lower = gen_name.lower()
            for key, label in C2PA_TOOL_MAP.items():
                if key in gen_lower:
                    return label
            return gen_name
    return None


def _merge_c2pa_data(obj: dict, result: dict):
    if 'actions' in obj:
        existing = result.get('actions', [])
        if isinstance(existing, list):
            if isinstance(obj['actions'], list):
                result['actions'] = existing + obj['actions']
            else:
                result['actions'] = existing + [obj['actions']]
    if 'claim_generator' in obj and not result.get('claim_generator'):
        result['claim_generator'] = obj['claim_generator']
    if 'claim_generator_info' in obj and not result.get('claim_generator_info'):
        result['claim_generator_info'] = obj['claim_generator_info']
    if 'signature' in obj and not result.get('signature'):
        result['signature'] = str(obj['signature'])[:500]
    if 'software_agent' in obj and not result.get('software_agent'):
        result['software_agent'] = obj['software_agent']
    if 'digital_source_type' in obj and not result.get('digital_source_type'):
        result['digital_source_type'] = obj['digital_source_type']
    if 'instance_id' in obj and not result.get('instance_id'):
        result['instance_id'] = obj['instance_id']
    if 'title' in obj and not result.get('title'):
        result['title'] = obj['title']
    for key in ('credentials', 'certificate', 'ocsp', 'hash', 'exclusions'):
        if key in obj and key not in result:
            result[key] = obj[key]
    for k, v in obj.items():
        if k not in result and not k.startswith('_'):
            if isinstance(v, (str, int, float, bool)):
                result[k] = v


def format_c2pa_summary(c2pa_data: dict) -> str:
    parts = []
    agent = identify_agent_name(c2pa_data)
    tool = identify_tool_from_c2pa(c2pa_data)
    if tool:
        parts.append(f"Tool: {tool}")
    if agent:
        parts.append(f"Agent: {agent}")
    generator = (c2pa_data.get('claim_generator') or
                 c2pa_data.get('claim_generator_info', {}).get('name'))
    if generator:
        parts.append(f"Generator: {generator}")
    actions = c2pa_data.get('actions', [])
    if isinstance(actions, list) and actions:
        action_types = []
        for a in actions:
            if isinstance(a, dict):
                action_types.append(a.get('action', str(a)))
            else:
                action_types.append(str(a))
        parts.append(f"Actions: {', '.join(action_types)}")
    if not parts:
        return "C2PA manifest present"
    return " | ".join(parts)
