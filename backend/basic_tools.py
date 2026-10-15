"""Bounded text, date and arithmetic utilities for the offline chatbot."""
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re

NUMBER = r'-?\d{1,12}(?:\.\d{1,6})?'


def display(value):
    result = format(value, '.8f').rstrip('0').rstrip('.')
    return '0' if result == '-0' else result


def numbers(text):
    parts = [x.strip() for x in re.split(r'[,，\s]+', text) if x.strip()]
    if not 1 <= len(parts) <= 100 or any(not re.fullmatch(NUMBER, x) for x in parts):
        raise ValueError('Invalid number list')
    return [Decimal(x) for x in parts]


def template(text, kind):
    # Only interpolate user-provided fields; never invent credentials or experience.
    values = {}
    for field in re.split(r'[;；\n]', text):
        if '=' not in field:
            continue
        key, value = field.split('=', 1)
        values[key.strip()] = value.strip()[:500]
    if kind == '자기소개':
        if not values.get('이름') or not values.get('분야'):
            return '예: 자기소개 작성: 이름=윤재; 분야=웹 개발; 경험=챗봇 제작; 목표=개발자\n이름과 분야는 필수예요. 제공한 정보만 고정 문장 틀에 넣어요.'
        lines = [f'안녕하세요. 저는 {values["분야"]}에 관심을 두고 있는 {values["이름"]}입니다.']
        if values.get('경험'):
            lines.append(f'관련 경험으로는 {values["경험"]}이 있습니다.')
        if values.get('목표'):
            lines.append(f'앞으로의 목표는 {values["목표"]}입니다.')
        return '\n'.join(lines) + '\n\n입력한 정보로 채운 기본 초안이에요. 표현과 사실관계를 확인해 주세요.'
    if not values.get('주제') or not values.get('내용'):
        return '예: 이메일 작성: 받는사람=담당자; 주제=일정 문의; 내용=면접 일정을 확인하고 싶습니다\n주제와 내용은 필수예요. 메일을 실제로 보내지는 않아요.'
    recipient = values.get('받는사람', '담당자')
    sender = values.get('보내는사람', '[이름]')
    return f'제목: {values["주제"]}\n\n안녕하세요, {recipient}님.\n\n{values["내용"]}\n\n확인해 주시면 감사하겠습니다.\n{sender} 드림\n\n입력한 내용을 고정 형식에 넣은 초안이며 실제로 발송하지 않았어요.'


def tool_reply(text):
    percent = re.fullmatch(fr'({NUMBER})\s*의\s*({NUMBER})\s*%\s*(?:는|가)?\s*(?:얼마(?:야|예요|인가요)?|계산해줘)?[?？.!]*', text)
    if percent:
        return tool_reply(f'퍼센트: {percent[1]}의 {percent[2]}%')
    discount = re.fullmatch(fr'({NUMBER})\s*원?\s*(?:에서|을|를)?\s*({NUMBER})\s*%\s*할인(?:하면|한)?\s*(?:얼마(?:야|예요|인가요)?)?[?？.!]*', text)
    if discount:
        return tool_reply(f'할인: {discount[1]}, {discount[2]}%')
    # Natural date additions are normalized to the same explicit command grammar.
    natural = re.fullmatch(r'(\d{4}-\d{2}-\d{2})\s*(?:에서|부터)?\s*(-?\d{1,5})일\s*(뒤|후|전)(?:는|이야|알려줘|가언제야)?[?？]?', text.replace(' ', ''))
    if natural:
        origin, days, direction = natural.groups()
        count = int(days) * (-1 if direction == '전' else 1)
        return tool_reply(f'날짜 더하기: {origin}, {count}')
    match = re.match(r'^(자기소개\s*작성|이메일\s*작성|메일\s*작성)\s*[:：]\s*(.*)$', text, re.S)
    if match:
        return template(match[2], '자기소개' if match[1].startswith('자기') else '이메일')
    match = re.match(r'^(퍼센트|할인|평균|합계|최댓값|최솟값|정렬|중복\s*제거|목록\s*정리|대문자로|소문자로|날짜\s*차이|날짜\s*더하기)\s*[:：]\s*(.*)$', text, re.S)
    if not match:
        return None
    command = re.sub(r'\s+', '', match[1])
    content = match[2].strip()
    if not content:
        return '콜론 뒤에 처리할 값을 적어 주세요. “질문 예시”에서 입력 형식을 볼 수 있어요.'
    if command in ('대문자로', '소문자로'):
        return content.upper() if command == '대문자로' else content.lower()
    if command in ('중복제거', '목록정리'):
        items = [x.strip() for x in re.split(r'[,，\n]', content) if x.strip()]
        if not 1 <= len(items) <= 100:
            return '쉼표나 줄바꿈으로 구분해서 1~100개를 적어 주세요.'
        if command == '중복제거':
            items = list(dict.fromkeys(items))
        return '\n'.join(f'{index}. {item}' for index, item in enumerate(items, 1))
    if command in ('날짜차이', '날짜더하기'):
        parts = [x.strip() for x in content.split(',')]
        try:
            if len(parts) != 2 or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', parts[0]):
                raise ValueError
            origin = date.fromisoformat(parts[0])
            if command == '날짜차이':
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', parts[1]):
                    raise ValueError
                target = date.fromisoformat(parts[1])
                diff = (target - origin).days
                direction = '뒤' if diff >= 0 else '전'
                return f'{target.isoformat()}은 {origin.isoformat()}에서 {abs(diff)}일 {direction}예요. 시작일을 포함하지 않은 날짜 간격이에요.'
            if not re.fullmatch(r'-?\d{1,5}', parts[1]):
                raise ValueError
            target = origin + timedelta(days=int(parts[1]))
            return f'{origin.isoformat()}에 {int(parts[1])}일을 더하면 {target.isoformat()}이에요.'
        except (ValueError, OverflowError):
            return '실제 존재하는 날짜를 YYYY-MM-DD로 적어 주세요. 예: 날짜 차이: 2026-10-15, 2026-12-25 / 날짜 더하기: 2026-10-15, 7'
    if command in ('퍼센트', '할인'):
        expression = re.fullmatch(fr'({NUMBER})\s*(?:의|,)\s*({NUMBER})\s*%', content)
        if not expression:
            return '예: 퍼센트: 200의 15% / 할인: 50000, 20%\n숫자 안의 천 단위 쉼표는 빼고 입력해 주세요.'
        value, rate = map(Decimal, expression.groups())
        portion = value * rate / 100
        if command == '퍼센트':
            return f'{display(value)}의 {display(rate)}%는 {display(portion)}이에요.'
        if value < 0 or not 0 <= rate <= 100:
            return '금액은 0 이상, 할인율은 0~100%로 입력해 주세요.'
        return f'할인액: {display(portion)}\n할인 후 금액: {display(value - portion)}\n입력한 숫자로만 계산했으며 세금·배송비 등은 포함하지 않았어요.'
    try:
        values = numbers(content)
        if command == '정렬':
            return '오름차순: ' + ', '.join(display(x) for x in sorted(values))
        total = sum(values, Decimal(0))
        result = {'평균': lambda: total / len(values), '합계': lambda: total,
                  '최댓값': lambda: max(values), '최솟값': lambda: min(values)}[command]()
        return f'{command}: {display(result)}\n숫자 {len(values)}개로 계산했어요. 소수점 이하 최대 8자리로 표시해요.'
    except (ValueError, InvalidOperation):
        return '숫자를 쉼표나 공백으로 구분해 1~100개 입력해 주세요. 예: 평균: 10, 20, 30'
