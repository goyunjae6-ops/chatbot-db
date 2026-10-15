"""Deterministic, offline replies. No model, network, eval, or paid API."""
import ast
import operator
import re
from basic_topics import EXAMPLES, extended_reply
from basic_knowledge import MORE_EXAMPLES

HELP = ("지금은 무료 기본 답변 모드예요. 외부 AI 없이 코드로 답하고 있어요.\n\n"
        "이렇게 말해 보세요.\n"
        "• 안녕 / 뭐 할 수 있어?\n"
        "• 계산: (12 + 8) * 3\n"
        "• 내 이름은 윤재 / 내 이름이 뭐야?\n"
        "• 메모: 내일 오후 3시 회의 / 메모 보여줘\n"
        "• 파이썬 공부 방법 / 챗봇 사용법\n\n"
        "자유로운 글 생성, 실시간 정보 조회, 복잡한 질문의 추론은 지원하지 않아요. "
        "이름과 메모는 현재 대화의 최근 기록 안에서만 참고해요.")
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod}
NAME = re.compile(r"^(?:내\s*이름은|제\s*이름은)\s*([가-힣a-zA-Z][가-힣a-zA-Z ]{0,29}?)(?:이야|입니다|이에요|예요|야)?[.!。 ]*$")
MEMO = re.compile(r"^(?:메모|기억해\s*줘|기억해줘)\s*[:：]\s*(.+)$", re.S)


def calculate(expression):
    if len(expression) > 150:
        raise ValueError("Expression too long")
    tree = ast.parse(expression.strip(), mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 80:
        raise ValueError("Expression too complex")

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in OPS:
            value = OPS[type(node.op)](visit(node.left), visit(node.right))
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand) * (-1 if isinstance(node.op, ast.USub) else 1)
        else:
            raise ValueError("Unsupported expression")
        if abs(value) > 10**15 or value != value:
            raise ValueError("Result out of range")
        return value

    value = visit(tree.body)
    return format(value, '.12g') if isinstance(value, float) else str(value)


def basic_reply(history):
    users = [m['content'].strip() for m in history if m.get('role') == 'user']
    text = users[-1] if users else ''
    lower = text.lower()
    compact = re.sub(r'\s+', '', lower).strip('!?.,~。')
    if compact in ('도움말','도움','뭐할수있어','무엇을할수있어','기능','help','사용법'):
        return HELP + '\n\n' + EXAMPLES + '\n\n' + MORE_EXAMPLES
    if compact in ('안녕','안녕하세요','안녕하세요윤재피티','윤재피티안녕','반가워','반갑습니다','하이','hi','hello','안뇽','ㅎㅇ'):
        return '안녕하세요! 저는 윤재피티예요. 지금은 코드로 동작하는 기본 답변 모드예요. 간단한 계산이나 메모부터 해볼까요?'
    if any(word in compact for word in ('내이름이뭐','제이름이뭐','내이름기억','내이름알아')):
        for previous in reversed(users[:-1]):
            match = NAME.fullmatch(previous)
            if match:
                return f'이 대화에서 알려주신 이름은 {match[1].strip()}님이에요.'
        return '아직 이 대화의 최근 기록에서 이름을 찾지 못했어요. “내 이름은 윤재”처럼 알려주세요.'
    match = NAME.fullmatch(text)
    if match:
        return f'반가워요, {match[1].strip()}님! 이 대화의 최근 기록에서 이름을 참고할게요.'
    if compact in ('메모보여줘','메모목록','메모알려줘','기억한내용','저장한메모'):
        notes = [match[1].strip() for previous in users[:-1] if (match := MEMO.fullmatch(previous))]
        if notes:
            return '현재 대화의 최근 기록에 있는 메모예요.\n\n' + '\n'.join(f'{i}. {note}' for i, note in enumerate(notes, 1))
        return '아직 최근 대화 기록에 메모가 없어요. “메모: 내일 오후 3시 회의”처럼 입력해 주세요.'
    match = MEMO.fullmatch(text)
    if match:
        return '이 대화에 메모를 남겼어요.\n\n' + match[1].strip() + '\n\n“메모 보여줘”로 최근 기록의 메모를 확인할 수 있어요. 알림을 보내는 기능은 없어요.'
    extra = extended_reply(text, users[:-1])
    if extra is not None:
        return extra
    expression = re.sub(r'^(?:계산(?:해\s*줘)?|계산기)\s*[:：]?\s*', '', text)
    looks_like_math = bool(re.fullmatch(r'[\d\s.+\-*/%()×÷=]+', expression)) and bool(re.search(r'\d', expression))
    if text.startswith(('계산', '계산기')) or looks_like_math:
        expression = expression.rstrip('= ').replace('×','*').replace('÷','/')
        try:
            return f'{expression} = {calculate(expression)}'
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError, RecursionError):
            return '이 계산은 처리할 수 없어요. 숫자, 괄호와 +, -, *, /, //, %만 사용해 주세요. 0으로 나누거나 너무 큰 수는 계산할 수 없어요.'
    if '파이썬' in text or 'python' in lower:
        return '파이썬 입문은 변수 → 조건문 → 반복문 → 함수 순서로 연습해 보세요. 아래는 이름을 입력받는 예제예요.\n\n```python\nname = input("이름을 입력하세요: ")\nprint(f"안녕하세요, {name}님!")\n```\n\n기본 모드는 정해진 예제를 안내하며, 임의의 코드를 실행하거나 분석하지는 않아요.'
    if '사용법' in text or '챗봇' in text or compact in ('너누구야','넌누구야','누구세요'):
        return HELP + '\n\nEnter로 전송하고 Shift + Enter로 줄바꿈할 수 있어요. 대화 목록에서는 검색·제목 변경·삭제를 할 수 있어요.'
    if compact in ('고마워','감사합니다','고맙습니다','땡큐','thanks','thankyou'):
        return '도움이 됐다니 다행이에요! 계산이나 메모가 필요하면 말씀해 주세요.'
    if compact in ('잘가','안녕히가세요','다음에봐','bye'):
        return '다음에 또 만나요! 이 대화는 대화 목록에서 다시 열 수 있어요.'
    return '지금은 정해진 기능만 처리하는 기본 답변 모드라서 이 질문에 맞는 답을 만들 수는 없어요.\n\n“도움말”, “계산: 25 * 4”, “내 이름은 윤재”, “메모: 할 일” 중 하나로 시작해 보세요.'
