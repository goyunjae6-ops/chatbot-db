"""Extra offline intents and bounded utilities; never calls an external service."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import random
import re
from basic_knowledge import knowledge_reply, MORE_EXAMPLES
from basic_tools import tool_reply


EXAMPLES = (
    "추가로 이런 질문도 할 수 있어요.\n\n"
    "• 오늘 날짜 / 지금 몇 시야? (한국 시간)\n"
    "• 단위 변환: 2.5 km -> m\n"
    "• 글자수: 안녕하세요 / 단어수: hello world\n"
    "• 골라줘: 김밥, 라면, 샌드위치\n"
    "• 주사위 / 동전 던져줘 / 가위바위보: 가위\n"
    "• 할 일 정리: 빨래, 공부, 산책\n"
    "• 번역: 안녕하세요 / 번역: thank you (등록된 짧은 표현만)\n"
    "• 파이썬 반복문 / 자바스크립트 / HTML / CSS / SQL / Git\n"
    "• 공부 방법 / 면접 준비 / 자기소개 틀 / 이메일 틀\n"
    "• 점심 추천 / 심심해 / 응원해줘 / 수수께끼"
)

# Dimension and scale in base units. Temperature uses a separate affine conversion.
UNITS = {
    'mm': ('length', '0.001'), 'cm': ('length', '0.01'), 'm': ('length', '1'), 'km': ('length', '1000'),
    'mg': ('mass', '0.001'), 'g': ('mass', '1'), 'kg': ('mass', '1000'),
    'ml': ('volume', '0.001'), 'l': ('volume', '1'),
    '초': ('time', '1'), '분': ('time', '60'), '시간': ('time', '3600'),
}
PHRASES = {
    '안녕하세요': 'Hello', '안녕': 'Hi', '감사합니다': 'Thank you', '고마워': 'Thank you',
    '미안합니다': 'I am sorry', '미안해': 'I am sorry', '좋은아침': 'Good morning',
    '잘자': 'Good night', '잘자요': 'Good night', '만나서반가워': 'Nice to meet you',
    'hello': '안녕하세요', 'hi': '안녕', 'thankyou': '감사합니다', 'thanks': '고마워요',
    'sorry': '미안합니다', 'goodmorning': '좋은 아침이에요', 'goodnight': '잘 자요',
    'nicetomeetyou': '만나서 반가워요', 'seeyou': '다음에 만나요',
}

TOPICS = [
    (r'파이썬.*(?:반복문|for문)|python.*(?:loop|for)',
     '파이썬의 for문은 여러 값을 하나씩 처리할 때 사용해요.\n\n```python\nfor number in range(1, 4):\n    print(number)\n```\n\n1, 2, 3을 차례로 출력하는 고정 예제예요.'),
    (r'파이썬.*(?:조건문|if문)',
     '조건문은 조건에 따라 다른 코드를 실행해요.\n\n```python\nscore = 80\nif score >= 60:\n    print("통과")\nelse:\n    print("다시 도전")\n```'),
    (r'파이썬.*함수',
     '함수는 반복해서 사용할 작업에 이름을 붙인 것이에요.\n\n```python\ndef greet(name):\n    return f"안녕하세요, {name}님!"\n\nprint(greet("윤재"))\n```'),
    (r'자바스크립트|javascript|js란',
     '자바스크립트는 웹 페이지에 동작을 넣는 데 널리 쓰이는 언어예요.\n\n```javascript\nconst name = "윤재";\nconsole.log(`안녕하세요, ${name}님!`);\n```\n\n변수 → 조건문 → 반복문 → 함수 → DOM 이벤트 순서로 익혀 보세요.'),
    (r'html',
     'HTML은 웹 페이지의 구조를 표현해요. 제목, 문단, 버튼처럼 내용의 역할을 태그로 나타냅니다.\n\n```html\n<h1>안녕하세요</h1>\n<p>나의 첫 웹 페이지예요.</p>\n<button type="button">클릭</button>\n```'),
    (r'css',
     'CSS는 웹 페이지의 색상, 간격, 크기와 배치를 정해요.\n\n```css\nbutton {\n  background: #315b49;\n  color: white;\n  padding: 12px 20px;\n  border-radius: 8px;\n}\n```'),
    (r'sql|데이터베이스란|db란',
     '데이터베이스는 데이터를 체계적으로 저장하고 찾는 곳이고, SQL은 관계형 데이터베이스에 질의하는 언어예요.\n\n```sql\nSELECT name\nFROM users\nWHERE age >= 20;\n```\n\n이 예제는 users 표에서 age가 20 이상인 행의 name을 조회해요.'),
    (r'git|깃이뭐|버전관리',
     'Git은 파일 변경 이력을 관리하는 도구예요. 저장소에 들어가 다음 명령으로 상태와 차이를 볼 수 있어요.\n\n```bash\ngit status\ngit diff\n```\n\n커밋은 변경 이력을 남기는 작업이고, 푸시는 원격 저장소로 커밋을 보내는 작업이에요.'),
    (r'api란|api가뭐|api설명',
     'API는 프로그램끼리 정해진 방식으로 요청과 응답을 주고받는 접점이에요. 예를 들어 이 화면은 서버에 질문을 보내고, 서버가 돌려준 답변을 표시해요.'),
    (r'프론트엔드|백엔드',
     '프론트엔드는 사용자가 보는 화면과 상호작용을 담당하고, 백엔드는 서버에서 요청 처리와 데이터 저장 같은 일을 맡아요. 이 챗봇은 React 화면과 FastAPI 서버로 구성되어 있어요.'),
    (r'리액트|react',
     'React는 화면을 컴포넌트로 나누어 구성하는 라이브러리예요. props로 데이터를 전달하고, state로 바뀌는 값을 관리해요. 이 설명은 기본 개념 안내이며 임의의 React 코드를 분석하는 기능은 없어요.'),
    (r'에러가나|오류가나|오류해결|에러해결|디버깅',
     '오류를 확인할 때는 이렇게 정리해 보세요.\n\n1. 오류 메시지 전체를 읽어요.\n2. 파일 이름과 줄 번호를 찾아요.\n3. 오류 직전 변경한 부분을 확인해요.\n4. 입력값과 실제 결과를 기록해요.\n5. 가장 작은 예제로 다시 실행해요.\n\n기본 모드에서는 개별 오류의 원인을 자동으로 분석하지는 못해요.'),
    (r'공부방법|공부하는법|학습계획|집중하는법|집중안돼|집중이안돼',
     '작게 시작해 보세요.\n\n1. 오늘 끝낼 목표를 하나 정해요.\n2. 알림을 끄고 25분 동안 한 가지를 해요.\n3. 5분 쉬고, 배운 내용을 자기 말로 적어요.\n4. 마지막 10분은 예제나 문제로 확인해요.\n\n시간은 본인에게 맞게 조절해도 괜찮아요.'),
    (r'면접준비|면접팁|면접잘',
     '면접 준비용 체크리스트예요.\n\n• 지원한 역할과 관련된 경험 2~3개 정리\n• 상황 → 맡은 일 → 행동 → 결과 순서로 설명\n• 프로젝트에서 직접 한 일과 배운 점 구분\n• 모르는 질문은 아는 범위와 확인 방법 설명\n• 마지막에 물어볼 질문 1~2개 준비'),
    (r'자기소개',
     '직접 채워 쓰는 자기소개 틀이에요.\n\n안녕하세요. 저는 [관심 분야]를 공부하는 [이름]입니다.\n[프로젝트/경험]에서 [직접 한 일]을 맡아 [결과/배운 점]을 얻었습니다.\n앞으로 [목표]를 향해 [실천할 일]을 이어가고 싶습니다.\n\n기본 모드는 제공한 내용을 바탕으로 새 글을 작성하지는 못해요.'),
    (r'이메일.*(?:틀|예시|작성)|메일.*(?:틀|예시|작성)',
     '업무 문의 메일에 쓸 수 있는 틀이에요.\n\n제목: [주제] 관련 문의드립니다\n\n안녕하세요, [상대 이름/팀]님.\n저는 [소속/이름]입니다.\n[문의 배경]으로 연락드립니다.\n[구체적인 질문 또는 요청]을 확인해 주실 수 있을까요?\n감사합니다.\n[이름] 드림'),
    (r'점심추천|저녁추천|뭐먹을까|메뉴추천|오늘뭐먹',
     '가볍게 고를 수 있는 메뉴 후보예요.\n\n• 따뜻한 한 끼: 국밥, 우동\n• 간단한 한 끼: 김밥, 샌드위치\n• 채소와 함께: 비빔밥, 샐러드\n\n“골라줘: 김밥, 우동, 비빔밥”처럼 후보를 주면 하나를 무작위로 골라드릴게요. 취향이나 알레르기는 직접 확인해 주세요.'),
    (r'심심해|심심하다|놀아줘',
     '짧게 기분을 바꿔볼까요? “수수께끼”, “주사위”, “동전 던져줘”, “가위바위보: 가위” 중 하나를 골라보세요.'),
    (r'응원해줘|응원좀|힘내라고|자신이없어',
     '지금 당장 완벽하게 하지 않아도 괜찮아요. 오늘 끝낼 수 있는 작은 일 하나만 골라보세요. 시작하고 이어가는 것도 충분히 의미 있는 진전이에요.'),
    (r'힘들어|지쳤어|속상해|우울해|슬퍼',
     '많이 지치셨나 봐요. 잠깐 쉬면서 지금 가장 부담되는 일을 한 문장으로 적어보는 건 어떨까요? 혼자 감당하기 어렵다면 믿을 수 있는 사람에게 이야기해 보세요. 저는 기본 모드라 깊은 상담을 제공하지는 못해요.'),
    (r'수수께끼정답|퀴즈정답', '수수께끼 정답은 “나이”예요. 해마다 먹지만 배가 부르지는 않죠.'),
    (r'수수께끼|퀴즈내줘', '먹어도 먹어도 배가 부르지 않는 것은 무엇일까요?\n\n“수수께끼 정답”이라고 말하면 답을 알려드릴게요.'),
    (r'취미추천|취미뭐', '가볍게 시작할 취미로 산책하며 사진 찍기, 한 페이지 독서, 짧은 일기, 간단한 스케치, 종이접기를 생각해 보세요. 처음에는 10분만 해보는 것도 좋아요.'),
    (r'잘지내|기분이어때|기분어때', '저는 실제 감정을 느끼지는 않지만, 지금 질문에 답할 준비가 되어 있어요. 오늘 하루는 어땠나요?'),
    (r'좋은아침|굿모닝', '좋은 아침이에요! 오늘 해내고 싶은 일 하나를 정해볼까요? “메모: 오늘 할 일”로 남겨도 좋아요.'),
    (r'잘자|굿나잇', '오늘도 수고 많았어요. 편안한 밤 보내세요!'),
]


def extended_reply(text, previous):
    compact = re.sub(r'\s+', '', text.lower()).strip('!?.,~。')
    utility = tool_reply(text)
    if utility is not None:
        return utility
    if compact in ('더알려줘', '예시'):
        followup = knowledge_reply(text, previous)
        if followup is not None:
            return followup
    if compact in ('예시', '질문예시', '다른기능', '기능더보기', '더알려줘'):
        return EXAMPLES + '\n\n' + MORE_EXAMPLES
    if compact in ('오늘날짜', '오늘며칠', '오늘며칠이야', '날짜알려줘', '오늘무슨요일', '오늘무슨요일이야', '지금몇시야', '지금몇시', '현재시간', '시간알려줘'):
        now = datetime.now(timezone(timedelta(hours=9)))
        day = '월화수목금토일'[now.weekday()]
        return f'한국 시간(KST) 기준 {now:%Y년 %m월 %d일} {day}요일 {now:%H시 %M분}이에요. 서버 시계를 기준으로 표시해요.'
    if text.startswith(('글자수:', '글자수：', '글자 수:', '글자 수：', '단어수:', '단어수：', '단어 수:', '단어 수：')):
        label, content = re.split(r'[:：]', text, maxsplit=1)
        if not content.strip():
            return '콜론 뒤에 셀 문장을 넣어 주세요. 예: 글자수: 안녕하세요'
        if label.replace(' ', '') == '단어수':
            return f'공백으로 구분한 단어는 {len(content.split())}개예요.'
        content = content.removeprefix(' ')
        without_spaces = len(re.sub(r'\s', '', content))
        return f'글자 수는 공백 포함 {len(content)}자, 공백 제외 {without_spaces}자예요. 줄바꿈도 공백에 포함하며 이모지는 여러 문자로 셀 수 있어요.'
    if text.startswith(('골라줘:', '골라줘：', '할 일 정리:', '할일 정리:', '할일정리:')):
        label, content = re.split(r'[:：]', text, maxsplit=1)
        items = [item.strip() for item in re.split(r'[,，/\n]', content) if item.strip()]
        if not 2 <= len(items) <= 30:
            return '쉼표로 구분해서 2~30개를 적어 주세요. 예: 골라줘: 김밥, 라면, 우동'
        if label.startswith('골라줘'):
            return f'무작위로 골라봤어요: {random.choice(items)}\n선택을 돕는 추첨이며 후보를 평가한 결과는 아니에요.'
        return '적어주신 순서대로 정리했어요.\n\n' + '\n'.join(f'☐ {item}' for item in items) + '\n\n체크 상태나 알림을 관리하는 기능은 없어요.'
    if text.startswith(('번역:', '번역：')):
        phrase = re.split(r'[:：]', text, maxsplit=1)[1].strip()
        translated = PHRASES.get(re.sub(r'\s+', '', phrase.lower()).strip('!?.'))
        return f'{phrase} → {translated}\n등록된 표현의 기본 번역이에요.' if translated else '등록된 짧은 표현만 번역할 수 있어요. “번역: 안녕하세요”, “번역: thank you”, “번역: good night”를 사용해 보세요.'
    if text.startswith(('단위 변환:', '단위변환:', '변환:')):
        expression = text.split(':', 1)[1].strip().lower()
        match = re.fullmatch(r'(-?\d{1,12}(?:\.\d{1,6})?)\s*([a-z°가-힣]+)\s*(?:->|→|에서)\s*([a-z°가-힣]+)', expression)
        if not match:
            return '예: 단위 변환: 2.5 km -> m\n지원: mm/cm/m/km, mg/g/kg, ml/l, 초/분/시간, c/f(섭씨/화씨)'
        number, source, target = match.groups()
        try:
            value = Decimal(number)
            if source in ('c', '°c') and target in ('f', '°f'):
                result = value * Decimal(9) / Decimal(5) + 32
            elif source in ('f', '°f') and target in ('c', '°c'):
                result = (value - 32) * Decimal(5) / Decimal(9)
            elif source in UNITS and target in UNITS and UNITS[source][0] == UNITS[target][0]:
                result = value * Decimal(UNITS[source][1]) / Decimal(UNITS[target][1])
            else:
                return '같은 종류의 단위끼리만 변환할 수 있어요. 예: km → m, kg → g, 시간 → 분, c → f'
            formatted = format(result, '.10f').rstrip('0').rstrip('.')
            if formatted == '-0':
                formatted = '0'
            return f'{number} {source} = {formatted} {target}\n소수점 이하 최대 10자리로 표시해요.'
        except InvalidOperation:
            return '변환할 숫자를 확인해 주세요.'
    if compact in ('주사위', '주사위던져', '주사위던져줘'):
        return f'주사위 결과는 {random.randint(1, 6)}이에요!'
    if compact in ('동전', '동전던져', '동전던져줘'):
        return f'동전 결과는 {random.choice(["앞면", "뒷면"])}이에요!'
    match = re.fullmatch(r'가위바위보[:：]?(가위|바위|보)', compact)
    if match:
        user = match[1]
        bot = random.choice(['가위', '바위', '보'])
        outcome = '비겼어요!' if user == bot else '사용자가 이겼어요!' if (user, bot) in [('가위', '보'), ('바위', '가위'), ('보', '바위')] else '제가 이겼어요!'
        return f'사용자: {user} / 윤재피티: {bot}\n{outcome}'
    if compact == '가위바위보':
        return '“가위바위보: 가위”처럼 낼 것을 함께 적어 주세요. 가위·바위·보 중 하나를 내면 돼요.'
    knowledge = knowledge_reply(text, previous)
    if knowledge is not None:
        return knowledge
    if compact in ('예제보여줘', '예제', '코드예제') and previous:
        # Only follow a known topic; do not claim open-ended context understanding.
        recent = re.sub(r'\s+', '', previous[-1].lower())
        for pattern, reply in TOPICS[:11]:
            if re.search(pattern, recent):
                return reply
        return '“파이썬 반복문”, “HTML”, “CSS”, “자바스크립트”처럼 주제를 지정해 주세요.'
    for pattern, reply in TOPICS:
        if re.search(pattern, compact):
            return reply
    return None
