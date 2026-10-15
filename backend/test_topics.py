import unittest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from basic_bot import basic_reply

class ExtraReplyTests(unittest.TestCase):
    def ask(self,*texts):
        return basic_reply([{'role':'user','content':s} for s in texts])

    def test_expanded_help(self):
        answer=self.ask('도움말')
        for example in ['단위 변환','글자수','면접','가위바위보']:
            self.assertIn(example,answer)

    def test_length_and_word_counts(self):
        self.assertIn('공백 포함 5자, 공백 제외 4자',self.ask('글자수: 안녕 세계'))
        self.assertIn('3개',self.ask('단어수: one  two\nthree'))
        self.assertIn('콜론 뒤',self.ask('글자수:   '))

    def test_unit_conversions(self):
        for text,expected in [('2.5 km -> m','2500'),('2 kg -> g','2000'),('90 분 -> 시간','1.5'),('32 f -> c','0'),('0 c -> f','32'),('500 ml -> l','0.5')]:
            with self.subTest(text=text):
                answer=self.ask('단위 변환: '+text)
                self.assertEqual(answer.split(' = ')[1].split()[0],expected)

    def test_invalid_units(self):
        self.assertIn('같은 종류',self.ask('단위 변환: 1 kg -> km'))
        self.assertIn('지원:',self.ask('단위 변환: 무슨 단위'))
        self.assertIn('지원:',self.ask('단위 변환: 1e999 kg -> g'))

    def test_choice_and_checklist(self):
        with patch('basic_topics.random.choice',return_value='김밥'):
            self.assertIn('김밥',self.ask('골라줘: 김밥, 우동'))
        self.assertIn('2~30개',self.ask('골라줘: 김밥'))
        answer=self.ask('할 일 정리: 빨래, 공부, 산책')
        self.assertEqual(answer.count('☐'),3)
        self.assertIn('적어주신 순서',answer)

    def test_registered_translations_only(self):
        self.assertIn('Hello',self.ask('번역: 안녕하세요'))
        self.assertIn('감사합니다',self.ask('번역: Thank you!'))
        self.assertIn('등록된 짧은 표현만',self.ask('번역: arbitrary sentence'))

    def test_games(self):
        with patch('basic_topics.random.randint',return_value=4):
            self.assertIn('4',self.ask('주사위 던져줘'))
        with patch('basic_topics.random.choice',return_value='보'):
            self.assertIn('사용자가 이겼어요',self.ask('가위바위보: 가위'))
        with patch('basic_topics.random.choice',return_value='가위'):
            self.assertIn('비겼어요',self.ask('가위바위보: 가위'))
        with patch('basic_topics.random.choice',return_value='바위'):
            self.assertIn('제가 이겼어요',self.ask('가위바위보: 가위'))
        self.assertIn('함께 적어',self.ask('가위바위보'))

    def test_korea_time_uses_server_clock(self):
        fake=datetime(2026,10,15,18,30,tzinfo=timezone(timedelta(hours=9)))
        with patch('basic_topics.datetime') as clock:
            clock.now.return_value=fake
            reply=self.ask('지금 몇 시야?')
            self.assertIn('2026년 10월 15일 목요일 18시 30분',reply)
            self.assertIn('KST',reply)

    def test_programming_topics(self):
        for question,expected in [('파이썬 반복문','for number'),('파이썬 조건문','score'),('파이썬 함수','def greet'),('자바스크립트','console.log'),('HTML','<h1>'),('CSS','background:'),('SQL','SELECT'),('Git','git status'),('API가 뭐야','프로그램끼리')]:
            with self.subTest(question=question): self.assertIn(expected,self.ask(question))

    def test_known_topic_followup(self):
        self.assertIn('background:',self.ask('CSS 알려줘','예제 보여줘'))
        self.assertIn('주제를 지정',self.ask('모르는 주제','예제 보여줘'))

    def test_daily_and_writing_templates(self):
        for question,expected in [('면접 준비','체크리스트'),('자기소개','[이름]'),('이메일 작성 틀','제목:'),('공부 방법','25분'),('심심해','수수께끼'),('응원해줘','작은 일'),('점심 추천','무작위'),('수수께끼 정답','나이')]:
            with self.subTest(question=question): self.assertIn(expected,self.ask(question))

    def test_memory_still_takes_priority(self):
        self.assertIn('메모를 남겼어요',self.ask('메모: HTML 공부'))
        self.assertIn('1. HTML 공부',self.ask('메모: HTML 공부','메모 보여줘'))
        self.assertIn('이 질문에 맞는 답을 만들 수는 없어요',self.ask('내일 날씨 알려줘'))
